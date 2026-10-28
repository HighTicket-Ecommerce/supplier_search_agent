"""Bounded two-site distributor feasibility preview; never discovers or exports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    args = parser.parse_args()
    if not args.round or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.round):
        parser.error("Use letters, digits, hyphens and underscores in round names")
    cases_path = Path(__file__).with_name("cases.json")
    cases = json.loads(cases_path.read_text())
    output = ROOT / "var" / "eval" / cases["id"] / args.round
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    os.environ["SUPPLIER_JOB_DB"] = str(output / "jobs.sqlite")
    from backend import supplier_validator, web_fetcher
    from backend.job_store import get_job, init_job
    from backend.models import ResearchRequest
    from backend.research_runner import run_research_job

    request = ResearchRequest(product=cases["product"], candidate_urls=[c["url"] for c in cases["cases"]],
        allowed_countries=["United States", "Canada"], allowed_supplier_types=["Distributor"],
        excluded_products=["accessories", "replacement parts", "charcoal grills", "electric grills"],
        use_apify=False, use_shopping=False, use_shopify_catalogue=False, preview_only=True,
        allow_browser_fallback=True, target_suppliers=2, max_candidate_domains=2,
        max_pages=6, max_pages_per_supplier=3, max_external_calls=12,
        max_runtime_seconds=600, max_execution_cost_usd=4, max_actor_charge_usd=0.5)
    sources = sorted(ROOT.glob("backend/*.py")) + [Path(__file__).resolve(), cases_path, cases_path.with_name("brief.md")]
    manifest = {"started_at": time.time(), "settings": request.model_dump(),
        "case_ids": [c["id"] for c in cases["cases"]],
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "sheets_writes": 0, "production_changes": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
    except FileExistsError:
        parser.error("Round already exists; inspect saved state instead of repeating uncertain operations")
    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))
    job_id = "distributor-" + uuid.uuid4().hex[:12]
    manifest["job_id"] = job_id
    save("manifest.json", manifest)
    init_job(job_id, request.model_dump())
    web_fetcher._CACHE.clear()
    attempts, analyses = [], []
    read_original = web_fetcher._read_page
    analyze_original = supplier_validator.analyze_supplier_with_llm

    def traced_read(url, context, tool):
        started, operation_start = time.monotonic(), len(context.operations)
        attempt = {"url": url, "scraping_tool": tool, "status": "started"}
        attempts.append(attempt)
        save("fetch_attempts.json", attempts)
        try:
            page = read_original(url, context, tool)
            attempt.update(status="page_returned" if page else "no_page")
            if page:
                attempt.update(loaded_url=page["url"], text_chars=len(page["text"]),
                    main_text_chars=page.get("main_text_chars"), cache_hit=bool(page.get("cache_hit")))
            return page
        except Exception as exc:
            attempt.update(status="error", error_type=type(exc).__name__)
            raise
        finally:
            attempt.update(elapsed_seconds=round(time.monotonic()-started, 3),
                actor_run_ids=[op["run_id"] for op in context.operations[operation_start:] if op.get("run_id")])
            save("fetch_attempts.json", attempts)
            save("captured_pages.json", [entry[1] for entry in web_fetcher._CACHE.values()])

    def traced_analyze(product, pages, context, **kwargs):
        analysis = analyze_original(product, pages, context, **kwargs)
        analyses.append({"url": pages[0]["url"], "analysis": analysis})
        save("model_analyses.json", analyses)
        return analysis

    web_fetcher._read_page = traced_read
    supplier_validator.analyze_supplier_with_llm = traced_analyze
    print(json.dumps({"job_id": job_id, "round": args.round, "status": "starting"}), flush=True)
    try:
        run_research_job(job_id, request)
    finally:
        web_fetcher._read_page = read_original
        supplier_validator.analyze_supplier_with_llm = analyze_original
        result = get_job(job_id)
        result.update(job_id=job_id, elapsed_seconds=round(time.time()-manifest["started_at"], 2))
        save("result.json", result)
        save("captured_pages.json", [entry[1] for entry in web_fetcher._CACHE.values()])
    print(json.dumps({"job_id": job_id, "status": result["status"], "elapsed_seconds": result["elapsed_seconds"],
        "rows": [{"name": r.get("supplier_name"), "status": r["status"], "reason": r["reason"]}
                 for group in ["accepted", "review", "rejected"] for r in result[group]],
        "output": str(output)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
