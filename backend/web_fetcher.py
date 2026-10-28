import hashlib
from html.parser import HTMLParser
import re
import time
from urllib.parse import urljoin, urlsplit, urldefrag, unquote, parse_qsl

from backend.actor_client import run_actor
from backend.config import RAG_BROWSER_ACTOR_ID
from backend.filters import is_blocked_domain
from backend.location_evidence import has_address_lead, has_company_location
from backend.utils import domain_from_url, normalize_url, is_search_destination
from backend.research_context import JobStopped, LimitReached
from backend.product_brief import positive_brief

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
    # Exclusions are evidence for the model, never positive navigation keywords.
    positive = re.split(r"\b(?:excluding|except(?: for)?|but not)\b", product or "", maxsplit=1, flags=re.I)[0]
    words = re.findall(r"\w+", positive.casefold().replace("_", " "))
    return {t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t
            for t in words if len(t) >= 3 and t not in {"and", "the", "for", "with", "our", "not"}}


def _positive_product_brief(product):
    return positive_brief(product)


def _page_priority(url, product, label="", *, excluded_products=None, trade_policy=False):
    parsed = urlsplit(url)
    path = unquote(parsed.path).casefold()
    if re.search(r"\.(?:jpe?g|png|webp|gif|svg|ico|css|js|json|pdf|zip|mp4|woff2?)$", path) or re.search(r"/(?:cdn|assets)/", path):
        return None
    # Only public entry/policy pages are candidates; account actions stay excluded.
    public_entry = bool(re.fullmatch(r"/(?:account/(?:login|register)|login|register|sign-in)/?", path))
    public_query = all(key.casefold() == "returnurl" for key, _ in parse_qsl(parsed.query, keep_blank_values=True))
    if trade_policy and public_entry and public_query:
        return (3, 0)
    if re.search(r"logout|password|reset|delete|subscribe", path):
        return None
    if re.search(r"privacy|terms|checkout|cart|login|account|shipping|refund|returns|blog|news", path):
        return None
    positive_product = _positive_product_brief(product)
    terms = _product_terms(positive_product) - {"complete", "system", "supplier", "product", "primary"}
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
    # Decode category facets and match whole words: Fire must not match fireplaces,
    # and the three-letter product word "gas" must distinguish gas from charcoal.
    target = unquote(parsed.path + " " + parsed.query) + " " + label
    target_terms = _product_terms(target)
    hits = len(terms & target_terms)
    if product_path or collection_path or hits:
        # A matching collection/product beats an editorial landing page or unrelated product.
        tier = (0 if product_path else 1) if hits else 3
        if not product_path and not collection_path:
            tier = 2
        # Inspect the item/category subject, before included extras. A grill with
        # accessories still outranks accessories for a grill.
        subjects = [re.split(r"\b(?:with|including|includes?)\b", value, maxsplit=1, flags=re.I)[0]
                    for value in [label, unquote(parsed.path).rsplit("/", 1)[-1].replace("-", " "), unquote(parsed.query)]]
        subject_terms = [_product_terms(value) for value in subjects]
        for exclusion in excluded_products or []:
            # Broad category exclusions must not bury a potentially relevant
            # dual-purpose product (e.g. a hot/cold tub). The model evaluates
            # those contents; only explicit accessory/service product subjects
            # are demoted here, alongside excluded category/facet links.
            if product_path and not re.search(r"\b(?:accessor\w*|parts?|replacements?|filters?|covers?|services?)\b", exclusion, re.I):
                continue
            excluded = _product_terms(exclusion)
            if excluded and not excluded <= terms and any(excluded <= subject for subject in subject_terms):
                tier += 4
                break
        if re.search(r"complete|system", product, re.I) and re.search(r"cold|plunge", product, re.I):
            # "All-in-one plunge filter" names an accessory, even with system keywords.
            # Inspect the item slug/label, not a parent collection or included extras.
            names = [re.sub(r"[-_]+", " ", unquote(name).casefold())
                     for name in (positive_product, path.rstrip("/").rsplit("/", 1)[-1], label)]
            heads = [re.split(r"\b(?:with|including|includes?|for|compatible with|suitable for)\b", name, maxsplit=1)[0] for name in names]
            accessory_pattern = r"\b(?:accessor(?:y|ies)|filters?|covers?|(?:dry )?mats?|chemicals?|cleaners?|hoses?|steps?)\b"
            def complete_configuration(name):
                marker = re.search(r"\b(?:bundle|package|combo|system|kit)\b", name)
                if not marker:
                    return False
                subject = name[:marker.start()]
                if re.search(accessory_pattern, subject):
                    return False
                pair = re.search(r"\b(?:tub|plunge|ice bath)\b", subject) and re.search(r"\bchiller\b", subject)
                primary = re.search(r"\b(?:plunge|ice bath)\b", subject) and re.search(r"\b(?:complete|integrated|all in one)\b", subject)
                return bool(pair or primary)
            accessory = not re.search(accessory_pattern, heads[0]) and any(
                re.search(accessory_pattern, name) and not complete_configuration(name) for name in heads[1:])
            component = re.search(r"chiller|tubs?-only", path)
            complete = any(complete_configuration(name) for name in heads[1:]) or re.search(r"bundle|integrated|all-in-one|tub-and-chiller", path)
            if accessory or (component and not complete):
                tier += 4
            elif complete:
                tier = min(tier - 1, -1)
        return (2, tier, -hits)
    if re.search(r"dealer|wholesale", path):
        return (3, 0)
    return None


def evidence_links(html, text, source_url, product, *, excluded_products=None, trade_policy=False):
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
        rank = _page_priority(target, product, label, excluded_products=excluded_products, trade_policy=trade_policy)
        if rank is None:
            continue
        links.setdefault(target, {"url": target, "label": label, "discovered_from": source_url})
    ordered = sorted(links.values(), key=lambda row: (_page_priority(row["url"], product, row["label"],
                     excluded_products=excluded_products, trade_policy=trade_policy), len(row["url"])))
    return ordered[:MAX_LINKS], parser


def _read_page(url, context, tool):
    context.take_page()
    trade_policy = context.request.allowed_supplier_types == ["Distributor"]
    key = (url, tool, "html-evidence-v2", context.request.product, tuple(context.request.excluded_products), trade_policy)
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
    links, parser = evidence_links(html, body, loaded_url, context.request.product,
        excluded_products=context.request.excluded_products, trade_policy=trade_policy)
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
    trade_policy = context.request.allowed_supplier_types == ["Distributor"]

    def discover(page):
        # Read legacy Markdown fixtures as well as the separately captured HTML anchors.
        links = page.get("links", []) + evidence_links("", page["text"], page["url"], context.request.product,
            excluded_products=context.request.excluded_products, trade_policy=trade_policy)[0]
        for link in links:
            target = link["url"]
            if domain_from_url(target) != domain or target.rstrip("/") in seen:
                continue
            rank = _page_priority(target, context.request.product, link.get("label", ""),
                excluded_products=context.request.excluded_products, trade_policy=trade_policy)
            if rank is not None:
                if trade_policy and rank[0] == 3 and "trade" in attempted_kinds:
                    continue
                candidates.setdefault(target, dict(link, rank=rank, kind="hq" if rank[0] < 2 else "product" if rank[0] == 2
                                                   else "trade" if trade_policy else "dealer"))

    discover(first)
    while candidates and attempts < context.request.max_pages_per_supplier and context.pages < context.request.max_pages:
        context.checkpoint()
        needs_hq = bool(context.request.allowed_countries) and not any(has_company_location(p["text"], p["url"]) for p in pages)
        # A footer city is a location lead, not HQ proof. Contact can establish office context.
        cues = [re.escape(cue) for country in context.request.allowed_countries
                for cue in COUNTRY_LOCATION_CUES.get(country, [country])]
        location_hint = any(has_address_lead(p["text"]) for p in pages) or (
            bool(cues) and any(re.search(r",\s*(?:"+"|".join(cues)+r")\b", p["text"], re.I) for p in pages))
        kinds = {c["kind"] for c in candidates.values()}
        # This only schedules evidence collection; a wholesale word does not
        # qualify the company or prove any particular brand relationship.
        needs_trade = trade_policy and not any(re.search(
            r"\bwholesale (?:trade(?: only)?|distributor|only)\b|\btrade (?:customers )?only\b", p["text"], re.I) for p in pages)
        # After one company page and one product page, collect the missing
        # policy before a second company page can consume the final slot.
        if needs_trade and "trade" in kinds and "trade" not in attempted_kinds and ("product" in attempted_kinds or "product" not in kinds):
            preferred = "trade"
        elif needs_hq and "hq" in kinds and ("hq" not in attempted_kinds or "product" in attempted_kinds):
            preferred = "hq"
        elif "product" in kinds:
            preferred = "product"
        else:
            preferred = "hq"
        def selection_rank(url):
            candidate = candidates[url]
            contact = bool(re.search(r"contact", urlsplit(url).path, re.I))
            return (candidate["kind"] != preferred,
                    not contact if preferred == "hq" and location_hint and not trade_policy else False,
                    candidate["rank"], len(urlsplit(url).path), url)
        target = min(candidates, key=selection_rank)
        candidate = candidates.pop(target)
        seen.add(target.rstrip("/"))
        attempted_kinds.add(candidate["kind"])
        if candidate["kind"] == "trade":
            candidates = {key: value for key, value in candidates.items() if value["kind"] != "trade"}
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
        add(_windows(text, r"manufactur\w*|own brand|engineer\w*|our brand|we design|brand owner|"
                     r"\b(?:we|\w+) (?:distribute|distributes|supply third[ -]party)|authorized distributor|"
                     r"\bwholesale\b|\btrade only\b|\b(?:retailer|reseller|marketplace|publisher)\b", after=500), 2)
        add(_windows(text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", after=180), 1)
        if country:
            add(_windows(text, "|".join(country), after=400), 1)
        if extra_terms:
            extra = "|".join(re.escape(t) for value in extra_terms for t in _product_terms(value))
            if extra:
                add(_windows(text, extra, after=300), 1)
        product_links = [link for link in page.get("links", [])
                         if (rank := _page_priority(link["url"], product, link.get("label", ""), excluded_products=extra_terms)) and rank[0] == 2]
        product_links.sort(key=lambda link: _page_priority(link["url"], product, link.get("label", ""), excluded_products=extra_terms))
        result.append({"url": page["url"], "excerpts": excerpts[:14], "observed_product_links": product_links[:10]})
    return result
