"""Directory labels are discovery observations, never verified company identities."""
import hashlib
from html.parser import HTMLParser
import json
import re
import time
from urllib.parse import urljoin, urlsplit, urldefrag

from backend.master_index import name_key
from backend.public_fetch import fetch_public, PublicFetchError
from backend.utils import domain_from_url
from backend.actor_client import run_actor
from backend.config import RAG_BROWSER_ACTOR_ID

ARIZONA_HOST = "shop.arizonafireplaces.com"
BRAND_QUERY = 'query SupplierDirectoryBrands { catalog { products(options:{keywords:"",page:{index:0,size:1}}) { totalCount facets { facets { name title values { title count value } } } } } }'


class BrandLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = {"href": dict(attrs).get("href", ""), "parts": []}
        elif tag == "img" and self.current:
            self.current["parts"].append(dict(attrs).get("alt", ""))

    def handle_data(self, text):
        if self.current is not None:
            self.current["parts"].append(text)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append((self.current["href"], " ".join(self.current["parts"]).strip()))
            self.current = None


def extract_html_brands(html, source_url):
    parser = BrandLinks()
    parser.feed(html)
    rows, seen = [], set()
    for href, name in parser.links:
        url = urldefrag(urljoin(source_url, href))[0]
        path = urlsplit(url).path
        if domain_from_url(url) != domain_from_url(source_url) or not re.search(r"/(?:brandsupplier|brands?|manufacturers?)/[^/]+", path, re.I):
            continue
        name = re.sub(r"\s+", " ", name).strip()
        if not name or len(name) > 300 or name.casefold() in {"clearance", "miscellaneous", "all brands", "shop all"}:
            continue
        # Repeated mobile/desktop navigation is one observation; aliases remain separate.
        key = (name_key(name), path.rstrip("/"))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"supplier_name": name, "directory_entry_url": url, "source_url": source_url})
    return rows


def extract_arizona_brands(payload, source_url):
    if payload.get("errors"):
        raise ValueError("Directory API returned an error")
    products = payload["data"]["catalog"]["products"]
    facets = products["facets"]["facets"]
    brand = next((f for f in facets if f.get("name") == "U_GL_Brand"), None)
    if brand is None:
        raise ValueError("Expected brand facet was not found")
    rows = [{"supplier_name": v["title"].strip(), "source_url": source_url,
             "directory_entry_url": None, "listed_product_count": v.get("count")}
            for v in brand.get("values", []) if v.get("title", "").strip()]
    return rows, products.get("totalCount")


def fetch_browser_directory(url, context):
    context.take_page()
    items = run_actor(RAG_BROWSER_ACTOR_ID, {"query": url, "maxResults": 1, "outputFormats": ["html"],
        "scrapingTool": "browser-playwright", "requestTimeoutSecs": 40, "maxRequestRetries": 0,
        "desiredConcurrency": 1, "dynamicContentWaitSecs": 3,
        "removeElementsCssSelector": "script,style,noscript", "removeCookieWarnings": False},
        context, result_limit=1, timeout_seconds=60, memory_mb=2048)
    if not items or items[0].get("#error") or items[0].get("crawl", {}).get("httpStatusCode", 200) >= 400:
        raise ValueError("Browser directory evidence unavailable")
    item = items[0]
    html = item.get("html") or ""
    if not html or len(html.encode()) > 3_000_000:
        raise ValueError("Browser directory HTML empty or exceeds size limit")
    loaded_url = item.get("metadata", {}).get("redirectedUrl") or item.get("metadata", {}).get("url") or url
    if domain_from_url(loaded_url) != domain_from_url(url):
        raise ValueError("Browser directory redirected to a different website")
    return {"url": loaded_url, "text": html, "retrieved_at": time.time(),
            "body_sha256": hashlib.sha256(html.encode()).hexdigest(),
            "actor_run_id": context.operations[-1].get("run_id"), "dataset_id": context.operations[-1].get("dataset_id")}


def fetch_directory(url, context, *, limit):
    if domain_from_url(url) == ARIZONA_HOST:
        source = fetch_public("https://www.shop.arizonafireplaces.com/api/graph", context, json_body={"query": BRAND_QUERY})
        rows, total_products = extract_arizona_brands(json.loads(source["text"]), source["url"])
        adapter = "arizona_public_brand_facet"
    else:
        source, rows = None, []
        try:
            source = fetch_public(url, context)
            rows = extract_html_brands(source["text"], source["url"])
        except PublicFetchError:
            if not context.request.allow_browser_fallback:
                raise
        browser_used = False
        if not rows and context.request.allow_browser_fallback:
            source = fetch_browser_directory(url, context)
            rows = extract_html_brands(source["text"], source["url"])
            browser_used = True
        total_products = None
        adapter = "browser_brand_links" if browser_used else "html_brand_links"
        if not rows:
            raise ValueError("No supported brand links found; this directory needs a specific adapter")
    coverage = {"requested_url": url, "source_url": source["url"], "adapter": adapter,
                "observed_entries": len(rows), "returned_entries": min(len(rows), limit),
                "truncated": len(rows) > limit, "listed_catalogue_product_total": total_products,
                "products_extracted": 0, "retrieved_at": source["retrieved_at"], "body_sha256": source["body_sha256"]}
    for key in ["actor_run_id", "dataset_id"]:
        if source.get(key):
            coverage[key] = source[key]
    for row in rows[:limit]:
        row.update(url="", status="observation", reason="directory_label_requires_official_site_verification",
                   discovery_source="distributor_directory", retrieved_at=source["retrieved_at"],
                   source_sha256=source["body_sha256"])
        row["observation_id"] = hashlib.sha256(json.dumps([row["source_url"], row["supplier_name"], row["directory_entry_url"]]).encode()).hexdigest()[:24]
    return rows[:limit], coverage
