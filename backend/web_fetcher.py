import hashlib
import re
import time
from urllib.parse import urljoin, urlsplit, urldefrag

from backend.actor_client import run_actor
from backend.config import RAG_BROWSER_ACTOR_ID
from backend.filters import is_blocked_domain
from backend.utils import domain_from_url, normalize_url, is_search_destination

_CACHE = {}


def _read_page(url, context, tool):
    context.take_page()
    key = (url, tool)
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < 3600:
        return dict(cached[1], cache_hit=True)
    items = run_actor(RAG_BROWSER_ACTOR_ID, {
        "query": url, "maxResults": 1, "scrapingTool": tool,
        "requestTimeoutSecs": 40 if tool == "browser-playwright" else 20,
        "maxRequestRetries": 0, "desiredConcurrency": 1,
        "dynamicContentWaitSecs": 3, "removeCookieWarnings": True,
    }, context, result_limit=1, timeout_seconds=60 if tool == "browser-playwright" else 45,
       memory_mb=2048 if tool == "browser-playwright" else 1024)
    if not items:
        return None
    item = items[0]
    metadata = item.get("metadata") or {}
    loaded_url = metadata.get("redirectedUrl") or metadata.get("url") or url
    body = item.get("markdown") or item.get("text") or ""
    crawl = item.get("crawl") or {}
    if item.get("#error") or crawl.get("httpStatusCode", 200) >= 400 or not body.strip():
        return None
    if is_search_destination(loaded_url) or is_blocked_domain(domain_from_url(loaded_url)):
        return None
    text = "\n".join([metadata.get("title") or "", metadata.get("description") or "", body])[:50000]
    page = {"url": loaded_url, "requested_url": url, "text": text, "scraping_tool": tool,
            "retrieved_at": time.time(), "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "actor_run_id": context.operations[-1].get("run_id"),
            "dataset_id": context.operations[-1].get("dataset_id")}
    _CACHE[key] = (time.time(), page)
    return page


def fetch_page(url, context, *, attempts_left=None):
    page = _read_page(url, context, "raw-http")
    thin = not page or len(page["text"].strip()) < 400 or re.search(r"enable javascript|javascript is required", page["text"], re.I)
    if (thin and context.request.allow_browser_fallback and (attempts_left is None or attempts_left > 1)
            and context.pages < context.request.max_pages):
        # One bounded retry for empty/thin/JavaScript-shell evidence only.
        from backend.research_context import JobStopped, LimitReached
        try:
            browser = _read_page(url, context, "browser-playwright")
        except (JobStopped, LimitReached):
            raise
        except Exception:
            browser = None
        if browser and (not page or len(browser["text"]) > len(page["text"])):
            page = dict(browser, browser_fallback=True)
    return page


def _page_priority(url, product):
    path = urlsplit(url).path.casefold()
    if re.search(r'privacy|terms|checkout|cart|login|account|shipping|refund|returns|blog|news', path):
        return None
    if re.search(r'product|collection|catalog|sauna|plunge|fireplace|heater', path):
        terms = {t.rstrip('s') for t in re.findall(r'\w+', product.casefold()) if len(t) > 3}
        return (0, -sum(t in path for t in terms))
    if re.search(r'about|company|our-story', path):
        return (1, 0)
    if re.search(r'contact', path):
        return (2, 0)
    if re.search(r'dealer|wholesale', path):
        return (3, 0)
    return None


def fetch_website_pages(base_url, context):
    before = context.pages
    first = fetch_page(normalize_url(base_url), context, attempts_left=context.request.max_pages_per_supplier)
    attempts = max(1, context.pages - before)
    if not first:
        return []
    pages = [first]
    domain = domain_from_url(first["url"])
    discovered = {}
    for match in re.finditer(r'\]\(([^)\s]+)(?:\s+[^)]*)?\)', first["text"]):
        url = urldefrag(urljoin(first["url"], match.group(1)))[0]
        if domain_from_url(url) != domain or url.rstrip('/') == first['url'].rstrip('/'):
            continue
        rank = _page_priority(url, context.request.product)
        if rank is not None:
            discovered.setdefault(url, rank)
    for url in sorted(discovered, key=lambda u: (discovered[u], len(urlsplit(u).path))):
        if attempts >= context.request.max_pages_per_supplier or context.pages >= context.request.max_pages:
            break
        before = context.pages
        page = fetch_page(url, context, attempts_left=context.request.max_pages_per_supplier-attempts)
        attempts += max(1, context.pages-before)
        if page and domain_from_url(page["url"]) == domain:
            pages.append(page)
    return pages


def prompt_pages(pages, product):
    # Scan complete captured pages before choosing excerpts; long navigation cannot hide contacts.
    terms = [re.escape(t) for t in re.findall(r'\w+', product) if len(t) > 3]
    patterns = [r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', r'headquarters|based in|Canada|Ontario|United States|Surrey',
                r'manufactur\w*|own brand|engineer\w*'] + terms
    result = []
    for page in pages:
        text = page['text']
        excerpts = [text[:1000]]
        for pattern in patterns:
            for match in list(re.finditer(pattern, text, re.I))[:2]:
                excerpt = text[max(0, match.start()-80):match.end()+220]
                if excerpt not in excerpts:
                    excerpts.append(excerpt)
        result.append({"url": page['url'], "excerpts": excerpts[:12]})
    return result
