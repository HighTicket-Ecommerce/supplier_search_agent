import hashlib
from html.parser import HTMLParser
import re
import time
from urllib.parse import urljoin, urlsplit, urldefrag

from backend.actor_client import run_actor
from backend.config import RAG_BROWSER_ACTOR_ID
from backend.filters import is_blocked_domain
from backend.location_evidence import has_company_location
from backend.utils import domain_from_url, normalize_url, is_search_destination
from backend.research_context import JobStopped, LimitReached

_CACHE = {}
MAX_HTML_CHARS = 1_500_000
MAX_TEXT_CHARS = 120_000
MAX_LINKS = 300


class PageHTML(HTMLParser):
    """Extract visible text and anchors without executing any page content."""
    HIDDEN = {"script", "style", "noscript", "svg", "template", "iframe"}
    BLOCKS = {"p", "div", "section", "article", "address", "li", "br", "h1", "h2", "h3", "h4", "footer", "nav", "header",
              "table", "tr", "th", "td", "dl", "dt", "dd"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.navigation = 0
        self.parts, self.main_parts, self.links = [], [], []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or "" for key, value in attrs}
        if tag in self.HIDDEN:
            self.hidden += 1
        if self.hidden:
            return
        if tag in {"nav", "header", "footer"}:
            self.navigation += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")
            if not self.navigation:
                self.main_parts.append("\n")
        if tag == "a":
            self.anchor = {"href": attrs.get("href", ""), "parts": [],
                           "label": attrs.get("aria-label") or attrs.get("title") or ""}
        elif tag == "img" and self.anchor is not None:
            self.anchor["parts"].append(attrs.get("alt", ""))

    def handle_endtag(self, tag):
        if tag in self.HIDDEN:
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag == "a" and self.anchor is not None:
            if len(self.links) < 4000:
                self.links.append((self.anchor["href"], " ".join(self.anchor["parts"]).strip() or self.anchor["label"]))
            self.anchor = None
        if tag in self.BLOCKS:
            self.parts.append("\n")
            if not self.navigation:
                self.main_parts.append("\n")
        if tag in {"nav", "header", "footer"}:
            self.navigation = max(0, self.navigation - 1)

    def handle_data(self, value):
        if self.hidden:
            return
        self.parts.append(value)
        if not self.navigation:
            self.main_parts.append(value)
        if self.anchor is not None:
            self.anchor["parts"].append(value)


def _product_terms(product):
    return {t.rstrip("s") for t in re.findall(r"\w+", (product or "").casefold()) if len(t) > 3}


def _page_priority(url, product, label=""):
    path = urlsplit(url).path.casefold()
    if re.search(r"\.(?:jpe?g|png|webp|gif|svg|ico|css|js|json|pdf|zip|mp4|woff2?)$", path) or re.search(r"/(?:cdn|assets)/", path):
        return None
    if re.search(r"privacy|terms|checkout|cart|login|account|shipping|refund|returns|blog|news", path):
        return None
    terms = _product_terms(product) - {"complete", "system", "supplier", "product", "primary"}
    if re.search(r"about|company|our-story|who-we-are|our-team|mission", path) or re.search(
            r"^(?:about\b|our (?:story|company|team)\b|who we are\b)", label.casefold()):
        return (0, 0)
    if re.search(r"contact|location|headquarters|\bhq\b|faq", path) or re.search(
            r"^(?:contact\b|headquarters\b|hq\b|faqs?\b)", label.casefold()):
        return (1, 0)
    product_path = bool(re.search(r"/products?/", path))
    collection_path = bool(re.search(r"/collections?/|/catalog|/shop", path))
    if not product_path and not collection_path and re.search(r"protocol|buying-guide|how-to|health-benefit", path):
        return None
    hits = sum(term in (path + " " + label.casefold()) for term in terms)
    if product_path or collection_path or any(term in path for term in terms):
        # A matching collection/product beats an editorial landing page or unrelated product.
        tier = (0 if product_path else 1) if hits else 3
        if not product_path and not collection_path:
            tier = 2
        if re.search(r"complete|system", product, re.I) and re.search(r"cold|plunge", product, re.I):
            component = re.search(r"chiller|tubs?-only|accessor|filters?|covers?|dry-mat|chemical|cleaner|hoses?|steps", path)
            complete = re.search(r"bundle|integrated|all-in-one|tub-and-chiller", path)
            if component and not complete:
                tier += 4
            if complete and hits:
                tier -= 1
        return (2, tier, -hits)
    if re.search(r"dealer|wholesale", path):
        return (3, 0)
    return None


def evidence_links(html, text, source_url, product):
    parser = PageHTML()
    parser.feed((html or "")[:MAX_HTML_CHARS])
    candidates = list(parser.links)
    for match in re.finditer(r'\[([^\]\n]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)|href=["\']([^"\']+)["\']', text, re.I):
        candidates.append((match.group(2) or match.group(3), match.group(1) or ""))
    links = {}
    for href, label in candidates:
        if not href or href.startswith("#"):
            continue
        target = urldefrag(urljoin(source_url, href))[0]
        if domain_from_url(target) != domain_from_url(source_url) or target.rstrip("/") == source_url.rstrip("/"):
            continue
        label = re.sub(r"\s+", " ", label).strip()[:200]
        rank = _page_priority(target, product, label)
        if rank is None:
            continue
        links.setdefault(target, {"url": target, "label": label, "discovered_from": source_url})
    ordered = sorted(links.values(), key=lambda row: (_page_priority(row["url"], product, row["label"]), len(row["url"])))
    return ordered[:MAX_LINKS], parser


def _read_page(url, context, tool):
    context.take_page()
    key = (url, tool, "html-evidence-v1", context.request.product)
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < 3600:
        return dict(cached[1], cache_hit=True)
    items = run_actor(RAG_BROWSER_ACTOR_ID, {
        "query": url, "maxResults": 1, "scrapingTool": tool,
        "outputFormats": ["markdown", "html"], "htmlTransformer": "none",
        # Keep actual navigation/footer links and office addresses. Never retain scripts.
        "removeElementsCssSelector": "script,style,noscript,svg,template,iframe,img[src^='data:'],[role='dialog'],[aria-modal='true']",
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
    html = item.get("html") or ""
    body = item.get("markdown") or item.get("text") or ""
    crawl = item.get("crawl") or {}
    if item.get("#error") or crawl.get("httpStatusCode", 200) >= 400:
        return None
    if is_search_destination(loaded_url) or is_blocked_domain(domain_from_url(loaded_url)):
        return None
    links, parser = evidence_links(html, body, loaded_url, context.request.product)
    visible_text = "".join(parser.parts).strip()
    body = visible_text or body
    if not body.strip():
        return None
    text = "\n".join([metadata.get("title") or "", metadata.get("description") or "", body])[:MAX_TEXT_CHARS]
    operation = context.operations[-1] if context.operations else {}
    page = {"url": loaded_url, "requested_url": url, "text": text, "scraping_tool": tool,
            "retrieved_at": time.time(), "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "actor_run_id": operation.get("run_id"), "dataset_id": operation.get("dataset_id"),
            "links": links, "html_captured": bool(html), "text_truncated": len(body) > MAX_TEXT_CHARS,
            "text_format": "visible_html_text" if visible_text else "markdown",
            "shopify_detected": bool(re.search(r"cdn\.shopify\.com|myshopify\.com|/cdn/shop/", html + body, re.I)),
            "main_text_chars": len("".join(parser.main_parts).strip()) if html else len(body.strip())}
    _CACHE[key] = (time.time(), page)
    return page


def fetch_page(url, context, *, attempts_left=None):
    page = _read_page(url, context, "raw-http")
    thin = not page or page.get("main_text_chars", len(page["text"].strip())) < 400 or re.search(r"enable javascript|javascript is required", page["text"], re.I)
    if (thin and context.request.allow_browser_fallback and (attempts_left is None or attempts_left > 1)
            and context.pages < context.request.max_pages):
        from backend.research_context import JobStopped, LimitReached
        try:
            browser = _read_page(url, context, "browser-playwright")
        except (JobStopped, LimitReached):
            raise
        except Exception:
            browser = None
        if browser and (not page or browser.get("main_text_chars", len(browser["text"])) > page.get("main_text_chars", len(page["text"]))):
            page = dict(browser, browser_fallback=True)
    return page


def fetch_website_pages(base_url, context):
    before = context.pages
    first = fetch_page(normalize_url(base_url), context, attempts_left=context.request.max_pages_per_supplier)
    attempts = max(1, context.pages - before)
    if not first:
        return []
    pages, attempted_kinds = [first], set()
    domain = domain_from_url(first["url"])
    seen = {base_url.rstrip("/"), first["url"].rstrip("/")}
    candidates = {}

    def discover(page):
        # Read legacy Markdown fixtures as well as the separately captured HTML anchors.
        links = page.get("links", []) + evidence_links("", page["text"], page["url"], context.request.product)[0]
        for link in links:
            target = link["url"]
            if domain_from_url(target) != domain or target.rstrip("/") in seen:
                continue
            rank = _page_priority(target, context.request.product, link.get("label", ""))
            if rank is not None:
                candidates.setdefault(target, dict(link, rank=rank, kind="hq" if rank[0] < 2 else "product" if rank[0] == 2 else "dealer"))

    discover(first)
    while candidates and attempts < context.request.max_pages_per_supplier and context.pages < context.request.max_pages:
        context.checkpoint()
        needs_hq = bool(context.request.allowed_countries) and not any(has_company_location(p["text"], p["url"]) for p in pages)
        # A footer city is a location lead, not HQ proof. Contact can establish office context.
        cues = [re.escape(cue) for country in context.request.allowed_countries
                for cue in COUNTRY_LOCATION_CUES.get(country, [country])]
        location_hint = bool(cues) and any(re.search(r",\s*(?:"+"|".join(cues)+r")\b", p["text"], re.I) for p in pages)
        kinds = {c["kind"] for c in candidates.values()}
        if needs_hq and "hq" in kinds and ("hq" not in attempted_kinds or "product" in attempted_kinds):
            preferred = "hq"
        elif "product" in kinds:
            preferred = "product"
        else:
            preferred = "hq"
        def selection_rank(url):
            candidate = candidates[url]
            contact = bool(re.search(r"contact", urlsplit(url).path, re.I))
            return (candidate["kind"] != preferred,
                    not contact if preferred == "hq" and location_hint else False,
                    candidate["rank"], len(urlsplit(url).path), url)
        target = min(candidates, key=selection_rank)
        candidate = candidates.pop(target)
        seen.add(target.rstrip("/"))
        attempted_kinds.add(candidate["kind"])
        before = context.pages
        try:
            page = fetch_page(target, context, attempts_left=context.request.max_pages_per_supplier-attempts)
        except (JobStopped, LimitReached):
            raise
        except Exception as exc:
            context.fetch_failures.append({"url": target, "error_type": type(exc).__name__})
            page = None
        finally:
            attempts += max(1, context.pages-before)
        if page and domain_from_url(page["url"]) == domain:
            seen.add(page["url"].rstrip("/"))
            candidates.pop(page["url"], None)
            page = dict(page, discovered_from=candidate.get("discovered_from"), evidence_purpose=candidate["kind"])
            pages.append(page)
            discover(page)
    return pages


COUNTRY_LOCATION_CUES = {
    "United States": ["United States", "USA", "California", "Oregon", "Washington", "Tennessee", "Texas", "New York", "Colorado", "Arizona", "Florida"],
    "Canada": ["Canada", "Ontario", "British Columbia", "Quebec", "Alberta", "Nova Scotia"],
    "United Kingdom": ["United Kingdom", "England", "Scotland", "Wales", "Britain"],
    "Germany": ["Germany", "Deutschland"], "Australia": ["Australia"],
}


def _windows(text, pattern, *, limit=12, before=180, after=850):
    result = []
    for match in re.finditer(pattern, text, re.I):
        start = max(0, match.start()-before)
        paragraph_start = text.rfind("\n\n", max(0, match.start()-500), match.start())
        if paragraph_start >= 0:
            start = paragraph_start + 2
        end = min(len(text), match.end()+after)
        # Keep a heading together with its value/next paragraph (e.g. HQ + city or bundle + contents).
        paragraph_end = text.find("\n\n", match.end()+min(250, after//2), end)
        if paragraph_end >= 0:
            end = paragraph_end
        excerpt = text[start:end]
        if excerpt not in result:
            result.append(excerpt)
        if len(result) >= limit:
            break
    return result


def prompt_pages(pages, product, *, countries=None, extra_terms=None):
    # Reserve space for each evidence type; long exclusion lists cannot crowd out products/roles.
    terms = _product_terms(product)
    specific = terms - {"complete", "system", "primary", "supplier", "product"}
    config = r"\b(?:includ\w*|integrated|all[ -]in[ -]one|bundle|paired|package)\b"
    if re.search(r"cold|plunge", product, re.I):
        config += r"|\b(?:tub|chiller)\b"
    hq = r"headquarters|\bhq\b|based (?:just )?(?:outside|in|near)|head office|office address|located in|our office"
    country = [re.escape(cue) for name in countries or [] for cue in COUNTRY_LOCATION_CUES.get(name, [name])]
    product_pattern = "|".join(re.escape(t) for t in sorted(specific, key=len, reverse=True)) or re.escape(product)
    result = []
    for page in pages:
        text = page["text"]
        excerpts = []
        def add(values, count):
            added = 0
            for excerpt in values:
                if not excerpt.strip() or any(excerpt in old for old in excerpts):
                    continue
                excerpts.append(excerpt)
                added += 1
                if added >= count:
                    break
        add([text[:900]], 1)
        add(_windows(text, hq, limit=8, after=500), 3)
        product_windows = _windows(text, config, limit=60) + _windows(text, product_pattern, limit=60)
        product_windows.sort(key=lambda s: (-(sum(term in s.casefold() for term in specific) + 2*bool(re.search(config, s, re.I))), -len(s)))
        add(product_windows, 5)
        add(_windows(text, r"manufactur\w*|own brand|engineer\w*|our brand|we design", after=500), 2)
        add(_windows(text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", after=180), 1)
        if country:
            add(_windows(text, "|".join(country), after=400), 1)
        if extra_terms:
            extra = "|".join(re.escape(t) for value in extra_terms for t in _product_terms(value))
            if extra:
                add(_windows(text, extra, after=300), 1)
        product_links = [link for link in page.get("links", [])
                         if (rank := _page_priority(link["url"], product, link.get("label", ""))) and rank[0] == 2]
        product_links.sort(key=lambda link: _page_priority(link["url"], product, link.get("label", "")))
        result.append({"url": page["url"], "excerpts": excerpts[:14], "observed_product_links": product_links[:10]})
    return result
