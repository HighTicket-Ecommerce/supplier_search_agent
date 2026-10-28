# Candidate-selection validation — 2026-10-28

**Discovery now filters known/seen hosts before choosing checks and considers every query in its retained pool.** It rotates queries within source-priority tiers and preserves all retained rows with reasons. This changes checking order, not the requirements for qualified suppliers.

Local branch `fix/discovery-candidate-selection`, based on `2f2ef66`. Core application/live snapshot: `4f241a7`. Final generic roundup-format refinement: `141024c`. The [confirmation brief](selection-fix-brief.md) was committed before provider execution. Qualification modules and frozen labels are unchanged.

## Implementation and offline checks

A pure selector retains up to ten SERP pages and one hundred organic rows per page, with explicit omitted-row coverage. Existing actor inputs remain one page per query and a ten-item dataset cap. Exact master hosts and previously seen/resolved hosts are removed before allocating verification slots. Blocked, invalid and search-destination rows are also filtered. Seeds still run first and are checked even if known; related subdomains are not automatically merged or skipped.

Within each source tier, query queues take turns while retaining organic rank and deduplicating normalized hosts. Generic editorial/comparison, support-document and multi-brand/price-comparison hints lower checking priority. They never prove ownership/manufacture, product contents, location or identity, and do not exclude the source if checks remain available. Explicit brand lookups preserve their exact query and organic ordering while receiving the same known/seen filter.

The durable `discovery_candidates` and `discovery_coverage` fields expose selected/skipped/deferred rows, source hints, query/rank, duplicate links, pool bounds and verification status through the results API and a collapsed UI table. Selected means planned, with completed, failed, interrupted and unstarted checks kept distinct. Older job responses default to empty fields. Existing skipped-site records now include known/blocked hosts encountered anywhere in the retained pool before paid verification begins.

**194 tests passed**, including twenty-one new regression methods. The core fix passed 192 before the live run; two later methods cover compact/dated roundup formatting and false positives. Coverage includes cross-query fairness, known-first cutoff, already-seen/resolved sites, late blocked/known rows, duplicate ranking, weak-source fallback, identity-query/order preservation, related-host ambiguity, explicit pool bounds, global caps, stop/limit/failure provenance and API compatibility. Network access was forbidden in these tests. Product, requested-product role and country verification modules were not changed.

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

Job `discovery-1bf9d4b3fc81`, round `selection-fix-1`, completed on unchanged `4f241a7` in **153.85 seconds**. It used the original settings: no seeds, Manufacturer/Brand owner, US/Canada allowed, saved master, three candidate checks, three attempts per site, nine pages, fifteen external calls, 600 seconds, $6 exposure and $0.50 per actor. No Shopping, catalogue, browser fallback or exports.

Fresh US-localized search returned **nineteen rows / eighteen unique hosts** across both role queries. Before any website checks, the job recorded **nine exact-master skips and one blocked skip**. Its full ledger accounts for nineteen rows: three selected, eleven skipped (including one duplicate observation) and five deferred. One repeated domain appeared as a roundup in the first query and a homepage in the second; the homepage correctly represented that company. Both queries supplied checks: two Manufacturer-query results and one Brand-owner-query result. No known host was selected or checked.

| Actual checked lead | Outcome |
| --- | --- |
| [Syochi roundup](https://syochi.com/2025-top10-cold-plunge-brands-review-in-us/) | No usable page; `retry_needed / website_evidence_unavailable`. The compact “Top10” title/year-prefixed path escaped the first editorial hint and led to the bounded refinement below. No model judgment or negative supplier label was made. |
| [OMNI Ice / ColdTubChiller](https://coldtubchiller.com/) | `review / supplier_role_not_established`. Captured wording did not pass exact company-role validation; the [chiller-ready tub](https://coldtubchiller.com/product/inflatable-cold-plunge-tub/) does not establish an included chiller. Raw model China/HQ fields were not source-verified location results. |
| [Himalaya IceTech](https://himalayaicetech.com/cold-plunge-tubs-ice-bath-systems/) | Company Manufacturer role supported, but `review / complete_system_components_not_established`. Captured pages did not prove an included tub/chiller configuration; a selected all-in-one page yielded no usable evidence. Factory-location text does not establish a qualifying company office/HQ. |

**Zero qualified, zero excluded, two evidence reviews and one collection failure.** All three checked identities were unmatched against the master, not confirmed new suppliers. The later country resolver was not reached after earlier role/component holds; raw country fields must not be described as verified locations. US-localized results can include overseas manufacturers. Country-aware query wording and further evidence coverage remain follow-ups.

The global three-check allowance again filled in the US batch, so Canada-localized discovery remains untested. Four historical development hosts naturally surfaced and were master-known; no historical final-check host surfaced. There was no label or qualification tuning. Fresh search results differ from the original baseline, so use the same-input replay above to attribute selection changes; this is not a controlled before/after qualification score or web-wide recall estimate.

## Final source-format refinement

The live run exposed a generic lexical miss: `Top10`, `Top-10`, and year-prefixed roundup paths should receive the same editorial hint as `Top 10`. `141024c` adds those forms with synthetic regressions, including checks that “Top quality”, “Desktop10” and “Best selling” are not roundup signals. There are no site-specific exceptions.

Network-blocked replay on the fresh nineteen captured rows now chooses **Himalaya IceTech, OMNI Ice's homepage and Polar Dive USA**, with one Manufacturer-query and two Brand-owner-query results. Syochi's roundup becomes deferred; known/blocked filtering and the three-slot allowance are unchanged. Polar Dive USA is an **unverified search lead**: no page/model call was made for it, and its name does not establish country. The final selector also preserves the original baseline replay's Titan/Aureline/NW Immersion selection. No additional provider run was needed for this pure format correction; it is offline-confirmed, separate from the earlier live outcomes.

`compact-title-replay/` preserves both selections, raw-input/source hashes and control assertions. Its final selector hash matches `141024c`. Only the selector's format recognition and its two regression methods changed after the live application snapshot; provider, qualification and limit code stayed unchanged. The actual live job was not rewritten to pretend it had used the final ranking.

## Audits, cost and records

Seven website attempts returned **five usable pages**; eight actors and two model calls used ten external calls. All four retained quote observations matched captured sources and the twelve-word limit. All five page hashes and manifest implementation hashes matched the live commit. The master file hash remained unchanged.

Selection checks passed: nineteen rows accounted for, unique record IDs, valid duplicate links, no selected exact-master or duplicate host, no pending/checking states after completion, and actual outcomes matched the ledger. Offline Streamlit rendering of the actual live API payload displayed all nineteen rows without errors or a server.

All eight actors were terminal and successful when checked through read-only run API calls; page-level failures remain recorded separately. Final reported actor usage was **$0.016125**, and model token cost was an estimated **$0.045409**, for approximately **$0.061534** combined execution, excluding account/storage fees. Conservative exposure was **$4.045409** against the $6 cap.

Ignored artifacts are under `var/eval/cold-plunge-discovery-2026-10-28/`: `selection-fix-1/` holds manifest/settings, isolated jobs, raw SERPs, full selection ledger/result, fetch attempts/pages, analyses, provider/source/selection audit and actual API UI check; `selection-replay-final/` holds the core before/after replay; `compact-title-replay/` holds final ordering checks. Earlier preparation records are preserved. No source-list edits, Sheets writes, development servers, pushes, PRs or deployment occurred.

The requested selection defects are fixed locally. Verified-supplier yield and geographic relevance still need improvement; these results do not establish production precision.
