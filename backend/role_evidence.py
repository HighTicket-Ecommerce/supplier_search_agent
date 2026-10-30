"""Conservative, source-local support for the model's exact company role.

Own product design can support a product brand, but does not prove production.
This is a text guard, not a legal ownership or supply-chain audit.
"""
import re

from backend.location_evidence import normalize_quote


_CUES = re.compile(r"\b(?:manufactur\w*|produc(?:e|es|ed|tion|ing)|build\w*|built|handbuilt|craft\w*|design\w*|engineer\w*|"
                   r"brands?|own\w*|creates?|make|distribut\w*|wholesal\w*|retail\w*|resell\w*|suppl\w*|"
                   r"marketplace|publish\w*|reviews?|blog|media)\b", re.I)
_GOODS = re.compile(r"\b(?:products?|goods|equipment|systems?|heaters?|saunas?|tubs?|plunges?|chillers?|"
                    r"grills?|devices?|furniture|appliances?|components?)\b", re.I)
_UNSUPPORTED = re.compile(r"\b(?:not|never|no longer|don't|doesn't|didn't|isn't|aren't|cannot|can't|won't|haven't|hasn't|previously|formerly|used to|plan to|planning to|"
                          r"hope to|aim to|want to|will|would|could|might|should)\b", re.I)
_OTHER_SPEAKER = re.compile(r"\b(?:customer reviews?|testimonials?|our (?:dealer|supplier|partner)s? (?:says?|states?)|"
                            r"according to|they (?:say|said))\b", re.I)
_CONTRACT = re.compile(r"\b(?:for (?:other|third[ -]party) (?:brands?|companies)|contract design|"
                       r"design services|private[ -]label|OEM)\b", re.I)
_THIRD_PARTY = re.compile(r"\b(?:third[ -]party|other brands?|brands? (?:from|by))\b", re.I)
_B2B = re.compile(r"\b(?:wholesale|B2B|to (?:our )?(?:dealers|retailers|trade customers|businesses))\b", re.I)
_NON_GOODS_OBJECT = re.compile(r"\b(?:manufactur(?:e|es)|produc(?:e|es)|builds?|designs?|crafts?|creates?|engineers?)\s+(?:(?:our|own|a|an|strong|lasting|better)\s+){0,3}"
                               r"(?:relationships?|partnerships?|trust|brands?|communities|community|websites?|experiences?|reputation)\b", re.I)
_OUR_BRAND = re.compile(r"\bour (?:own )?brand\b(?!\s+(?:partners?|suppliers?|customers?|dealers?|directory|ambassadors?)\b)", re.I)


def _subjects(company):
    name = re.sub(r"\b(?:incorporated|inc|limited|ltd|llc|corp|corporation)\b[.,]?", "", normalize_quote(company), flags=re.I).strip()
    names = [re.escape(name)] if name else []
    # A distinctive single-word brand often precedes a company descriptor.
    first = name.split()[0] if name else ""
    if len(first) >= 5 and first.casefold() not in {"canadian", "american", "premium", "international"}:
        names.append(re.escape(first))
    named = r"\b(?:" + "|".join(names) + r")\b" if names else r"(?!)"
    return r"(?:\bwe\b|" + named + r")", named


def _has_goods(text, product=""):
    primary = re.split(r"\b(?:for|that|which|with|to)\b", text, maxsplit=1, flags=re.I)[0]
    if re.search(r"\b(?:services?|websites?|software|consulting|relationships?|experiences?|content|trust|tours?|trails?|tracks?|workshops?|films?|events?|communities|community)\b", primary, re.I):
        return False
    if _GOODS.search(primary):
        return True
    brief = re.split(r"\b(?:no|not|excluding|without)\b", product, maxsplit=1, flags=re.I)[0]
    terms = {t.rstrip("s") for t in re.findall(r"\w+", brief.casefold()) if len(t) > 3}
    terms -= {"complete", "premium", "quality", "outdoor", "indoor", "high", "electric", "supplier", "search", "with", "from"}
    return bool(terms & {t.rstrip("s") for t in re.findall(r"\w+", primary.casefold())})


def _action(text, actor, verb, *, physical_object=False, product=""):
    matches = re.finditer(actor + r"\s+(?:(?:also|proudly|personally|directly|locally)\s+){0,3}(?:" + verb + r")\b", text, re.I)
    return any(not physical_object or _has_goods(text[match.end():], product) for match in matches)


def _self_role(text, actor, role):
    modifiers = r"(?:(?:a|an|the|only|leading|Canadian|American|independent|trusted|authorized|premium|recovery|global|local|family-owned|largest|proudly|professional)\s+){0,8}"
    return bool(re.search(actor + r"(?:\s+(?:is|are)|'re)\s+" + modifiers + r"(?:" + role + r")\b", text, re.I))


def _passages(quote, source):
    blocks = [value for part in re.split(r"\n\s*\n", source) if (value := normalize_quote(part))]
    for index, block in enumerate(blocks):
        for match in re.finditer(re.escape(quote), block, re.I):
            stops = list(re.finditer(r"[.!?;]\s+", block[:match.start()]))
            start = stops[-1].end() if stops else 0
            tail = re.search(r"[.!?;](?:\s|$)", block[match.end():])
            end = match.end() if quote.endswith((".", "!", "?", ";")) else match.end()+tail.end() if tail else len(block)
            heading = blocks[index-1] if index and len(blocks[index-1]) < 150 else ""
            yield block[start:end], heading


def manufacturer_label(clause, company, heading="", product=""):
    actor, named = _subjects(company)
    # A label's value must identify this company. Under a company heading a
    # verbless tagline is allowed, but a manufacturer's actions/terms are not.
    direct_label = re.fullmatch(r"manufacturer\s*:\s*" + named + r"[.!]?", clause, re.I)
    tagline = re.fullmatch(
        r"(?:(?:a|an|the|trusted|leading|professional|independent|Canadian|American)\s+){0,8}"
        r"manufacturer(?:\s+(?:of|since)\s+[^.!?]+)?[.!]?", clause, re.I)
    label = (_self_role(clause, actor, "manufacturer(?!'s)") or direct_label or
             re.search(named + r",\s*(?:as\s+)?an?\s+manufacturer\b", clause, re.I) or
             (re.search(named, heading, re.I) and len(clause) < 160 and tagline and not re.search(r"\b(?:is|are|supplies|stocks|sells|provides)\b", clause, re.I)))
    title = re.match(named + r"\s+([^.!?;:,]{0,70})\bmanufacturer\b", clause, re.I)
    if title and _has_goods(clause, product) and not re.search(r"\b(?:is|are|stocks?|dealers?|official|of|sells?|supply|supplies|distributes?|retails?|resells?|from|for|with|by|partners?)\b", title[1], re.I):
        label = True
    return bool(label)


def _supported_roles(quote, clause, heading, company, product=""):
    if not _CUES.search(quote):
        return set(), "quote_does_not_assert_a_company_role"
    assertion = re.split(r"\b(?:that|which)\b", clause, maxsplit=1, flags=re.I)[0]
    if _UNSUPPORTED.search(assertion):
        return set(), "negated_historical_or_hypothetical_role"
    if _OTHER_SPEAKER.search(heading + " " + clause):
        return set(), "role_attributed_to_other_speaker"
    actor, named = _subjects(company)
    roles = set()
    goods = _has_goods(clause, product)
    production = r"(?:designs?\s+(?:and|&)\s+)?(?:manufactur(?:e|es)|produc(?:e|es)|builds?|handbuilds?)"
    maker = _action(clause, actor, production, physical_object=True, product=product) and not _NON_GOODS_OBJECT.search(clause)
    own_facility = bool(re.search(r"\b(?:manufactured|produced|built)\b.{0,25}\bin our\b.{0,35}\b(?:facility|factory|workshop)\b", clause, re.I)) and goods
    # An explicit self-description may sit immediately below the company's heading.
    maker_label = manufacturer_label(clause, company, heading, product)
    maker_service = re.search(r"\bmanufacturer(?:'s)?\s+(?:representative|rep|agent|directory|dealer)\b", clause, re.I)
    if re.search(r"\b(?:manufactur\w*|produc\w*|build\w*|built|handbuilt)\b", quote, re.I) and (maker or own_facility or maker_label) and not maker_service:
        roles.add("Manufacturer")
    explicit_brand = (_self_role(clause, actor, "brand(?: owner)?") or
                      bool(_OUR_BRAND.search(clause)) or
                      _action(clause, actor, r"owns?\s+(?:the\s+)?[^.!?;]{0,50}\bbrand"))
    own_design = ((_action(clause, actor, r"designs?|engineers?|crafts?|creates?", physical_object=True, product=product) or
                   re.search(r"\bevery product we (?:make|create)\b", clause, re.I)) and goods and
                  not _CONTRACT.search(clause) and not _NON_GOODS_OBJECT.search(clause))
    own_line = maker and bool(re.search(r"\bour (?:own )?(?:products?|line|brand)\b", clause, re.I))
    brand_service = re.search(r"\bbrand\s+(?:consultancy|consultant|agency|partner|directory|representative)\b", clause, re.I)
    if re.search(r"\b(?:brand\w*|own\w*|design\w*|engineer\w*|craft\w*|creates?|make)\b", quote, re.I) and (explicit_brand or own_design or own_line) and not brand_service:
        roles.add("Brand owner")
    supply = _action(clause, actor, r"distributes?|suppl(?:y|ies)|wholesale[sd]?|sells?") or _self_role(clause, actor, "distributor")
    distribution = re.search(r"\bauthorized distributor of\s+(?!our\b)(\w[^.!?;]*)", clause, re.I)
    other_brand = bool(_THIRD_PARTY.search(clause)) or bool(distribution and not re.match(named, distribution[1], re.I))
    if supply and other_brand and _B2B.search(clause) and re.search(r"\b(?:distribut\w*|suppl\w*|wholesal\w*|sell\w*|brands?)\b", quote, re.I):
        roles.add("Distributor")
    if _self_role(clause, actor, "retailer|reseller") and re.search(r"\b(?:retailer|reseller)\b", quote, re.I):
        roles.add("Retailer")
    if (_self_role(clause, actor, "marketplace") or _action(clause, actor, r"operate\s+(?:an?\s+)?marketplace")) and re.search(r"\bmarketplace\b", quote, re.I):
        roles.add("Marketplace")
    if (_self_role(clause, actor, "blog|media company|publisher") or
        (_action(clause, actor, r"publish(?:es)?") and re.search(r"\b(?:reviews?|articles|news)\b", clause, re.I))) and re.search(r"\b(?:blog|media|publish\w*|reviews?|articles|news)\b", quote, re.I):
        roles.add("Media / Blog")
    return roles, "specific_role_not_supported"


def verify_supplier_role(role, company, evidence, pages, product=""):
    result = {"status": "not_established", "claimed_role": role, "supported_roles": [],
              "supporting_evidence": [], "observations": []}
    supported = set()
    for entry in evidence:
        if entry.get("claim") != "role":
            continue
        quote = normalize_quote(entry["quote"])
        found = False
        for page in pages:
            if entry["source_url"] not in {page["url"], page.get("requested_url")}:
                continue
            for clause, heading in _passages(quote, page["text"]):
                found = True
                roles, reason = _supported_roles(quote, clause, heading, company, product)
                supported.update(roles)
                observation = {"source_url": entry["source_url"], "quote": entry["quote"],
                               "supported_roles": sorted(roles), "reason": "specific_role_supported" if role in roles else reason,
                               "context": clause[:800]}
                result["observations"].append(observation)
                if role in roles:
                    result["supporting_evidence"].append(observation)
        if not found:
            result["observations"].append({"source_url": entry["source_url"], "quote": entry["quote"],
                                           "supported_roles": [], "reason": "role_quote_crosses_source_blocks"})
    result["supported_roles"] = sorted(supported)
    if result["supporting_evidence"]:
        result["status"] = "supported"
    return result


def recover_role_evidence(role, company, pages, product=""):
    """Recover at most two literal role quotes from already captured pages.

    Only the exact proposed role is eligible; no model calls or reclassification.
    Candidate scanning is capped and every recovered quote is revalidated by the
    same source-local role guard before it can affect qualification.
    """
    actor, named = _subjects(company)
    recovered = []
    for page in pages:
        scanned = 0
        page_recovered = False
        blocks = [value for part in re.split(r"\n\s*\n", page["text"]) if (value := normalize_quote(part))]
        for index, block in enumerate(blocks):
            heading = blocks[index-1] if index and len(blocks[index-1]) < 150 else ""
            for clause in re.split(r"(?<=[.!?;])\s+", block):
                if not _CUES.search(clause) or not (re.search(actor, clause, re.I) or
                    re.search(named, heading, re.I) or re.search(r"\bour\b", clause, re.I)):
                    continue
                words = clause.split()
                candidates = [" ".join(words[start:start+12]) for start in range(min(96-scanned, max(1, len(words)-11)))]
                candidates = [q for q in candidates if _CUES.search(q)]
                candidates.sort(key=lambda q: (role not in _supported_roles(q, q, "", company, product)[0],
                                               not bool(re.match(actor + r"|our\b|every\b", q, re.I))))
                for quote in candidates:
                    scanned += 1
                    roles, _ = _supported_roles(quote, clause, heading, company, product)
                    if role in roles:
                        entry = {"claim": "role", "source_url": page["url"], "quote": quote,
                                 "evidence_origin": "captured_source_role_repair"}
                        if verify_supplier_role(role, company, [entry], [page], product)["status"] == "supported":
                            recovered.append(entry)
                            page_recovered = True
                            break
                    if scanned >= 96:
                        break
                if page_recovered or scanned >= 96:
                    break
            if page_recovered or scanned >= 96:
                break
        if len(recovered) >= 2:
            break
    return recovered
