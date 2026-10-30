from backend.actor_client import run_actor
from backend.config import APIFY_SERP_ACTOR_ID
from backend.filters import is_blocked_domain
from backend.utils import normalize_url, domain_from_url, is_search_destination

MARKETS = {"United States": "us", "Canada": "ca", "United Kingdom": "gb", "Germany": "de", "Australia": "au"}


def run_serp_discovery(product, context, *, country="United States", limit=20, query=None):
    pages = run_actor(APIFY_SERP_ACTOR_ID, {
        "queries": query or f"{product} manufacturer\n{product} brand official website\n{product} wholesale supplier",
        "countryCode": MARKETS[country], "languageCode": "en",
        "maxPagesPerQuery": 1, "maximumLeadsEnrichmentRecords": 0,
        "saveHtml": False, "saveHtmlToKeyValueStore": False,
    }, context, result_limit=10)
    results, flagged, seen = [], [], set()
    for page in pages:
        for row in page.get("organicResults", []):
            url = normalize_url(row.get("url") or "")
            domain = domain_from_url(url)
            if not domain or domain in seen or is_search_destination(url):
                continue
            seen.add(domain)
            item = {"url": url, "domain": domain, "title": row.get("title", ""),
                    "snippet": row.get("description", ""), "discovery_source": "serp",
                    "query": page.get("searchQuery", {}).get("term"), "search_country": country}
            if is_blocked_domain(domain):
                item["skip_reason"] = "blocked_domain"
                flagged.append(item)
                continue
            results.append(item)
            if len(results) >= limit:
                return flagged + results
    return flagged + results


def run_serp_brand_lookup(hint, product, context, *, country="United States", limit=3):
    # Return several candidates. Qualification must establish identity; never trust first rank.
    return run_serp_discovery(product, context, country=country, limit=limit,
                              query=f'{hint} {product} official website')
