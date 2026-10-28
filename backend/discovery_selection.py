"""Bounded SERP selection. Search hints order checks; they never qualify suppliers."""
from collections import defaultdict, deque
import re
from urllib.parse import unquote, urlsplit

from backend.filters import is_blocked_domain
from backend.utils import normalize_url, domain_from_url, is_search_destination

MAX_SERP_PAGES = 10
MAX_ORGANIC_ROWS_PER_PAGE = 100


def source_hints(url, title, snippet):
    path = unquote(urlsplit(url).path).lower()
    title = title.lower()
    hints = []
    if (re.search(r"/(?:blogs?|articles?)(?:/|$)|/(?:best-|(?:20\d{2}[-_])?top[-_]?\d+)", path)
            or re.search(r"\b(?:top[\s-]*\d+\b|best\b.*\b(?:tested|reviewed|of\s+20\d{2}))", title)):
        hints.append("editorial_comparison")
    if (domain_from_url(url).split(".")[0] in {"help", "support"}
            or re.search(r"/(?:hc|manuals?|support)(?:/|$)", path)):
        hints.append("support_document")
    if re.search(r"\bbrands?\s+(?:like|such as)\b|\bfrom\s+(?:multiple|different|leading|top)\s+brands\b"
                 r"|\bcompare\b.{0,100}\bprices\b", snippet, re.I):
        hints.append("multi_brand_or_price_comparison")
    return hints


def select_serp_candidates(pages, *, country, limit, known_domains=(), seen_domains=(), prioritize_sources=True):
    """Filter the whole bounded pool, then round-robin queries within source tiers.

    Every retained raw row gets a decision, including duplicate observations and
    candidates beyond the check allowance. Related subdomains remain eligible.
    Explicit identity lookups disable source hints and retain organic rank.
    """
    known, seen = set(known_domains), set(seen_domains)
    records, queues = [], defaultdict(lambda: defaultdict(deque))
    query_indexes = {}
    omitted_rows = sum(len(p.get("organicResults", [])) for p in pages[MAX_SERP_PAGES:])
    for page_index, page in enumerate(pages[:MAX_SERP_PAGES]):
        query = page.get("searchQuery", {}).get("term")
        query_key = query or ("page", page_index)
        query_index = query_indexes.setdefault(query_key, len(query_indexes))
        organic = page.get("organicResults", [])
        omitted_rows += max(0, len(organic) - MAX_ORGANIC_ROWS_PER_PAGE)
        for rank, row in enumerate(organic[:MAX_ORGANIC_ROWS_PER_PAGE], 1):
            url = normalize_url(row.get("url") or "")
            domain = domain_from_url(url)
            entry = {"record_id": str(len(records)), "url": url, "domain": domain,
                     "title": row.get("title") or "", "snippet": row.get("description") or "",
                     "discovery_source": "serp", "query": query, "query_index": query_index,
                     "organic_rank": rank, "search_country": country,
                     "decision": "skipped", "source_hints": []}
            records.append(entry)
            if not domain or not urlsplit(url).netloc or "." not in domain:
                entry["reason"] = "invalid_url"
            elif is_search_destination(url):
                entry["reason"] = "search_destination"
            elif domain in seen:
                entry["reason"] = "already_seen"
            elif is_blocked_domain(domain):
                entry["reason"] = "blocked_domain"
            elif domain in known:
                entry["reason"] = "already_in_master"
            else:
                hints = source_hints(url, entry["title"], entry["snippet"]) if prioritize_sources else []
                tier = 2 if any(h in hints for h in ["editorial_comparison", "support_document"]) else int(bool(hints))
                entry.update(decision="eligible", source_hints=hints, source_priority=tier)
                queues[tier][query_index].append(entry)

    selected, representatives = [], {}
    # Source tiers prevent a high-ranked article from taking a check ahead of an
    # apparent company page. Within each tier, every query gets a turn.
    for tier in sorted(queues):
        while any(queues[tier].values()) and len(selected) < max(0, limit):
            for query_index in sorted(queues[tier]):
                queue = queues[tier][query_index]
                while queue and queue[0]["domain"] in representatives:
                    queue.popleft()
                if queue and len(selected) < limit:
                    entry = queue.popleft()
                    entry.update(decision="selected", reason="source_priority_then_query_round_robin",
                                 selection_rank=len(selected) + 1, verification_status="pending")
                    representatives[entry["domain"]] = entry
                    selected.append(entry)

    # Assign duplicates after selection so an earlier low-priority occurrence
    # cannot hide a better occurrence of the same host in another query.
    for entry in records:
        if entry["decision"] != "eligible":
            continue
        representative = representatives.get(entry["domain"])
        if representative:
            entry.update(decision="skipped", reason="duplicate_domain", duplicate_of=representative["record_id"])
        else:
            entry.update(decision="not_selected", reason="verification_candidate_limit")
            representatives[entry["domain"]] = entry
    coverage = {"search_country": country, "query_count": len(query_indexes), "retained_rows": len(records),
                "omitted_rows": omitted_rows, "pool_truncated": bool(omitted_rows),
                "selected_count": len(selected), "candidate_limit": max(0, limit),
                "source_hints_enabled": prioritize_sources}
    return selected, records, coverage
