"""Conservative location support, shared by page selection and qualification.

This checks the meaning of a location passage, not the country or company identity.
Those still require the supplier analysis and its official source.
"""
import re
import unicodedata
from bisect import bisect_right
from backend.location_text import SELF_LOCATION_RE, NEGATION, ambiguous_shared_location, shared_headquarters


def normalize_quote(value):
    value = unicodedata.normalize("NFKC", value or "")
    for src, dst in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
                     ("\u2013", "-"), ("\u2014", "-")):
        value = value.replace(src, dst)
    return re.sub(r"\s+", " ", value).strip()


_NEGATION = NEGATION
_NEGATED = re.compile(r"\b" + _NEGATION + r"\b.{0,35}\b(?:based|located|headquartered|headquarters|hq|office)\b|"
                      r"\b(?:headquarters|hq|office)\b.{0,20}\b" + _NEGATION + r"\b", re.I)
_SITE_TYPES = [(kind, re.compile(pattern, re.I)) for kind, pattern in [
    ("shipping_or_returns", r"\b(?:shipping|ships?|shipped|deliver(?:s|y|ies)?|billing|returns?|service area)\b|\b(?:your|enter (?:an?|your))\s+(?:office\s+)?address\b"),
    ("customer_or_dealer", r"\b(?:customer|testimonial|dealer)\b"),
    ("workshop", r"\bworkshops?\b"),
    ("factory", r"\b(?:factory|factories|manufacturing facility|production facility)\b"),
    ("warehouse", r"\b(?:warehouse|distribution cent(?:er|re)|fulfil(?:l)?ment)\b"),
    ("showroom", r"\bshowrooms?\b"),
]]
_ORIGIN = re.compile(r"\b(?:born|founded|started|established|originated|assembled|made|handcrafted|manufactured|built|produced|engineered|tested)\b"
                     r".{0,30}\b(?:in|at)\b", re.I)
_HEAD_OFFICE = re.compile(r"\b(?:headquarters|hq|head office)\b", re.I)
_BASED = re.compile(r"\b(?:based|headquartered|located|situated)\s+(?:just\s+)?(?:in|near|outside|at)\s+"
                    r"[A-Za-z\u00c0-\u024f][A-Za-z\u00c0-\u024f .'\-]{1,70}", re.I)
_CITY_REGION = re.compile(r"\b[A-Za-z\u00c0-\u024f][A-Za-z\u00c0-\u024f .'\-]{1,40},\s*"
                          r"(?:[A-Z]{2}\b|[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+){0,2}\b)")
_STREET = re.compile(r"\b\d{1,6}\s+[A-Za-z0-9 .'\-]{1,70}\b"
                    r"(?:road|rd|street|st|avenue|ave|drive|dr|lane|ln|way|boulevard|blvd|line|court|ct|place|pl)\b", re.I)
_SELF_LOCATION = SELF_LOCATION_RE
_OFFICE_CONTEXT = re.compile(r"\boffice(?: address)?\b(?!\s+(?:hours|phone|email|number|supplies))", re.I)
_NAMED_LOCATION = re.compile(r"(?:\b(?:in|at|near|outside)\s+|:\s*)"
                             r"(?!(?:our|the|your|this|that|a|an|person|us)\b)[A-Za-z]{2,}", re.I)
HQ_LOCATION_TYPES = {"headquarters", "office", "company_base"}


def _site_kind(text):
    shared_hq = shared_headquarters(text)
    return next((kind for kind, pattern in _SITE_TYPES if pattern.search(text)
                 and not (shared_hq and kind in {"factory", "warehouse"})), None)


def _location_label(text):
    # Only nearby label/value blocks may lend context to a clipped location quote.
    if len(text) > 80 or len(text.split()) > 8 or _STREET.search(text) or _CITY_REGION.search(text):
        return False
    return bool(_site_kind(text) or _HEAD_OFFICE.search(text) or _OFFICE_CONTEXT.search(text))


def _contexts(quote, source, *, sentence_bound=True):
    needle = normalize_quote(quote)
    blocks = [value for part in re.split(r"\n\s*\n", source) if (value := normalize_quote(part))]
    starts, offset = [], 0
    for block in blocks:
        starts.append(offset)
        offset += len(block) + 1
    normalized = " ".join(blocks)
    for match in re.finditer(re.escape(needle), normalized, re.I):
        first = bisect_right(starts, match.start()) - 1
        last = bisect_right(starts, match.end() - 1) - 1
        prefix = []
        # An earlier address or an unrelated paragraph separates location cards.
        for previous in reversed(blocks[max(0, first-3):first]):
            if _location_label(previous):
                prefix.insert(0, previous)
                break
            if (len(previous) > 100 or not (_STREET.search(previous) or _CITY_REGION.search(previous))
                    or (_STREET.search(needle) and _STREET.search(previous))
                    or (_CITY_REGION.search(needle) and _CITY_REGION.search(previous))):
                break
            prefix.insert(0, previous)
        begin = max(starts[first], match.start()-140)
        end = min(starts[last]+len(blocks[last]), match.end()+300)
        if not sentence_bound:
            yield " ".join(prefix + [normalized[begin:end]])
            continue
        before = re.split(r"(?<=[.!?])\s+", normalized[begin:match.start()])[-1]
        after = "" if needle.endswith((".", "!", "?")) else re.split(r"(?<=[.!?])\s+", normalized[match.end():end])[0]
        yield " ".join(prefix + [before + normalized[match.start():match.end()] + after])


def location_quote_kind(quote, source="", source_url=""):
    """Classify a literal location passage; a Contact/About URL grants no location type."""
    quote = normalize_quote(quote)
    # An independent shipping action is not the subject of the location assertion.
    quote = re.split(r",?\s+(?:and\s+)?(?:we\s+)?(?:ship(?:s|ping)?\s+(?:across|to|worldwide)|offer\s+free\s+shipping)\b", quote, maxsplit=1, flags=re.I)[0]
    if not quote or _NEGATED.search(quote) or ambiguous_shared_location(quote):
        return "unknown"
    if shared_headquarters(quote):
        if source and any(ambiguous_shared_location(c) for c in _contexts(quote, source)):
            return "unknown"
        return "headquarters"
    if kind := _site_kind(quote):
        return kind
    explicit_hq, explicit_office = bool(_HEAD_OFFICE.search(quote)), bool(_OFFICE_CONTEXT.search(quote))
    if _ORIGIN.search(quote) and not (explicit_hq or explicit_office):
        return "manufacturing_origin"
    has_value = bool(_CITY_REGION.search(quote) or _STREET.search(quote) or
                     ((explicit_hq or explicit_office) and _NAMED_LOCATION.search(quote)))
    contexts = _contexts(quote, source) if source else [quote]
    rejected_kind = "unknown"
    for context in contexts:
        if _NEGATED.search(context) or ambiguous_shared_location(context):
            continue
        prefix = context.casefold().split(quote.casefold(), 1)[0]
        # Check the subject before accepting a clipped "based in" or address quote.
        if kind := _site_kind(prefix):
            rejected_kind = kind
            continue
        if has_value and (explicit_hq or explicit_office):
            return "headquarters" if explicit_hq else "office"
        if has_value and (_HEAD_OFFICE.search(prefix) or _OFFICE_CONTEXT.search(prefix)):
            return "headquarters" if _HEAD_OFFICE.search(prefix) else "office"
        # A separate self-attributed shipping action is not the location's subject.
        subject_context = re.split(r",?\s+(?:and\s+)?(?:we\s+)?(?:ship(?:s|ping)?\s+(?:across|to|worldwide)|offer\s+free\s+shipping)\b", context, maxsplit=1, flags=re.I)[0]
        if kind := _site_kind(subject_context):
            rejected_kind = kind
        elif _BASED.search(quote) or _SELF_LOCATION.search(quote):
            return "company_base"
        elif _ORIGIN.search(context):
            rejected_kind = "manufacturing_origin"
    if rejected_kind == "unknown" and source:
        # Preserve useful rejection diagnostics without lending a preceding/following
        # sentence authority to establish a company location.
        rejected_kind = next((kind for context in _contexts(quote, source, sentence_bound=False)
                              if (kind := _site_kind(context))), "unknown")
    return rejected_kind


def hq_quote_acceptable(quote, source="", source_url=""):
    return location_quote_kind(quote, source, source_url) in HQ_LOCATION_TYPES


def has_address_lead(text):
    # Routing only. Even a literal address cannot qualify without its own office/HQ context.
    return bool(_STREET.search(normalize_quote(text)))


def has_company_location(text, source_url=""):
    # Only a routing hint. Qualification always validates the actual model quote separately.
    for line in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z])", text):
        if (_HEAD_OFFICE.search(line) or _OFFICE_CONTEXT.search(line) or _BASED.search(line)
                or _SELF_LOCATION.search(line) or _STREET.search(line) or _CITY_REGION.search(line)) and hq_quote_acceptable(line[:250], text, source_url):
            return True
    return False
