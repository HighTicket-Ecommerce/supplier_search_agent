# Cold-plunge benchmark results — 2026-10-27

Follow-up: [targeted evidence-collection/HQ checks](evidence-collection-results.md). This document preserves the earlier benchmark results; the follow-up is not a full benchmark rerun.

Labels were frozen before any agent run: [brief.md](brief.md), [labels.json](labels.json).  
Jobs live in ignored `var/eval/cold-plunge-2026-10-27/`. No Sheets writes. No discovery. No Shopify catalogue.

## Verdict

**Did not pass.** Do not open pull requests.

After the headquarters and quote fixes on `fix/hq-pages-and-quotes`, development+anchor coverage is still **1 / 11** labelled eligible sites (BlueCube only). Precision stayed 1/1. The untouched final-check group was not rerun.

The first seed-only run on `fix/master-matching` was also 1/14 eligible. Quote-voiding is largely gone; missing About pages and conservative tub+chiller reading are now the blockers.

## HQ and quote rerun (`fix/hq-pages-and-quotes`)

Code: `2671acc`, `341893a`, `ff91c84`, `668aa19`.  
Scope: 2 anchors + 14 development sites. Final-check left untouched. 2 pages/site, $10/job, pairs of sites.

| Check | Target | Development + anchors |
| --- | --- | --- |
| Qualified precision | ≥ 90% | **1 / 1 (100%)** — BlueCube |
| Coverage of labelled eligible sites evaluated | ≥ 80% | **1 / 11 (9%)** |
| Accessory/service-only accepted | 0 | 0 |
| Wrong qualifies | 0 | 0 — Plunge’s “Born in California” qualify was rejected by the origin-quote gate |
| Sheets writes / source-list edits | 0 | 0 |
| Wrong master merges | 0 | 0 |
| Silent drops | 0 | 0 |

| Case | Eligible | Expected | Got | Why |
| --- | --- | --- | --- | --- |
| Homecraft | no | review | review | About fetched; HQ verified; no plunge |
| Coldture | yes | qualified | review | HQ quote now verified (`hq is in vaughan, ontario`); model still did not treat excerpts as a tub+chiller system |
| Plunge | yes | review | review | Origin/manufacturing quotes no longer count as HQ |
| Ice Barrel | yes | review | review | Role not established |
| Renu Therapy | yes | review | review | Handcrafted-in-California is manufacturing, not HQ |
| BlueCube | yes | qualified | **qualified** | Contact-page address + complete system |
| Redwood Outdoors | yes | qualified | review | Contact fetched, not About; HQ address found; tub+chiller not explicit in excerpts |
| Sun Home | yes | qualified | review | Product page fetched, not About; HQ line never seen |
| LeisureCraft | yes | qualified | review | About fetched; chiller listed separately from the tub |
| Penguin Chillers | yes | qualified | review | About fetched; office address found; collection page with complete plunges not fetched |
| Canadian Spa | no | review | review | Product not established |
| Fire Magic | no | review | review | Product not established; “Crafted in California” dropped as HQ |
| Alpha Sauna | no | excluded | review | China factory address never used as HQ |
| Morozko Forge | yes | review | review | HQ not established |
| Fluid Float | no | review | review | HQ not established (still review) |
| Polar Monkeys | yes | review | review | HQ not established |

What improved versus the first run: Homecraft and Renu no longer die on a single bad quote; Coldture’s FAQ HQ line is verified; Plunge no longer false-qualifies; About/contact beat product paths when those links are actually discovered.

What did not: Shopify About URLs often never appear as markdown or `href` in the raw-http capture (Redwood, Sun Home). A 2-page cap that prefers About then misses the collection page that would prove a complete system (Penguin). The model still refuses tub+chiller when the page says “cold plunges” and “chiller” in different excerpts (Coldture, LeisureCraft).

Final-check was not run. Do not tune on it.

## First run (`fix/master-matching`)

Code: `ae3439b` plus the docs commit. 24 sites, including final-check.

| Setting | First batch | Later batches |
| --- | --- | --- |
| Mode | seed-only, preview-only, discovery off | same |
| Pages per supplier | 3 | 2 (after the budget stop) |
| Execution budget | $8 | $10 |
| Result | `limited` / `execution_budget_limit` after 5 complete sites | completed |

Job IDs: `eval-4326d0f33310` (limited), `eval-b4270e1ecad6`, `eval-61df020559dd`, `eval-58ed73d0b872`, `eval-bac283047649`, `eval-826cb5d4ff83`, `eval-d79fea593519`, `eval-692ef5e1b1df`.

| Check | Target | Result |
| --- | --- | --- |
| Qualified precision | ≥ 90% | **1 / 1 (100%)** — BlueCube only |
| Coverage of labelled eligible sites | ≥ 80% | **1 / 14 (7%)** |
| Final-check eligible qualified | — | 0 / 3 |

## Next

Stay on local branches. Coverage is not in range. Do not open PRs. Next development-only work is proving complete systems from already-fetched pages and getting official About URLs into the 2-page budget without fetching a random product instead.
