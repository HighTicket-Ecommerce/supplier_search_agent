from backend.actor_client import run_actor
from backend.config import APIFY_SERP_ACTOR_ID
from backend.discovery_selection import select_serp_candidates

MARKETS = {"United States": "us", "Canada": "ca", "United Kingdom": "gb", "Germany": "de", "Australia": "au"}
ROLE_SEARCHES = {"Manufacturer": "manufacturer", "Brand owner": "brand official website",
                 "Distributor": "wholesale distributor", "Retailer": "retailer official website"}


def run_serp_discovery(product, context, *, country="United States", limit=20, query=None,
                       known_domains=(), seen_domains=()):
    pages = run_actor(APIFY_SERP_ACTOR_ID, {
        "queries": query or "\n".join(f"{product} {ROLE_SEARCHES[role]}"
                                      for role in dict.fromkeys(context.request.allowed_supplier_types)),
        "countryCode": MARKETS[country], "languageCode": "en",
        "maxPagesPerQuery": 1, "maximumLeadsEnrichmentRecords": 0,
        "saveHtml": False, "saveHtmlToKeyValueStore": False,
    }, context, result_limit=10)
    results, records, coverage = select_serp_candidates(pages, country=country, limit=limit,
        known_domains=known_domains, seen_domains=seen_domains, prioritize_sources=query is None)
    context.save_discovery_selection(records, coverage)
    flagged = [dict(entry, skip_reason=entry["reason"]) for entry in records
               if entry.get("reason") in {"blocked_domain", "already_in_master"}]
    # The job records these skips before verifying any selected candidate.
    return flagged + [{k: v for k, v in entry.items() if k not in {"decision", "verification_status"}}
                      for entry in results]


def run_serp_brand_lookup(hint, product, context, *, country="United States", limit=3,
                          known_domains=(), seen_domains=()):
    # Return several candidates. Qualification must establish identity; never trust first rank.
    return run_serp_discovery(product, context, country=country, limit=limit,
                              query=f'{hint} {product} official website',
                              known_domains=known_domains, seen_domains=seen_domains)
