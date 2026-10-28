# Candidate-selection validation — 2026-10-28

**Discovery now filters known/seen hosts before choosing checks and considers every query in its retained pool.** It rotates queries within source-priority tiers and preserves all retained rows with reasons. This changes checking order, not the requirements for qualified suppliers.

Local branch `fix/discovery-candidate-selection`, based on `2f2ef66`. The [confirmation brief](selection-fix-brief.md) describes the bounded scope and live settings. Implementation commit and live confirmation are pending in this preparation record.

## Implementation and offline checks

A pure selector retains up to ten SERP pages and one hundred organic rows per page, with explicit omitted-row coverage. Existing actor inputs remain one page per query and a ten-item dataset cap. Exact master hosts and previously seen/resolved hosts are removed before allocating verification slots. Blocked, invalid and search-destination rows are also filtered. Seeds still run first and are checked even if known; related subdomains are not automatically merged or skipped.

Within each source tier, query queues take turns while retaining organic rank and deduplicating normalized hosts. Generic editorial/comparison, support-document and multi-brand/price-comparison hints lower checking priority. They never prove ownership/manufacture, product contents, location or identity, and do not exclude the source if checks remain available. Explicit brand lookups preserve their exact query and organic ordering while receiving the same known/seen filter.

The durable `discovery_candidates` and `discovery_coverage` fields expose selected/skipped/deferred rows, source hints, query/rank, duplicate links, pool bounds and verification status through the results API and a collapsed UI table. Selected means planned, with completed, failed, interrupted and unstarted checks kept distinct. Older job responses default to empty fields. Existing skipped-site records now include known/blocked hosts encountered anywhere in the retained pool before paid verification begins.

**192 tests passed**, including nineteen new regression methods. Coverage includes cross-query fairness, known-first cutoff, already-seen/resolved sites, late blocked/known rows, duplicate ranking, weak-source fallback, identity-query/order preservation, related-host ambiguity, explicit pool bounds, global caps, stop/limit/failure provenance and API compatibility. Network access was forbidden in these tests. Product, requested-product role and country verification modules were not changed.

## Same-input replay

Network-blocked replay used the exact nineteen original saved organic rows and unchanged private master reference. It compared `2f2ef66` with the new selector through the real job runner and mock website verification. No provider or model call was made, and no supplier judgment or new qualification was produced.

| Measure | Before | After |
| --- | --- | --- |
| Sites selected for three checks | Cold Plunge Store, Men's Fitness, Titan | Titan, Aureline Wellness, NW Immersion |
| Requested role queries represented | Manufacturer only: three checks | Manufacturer: two; Brand owner: one |
| Exact known hosts recorded skipped | 0 | 7 |
| Blocked hosts recorded skipped | 1 | 4 |
| Retained rows with selection decisions | 0 | 19: three selected, eleven skipped, five deferred |
| Website verification slots | 3 | 3 |

The original baseline's full SERPs were captured by evaluation instrumentation, so replay could inspect rows the old selector had never returned. The replacement sites are **unverified search leads**, not automatically better or newly identified suppliers. The master file hash remained unchanged. A separate integration regression confirms that `[known host, unseen candidate]` with one slot now checks the unseen candidate.

Final replay records, source hashes, raw-input hash and before/after isolated job databases are under ignored `var/eval/cold-plunge-discovery-2026-10-28/selection-replay-final/`; the earlier preparation replay is preserved separately. An offline Streamlit render of the actual replay API payload displayed all nineteen selection records without errors or a server. Historical baseline artifacts and frozen labels remain unchanged.

## Live confirmation

Pending: one fresh three-candidate preview under the committed brief, followed by page/quote/hash, selection-ledger and read-only actor status/cost audits. No broader discovery accuracy claim is made from the offline selection replay.
