# Headquarters and location context — 2026-10-27

**The HQ guard now keeps BlueCube in review instead of accepting a workshop address as headquarters.** Penguin and Sun Home retain their valid office/HQ evidence. LeisureCraft's newly fetched Contact page establishes a head office, but its automatic qualification still needs manual product review: a chiller compartment does not prove an included chiller.

Application code: `136cd512ad46411767b4e6037208e79a613444a4`, branch `fix/headquarters-location-context`, based on `355d77e`. Application files stayed unchanged during live validation. This is a targeted development check, not a new full-cohort benchmark pass.

## What changed

- Contact/About URL paths and generic contact headings no longer turn unlabeled addresses into offices. A street address remains a research lead until the source establishes company-base, HQ or office context.
- Country evidence is classified as `headquarters`, `office` or `company_base` when supported. Workshop, factory, warehouse, showroom, shipping/return and customer/dealer passages cannot substitute for that context. Rejected location claims retain their type in diagnostics; unlabeled addresses remain `unknown`.
- Source context follows nearby label/address blocks. A heading from another address card or unrelated paragraph cannot establish the quoted location. HQ/office headings still need a location value; office hours or “visit our office in person” are insufficient.
- Valid overlong office quotes can still be shortened to a literal contiguous span. Unsupported workshop/origin quotes cannot be shortened into HQ proof. The original quote remains in the audit when shortening succeeds.
- Address leads now favor Contact for follow-up, without qualifying a country. Explicit homepage office context can instead leave follow-up slots for products. The model prompt states these distinctions; the deterministic validator enforces them even when the model disagrees.

The brief permits a clearly labelled company office as location support. The `location_type` records whether evidence actually says HQ, office or company base; accepting an office does not independently prove global legal headquarters. Country geography and company identity still require the model and official source context. This remains a conservative text heuristic.

## Offline validation

All **92 tests pass**, including eight new regression tests covering BlueCube's actual workshop passage, unlabeled Contact/About addresses, nearby-but-separate address cards, clipped production-site statements, explicit HQ/office cards, missing location values, full qualification despite a false model HQ claim, and address-lead routing. Existing bare-contact-address expectations were tightened to require office context. A further subcase preserves LeisureCraft's newly observed Head Office & Manufacturing card.

Revalidation of **18 saved decisions** (the 16-case development rerun plus the two page-selection controls) removed only BlueCube's retained country evidence. Five other accepted observations across four distinct suppliers retained HQ/office support. LeisureCraft's old unlabeled footer address stayed unknown. This rechecked retained evidence, not new model judgments.

The network-blocked 16-case navigation replay changed five routes: Penguin, LeisureCraft, Fire Magic, Alpha Sauna and Polar Monkeys. The remaining eleven routes stayed identical. Some new destinations were absent from old captures, so that replay proves selection only. Live checks below cover Penguin and LeisureCraft's changed routes plus BlueCube and Sun Home controls; the other three changed routes have not been live-tested on this version. No provider calls were made during either replay.

## Live results and manual review

| Case | Automatic result | Evidence and manual conclusion |
| --- | --- | --- |
| BlueCube | **Review: HQ not established** | Complete C1 product evidence retained. Model again asserted HQ from the visit/workshop address; validator rejected it as `workshop`. Keep for HQ review, not exclusion |
| Penguin | **Qualified** | Labelled Knoxville office retained as `office`. Homepage office context lets the remaining pages reach the cold-therapy collection and actual Summit product; complete-system evidence remains supported |
| LeisureCraft | **Qualified automatically; hold for product review** | Contact now supplies a Head Office & Manufacturing label with the adjacent Melancthon address, classified `headquarters`. Product quotes establish a compartment and optional/compatible chillers, not an included chiller. This is an unconfirmed qualification |
| Sun Home | **Qualified** | San Diego headquarters card retained as `headquarters`; integrated-chiller product remains supported |

Raw totals: three qualified and one review. Manually confirmed complete-system qualifications in this targeted check: Penguin and Sun Home. BlueCube needs HQ evidence; LeisureCraft needs configuration evidence. Do not describe the three automatic qualifications as three confirmed suppliers. Frozen labels and the original job results are preserved; LeisureCraft's separate manual adjudication records the concern.

All **28 retained quotes** were matched against captured source text, including requested/redirected URLs and Unicode/whitespace normalization. This is literal verification, not proof of claim meaning. LeisureCraft's product decision demonstrates the remaining semantic gap. Raw model country/notes can also disagree with the final verified evidence; they remain model observations and do not bypass the qualification guard.

## Execution and cost

Both batches were seed-only, preview-only, with discovery, Shopping, catalogue analysis and browser fallback disabled. Each pair retained three pages/site, six pages total, twenty external-call maximum, 600 seconds, a $4 exposure ceiling and $0.50 cap per actor. No final-check cases, exports, source-list edits, servers, pushes, pull requests or deployment.

| Round | Job | Cases | Elapsed |
| --- | --- | --- | --- |
| `location-context-1` | `evidence-f6e969aaac1e` | BlueCube, Penguin | 66.19 seconds |
| `location-context-2` | `evidence-7c76816c444e` | LeisureCraft, Sun Home | 69.74 seconds |

The two completed jobs used twelve actor runs, four model calls, twelve pages and sixteen external calls. Final read-only verification found every actor run terminal and no missing usage values.

- Reported Apify usage: **$0.025500**.
- Model usage: **$0.07022925 estimated at configured rates**.
- Combined execution: approximately **$0.09573**, excluding account/storage fees.
- Conservative reservations: $3.03818 and $3.032049 within the $4 per-pair ceilings; reservations are not spend.

Ignored records are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `location-context-offline-replay.json`, `location-context-navigation-replay.json`, `location-context-provider-verification.json`, and the two round folders containing manifests, isolated databases, captured pages, results and evidence audits. LeisureCraft's manual decision is in `location-context-2/manual_adjudication.json`. Application-source hashes match the code tested.

## Next

Require evidence of supplied components before declaring a complete system. Start with LeisureCraft's saved compartment/compatibility passages and compare them with explicit Summit/Sun Home inclusion statements. Also tighten role evidence and exact role classification; contact lines and design statements alone do not settle every manufacturer/brand distinction. Test those saved cases before another paid preview. Browser fallback for Morozko, discovery/catalogue evaluation and fresh independent final cases remain later steps.
