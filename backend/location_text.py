"""Shared location language and administrative-region values.

A comma followed by an adjective is not a region. Region inventories are data,
not supplier-specific hints, and preserve Unicode spellings.
"""
import re

NEGATION = r"(?:not|never|no longer|cannot|\w+n['’]t)"

US_CODES = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
CA_CODES = "AB BC MB NB NL NS NT NU ON PE QC SK YT".split()
US_NAMES = ("Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|"
             "Florida|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|"
             "Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|"
             "New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|"
             "South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming")
CA_NAMES = "Alberta|British Columbia|Manitoba|New Brunswick|Newfoundland and Labrador|Nova Scotia|Northwest Territories|Nunavut|Ontario|Prince Edward Island|Quebec|Québec|Saskatchewan|Yukon"

REGION_NAMES = US_NAMES + "|" + CA_NAMES + "|United States|Canada|England|Scotland|Wales|Germany|Australia"
REGION_VALUE = r"(?:(?i:" + REGION_NAMES + r")|(?-i:" + "|".join(US_CODES + CA_CODES) + r"))"
_CITY_WORD = r"[^\W\d_]+(?:[-'][^\W\d_]+)*"
_CITY = r"(?!(?:supplier|manufacturer|customer|partner|dealer)\b)" + _CITY_WORD + r"(?:\s+(?!(?:to|for|a|an|supplier|customer|manufacturer)\b)" + _CITY_WORD + r"){0,4}"
SELF_LOCATION_RE = re.compile(r"\bwe(?:'re|\s+are)\s+(?:an?\s+)?" + _CITY + r",\s*" + REGION_VALUE +
                              r"\s+(?:manufacturer|company|business)\b", re.I)

_HQ = r"(?:(?:corporate|global|company|registered)\s+)?(?:headquarters|head office|hq)"
_FACILITY = r"(?:factor(?:y|ies)|warehouses?|manufacturing facilit(?:y|ies)|production facilit(?:y|ies))"
_SHARED = re.compile(r"\b(?:our\s+)?(?P<left>"+_HQ+"|"+_FACILITY+r")\s*(?:and|&)\s*(?P<right>"+
                     _HQ+"|"+_FACILITY+r")\s+(?:are|is)\s+(?:both\s+)?(?:(?:located|situated|based)\s+)?"
                     r"(?:in|at)\s+(?P<value>[^.!?]+)", re.I)


def _shared_location(text):
    match = _SHARED.search(text)
    if match and bool(re.fullmatch(_HQ, match["left"], re.I)) != bool(re.fullmatch(_HQ, match["right"], re.I)):
        return match
    return None


def ambiguous_shared_location(text):
    match = _shared_location(text)
    if not match:
        return False
    # Coordination inside a recognized region name is not a second location.
    value = re.sub(REGION_NAMES, "REGION", match["value"], flags=re.I)
    return bool(re.search(r"\b(?:respectively|and)\b|&", value, re.I))


def shared_headquarters(text):
    return bool(_shared_location(text)) and not ambiguous_shared_location(text)
