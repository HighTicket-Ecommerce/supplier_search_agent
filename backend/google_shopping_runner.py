from backend.actor_client import run_actor
from backend.config import APIFY_GOOGLE_SHOPPING_ACTOR_ID
from backend.utils import domain_from_url
from backend.apify_runner import MARKETS


def normalize_shopping_items(items):
    observations = []
    seen = set()
    for offset, item in enumerate(items):
        title = item.get("product_title") or item.get("title") or ""
        url = item.get("product_page_url") or item.get("productUrl") or item.get("url") or ""
        merchant = item.get("store_name") or item.get("merchant") or item.get("storeName") or ""
        brand = item.get("brand")
        if not title or not domain_from_url(url):
            continue
        key = (title, url, merchant)
        if key in seen:
            continue
        seen.add(key)
        observations.append({"title": title, "brand": brand, "merchant": merchant,
                             "lookup_hint": brand or merchant or title,
                             "price_hint_raw": item.get("price"), "example_product_url": url,
                             "official_company_url": None, "identity_status": "needs_resolution",
                             "discovery_source": "google_shopping", "dataset_offset": offset})
    return observations


def run_google_shopping_discovery(product, context, *, country="United States", limit=20):
    items = run_actor(APIFY_GOOGLE_SHOPPING_ACTOR_ID, {
        "searchQuery": product, "country": MARKETS[country], "language": "en",
        "limit": min(limit, 50), "sortBy": "BEST_MATCH",
    }, context, result_limit=min(limit, 50))
    return normalize_shopping_items(items)
