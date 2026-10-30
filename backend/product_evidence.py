"""Verify supplied components for the complete cold-plunge brief.

Other categories retain their existing checks until their component requirements
are explicit. This is a conservative text check, not a catalogue/variant audit.
"""
import re
from urllib.parse import urlsplit

from backend.location_evidence import normalize_quote

_TUB = re.compile(r"\b(?:tubs?|barrels?|ice[ -]baths?)\b", re.I)
_CHILLER = re.compile(r"\b(?:chillers?|cooling units?)\b", re.I)
_INCLUSION = re.compile(r"\b(?:includ(?:e|es|ed)|comes? with|features?|pairs?|paired|combines?|integrated|built[ -]in)\b", re.I)
_NEGATIVE = re.compile(
    r"\b(?:not|never)\b.{0,25}\b(?:includ\w*|suppl\w*|provid\w*|come\w*)\b|"
    r"\b(?:chillers?|cooling units?)\b.{0,30}\b(?:not included|excluded|added|extra cost|additional cost)\b|"
    r"\bexcludes?\b.{0,30}\bchiller\b|\b(?:sold|available|purchased|ordered) separately\b|"
    r"\bno\s+(?:included\s+)?(?:chiller|tub)\b|\bwithout\s+(?:(?:a|the|any)\s+)?(?:chiller|tub)\b", re.I)
_UNCERTAIN = re.compile(
    r"\boptional(?:ly)?\b.{0,40}\b(?:chiller|cooling unit)\b|\bchiller\s+(?:is\s+)?optional\b|"
    r"\bcompatible\s+with\b.{0,80}\b(?:chiller|cooling unit)\b|\bchiller[ -]compatible\b|"
    r"\bchiller[ -]ready\b|\b(?:prepared|designed|pre[ -]?plumbed) for\s+(?:an?\s+)?(?:integrated\s+)?chiller\b|"
    r"\b(?:add|adding|upgrade)\b.{0,40}\bchiller\b|"
    r"\b(?:should|must|would|could|might|may|recommend(?:ed)?)\b.{0,50}\b(?:includ\w*|feature\w*|come\w*|integrated)\b", re.I)
_CHILLER_PART = re.compile(
    r"\bchiller\s+(?:compartments?|housings?|hoses?|connections?|connectors?|fittings?|filters?|covers?|controls?|control panels?|ports?)\b|"
    r"\b(?:compartment|housing)\b.{0,45}\bchiller\b", re.I)
_RELATED = re.compile(r"\b(?:related|recommended|accessories|standalone|components?|module)\b", re.I)
_ACCESSORY_TITLE = re.compile(r"\b(?:filters?|covers?|hoses?|compartments?|accessor(?:y|ies)|components?|modules?)\b", re.I)
_CATALOGUE_LIST = re.compile(r"\b(?:catalog(?:ue)?|product range|product list|our range|our products|products we (?:offer|sell))\b", re.I)
_EXCLUDED_HEADING = re.compile(r"^(?:what(?:\'s| is)\s+)?(?:not included|excluded|sold separately|optional(?: accessories| components)?|accessories|add[ -]ons?)\s*[:?-]?$", re.I)
_CONFIGURATION = re.compile(r"\b(?:bundles?|package|pairing|paired|all[ -]in[ -]one|complete systems?)\b", re.I)


def required_components(product):
    name = normalize_quote(product).casefold()
    head = re.split(r"\bwith\b", name, maxsplit=1)[0]
    if not re.search(r"\bcold[ -]plunges?\b|\bice[ -]baths?\b", name):
        return []
    explicit_pair = bool(re.search(r"\b(?:tubs?|barrels?)\b", head) and _CHILLER.search(head))
    if _ACCESSORY_TITLE.search(head) or (not explicit_pair and re.search(r"\bchillers?(?:\s+(?:systems?|kits?|bundles?))?$", head)):
        return []
    if re.search(r"\b(?:complete|systems?|bundles?|kits?)\b", name) or (_TUB.search(name) and _CHILLER.search(name)):
        return ["tub", "chiller"]
    return []


def _passages(quote, text):
    """Keep the quoted clause and a nearby heading; never combine product cards."""
    needle = normalize_quote(quote)
    blocks = [value for part in re.split(r"\n\s*\n", text) if (value := normalize_quote(part))]
    for index, block in enumerate(blocks):
        for match in re.finditer(re.escape(needle), block, re.I):
            prefix = block[:match.start()]
            boundaries = list(re.finditer(r"[.!?]\s+", prefix))
            begin = boundaries[-1].end() if boundaries else 0
            tail = re.search(r"[.!?](?:\s|$)", block[match.end():])
            end = match.end() if needle.endswith((".", "!", "?")) else match.end()+tail.end() if tail else len(block)
            heading = blocks[index-1] if index and len(blocks[index-1]) <= 150 and not re.search(r"[.!?]", blocks[index-1]) else ""
            yield block[begin:end], heading


def _primary_tub(page, matched_urls):
    title = next((normalize_quote(line.replace("™", "").replace("®", ""))
                  for line in page["text"].splitlines() if line.strip()), "")
    head = re.split(r"\bwith\b", title, maxsplit=1, flags=re.I)[0]
    path = urlsplit(page["url"]).path
    matched = page["url"] in matched_urls or page.get("requested_url") in matched_urls
    if not matched or re.search(r"/collections?/|/catalog|\b(?:range|collection|catalogue)\b", path + " " + title, re.I):
        return False
    if _ACCESSORY_TITLE.search(head) or (_CHILLER.search(head) and not _TUB.search(head)):
        return False
    return bool(_TUB.search(title) or re.search(r"\bcold[ -]plunge\b", title, re.I))


def verify_product_configuration(product, evidence, pages, matched_urls):
    components = required_components(product)
    result = {"status": "not_required" if not components else "not_established",
              "required_components": components, "supporting_evidence": [], "observations": []}
    if not components:
        return result
    for entry in evidence:
        if entry.get("claim") != "product_match":
            continue
        quote = normalize_quote(entry.get("quote", ""))
        if not quote:
            continue
        for page in pages:
            if entry.get("source_url") not in {page["url"], page.get("requested_url")}:
                continue
            passages = list(_passages(quote, page["text"]))
            if not passages and quote.casefold() in normalize_quote(page["text"]).casefold():
                result["observations"].append({"source_url": entry["source_url"], "quote": entry["quote"],
                                               "reason": "configuration_quote_crosses_source_blocks"})
            for clause, heading in passages:
                reason, basis = "components_not_affirmatively_supplied", None
                if _EXCLUDED_HEADING.search(heading) or _NEGATIVE.search(clause):
                    reason = "components_negated_or_sold_separately"
                elif _CHILLER_PART.search(clause):
                    reason = "chiller_compartment_or_accessory_only"
                elif _UNCERTAIN.search(clause):
                    reason = "optional_compatible_or_hypothetical_chiller"
                elif _CATALOGUE_LIST.search(heading + " " + clause) and not _CONFIGURATION.search(clause):
                    reason = "separate_product_list_only"
                elif _CHILLER.search(quote):
                    affirmative = bool(_INCLUSION.search(quote) or _INCLUSION.search(clause) or _INCLUSION.search(heading))
                    if _TUB.search(quote) and (affirmative or "+" in quote):
                        basis = "combined_tub_and_chiller"
                    elif affirmative and _primary_tub(page, matched_urls) and not _RELATED.search(heading + " " + clause):
                        basis = "included_chiller_in_primary_tub"
                observation = {"source_url": entry["source_url"], "quote": entry["quote"],
                               "reason": basis or reason, "context": clause[:800]}
                result["observations"].append(observation)
                if basis:
                    result["status"] = "supported"
                    result["supporting_evidence"].append(observation)
    return result
