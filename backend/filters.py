from urllib.parse import urlparse

# =========================================================
# BLOCKED DOMAIN SUBSTRINGS
# =========================================================
BLOCKED_DOMAINS_CONTAINS = (
    # ------------------
    # Marketplaces
    # ------------------
    "amazon.",
    "ebay.",
    "alibaba.",
    "aliexpress.",
    "walmart.",
    "etsy.",
    "wayfair.",
    "overstock.",
    "rakuten.",
    "flipkart.",

    # ------------------
    # Big-box retailers
    # ------------------
    "homedepot.",
    "lowes.",
    "costco.",
    "samsclub.",
    "target.",
    "bestbuy.",
    "menards.",
    "ikea.",
    "acehardware.",
    "canadiantire.",
    "bunnings.",
    "homehardware.",
    "tractorsupply.",
    "harborfreight.",
    "fleetfarm.",
    "northerntool.",

    # ------------------
    # Social / UGC
    # ------------------
    "youtube.",
    "facebook.",
    "instagram.",
    "tiktok.",
    "pinterest.",
    "reddit.",
    "linkedin.",

    # ------------------
    # Reviews / forums
    # ------------------
    "trustpilot.",
    "yelp.",
    "glassdoor.",
    "quora.",

    # ------------------
    # Media / publishers
    # ------------------
    "wikipedia.org",
    "forbes.com",
    "fortune.com",
    "bloomberg.com",
    "wsj.com",
    "nytimes.com",
    "cnn.com",
    "bbc.",
    "reuters.com",
    "techcrunch.com",
    "cnet.com",
    "theverge.com",
    "thespruce.com",
    "healthline.com",
    "verywellhealth.com",
    "everydayhealth.com",
    "medium.com",

    # ------------------
    # Design / inspiration
    # ------------------
    "dribbble.com",
    "behance.net",
    "webflow.com",
)

# =========================================================
# BLOCKED TLDS (institutional)
# =========================================================
BLOCKED_TLDS = (
    ".gov",
    ".edu",
    ".mil",
)

# =========================================================
# BLOCKED ORG KEYWORDS (non-commercial orgs)
# =========================================================
BLOCKED_ORG_KEYWORDS = (
    "university",
    "college",
    "school",
    "institute",
    "research",
    "extension",
    "foundation",
    "association",
    "council",
    "regional",
)

# =========================================================
# PUBLIC API
# =========================================================
def is_blocked_domain_or_url(value: str) -> bool:
    """
    Returns True if domain or URL should be excluded entirely.
    Safe for SERP filtering and supplier validation.
    """
    if not value:
        return True

    v = value.lower().strip()

    # Normalize to domain if URL
    if "://" in v:
        parsed = urlparse(v)
        domain = parsed.netloc.lower()
    else:
        domain = v

    # ------------------
    # TLD block (.gov, .edu, etc)
    # ------------------
    for tld in BLOCKED_TLDS:
        if domain.endswith(tld):
            return True

    host = domain[4:] if domain.startswith("www.") else domain
    labels = [part for part in host.split(".") if part]

    for blocked in BLOCKED_DOMAINS_CONTAINS:
        blocked = blocked.lower().strip()
        if blocked.endswith("."):
            if blocked[:-1] in labels:
                return True
        elif host == blocked or host.endswith("." + blocked):
            return True

    if host.endswith(".org"):
        for kw in BLOCKED_ORG_KEYWORDS:
            if kw in host:
                return True

    return False


def is_blocked_domain(domain: str) -> bool:
    return is_blocked_domain_or_url(domain)
