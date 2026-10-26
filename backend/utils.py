from urllib.parse import urlparse
import re

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


def spreadsheet_safe(value):
    """Prefix text that a spreadsheet would evaluate as a formula."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value
