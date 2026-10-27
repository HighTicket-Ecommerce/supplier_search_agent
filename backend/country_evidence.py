"""Resolve country and location basis from source-verified company locations.

Recognizes explicit supported country names and conventional US/Canadian region
addresses. Unknown geography stays unknown; model guesses are never geography.
"""
import re

from backend.location_evidence import HQ_LOCATION_TYPES, location_quote_kind, normalize_quote


_US_CODES = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
_CA_CODES = "AB BC MB NB NL NS NT NU ON PE QC SK YT".split()
_US_NAMES = ("Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|"
             "Florida|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|"
             "Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|"
             "New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|"
             "South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming")
_CA_NAMES = "Alberta|British Columbia|Manitoba|New Brunswick|Newfoundland and Labrador|Nova Scotia|Northwest Territories|Nunavut|Ontario|Prince Edward Island|Quebec|Québec|Saskatchewan|Yukon"
_COUNTRIES = {"United States": r"United States(?: of America)?|USA|U\.S\.(?:A\.)?",
              "Canada": r"Canada", "United Kingdom": r"United Kingdom|Great Britain|England|UK",
              "Germany": r"Germany|Deutschland", "Australia": r"Australia", "China": r"China"}
_ANCHOR = re.compile(r"\b(?:headquarters|hq|head office|office(?!\s+(?:hours|phone|email|number|supplies))|"
                     r"(?:based|headquartered|located|situated)\s+(?:just\s+)?(?:in|at|near|outside))\b", re.I)
_PRIORITY = {"headquarters": 0, "office": 1, "company_base": 2}


def _geography(quote):
    countries = {name for name, pattern in _COUNTRIES.items() if re.search(r"\b(?:"+pattern+r")(?!\w)", quote, re.I)}
    # A postal region disambiguates Ontario, California from Ontario province.
    if re.search(r",\s*(?:"+"|".join(_US_CODES)+r")\s+\d{5}(?:-\d{4})?\b", quote, re.I):
        countries.add("United States")
    elif re.search(r",\s*(?:"+"|".join(_CA_CODES)+r")\s+[A-Z]\d[A-Z]\s*\d[A-Z]\d\b", quote, re.I):
        countries.add("Canada")
    else:
        if re.search(r"(?:,\s*|\bin\s+|:\s*)(?:"+_US_NAMES+r")\b", quote, re.I):
            countries.add("United States")
        if re.search(r"(?:,\s*|\bin\s+|:\s*)(?:"+_CA_NAMES+r"|"+"|".join(_CA_CODES)+r")\b", quote, re.I):
            countries.add("Canada")
    return countries


def verify_company_location(evidence, pages):
    result = {"status": "not_established", "country": None, "location_type": "unknown",
              "supporting_evidence": [], "observations": [], "source_repair_used": False}
    observations = []
    seen = set()
    for page_index, page in enumerate(pages):
        blocks = [value for part in re.split(r"\n\s*\n", page["text"]) if (value := normalize_quote(part))]

        def card(index):
            if _ANCHOR.search(blocks[index]):
                return index
            return next((i for i in range(index-1, max(-1, index-4), -1)
                         if len(blocks[i]) < 150 and _ANCHOR.search(blocks[i])), index)

        def add(quote, index, origin):
            quote = normalize_quote(quote)
            if not quote or len(quote.split()) > 12:
                return
            kind = location_quote_kind(quote, page["text"], page["url"])
            if kind not in HQ_LOCATION_TYPES:
                return
            key = (page_index, quote.casefold())
            if key in seen:
                return
            seen.add(key)
            countries = sorted(_geography(quote))
            observations.append({"claim": "country", "source_url": page["url"], "quote": quote,
                "location_type": kind, "countries": countries, "evidence_origin": origin,
                "card_id": [page_index, card(index)],
                "reason": "country_supported_by_location" if len(countries) == 1 else
                          "conflicting_geography" if countries else "location_geography_not_established"})

        # Retain model quotes when usable, but derive their country independently.
        joined = " ".join(blocks)
        for entry in evidence:
            if entry.get("claim") != "country" or entry["source_url"] not in {page["url"], page.get("requested_url")}:
                continue
            needle = normalize_quote(entry["quote"])
            if not needle or needle.casefold() not in joined.casefold():
                continue
            index = next((i for i, block in enumerate(blocks) if needle.casefold() in block.casefold()), 0)
            add(needle, index, entry.get("evidence_origin", "model_quote"))

        # Scan only location-bearing blocks and their adjacent address values.
        scanned = 0
        indices = [i for i, block in enumerate(blocks) if _ANCHOR.search(block) or
                   any(_ANCHOR.search(old) for old in blocks[max(0, i-3):i])]
        for index in indices:
            words = blocks[index].split()
            starts = list(range(min(96, max(1, len(words)-11))))
            # Long blocks may contain the label after navigation text.
            for match in _ANCHOR.finditer(blocks[index]):
                position = len(blocks[index][:match.start()].split())
                starts.extend(range(max(0, position-3), position+1))
            for start in dict.fromkeys(starts):
                add(" ".join(words[start:start+12]), index, "captured_source_location_repair")
                scanned += 1
                if scanned >= 256:
                    break
            if scanned >= 256:
                break

    result["observations"] = observations
    if not observations:
        return result
    priority = min(_PRIORITY[e["location_type"]] for e in observations)
    top = [e for e in observations if _PRIORITY[e["location_type"]] == priority]
    result["location_type"] = top[0]["location_type"]
    countries = {country for e in top for country in e["countries"]}
    if len(countries) > 1:
        result["status"] = "ambiguous"
        return result
    unresolved = {tuple(e["card_id"]) for e in top if not e["countries"]}
    resolved = {tuple(e["card_id"]) for e in top if len(e["countries"]) == 1}
    if not countries or unresolved-resolved:
        return result
    result["status"], result["country"] = "supported", next(iter(countries))
    support = [e for e in top if e["countries"] == [result["country"]]]
    # Prefer original usable quotes, otherwise a compact recovered value.
    support.sort(key=lambda e: (e["evidence_origin"] != "model_quote", len(e["quote"].split())))
    for entry in support:
        if any(e["source_url"] == entry["source_url"] and e["quote"] == entry["quote"] for e in result["supporting_evidence"]):
            continue
        result["supporting_evidence"].append(dict(entry, verified_country=result["country"]))
        if len(result["supporting_evidence"]) == 2:
            break
    result["source_repair_used"] = all(e["evidence_origin"] != "model_quote" for e in result["supporting_evidence"])
    return result
