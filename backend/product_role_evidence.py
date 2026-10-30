"""Bind company roles to the complete cold-plunge category in the benchmark.

Other briefs explicitly report not_required and retain their current checks.
This is not a legal ownership, named-model alias or authorization audit.
"""
import re

from backend.location_evidence import normalize_quote
from backend.product_evidence import required_components
from backend.role_evidence import role_object_spans, verify_supplier_role

_PRIMARY = re.compile(r"\b(?:cold[ -]plunges?|ice[ -]baths?)\b", re.I)
_PURPOSE_OR_OTHER_ACTION = re.compile(
    r"\b(?:for|used (?:in|with)|compatible with|to (?:cool|power|support|build|make|assemble|create|produce))\b|"
    r"\b(?:and|but|while)\s+(?:\w+\s+){0,3}"
    r"(?:sell\w*|offer\w*|distribut\w*|resell\w*|suppl\w*|design\w*|manufactur\w*|build\w*|make\w*|own\w*)\b", re.I)
_ROLE_CUE = re.compile(r"\b(?:manufactur\w*|produc\w*|build\w*|built|design\w*|engineer\w*|craft\w*|creates?|makes?|owns?|brand)\b", re.I)
_CONTRACT_CREATION = re.compile(r"\b(?:for (?:other|third[ -]party) (?:brands?|companies)|contract design|design services|private[ -]label|OEM)\b", re.I)
MAX_RECOVERY_WINDOWS_PER_PAGE = 96
_COMPONENT_NOUN = re.compile(r"\b(?:chillers?|cooling|filtration|filters?|covers?|hoses?|pumps?|accessor\w*|parts?|components?|compartments?|heaters?|equipment|products?|housings?|enclosures?|liners?|shells?)\b", re.I)


def _primary_object(role, company, context, heading=""):
    objects = role_object_spans(role, company, context, heading)
    if role == "Brand owner" and _CONTRACT_CREATION.search(context):
        return False, objects
    for value in objects:
        subject = _PURPOSE_OR_OTHER_ACTION.split(value, maxsplit=1)[0]
        for match in _PRIMARY.finditer(subject):
            prefix = re.split(r"[,;]|\b(?:and|including|includes?|such as)\b", subject[:match.start()], flags=re.I)[-1]
            suffix = re.split(r"[,;]|\b(?:with|including|includes?|featuring|and|that|which)\b", subject[match.end():], maxsplit=1, flags=re.I)[0]
            if not _COMPONENT_NOUN.search(prefix) and not _COMPONENT_NOUN.search(suffix):
                return True, objects
    return False, objects


def verify_requested_product_role(product, role, company, evidence, pages):
    required = required_components(product) == ["tub", "chiller"] and role in {"Manufacturer", "Brand owner"}
    result = {"status": "not_established" if required else "not_required", "claimed_role": role,
              "scope": "complete_cold_plunge_category" if required else None,
              "supporting_evidence": [], "observations": [], "recovered_evidence": [], "source_repair_used": False}
    if not required:
        return result
    inspected_entries, inspected_support = set(), set()

    def inspect(entries):
        entries = [entry for entry in entries if (entry["source_url"], entry["quote"].casefold()) not in inspected_entries]
        if not entries:
            return
        inspected_entries.update((entry["source_url"], entry["quote"].casefold()) for entry in entries)
        company_role = verify_supplier_role(role, company, entries, pages, product)
        for support in company_role["supporting_evidence"]:
            key = (support["source_url"], support["quote"], support["context"])
            if key in inspected_support:
                continue
            inspected_support.add(key)
            scoped, objects = _primary_object(role, company, support["context"], support.get("heading", "")) if not support.get("context_truncated") else (False, [])
            observation = {**support, "role_objects": objects,
                           "reason": "requested_product_role_supported" if scoped else "role_context_truncated" if support.get("context_truncated")
                           else "company_role_does_not_establish_requested_product_role"}
            if observation not in result["observations"]:
                result["observations"].append(observation)
            if scoped and observation not in result["supporting_evidence"]:
                result["supporting_evidence"].append(observation)
                result["status"] = "supported"

    inspect([entry for entry in evidence if entry.get("claim") == "role"])
    if result["status"] == "supported":
        return result

    # Only recover explicit role+primary-product assertions from captured source
    # blocks. Links/titles or nearby product cards cannot fill the relationship.
    # There are no additional model/provider requests.
    for page in pages:
        scanned = 0
        for block in re.split(r"\n\s*\n", page["text"]):
            block = normalize_quote(block)
            if not _PRIMARY.search(block) or not _ROLE_CUE.search(block):
                continue
            for clause in re.split(r"(?<=[.!?;])\s+", block):
                if not _PRIMARY.search(clause) or not _ROLE_CUE.search(clause):
                    continue
                words = clause.split()
                for start in range(max(1, len(words)-11)):
                    if scanned >= MAX_RECOVERY_WINDOWS_PER_PAGE:
                        break
                    scanned += 1
                    quote = " ".join(words[start:start+12])
                    if not _PRIMARY.search(quote) or not _ROLE_CUE.search(quote):
                        continue
                    entry = {"claim": "role", "source_url": page["url"], "quote": quote,
                             "evidence_origin": "captured_source_product_role_repair"}
                    inspect([entry])
                    if result["status"] == "supported":
                        result["recovered_evidence"].append(entry)
                        result["source_repair_used"] = True
                        return result
                if scanned >= MAX_RECOVERY_WINDOWS_PER_PAGE:
                    break
            if scanned >= MAX_RECOVERY_WINDOWS_PER_PAGE:
                break
    return result
