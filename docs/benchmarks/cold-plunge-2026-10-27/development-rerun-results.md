# Complete development rerun — 2026-10-27

**Improved, but not ready to pass the benchmark.** All 16 development/anchor cases were rerun on the same fixed application version. The agent returned **4 qualified, 11 review, 1 retry needed, and 0 excluded**. Qualification coverage against the six frozen expected-qualified labels rose from **1/6 to 4/6 (67%)**, below the 80% target. BlueCube also needs manual headquarters review: its contact/workshop address passes the implemented gate but does not explicitly establish headquarters or an office.

This report supersedes the earlier targeted checks for the current development-cohort result. It does not establish discovery performance or production accuracy.

## Reproducible scope

- Code: `480d5b6f24b8569ef3b2c9907189a5a307402f62`, branch `fix/evidence-collection-and-hq`. Application code stayed unchanged throughout the rerun. All eight manifests have identical application-source, brief and label hashes, verified against the working files.
- Cohort: 14 development sites and two regression anchors. No final-check cases ran. The original final-check set was used in the first baseline, so a fresh independent final set is still required.
- Eight sequential pairs; seed-only and preview-only. Discovery, Shopping, Shopify catalogue analysis and browser fallback were off. No Sheets exports or source-list edits.
- Per pair: at most three pages/site, six pages, twenty external calls, 600 seconds and a $4 conservative execution ceiling. Each actor had a $0.50 provider charge cap.
- Master reference: `bfc9de773286a1302310ec926981c1f4f0632b04776bdfe5933728794a7d99a2`.

The earlier HQ/quote rerun used two pages/site. The improvement measures the combined code changes and increased page allowance; it is not an isolated A/B estimate of either change. The last offline suite passed all 80 tests before this rerun; no application code changed afterward.

## Scores and their limits

| Check | Result |
| --- | --- |
| Cases attempted / cohort | 16/16; 15 evidence-based decisions and one fetch failure |
| Frozen expected-qualified returned qualified | **4/6 (67%)**: Coldture, Sun Home, Redwood, BlueCube |
| Qualified suppliers commercially eligible under frozen labels | 4/4; this does not independently validate headquarters |
| Qualified suppliers with clear HQ/office evidence on manual inspection | 3/4; BlueCube remains unconfirmed under the strict HQ/office brief |
| Relevant suppliers retained in review | 6: Penguin, LeisureCraft, Plunge, Ice Barrel, Renu, Polar Monkeys |
| Relevant supplier with unavailable evidence | 1: Morozko; not a negative supplier label |
| Retained quotes found in captured sources | 68/68, checking both requested and redirected URLs with Unicode/whitespace normalization |
| Known master hosts recognized | 16/16: 11 `existing_domain_match`, 5 `domain_match_name_conflict` |
| Duplicate qualified domains / candidates silently dropped | 0 / 0 |
| Wrong automatic exclusions | 0; there were no exclusions |
| Sheets exports / final-check cases run | 0 / 0 |

Literal text matching does not prove that a quote supports its assigned claim. Some retained role quotes are weak or irrelevant, such as an email address or support phone line. The accepted cases also have substantive role/product quotes, but claim semantics still need a separate check. For a shortlist requiring verified HQ/office evidence, keep BlueCube in manual review; the three currently substantiated automatic qualifications cover **3/6** frozen expected-qualified cases.

The two anchors returned one qualified (Coldture) and one review (Homecraft). The 14 development sites returned three qualified, ten review and one retry; development-only frozen qualification coverage is 3/5. These small, repeatedly inspected development sets do not provide an independent accuracy estimate.

## Every case

| Case | Frozen expected | Returned | Evidence / limitation |
| --- | --- | --- | --- |
| Coldture (anchor) | Qualified | **Qualified** | Explicit Vaughan HQ statement, company engineering evidence, tub + Chiller Pro bundle |
| Homecraft (anchor) | Review | Review | Sauna heaters/kits; requested plunge system not established |
| Redwood Outdoors | Qualified | **Qualified** | Kent office address, design/brand evidence, complete tub-and-chiller collection and Denali kit |
| Penguin Chillers | Qualified | Review | Office/manufacturer evidence found; product follow-up chose an all-in-one **replacement filter** instead of the observed cold-therapy collection |
| LeisureCraft | Qualified | Review | About and plunge pages captured; model used manufacturing as its country claim even though an address appeared in the About excerpts. Optional chiller/compartment evidence does not settle the packaged-system question |
| Sun Home | Qualified | **Qualified** | About-page San Diego HQ card and integrated-chiller Pro Apex product |
| BlueCube | Qualified | **Qualified; manual HQ review required** | C1 includes heater/chiller; contact page invites visits to a Redmond address and workshop. Clear operating location, no explicit HQ/office statement |
| Plunge | Review | Review | Complete-system evidence found; Sacramento crafting/production quote rejected as headquarters |
| Ice Barrel | Review | Review | Bundle explicitly includes tub + chiller; headquarters unknown |
| Renu Therapy | Review | Review | Integrated-chiller product; California manufacturing rejected as headquarters |
| Canadian Spa | Review | Review | Hot tubs/swim spas; requested plunge system not established |
| Fire Magic | Review | Review | Grills; requested plunge system not established |
| Alpha Sauna | Excluded | Review | Role established; product quote exceeded the limit, and a China manufacturing statement did not establish HQ. Frozen factory-based HQ label is disputed |
| Morozko Forge | Review | **Retry needed** | Provider request returned HTTP 500 / response-stream timeout. No usable page or model decision |
| Fluid Float | Review | Review | Found a combined hot-tub/cold-plunge system; headquarters unknown. The hot-tub exclusion makes product interpretation worth reviewing |
| Polar Monkeys | Review | Review | Relevant product fetched; assembly/service in the USA rejected as headquarters |

The five master-name conflicts are Homecraft, Coldture, LeisureCraft/Dundalk Leisurecraft, BlueCube and Morozko (which retained a hostname after the fetch failure). They are recognized as known websites and remain unresolved identity comparisons. No relationship was silently merged or labelled a confirmed new supplier.

## Changes to prioritize next

1. **Fix page selection using Penguin's saved pages.** Penalize replacement filters and other accessories even when their names contain “all-in-one cold plunge.” Prefer the observed relevant collection when no actual complete-product link is available. Test the ranking offline before another paid preview.
2. **Separate headquarters, offices and production sites.** BlueCube shows that a street address on Contact is insufficient by itself. Preserve location type and context, including workshop/factory/showroom, and require explicit HQ/office support. LeisureCraft needs better address-quote selection while continuing to reject manufacturing as HQ. Replay both saved responses before live checks.
3. **Require evidence that supports the claim.** A compartment or compatible optional chiller does not automatically prove a supplied complete system; an email or phone line does not prove a company role. LeisureCraft and Alpha have `product_match=supported` despite notes saying a packaged system is unproven. They did not qualify, but that inconsistency needs regression coverage.
4. **Test a bounded fetch fallback for Morozko.** Its saved provider output establishes an extraction timeout, not supplier ineligibility. Benchmark browser fallback separately with its own caps and cost record.
5. **Review ambiguous labels separately.** Preserve these frozen results. Create an adjudicated version for BlueCube's HQ, Alpha's factory address, LeisureCraft's complete-system configuration, and Fluid Float's dual hot/cold product. Do not rewrite the frozen labels to improve this score.

After these development fixes, test discovery and catalogue assistance separately, then evaluate fresh independent final cases. No actor comparison, discovery, catalogue pricing/variant coverage or overall internet recall was measured in this rerun.

## Cost, execution and saved evidence

Final read-only provider verification found **46 terminal actor runs** and no active runs or missing usage values. One succeeded actor contains Morozko's failed page request; actor completion is not proof of extraction success. There were **15 model calls**, 46 page attempts and 61 external calls. All eight jobs completed without reaching a job limit; Morozko's per-site failure remains recorded.

- Reported Apify usage: **$0.095850**.
- Model usage: **$0.228291 estimated at configured rates**.
- Combined execution: approximately **$0.324141**, excluding account/storage fees; approximately $0.081 per frozen-label qualified result, or $0.108 per qualification with clear HQ/office evidence on inspection.
- Conservative reservations ranged from $2.017 to $3.035 per pair within the $4 ceiling. Reservations are not actual spend.
- Sum of recorded job elapsed times: **671.01 seconds (11 minutes 11 seconds)**, excluding inspection and gaps between jobs.

All rounds are under ignored `var/eval/cold-plunge-2026-10-27/evidence-collection/`:

| Round | Job | Cases |
| --- | --- | --- |
| `remaining-development-1` | `evidence-a2ddcf7d8219` | Redwood, Penguin |
| `remaining-development-2` | `evidence-c913f96d0a26` | LeisureCraft, Homecraft |
| `remaining-development-3` | `evidence-6a6c6c322026` | Ice Barrel, Renu |
| `remaining-development-4` | `evidence-ecb1d30e0729` | Canadian Spa, Fire Magic |
| `remaining-development-5` | `evidence-b2b5cc041819` | Alpha, Morozko |
| `remaining-development-6` | `evidence-821e62c45bdd` | Fluid Float, Polar Monkeys |
| `remaining-development-7` | `evidence-7e0d57748e64` | Coldture, Sun Home |
| `remaining-development-8` | `evidence-e9c2bd8f2ff4` | BlueCube, Plunge |

Each retains its manifest, isolated job database, result and captured pages. Aggregate files are `remaining-development-metrics.json`, `remaining-development-evidence-audit.json` and `remaining-development-provider-verification.json`. Morozko's saved error is `remaining-development-5/morozko-provider-response.json`. Earlier debugging costs and offline replay results are excluded from this rerun's totals. No development servers, deployments or pull requests were started.
