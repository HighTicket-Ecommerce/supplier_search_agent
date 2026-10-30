"""One bounded discovery preview with an immutable round and private source captures."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_actor_value(value):
    """Retain raw content, excluding credentials and transport headers/cookies."""
    private = {"headers", "requestheaders", "responseheaders", "authorization", "proxyauthorization",
               "token", "apikey", "apifytoken", "password", "cookies", "cookie", "setcookie"}
    if isinstance(value, dict):
        return {key: capture_actor_value(item) for key, item in value.items()
                if re.sub(r"[^a-z]", "", key.casefold()) not in private}
    if isinstance(value, list):
        return [capture_actor_value(item) for item in value]
    return value


def trace_actor(original, records, save, filename):
    def traced(actor, run_input, context, **kwargs):
        entry = {"actor": actor, "input": capture_actor_value(run_input), "status": "started"}
        records.append(entry)
        save(filename, records)
        operation_start = len(context.operations)
        try:
            items = original(actor, run_input, context, **kwargs)
            # Capture at the actor boundary, before parsing, truncation or rejection.
            entry.update(status="returned", items=capture_actor_value(items))
            return items
        except Exception as exc:
            entry.update(status="error", error_type=type(exc).__name__)
            raise
        finally:
            entry["actor_runs"] = [{key: operation[key] for key in ("run_id", "dataset_id", "status") if key in operation}
                                   for operation in context.operations[operation_start:]]
            save(filename, records)
    return traced


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    parser.add_argument("--master-reference-id", required=True)
    args = parser.parse_args()
    if not args.round or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.round):
        parser.error("Round names use letters, digits, hyphens and underscores")

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    output = ROOT / "var/eval/cold-plunge-discovery-2026-10-28" / args.round
    os.environ["SUPPLIER_JOB_DB"] = str(output / "jobs.sqlite")
    from backend import apify_runner, research_runner, supplier_validator, web_fetcher
    from backend.job_store import get_job, init_job
    from backend.master_index import load_reference, reference_directory
    from backend.models import ResearchRequest
    from backend.config import model_settings_snapshot
    reference = load_reference(args.master_reference_id)
    master_path = reference_directory() / (args.master_reference_id + ".json")
    request = ResearchRequest(product="Complete cold plunge systems", candidate_urls=[],
        allowed_countries=["United States", "Canada"], allowed_supplier_types=["Manufacturer", "Brand owner"],
        excluded_products=["replacement filters", "assembly services", "chillers sold without a tub",
                           "inflatable tubs without a chiller", "sauna heaters", "hot tubs"],
        use_apify=True, use_shopping=False, preview_only=True, use_shopify_catalogue=False,
        allow_browser_fallback=False, master_reference_id=args.master_reference_id,
        target_suppliers=3, max_candidate_domains=3, max_pages=9, max_pages_per_supplier=3,
        max_runtime_seconds=600, max_external_calls=15, max_execution_cost_usd=6,
        max_actor_charge_usd=0.5)
    sources = sorted((ROOT / "backend").glob("*.py")) + [Path(__file__).resolve(), Path(__file__).with_name("brief.md")]
    manifest = {"started_at": time.time(), "settings": request.model_dump(), "model_settings": model_settings_snapshot(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "master_sha256": digest(master_path), "master_record_count": reference["record_count"],
        "preview_only": True, "sheets_writes": 0, "capture_format_version": 2}
    output.mkdir(parents=True, exist_ok=True)
    try:
        with (output / "manifest.json").open("x") as file:
            json.dump(manifest, file, indent=2)
    except FileExistsError:
        parser.error("Round already exists; inspect saved state rather than rerunning it")

    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))

    job_id = "discovery-" + uuid.uuid4().hex[:12]
    manifest["job_id"] = job_id
    save("manifest.json", manifest)
    init_job(job_id, request.model_dump())
    web_fetcher._CACHE.clear()
    serp, selections, attempts, analyses = [], [], [], []
    original_actor = apify_runner.run_actor
    original_website_actor = web_fetcher.run_actor
    website_actor_records = []
    original_discover = research_runner.run_serp_discovery
    original_read = web_fetcher._read_page
    original_analyze = supplier_validator.analyze_supplier_with_llm

    traced_actor = trace_actor(original_actor, serp, save, "serp.json")
    traced_website_actor = trace_actor(original_website_actor, website_actor_records, save, "website_actor_records.json")

    def traced_discover(*call_args, **kwargs):
        rows = original_discover(*call_args, **kwargs)
        selections.append({"country": kwargs.get("country"), "limit": kwargs.get("limit"), "rows": rows})
        save("selected_candidates.json", selections)
        return rows

    def traced_read(url, context, tool):
        started = time.monotonic()
        operation_start = len(context.operations)
        entry = {"url": url, "scraping_tool": tool, "status": "started"}
        attempts.append(entry)
        save("fetch_attempts.json", attempts)
        try:
            page = original_read(url, context, tool)
            entry.update(status="page_returned" if page else "no_page")
            if page:
                entry.update(loaded_url=page["url"], text_chars=len(page["text"]))
            return page
        except Exception as exc:
            entry.update(status="error", error_type=type(exc).__name__)
            raise
        finally:
            entry.update(elapsed_seconds=round(time.monotonic()-started, 3),
                         actor_run_ids=[o["run_id"] for o in context.operations[operation_start:] if o.get("run_id")])
            save("fetch_attempts.json", attempts)
            save("captured_pages.json", [entry[1] for entry in web_fetcher._CACHE.values()])

    def traced_analyze(product, pages, context, **kwargs):
        analysis = original_analyze(product, pages, context, **kwargs)
        analyses.append({"url": pages[0]["url"], "analysis": analysis})
        save("model_analyses.json", analyses)
        return analysis

    apify_runner.run_actor = traced_actor
    web_fetcher.run_actor = traced_website_actor
    research_runner.run_serp_discovery = traced_discover
    web_fetcher._read_page = traced_read
    supplier_validator.analyze_supplier_with_llm = traced_analyze
    print(json.dumps({"job_id": job_id, "round": args.round, "status": "starting"}), flush=True)
    try:
        research_runner.run_research_job(job_id, request)
    finally:
        apify_runner.run_actor = original_actor
        web_fetcher.run_actor = original_website_actor
        research_runner.run_serp_discovery = original_discover
        web_fetcher._read_page = original_read
        supplier_validator.analyze_supplier_with_llm = original_analyze
        result = get_job(job_id)
        result.update(job_id=job_id, elapsed_seconds=round(time.time()-manifest["started_at"], 2),
                      master_unchanged=digest(master_path) == manifest["master_sha256"])
        save("result.json", result)
        save("captured_pages.json", [entry[1] for entry in web_fetcher._CACHE.values()])
    print(json.dumps({"job_id": job_id, "status": result["status"], "processed": result["processed"],
        "elapsed_seconds": result["elapsed_seconds"], "master_unchanged": result["master_unchanged"],
        "counts": {g: len(result[g]) for g in ["accepted", "review", "rejected", "skipped"]},
        "limits": result["limits"], "output": str(output)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
