"""Bounded development-only previews. Never exports or runs final-check cases."""
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
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--round", required=True, help="Unique local round name; an existing round is never repeated")
    parser.add_argument("--master-reference-id")
    parser.add_argument("--pages-per-site", type=int, default=3, choices=range(1, 5))
    parser.add_argument("--budget", type=float, default=4.0)
    args = parser.parse_args()
    if not 1 <= len(args.cases) <= 3 or len(set(args.cases)) != len(args.cases):
        parser.error("Select 1–3 distinct development/anchor cases per bounded batch")
    if not args.round or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.round):
        parser.error("Round names use letters, digits, hyphens and underscores")
    labels_path = Path(__file__).with_name("labels.json")
    labels = json.loads(labels_path.read_text())
    lookup = {case["id"]: case for case in labels["cases"] if case["group"] in {"development", "anchor"}}
    if any(case not in lookup for case in args.cases):
        parser.error("Only development/anchor IDs are allowed; final-check cases are protected")

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    output = ROOT / "var" / "eval" / labels["id"] / "evidence-collection" / args.round
    os.environ["SUPPLIER_JOB_DB"] = str(output / "jobs.sqlite")
    from backend.job_store import get_job, init_job
    from backend.models import ResearchRequest
    from backend.research_runner import run_research_job
    from backend import web_fetcher
    from backend.master_index import load_reference
    if args.master_reference_id:
        load_reference(args.master_reference_id)
    request = ResearchRequest(product=labels["product"], candidate_urls=[lookup[i]["url"] for i in args.cases],
        allowed_countries=labels["allowed_countries"], allowed_supplier_types=labels["allowed_roles"],
        excluded_products=["replacement filters", "assembly services", "chillers sold without a tub",
                           "inflatable tubs without a chiller", "sauna heaters", "hot tubs"],
        use_apify=False, use_shopping=False, preview_only=True, use_shopify_catalogue=False,
        allow_browser_fallback=False, master_reference_id=args.master_reference_id,
        target_suppliers=len(args.cases), max_candidate_domains=len(args.cases),
        max_pages=args.pages_per_site*len(args.cases), max_pages_per_supplier=args.pages_per_site,
        max_runtime_seconds=600, max_external_calls=20, max_execution_cost_usd=args.budget)
    sources = ["backend/web_fetcher.py", "backend/location_evidence.py", "backend/product_evidence.py", "backend/role_evidence.py", "backend/supplier_validator.py",
               "backend/models.py", "backend/model_client.py", "backend/research_runner.py", "backend/actor_client.py"]
    manifest = {"started_at": time.time(), "case_ids": args.cases, "settings": request.model_dump(),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sources},
        "labels_sha256": hashlib.sha256(labels_path.read_bytes()).hexdigest(),
        "brief_sha256": hashlib.sha256(labels_path.with_name("brief.md").read_bytes()).hexdigest(),
        "preview_only": True, "sheets_writes": 0}
    output.mkdir(parents=True, exist_ok=True)
    # Claim the round before any provider call; uncertain/partial rounds are inspected, not retried.
    try:
        with (output / "manifest.json").open("x") as file:
            json.dump(manifest, file, indent=2)
    except FileExistsError:
        parser.error("This round already exists; inspect its saved state before choosing a new round")
    web_fetcher._CACHE.clear()
    job_id = "evidence-" + uuid.uuid4().hex[:12]
    init_job(job_id, request.model_dump())
    manifest["job_id"] = job_id
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"job_id": job_id, "round": args.round, "cases": args.cases, "status": "starting"}), flush=True)
    run_research_job(job_id, request)
    result = get_job(job_id)
    result["job_id"] = job_id
    result["elapsed_seconds"] = round(time.time()-manifest["started_at"], 2)
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (output / "captured_pages.json").write_text(json.dumps([entry[1] for entry in web_fetcher._CACHE.values()], ensure_ascii=False, indent=2))
    summary = {"job_id": job_id, "status": result["status"], "limit_reason": result.get("limit_reason"),
               "elapsed_seconds": result["elapsed_seconds"], "output": str(output),
               "rows": [{"name": row.get("supplier_name"), "url": row["url"], "status": row["status"],
                         "reason": row["reason"], "sources": [source["url"] for source in row.get("sources", [])]}
                        for group in ["accepted", "review", "rejected"] for row in result[group]]}
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
