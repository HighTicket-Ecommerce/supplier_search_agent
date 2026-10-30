"""Audit captured evidence; optionally GET the status/cost of existing actor runs."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", required=True)
    parser.add_argument("--check-provider", action="store_true")
    args = parser.parse_args()
    if not args.round or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.round):
        parser.error("Invalid round name")
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from backend.master_index import MasterIndex, load_reference, reference_directory
    from backend.supplier_validator import quote_in_source
    from backend.utils import domain_from_url, normalize_url
    output = ROOT / "var/eval/cold-plunge-discovery-2026-10-28" / args.round
    def read(name, default=None):
        path = output / name
        return json.loads(path.read_text()) if path.exists() else default
    result, manifest = read("result.json"), read("manifest.json")
    pages = read("captured_pages.json", [])
    master_id = manifest["settings"]["master_reference_id"]
    master = MasterIndex(load_reference(master_id))
    master_path = reference_directory() / (master_id + ".json")
    groups = {domain_from_url(case["url"]): case["group"] for case in
              json.loads((ROOT / "docs/benchmarks/cold-plunge-2026-10-27/labels.json").read_text())["cases"]}
    outcomes = {}
    for group in ["accepted", "review", "rejected", "skipped"]:
        for row in result[group]:
            outcomes[domain_from_url(row["url"])] = {"group": group, "reason": row.get("reason")}
    raw_rows, seen = [], set()
    for batch in read("serp.json", []):
        for page in batch.get("items", batch.get("pages", [])):
            for row in page.get("organicResults", []):
                url = normalize_url(row.get("url") or "")
                host = domain_from_url(url)
                if not host:
                    continue
                raw_rows.append({"country_code": batch["input"]["countryCode"],
                    "query": page.get("searchQuery", {}).get("term"), "domain": host,
                    "url": url, "title": row.get("title"), "snippet": row.get("description"),
                    "first_domain_observation": host not in seen,
                    "master_exact_host": master.has_exact_host(host), "historical_group": groups.get(host),
                    "job_outcome": outcomes.get(host, {"group": "not_processed"})})
                seen.add(host)
    quote_checks = []
    for group in ["accepted", "review", "rejected"]:
        for row in result[group]:
            for entry in row.get("evidence", []):
                matching = [p for p in pages if entry["source_url"] in {p["url"], p.get("requested_url")}]
                quote_checks.append({"supplier": row.get("supplier_name"), **entry,
                    "verified": any(quote_in_source(entry["quote"], p["text"]) for p in matching),
                    "words": len(entry["quote"].split())})
    page_checks = [{"url": p["url"], "matches": hashlib.sha256(p["text"].encode()).hexdigest() == p["text_sha256"]} for p in pages]
    code_checks = []
    for path, expected in manifest["source_sha256"].items():
        content = subprocess.check_output(["git", "show", manifest["code_commit"] + ":" + path], cwd=ROOT)
        code_checks.append({"path": path, "matches_commit": hashlib.sha256(content).hexdigest() == expected})
    ledger = result.get("discovery_candidates", [])
    coverage = result.get("discovery_coverage", [])
    selection_checks = None
    if coverage:
        by_id = {r["record_id"]: r for r in ledger}
        selected = [r for r in ledger if r["decision"] == "selected"]
        linked = [r for g in ["accepted", "review", "rejected"] for r in result[g]
                  if r.get("discovery", {}).get("record_id")]
        selection_checks = {
            "ledger_row_count": len(ledger), "unique_ids": len(by_id) == len(ledger),
            "retained_count_matches": sum(c["retained_rows"] for c in coverage) == len(ledger),
            "no_unreported_pool_loss": sum(c["retained_rows"] + c["omitted_rows"] for c in coverage) ==
                sum(len(page.get("organicResults", [])) for b in read("serp.json", []) for page in b.get("items", b.get("pages", []))),
            "no_exact_master_host_selected": all(not master.has_exact_host(r["domain"]) for r in selected),
            "no_duplicate_host_selected": len({r["domain"] for r in selected}) == len(selected),
            "no_pending_checks": all(r.get("verification_status") not in {"pending", "checking"} for r in ledger),
            "duplicate_links_valid": all(r["duplicate_of"] in by_id and
                by_id[r["duplicate_of"]]["domain"] == r["domain"] for r in ledger if "duplicate_of" in r),
            "outcomes_match_ledger": all(by_id[r["discovery"]["record_id"]].get("verification_status") ==
                ("interrupted" if r.get("reason", "").startswith("verification_interrupted:") else r["status"]) for r in linked)}
        assert all(v for k, v in selection_checks.items() if k != "ledger_row_count")
    operations = [op for op in result["operations"] if op["kind"] == "apify" and op.get("run_id")]
    def inspect(op):
        import requests
        response = requests.get("https://api.apify.com/v2/actor-runs/" + op["run_id"],
            headers={"Authorization": "Bearer " + os.environ["APIFY_TOKEN"]}, timeout=30)
        response.raise_for_status()
        data = response.json()["data"]
        return {"run_id": data["id"], "status": data["status"], "usage_total_usd": data.get("usageTotalUsd"),
                "terminal": data["status"] in {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}}
    if args.check_provider:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            runs = list(pool.map(inspect, operations))
    else:
        runs = [{"run_id": op["run_id"], "status": op["status"],
                 "usage_total_usd": op.get("reported_usage_usd"), "terminal": op["status"] in
                 {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}} for op in operations]
    actor_cost = sum(r["usage_total_usd"] for r in runs) if all(r["usage_total_usd"] is not None for r in runs) else None
    model_cost = sum(op.get("estimated_cost_usd", 0) for op in result["operations"] if op["kind"] == "openai")
    audit = {"job_id": result["job_id"], "raw_organic_rows": len(raw_rows), "unique_domains": len(seen),
        "counts": {g: len(result[g]) for g in ["accepted", "review", "rejected", "skipped"]},
        "all_quotes_verified": all(q["verified"] and q["words"] <= 12 for q in quote_checks),
        "all_page_hashes_verified": all(p["matches"] for p in page_checks),
        "implementation_matches_commit": all(p["matches_commit"] for p in code_checks),
        "master_unchanged": hashlib.sha256(master_path.read_bytes()).hexdigest() == manifest["master_sha256"],
        "provider_rechecked": args.check_provider, "all_actors_terminal": all(r["terminal"] for r in runs),
        "actor_usage_usd": actor_cost, "estimated_model_usd": model_cost,
        "combined_execution_usd": actor_cost + model_cost if actor_cost is not None else None,
        "selection_checks": selection_checks,
        "quote_checks": quote_checks, "page_checks": page_checks, "implementation": code_checks,
        "runs": runs, "discovery_rows": raw_rows}
    (output / "validation.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    assert all(audit[k] for k in ["all_quotes_verified", "all_page_hashes_verified", "implementation_matches_commit",
                                "master_unchanged", "all_actors_terminal"])
    print(json.dumps({k: v for k, v in audit.items() if k not in
                     {"quote_checks", "page_checks", "implementation", "runs", "discovery_rows"}}, indent=2))


if __name__ == "__main__":
    main()
