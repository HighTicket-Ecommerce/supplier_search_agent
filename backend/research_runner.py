import logging

from backend.job_store import update_job, get_job
from backend.actor_client import ActorError
from backend.apify_runner import run_serp_discovery, run_serp_brand_lookup
from backend.google_shopping_runner import run_google_shopping_discovery
from backend.supplier_validator import process_supplier
from backend.filters import is_blocked_domain
from backend.research_context import ResearchContext, JobStopped, LimitReached
from backend.utils import normalize_url, domain_from_url, is_search_destination
from backend.master_index import MasterIndex, load_reference, reference_summary, match_without_reference
from backend.directory_runner import fetch_directory


def run_research_job(job_id, req):
    context = ResearchContext(job_id, req)
    accepted, review, rejected, skipped = [], [], [], []
    seen = set()
    resolved = set()
    identity_attempts = set()
    retryable_identities = set()
    processed = 0
    observations, coverage, warnings = [], [], []
    master = None

    def save(**extra):
        if extra.get("status") in {"completed", "failed", "stopped", "limited"}:
            reason = extra.get("limit_reason") or extra["status"]
            if extra["status"] == "completed":
                reason = ("target_reached" if len(accepted) >= req.target_suppliers else
                          "candidate_limit" if processed >= req.max_candidate_domains else "pool_exhausted")
            context.finish_discovery(reason)
        update_job(job_id, accepted=accepted, review=review, rejected=rejected, skipped=skipped,
                   processed=processed, total=max(len(seen), len(observations)), target_suppliers=req.target_suppliers,
                   observations=observations, directory_coverage=coverage, warnings=warnings,
                   master_reference=reference_summary(master.reference) if master else None, **extra)

    def skip(item, url, domain, reason):
        if domain in seen:
            return
        seen.add(domain)
        skipped.append({"url": url, "domain": domain, "reason": reason,
                        "discovery_source": item.get("discovery_source"), "title": item.get("title", "")})
        save()

    def enough():
        return len(accepted) >= req.target_suppliers or processed >= req.max_candidate_domains

    def process(candidates):
        nonlocal processed
        for item in candidates:
            context.checkpoint()
            if enough():
                break
            url = normalize_url(item["url"])
            domain = domain_from_url(url)
            hint = (item.get("brand_name") or "").strip().casefold()
            identity_key = (domain, hint)
            retry_identity = bool(hint and domain in retryable_identities and identity_key not in identity_attempts)
            if not domain or (domain in seen and not retry_identity) or is_search_destination(url):
                continue
            is_seed = item.get("discovery_source") == "seed"
            if not is_seed and (item.get("skip_reason") == "blocked_domain" or is_blocked_domain(domain)):
                skip(item, url, domain, "blocked_domain")
                continue
            if not is_seed and master and master.has_exact_host(domain):
                skip(item, url, domain, "already_in_master")
                continue
            seen.add(domain)
            identity_attempts.add(identity_key)
            save()
            context.record_discovery_verification(item, "checking")
            try:
                supplier = process_supplier(req.product, url, context,
                                            brand_hint=item.get("brand_name"), discovery_source=item.get("discovery_source"),
                                            price_hint=item.get("price_hint_raw"))
                supplier["discovery"] = {k: v for k, v in item.items() if k != "url"}
                supplier["master_match"] = (master.match(supplier.get("supplier_name", ""), supplier.get("url", url),
                                                         alternate_urls=(url,))
                                            if master else match_without_reference())
                final_domain = domain_from_url(supplier.get("url", url))
                if final_domain in resolved:
                    supplier.update(status="review", reason="duplicate_resolved_website")
                if supplier.get("reason") == "shopping_identity_not_established":
                    retryable_identities.add(domain)
                else:
                    retryable_identities.discard(domain)
                if final_domain and supplier["status"] == "qualified":
                    resolved.add(final_domain)
                if supplier["status"] == "qualified":
                    accepted.append(supplier)
                elif supplier["status"] == "excluded":
                    rejected.append(supplier)
                else:
                    review.append(supplier)
                context.record_discovery_verification(item, supplier["status"])
            except (JobStopped, LimitReached) as exc:
                review.append({"url": url, "status": "retry_needed", "reason": "verification_interrupted:" + str(exc),
                               "discovery": {k: v for k, v in item.items() if k != "url"}})
                save()
                context.record_discovery_verification(item, "interrupted")
                raise
            except Exception as exc:
                review.append({"url": url, "status": "retry_needed", "reason": "processing_failed:" + type(exc).__name__,
                               "discovery": {k: v for k, v in item.items() if k != "url"}})
                context.record_discovery_verification(item, "retry_needed")
            processed += 1
            save()

    try:
        context.checkpoint()
        if req.master_reference_id:
            master = MasterIndex(load_reference(req.master_reference_id))
        save(status="running")
        if req.research_mode == "list_compare":
            for row in req.comparison_rows:
                context.checkpoint()
                observations.append(dict(row.model_dump(), status="observation", master_match=master.match(row.supplier_name, row.url)))
                processed += 1
            save(status="completed")
            return
        if req.research_mode == "distributor_brands":
            for url in req.directory_urls:
                remaining = req.max_directory_entries - len(observations)
                if remaining <= 0:
                    warnings.append("directory_entry_limit: some source URLs were not fetched")
                    break
                try:
                    rows, source_coverage = fetch_directory(url, context, limit=remaining)
                    for row in rows:
                        row["master_match"] = master.match(row["supplier_name"], "") if master else match_without_reference()
                    observations.extend(rows)
                    coverage.append(source_coverage)
                    save()
                except (JobStopped, LimitReached):
                    raise
                except Exception as exc:
                    warnings.append({"source_url": url, "error": "directory_request_failed:" + type(exc).__name__,
                                     "diagnostic": str(exc) if isinstance(exc, (ActorError, ValueError)) else "Public directory request failed"})
                    save()
            if req.verify_directory_brands:
                for row in observations:
                    if enough():
                        break
                    context.checkpoint()
                    candidates = run_serp_brand_lookup(row["supplier_name"], req.product, context,
                        country=(req.allowed_countries or ["United States"])[0], limit=min(3, req.max_candidate_domains-processed),
                        known_domains=master.by_domain if master else (), seen_domains=seen | resolved)
                    for candidate in candidates:
                        candidate.update(brand_name=row["supplier_name"], discovery_source="distributor_identity_lookup",
                                         directory_observation_id=row["observation_id"], directory_source_url=row["source_url"])
                    row["lookup_candidate_urls"] = [c["url"] for c in candidates if not c.get("skip_reason")]
                    process(candidates)
            save(status="completed" if observations else "failed", **({} if observations else {"error": "No directory observations could be extracted; see warnings"}))
            return
        process([{"url": url, "discovery_source": "seed"} for url in req.candidate_urls])
        if req.use_apify and not enough():
            for country in req.allowed_countries or ["United States"]:
                if enough():
                    break
                process(run_serp_discovery(req.product, context, country=country, limit=req.max_candidate_domains-processed,
                                          known_domains=master.by_domain if master else (), seen_domains=seen | resolved))
        if req.use_apify and req.use_shopping and not enough():
            for country in req.allowed_countries or ["United States"]:
                if enough():
                    break
                country_observations = run_google_shopping_discovery(req.product, context, country=country, limit=min(20, req.max_candidate_domains-processed))
                observations.extend(country_observations)
                for item in country_observations:
                    if enough():
                        break
                    candidates = run_serp_brand_lookup(item["lookup_hint"], req.product, context, country=country,
                        limit=min(3,req.max_candidate_domains-processed),
                        known_domains=master.by_domain if master else (), seen_domains=seen | resolved)
                    for candidate in candidates:
                        candidate.update(brand_name=item["lookup_hint"], discovery_source="shopping_identity_lookup", shopping_observation=item)
                    process(candidates)
        save(status="completed")
    except JobStopped:
        save(status="stopped")
    except LimitReached as exc:
        save(status="limited", limit_reason=str(exc))
    except ActorError as exc:
        save(status="failed", error=str(exc))
    except Exception as exc:
        logging.getLogger(__name__).error("Research failed: %s", type(exc).__name__)
        save(status="failed", error=type(exc).__name__ + ": research request failed; partial results are saved")
