"""Seed-only preview runner for the frozen cold-plunge labels. Isolated job DB."""
import json
import argparse
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.job_store import get_job, init_job
from backend.master_index import load_reference
from backend.models import ResearchRequest
from backend.research_runner import run_research_job

LABELS = json.loads((Path(__file__).with_name("labels.json")).read_text())


def cases_by_id(ids):
    lookup = {c["id"]: c for c in LABELS["cases"]}
    return [lookup[i] for i in ids]


def run(ids, *, master_reference_id):
    # Validate an explicitly selected immutable reference before any provider work.
    load_reference(master_reference_id)
    selected = cases_by_id(ids)
    os.environ["SUPPLIER_JOB_DB"] = str(ROOT / "var" / "eval" / "cold-plunge-2026-10-27" / "jobs.sqlite")
    request = ResearchRequest(
        product=LABELS["product"],
        candidate_urls=[c["url"] for c in selected],
        use_apify=False,
        use_shopping=False,
        preview_only=True,
        target_suppliers=len(selected),
        max_candidate_domains=len(selected),
        allowed_countries=LABELS["allowed_countries"],
        allowed_supplier_types=LABELS["allowed_roles"],
        excluded_products=[
            "replacement filters", "assembly services", "chillers sold without a tub",
            "inflatable tubs without a chiller", "sauna heaters", "hot tubs",
        ],
        max_pages=min(8, 2 * len(selected)),
        max_pages_per_supplier=2,
        max_runtime_seconds=600,
        max_external_calls=20,
        max_execution_cost_usd=10,
        research_mode="supplier_search",
        master_reference_id=master_reference_id,
        allow_browser_fallback=False,
        use_shopify_catalogue=False,
    )
    job_id = "eval-" + uuid.uuid4().hex[:12]
    init_job(job_id, request.model_dump())
    started = time.time()
    run_research_job(job_id, request)
    job = get_job(job_id)
    out = {
        "job_id": job_id,
        "elapsed_seconds": round(time.time() - started, 1),
        "case_ids": ids,
        "settings": request.model_dump(),
        "status": job["status"],
        "limit_reason": job.get("limit_reason"),
        "error": job.get("error"),
        "limits": job.get("limits"),
        "operations": job.get("operations"),
        "warnings": job.get("warnings"),
        "skipped": job.get("skipped", []),
        "accepted": job.get("accepted", []),
        "review": job.get("review", []),
        "rejected": job.get("rejected", []),
    }
    dest = ROOT / "var" / "eval" / "cold-plunge-2026-10-27" / (job_id + ".json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps({"job_id": job_id, "status": job["status"], "path": str(dest),
                      "accepted": len(out["accepted"]), "review": len(out["review"]),
                      "rejected": len(out["rejected"]), "skipped": len(out["skipped"]),
                      "elapsed": out["elapsed_seconds"], "limit_reason": job.get("limit_reason")},
                     indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-reference-id", required=True, help="Exact saved master-reference ID")
    parser.add_argument("case_ids", nargs="+")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    run(args.case_ids, master_reference_id=args.master_reference_id)
