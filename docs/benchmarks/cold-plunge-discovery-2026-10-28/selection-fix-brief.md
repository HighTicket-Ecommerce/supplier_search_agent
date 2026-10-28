# Candidate-selection fix and confirmation — 2026-10-28

User-authorized scope: improve selection across queries and filter master-known suppliers before choosing sites to check. Branch `fix/discovery-candidate-selection`, based on `2f2ef66`. Preserve qualification rules, historical captures and frozen labels.

The selector retains up to ten SERP dataset pages and one hundred organic rows per page, reporting omitted-row counts if its local bound is exceeded. Existing actor inputs still request one page per role query and at most ten dataset items. No extra queries, pages, model calls or actor retries are introduced by selection.

Filter exact master hosts, already-seen/previously-resolved hosts, invalid URLs, search destinations and blocked sources across the whole retained pool before allocating verification checks. Related subdomains are not automatically merged with the master. Explicitly supplied websites retain their existing behavior.

Within comparable source-priority tiers, take turns across query queues, retaining organic rank and deduplicating normalized hosts. Generic editorial/comparison, support-document and multi-brand/price-comparison hints lower priority; they do not exclude a site or prove a company role. A stronger source occurrence can represent a host even if an earlier query returned an article on that host. Explicit brand-identity lookups keep organic ordering and their exact query; they receive master/seen filtering without source-hint ranking.

Persist every retained row's query, rank, selection/skip/defer reason, hint and duplicate relationship. Distinguish planned checks from actual verification status, including target stops, interruptions and failures. Return the ledger/coverage through the authenticated results API and show it in a collapsed UI table. Previously saved jobs default to empty selection fields.

Offline confirmation must cover known-first, seeded/resolved, duplicate and cross-query ordering traps; deferred and late blocked/known rows; related-host ambiguity; limits; exact brand lookups; API compatibility and interruption states. Replay the nineteen original saved rows before/after with network blocked and mock verification, explicitly making no new supplier judgments.

Then run one new **three-candidate preview** using the existing discovery runner and original settings: complete cold-plunge systems, Manufacturer/Brand owner, US/Canada allowed, saved master, three page attempts per site, nine total, fifteen external calls, 600 seconds, $6 exposure and $0.50 per actor. No seeds, Shopping, catalogue, browser fallback, Sheets writes or source-list edits. Country search remains sequential; if the US fills the global cap, do not claim Canada was tested.

Commit the implementation before provider execution and preserve manifest source hashes, raw SERPs, selection ledger, page attempts/pages, model analyses, isolated job data and final run/source/cost audit. Manually inspect the three selected outcomes; label unfetched rows as search hints, not verified suppliers. Report query coverage, master skips, limits and qualification separately. No final-check tuning, overall accuracy claim, push, PR or deployment.
