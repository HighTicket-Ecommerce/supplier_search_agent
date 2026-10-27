from urllib.parse import urlparse
import re

import tldextract

_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)

def normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    if "://" not in u:
        u = "https://" + u
    return u

def domain_from_url(u: str) -> str:
    try:
        parsed = urlparse(normalize_url(u))
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            return ""
        host = (parsed.hostname or "").lower().rstrip(".")
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def is_search_destination(url):
    return bool(re.fullmatch(r"(?:google\.(?:com|ca|co\.uk|de|com\.au)|bing\.com)", domain_from_url(url)))


def registrable_domain(host):
    host = (host or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    return _EXTRACT(host).registered_domain


def spreadsheet_safe(value):
    """Prefix text that a spreadsheet would evaluate as a formula."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value
