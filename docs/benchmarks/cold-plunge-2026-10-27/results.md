# Cold-plunge benchmark results — 2026-10-27

Code: local `fix/master-matching` (`ae3439b` plus this docs commit).  
Labels were frozen before any agent run: [brief.md](brief.md), [labels.json](labels.json).  
Jobs live in ignored `var/eval/cold-plunge-2026-10-27/`. No Sheets writes. No discovery. No Shopify catalogue.

## Verdict

**Did not pass.** Do not open pull requests on the back of this run.

Qualified precision met the 90% target on a single accepted supplier. Coverage of labelled eligible sites was 1/14 (7%), far below 80%. Headquarters and source-quote checks are the main blockers.

## Settings

| Setting | First batch | Later batches |
| --- | --- | --- |
| Mode | seed-only, preview-only, discovery off | same |
| Pages per supplier | 3 | 2 (after the budget stop) |
| Execution budget | $8 | $10 |
| Result | `limited` / `execution_budget_limit` after 5 complete sites | completed |

Each Apify page fetch still reserves $0.50 for the whole job, so eight sites at three pages reserve $12 before model cost. Later batches of two or three sites finished.

Job IDs: `eval-4326d0f33310` (limited), `eval-b4270e1ecad6`, `eval-61df020559dd`, `eval-58ed73d0b872`, `eval-bac283047649`, `eval-826cb5d4ff83`, `eval-d79fea593519`, `eval-692ef5e1b1df`.

Conservative reservations across jobs were about $26. Actual token use on the first five model calls was a few thousand input tokens each; actor reported charges were not copied into every operation row. Treat reservations and spend as distinct.

## Scores

| Check | Target | Result |
| --- | --- | --- |
| Qualified precision | ≥ 90%, show counts | **1 / 1 (100%)** — BlueCube only |
| Coverage of labelled eligible sites | ≥ 80% | **1 / 14 (7%)** |
| Accessory/service-only accepted | 0 | 0 |
| Duplicate qualified companies | 0 | 0 |
| Sheets writes / source-list edits | 0 | 0 |
| Wrong master merges | 0 | 0 |
| Labelled master suppliers flagged | all | 23/23 in-master cases were `existing_domain_match` or `domain_match_name_conflict`; Wikipedia correctly `unmatched` |
| Silent drops | 0 | 0 — Wikipedia and IKEA are `retry_needed` |

Final-check group (untouched): 0 qualified / 3 eligible (Cryo Innovations, Inergize, Northern Saunas). Same failure mode as development. Brass Monkey (UK) stayed in review instead of excluded.

## What the agent did

| Case | Eligible | Expected | Got | Why |
| --- | --- | --- | --- | --- |
| Homecraft | no | review | review | quote not verified; no plunge |
| Coldture | yes | qualified | review | HQ not established (repeat of 2026-10-14) |
| Plunge | yes | review | review | HQ not established |
| Ice Barrel | yes | review | review | role not established |
| Renu Therapy | yes | review | review | quote not verified |
| BlueCube | yes | qualified | **qualified** | US HQ + complete system |
| Redwood Outdoors | yes | qualified | review | HQ not established |
| Sun Home | yes | qualified | review | quote not verified |
| LeisureCraft | yes | qualified | review | product not established |
| Penguin Chillers | yes | qualified | review | quote not verified |
| Canadian Spa | no | review | review | product not established |
| Fire Magic | no | review | review | product not established |
| Alpha Sauna | no | excluded | review | product not established; China HQ unused |
| Morozko Forge | yes | review | review | product not established |
| Fluid Float | no | review | review | product not established |
| Polar Monkeys | yes | review | review | HQ not established |
| Brass Monkey | no | excluded | review | product not established; UK HQ unused |
| Cryo Innovations | yes | qualified | review | HQ not established |
| Inergize | yes | qualified | review | quote not verified |
| Northern Saunas | yes | review | review | role not established |
| Backcountry | no | review | review | role not established |
| HARMAN | no | review | review | product not established |
| Wikipedia | no | retry | retry | actor error |
| IKEA | no | retry | retry | blocked/unavailable page |

## Largest problems (do not tune on final-check cases)

1. **Headquarters excerpts are missed.** Official HQ lines on Coldture, Redwood, Sun Home, Cryo Innovations and Inergize never became a verified country claim. Page selection in `web_fetcher.py` still keys on fixed words (`sauna`, `plunge`, `fireplace`, `heater`, `Surrey`).
2. **Literal quote checks fail** even when the product looks right (Sun Home, Penguin, Inergize, Homecraft, Renu). The model’s quote is not a contiguous 12-word span from the fetched text.
3. **Overseas headquarters are not excluded** if the product or HQ quote never lands (Alpha Sauna, Brass Monkey). They stay in review, which is safer than a wrong qualify, but it hides the true reason.
4. **Same-host extra words** (`Homecraft Saunas`, `Coldture Wellness`, `BlueCube Cold Plunge`) become `domain_match_name_conflict` instead of `existing_domain_match`. They are still flagged, not merged.

## Next

Stay on local branches. Fix headquarters page selection and quote verification on **development** cases only, then rerun those, then the final-check group. Open PRs after coverage on the labelled eligible set is actually in range, not before.
