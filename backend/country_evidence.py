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


def _location_cards(text, source_url):
    """Bound location values before geography, preserving adjacent label/address cards."""
    blocks = [value for part in re.split(r"\n\s*\n", text) if (value := normalize_quote(part))]
    bare_label = re.compile(r"(?:(?:our|global|corporate|registered|knoxville)\s+)*(?:headquarters|hq|head office|office(?: address)?)[: ]*$", re.I)
    for index, block in enumerate(blocks):
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z][a-z])", block):
            if not _ANCHOR.search(sentence) and location_quote_kind(sentence, text, source_url) != "company_base":
                continue
            value = sentence
            forced_kind = None
            if bare_label.fullmatch(sentence):
                forced_kind = "headquarters" if re.search(r"headquarters|hq|head office", sentence, re.I) else "office"
                values = []
                for following in blocks[index+1:index+4]:
                    if bare_label.fullmatch(following):
                        if forced_kind == "office" and not re.search(r"headquarters|hq|head office", following, re.I):
                            values.append(following)
                            continue
                        break
                    if re.search(r"\b(?:shipping|ships?|selling|sells?|deliver\w*|serving|serves?|returns?|exchanges)\b", following, re.I):
                        break
                    if _ANCHOR.search(following) or len(following.split()) > 16:
                        break
                    # Only address-like values or a short proper place name can bind a label.
                    if not (re.search(r"\d|,", following) or _geography(following) or
                            re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+){0,2}", following)):
                        break
                    if re.search(r"workshop|factory|warehouse|showroom|customer|supplier|partner|products?|services?", following, re.I):
                        break
                    values.append(following)
                if not values:
                    continue
                value = " ".join([sentence]+values)
            # A following market statement is not part of an address value.
            value = re.split(r"\b(?:we|our company)\s+(?:sell|ship|deliver|serve|supply|distribute|export)\b", value, maxsplit=1, flags=re.I)[0].strip(" ,")
            kind = location_quote_kind(value, text, source_url)
            if kind not in HQ_LOCATION_TYPES:
                # Keep unresolved, explicitly labelled HQ cards (e.g. Singapore).
                # They can block an office fallback, but cannot qualify a country.
                if forced_kind and not _geography(value):
                    kind = forced_kind
                else:
                    continue
            yield index, value, kind


def verify_company_location(evidence, pages):
    result = {"status": "not_established", "country": None, "location_type": "unknown",
              "supporting_evidence": [], "observations": [], "source_repair_used": False}
    observations = []
    for page_index, page in enumerate(pages):
        for index, value, kind in list(_location_cards(page["text"], page["url"]))[:256]:
            # Parse exactly once on the full bound value, never on truncated windows.
            countries = sorted(_geography(value))
            candidates = []
            for entry in evidence:
                if entry.get("claim") == "country" and entry["source_url"] in {page["url"], page.get("requested_url")}:
                    quote = normalize_quote(entry["quote"])
                    if quote and quote.casefold() in value.casefold() and len(quote.split()) <= 12:
                        candidates.append((quote, entry.get("evidence_origin", "model_quote")))
            words = value.split()
            candidates.extend((" ".join(words[start:start+12]), "captured_source_location_repair")
                              for start in range(min(128, max(1, len(words)))))
            usable = [(quote, origin) for quote, origin in candidates if
                      sorted(_geography(quote)) == countries and
                      location_quote_kind(quote, page["text"], page["url"]) == kind]
            if usable:
                quote, origin = min(usable, key=lambda row: (row[1] != "model_quote", len(row[0].split())))
            else:
                quote, origin = " ".join(words[:12]), "captured_source_location_repair"
            observations.append({"claim": "country", "source_url": page["url"], "quote": quote,
                "location_value": value[:2000], "quote_usable": bool(usable),
                "location_type": kind, "countries": countries, "evidence_origin": origin,
                "card_id": [page_index, index],
                "reason": "country_supported_by_location" if len(countries) == 1 and usable else
                          "conflicting_geography" if len(countries) > 1 else "location_geography_not_established"})

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
    if not countries or unresolved-resolved or any(not e["quote_usable"] for e in top):
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
