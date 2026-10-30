"""Replay a raw timeout then fetch at most one browser page; no qualification/export."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
RAW_FIXTURE = ROOT / "tests/fixtures/raw_fetch_timeout.json"


def run_probe(url, output, raw, *, browser_items=None):
    from backend import web_fetcher
    from backend.config import model_settings_snapshot
    from backend.job_store import get_job, init_job, update_job
    from backend.models import ResearchRequest
    from backend.research_context import ResearchContext

    if not raw or raw[0].get("crawl", {}).get("httpStatusCode") != 500:
        raise ValueError("The replay leg must contain the saved HTTP-500 failure shape")
    request = ResearchRequest(product="Complete cold plunge systems", candidate_urls=[url],
        use_apify=False, use_shopping=False, preview_only=True, allow_browser_fallback=True,
        target_suppliers=1, max_candidate_domains=1, max_pages=2, max_pages_per_supplier=2,
        max_external_calls=1, max_execution_cost_usd=.75, max_actor_charge_usd=.5, max_runtime_seconds=90)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    mode = "replayed_raw_then_fixture_browser" if browser_items is not None else "replayed_raw_then_live_browser"
    manifest = {"started_at": time.time(), "mode": mode, "settings": request.model_dump(),
        "model_settings": model_settings_snapshot(), "qualification_not_run": True, "sheets_writes": 0,
        "raw_replay_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    attempts = []
    original_actor = web_fetcher.run_actor
    browser_calls = 0

    def actor(actor_id, data, context, **options):
        nonlocal browser_calls
        tool = data["scrapingTool"]
        attempt = {"scraping_tool": tool, "status": "started", "replayed": tool == "raw-http" or browser_items is not None}
        attempts.append(attempt)
        (output/"fetch_attempts.json").write_text(json.dumps(attempts, indent=2))
        try:
            if tool == "raw-http":
                items = raw
            else:
                if tool != "browser-playwright" or browser_calls:
                    raise ValueError("Only one browser attempt is permitted")
                browser_calls += 1
                if browser_items is None:
                    items = original_actor(actor_id, data, context, **options)
                else:
                    items = browser_items
            attempt.update(status="returned", item_count=len(items))
            return items
        except Exception as exc:
            attempt.update(status="error", error_type=type(exc).__name__)
            raise
        finally:
            (output/"fetch_attempts.json").write_text(json.dumps(attempts, indent=2))

    with patch.dict(os.environ, {"SUPPLIER_JOB_DB": str(output/"jobs.sqlite")}):
        job_id = "fetch-probe-"+uuid.uuid4().hex[:12]
        init_job(job_id, request.model_dump())
        context = ResearchContext(job_id, request)
        web_fetcher._CACHE.clear()
        page, error = None, None
        try:
            with patch.object(web_fetcher, "run_actor", side_effect=actor):
                page = web_fetcher.fetch_page(url, context, attempts_left=2)
        except Exception as exc:
            error = type(exc).__name__
        update_job(job_id, status="failed" if error or any(a["status"] == "error" for a in attempts) else "completed",
            error=error, observations=[{"kind": "controlled_fetch_probe", "page_returned": bool(page),
                "browser_fallback_used": bool(page and page.get("browser_fallback")), "qualification_not_run": True}])
        result = dict(get_job(job_id), job_id=job_id, mode=mode)
    assert context.pages <= 2 and context.calls <= 1 and browser_calls <= 1 and not result["exports"]
    (output/"result.json").write_text(json.dumps(result, indent=2))
    (output/"captured_pages.json").write_text(json.dumps([page] if page else [], indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["dev-morozko", "dev-redwood"], required=True)
    parser.add_argument("--round", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live-browser", action="store_true", help="Permit one fresh, paid browser actor call")
    mode.add_argument("--browser-fixture", type=Path, help="Offline browser actor items JSON")
    args = parser.parse_args()
    if not args.round or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.round):
        parser.error("Round names use letters, digits, hyphens and underscores")
    labels = json.loads(Path(__file__).with_name("labels.json").read_text())
    url = next(c["url"] for c in labels["cases"] if c["id"] == args.case and c["group"] == "development")
    browser = json.loads(args.browser_fixture.read_text()) if args.browser_fixture else None
    output = ROOT/"var/eval"/labels["id"]/"evidence-collection"/args.round
    result = run_probe(url, output, json.loads(RAW_FIXTURE.read_text())["items"], browser_items=browser)
    print(json.dumps({"job_id": result["job_id"], "status": result["status"], "mode": result["mode"], "output": str(output)}))


if __name__ == "__main__":
    main()
