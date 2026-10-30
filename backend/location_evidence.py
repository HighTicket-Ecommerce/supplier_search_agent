"""Conservative location support, shared by page selection and qualification.

This checks the meaning of a location passage, not the country or company identity.
Those still require the supplier analysis and its official source.
"""
import re
import unicodedata
from urllib.parse import urlsplit


def normalize_quote(value):
    value = unicodedata.normalize("NFKC", value or "")
    for src, dst in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
                     ("\u2013", "-"), ("\u2014", "-")):
        value = value.replace(src, dst)
    return re.sub(r"\s+", " ", value).strip()


_NEGATION = r"(?:not|never|no longer|aren't|isn't|weren't|wasn't)"
_NEGATED = re.compile(r"\b" + _NEGATION + r"\b.{0,35}\b(?:based|located|headquartered|headquarters|hq|office)\b|"
                      r"\b(?:headquarters|hq|office)\b.{0,20}\b" + _NEGATION + r"\b", re.I)
_NON_LOCATION = re.compile(r"\b(?:shipping|ships?|shipped|deliver(?:s|y|ies)?|billing|returns?|"
                           r"warehouse|showroom|factory|factories|distribution cent(?:er|re)|"
                           r"fulfil(?:l)?ment|service area|customer|testimonial)\b|"
                           r"\b(?:your|enter (?:an?|your))\s+(?:office\s+)?address\b", re.I)
_OTHER_SITE = re.compile(r"\b(?:warehouse|showroom|factory|factories|distribution cent(?:er|re)|"
                         r"fulfil(?:l)?ment|customer|testimonial|dealer)\b", re.I)
_ORIGIN = re.compile(r"\b(?:born|founded|started|established|originated|assembled|made|handcrafted|manufactured|built|produced|engineered|tested)\b"
                     r".{0,30}\b(?:in|at)\b", re.I)
_HEAD_OFFICE = re.compile(r"\b(?:headquarters|hq|head office|registered office|office address)\b", re.I)
_BASED = re.compile(r"\b(?:based|headquartered|located|situated)\s+(?:just\s+)?(?:in|near|outside|at)\s+"
                    r"[A-Za-z\u00c0-\u024f][A-Za-z\u00c0-\u024f .'\-]{1,70}", re.I)
_CITY_REGION = re.compile(r"\b[A-Za-z\u00c0-\u024f][A-Za-z\u00c0-\u024f .'\-]{1,40},\s*"
                          r"(?:[A-Z]{2}\b|[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+){0,2}\b)")
_STREET = re.compile(r"\b\d{1,6}\s+[A-Za-z0-9 .'\-]{1,70}\b"
                    r"(?:road|rd|street|st|avenue|ave|drive|dr|lane|ln|way|boulevard|blvd|line|court|ct|place|pl)\b", re.I)
_SELF_LOCATION = re.compile(r"\bwe(?:'re|\s+are)\s+(?:an?\s+)?[^.!?]{1,70},\s*(?:[A-Z]{2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+"
                           r"(?:manufacturer|company|business)\b", re.I)
_OFFICE_CONTEXT = re.compile(r"\b(?:our office|office address|headquarters|hq|head office|contact (?:us|[A-Z][\w -]+)|"
                              r"company address|business address)\b", re.I)


def _contexts(quote, source):
    needle = normalize_quote(quote)
    found = False
    for paragraph in re.split(r"\n\s*\n", source):
        paragraph = normalize_quote(paragraph)
        for match in re.finditer(re.escape(needle), paragraph, re.I):
            found = True
            # A heading or shipping sentence elsewhere on a page cannot authorize or void a quote.
            before = re.split(r"[.!?]\s+", paragraph[max(0, match.start()-140):match.start()])[-1]
            after = re.split(r"[.!?]\s+", paragraph[match.end():min(len(paragraph), match.end()+100)])[0]
            yield before + paragraph[match.start():match.end()] + after
    if not found:
        # Tables/cards often put "Headquarters" and its city in adjacent HTML blocks.
        # The whole quote must still be a contiguous match after whitespace normalization.
        normalized = normalize_quote(source)
        for match in re.finditer(re.escape(needle), normalized, re.I):
            yield normalized[max(0, match.start()-140):min(len(normalized), match.end()+100)]


def hq_quote_acceptable(quote, source="", source_url=""):
    quote = normalize_quote(quote)
    shared_hq = bool(re.search(r"\bour\s+(?:headquarters|hq|head office)\s+and\s+(?:factory|warehouse)\s+(?:are|is)\s+(?:in|at)\b", quote, re.I))
    if not quote or (_NON_LOCATION.search(quote) and not shared_hq) or _NEGATED.search(quote):
        return False
    explicit_hq = bool(_HEAD_OFFICE.search(quote))
    if _ORIGIN.search(quote) and not explicit_hq:
        return False
    contexts = list(_contexts(quote, source)) if source else [quote]
    contact_page = bool(re.search(r"(?:contact|about|company|our-story|location)", urlsplit(source_url).path, re.I))
    for context in contexts:
        # A clipped quote from "not based in" or a warehouse/shipping address is not HQ proof.
        if _NEGATED.search(context):
            continue
        if not explicit_hq:
            if _OTHER_SITE.search(context):
                continue
            if not _BASED.search(quote) and not _SELF_LOCATION.search(quote) and (_NON_LOCATION.search(context) or _ORIGIN.search(context)):
                continue
            prefix = context.casefold().split(quote.casefold(), 1)[0]
            if _NON_LOCATION.search(prefix):
                continue
        if explicit_hq:
            # A heading alone ("Our HQ") contains no location; require a location in the quote.
            tail = _HEAD_OFFICE.sub("", quote).strip(" :|-#")
            if _CITY_REGION.search(quote) or _STREET.search(quote) or re.search(
                    r"\b(?:in|at|near|outside)\s+[A-Za-z]{2,}|:\s*[A-Za-z]{2,}", quote, re.I):
                return True
            if tail and tail.casefold() not in {"our", "the", "is", "are", "address"} and _CITY_REGION.search(context):
                return True
        if _BASED.search(quote) or _SELF_LOCATION.search(quote):
            return True
        if _STREET.search(quote) and (contact_page or _OFFICE_CONTEXT.search(context)):
            return True
        if _CITY_REGION.search(quote) and _OFFICE_CONTEXT.search(context):
            return True
    return False


def has_company_location(text, source_url=""):
    # Only a routing hint. Qualification always validates the actual model quote separately.
    for line in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z])", text):
        if hq_quote_acceptable(line[:250], text, source_url):
            return True
    return False
