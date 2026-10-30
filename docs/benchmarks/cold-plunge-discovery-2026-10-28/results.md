# Discovery preview — 2026-10-28

**The no-seed search completed, but produced no qualified suppliers. Candidate selection is now the next priority.** Qualification held two unsupported company roles for review; a third selected result was an editorial article with no usable fetched evidence. This preview does not demonstrate better discovery yet.

Local branch `feat/manufacturer-discovery-evaluation`, run commit `83365b3`. Backend behavior is unchanged from requested-product-role application `35a9304`. The [brief](brief.md) and [capture runner](run_discovery_check.py) were committed before execution. The [audit helper](audit_discovery.py) verifies saved evidence and can read existing actor statuses without starting new runs.

## Execution and decisions

Job `discovery-60c414c14ce4`, round `baseline-1`, completed in **101.73 seconds**. No supplied websites. Brief: complete cold-plunge systems, Manufacturer/Brand owner only, company location in the United States or Canada, existing private master reference with 13,267 records.

Limits were three candidate verifications, three page attempts per company, nine total pages, fifteen external calls, 600 seconds, $6 conservative exposure and $0.50 per actor. Shopping, catalogue analysis, browser fallback and exports were disabled.

Only the **US-localized search** ran. Its two query result pages filled the global three-candidate verification allowance before the country loop reached Canada. Canada remains untested in this discovery preview. Search localization never establishes a supplier's company location.

| Selected site | Saved evidence and manual review | Decision |
| --- | --- | --- |
| [The Cold Plunge Store](https://thecoldplungestore.com/pages/contact) | Multi-brand shopping presentation. The [Embrace product](https://thecoldplungestore.com/products/embrace-limitless) explicitly lists an included tub and chiller, but the captured material does not establish this company's manufacturer/brand-owner role or qualifying company location. | Review: `supplier_role_not_established`. Model Retailer was not retained as a verified role. |
| [Men's Fitness article](https://www.mensfitness.com/gear/best-cold-plunge-tubs-reviewed) | Title/path/snippet identify an editorial product comparison. The raw fetch returned no usable page; no model judgment was made. | Retry needed: `website_evidence_unavailable`. This remains a collection failure, not an automatic negative supplier label. |
| [Titan Wellness](https://titan-wellness.com/) | The [Summit bundle](https://titan-wellness.com/products/summit-barrel-cold-plunge-tub-chiller-bundle) presents a tub/chiller combination. Captured own-product naming and a chiller promotion do not establish the asserted Brand owner role. [Contact](https://titan-wellness.com/pages/contact-us) storefront wording is insufficient company-office/HQ evidence. | Review: `supplier_role_not_established`. Raw model US/office fields are unverified; the country resolver was not reached after the role hold. |

All three selected sites were `unmatched` against the saved master by available website/name checks. That means **research candidates, not confirmed new supplier identities**. There were zero automatic exclusions and zero qualifications. Qualified precision is undefined with no qualified results; this small sample cannot estimate production accuracy.

Seven website fetch attempts returned six usable captured pages, followed by two model calls. Titan's homepage and product captures reached the 120,000-character ceiling; long navigation/content can hide useful evidence. This is a separate collection concern, not permission to infer missing role or location facts.

## What the search returned

The actor returned **19 organic rows across two queries, with 19 distinct normalized hosts**:

1. `Complete cold plunge systems manufacturer` — ten rows.
2. `Complete cold plunge systems brand official website` — nine rows.

The current selector walks the first query's rows until three unblocked hosts have been selected. It returned The Cold Plunge Store, Men's Fitness and Titan, plus a blocked The Spruce record encountered before the cutoff. **No candidate from the second query reached verification.** All nineteen raw rows are available only because the evaluation runner captured the actor dataset before selection.

The following is a manual screen of public search titles/snippets/paths, with offline master checks. Unfetched sites have **not** been verified for role, complete-system contents, country or identity.

| Surfaced host | Search-result screen | Master check / actual job outcome |
| --- | --- | --- |
| thecoldplungestore.com | Multi-brand store; fetched | Unmatched; role review |
| mensfitness.com | Editorial comparison; fetch failed | Unmatched; retry needed |
| thespruce.com | Editorial comparison | Blocked; recorded skipped |
| titan-wellness.com | Product-company lead; fetched | Unmatched; role review |
| forbes.com | Editorial comparison | Blocked; outside selection window, no job skip record |
| desertplunge.com | Craftsmanship/manufacturing language; unverified | Exact master host; not processed |
| peakprimalwellness.com | Multi-brand collection; unverified | Unmatched; not processed |
| regentotalwellness.com | Company/building language; unverified | Exact master host; not processed |
| nwimmersion.com | Product-collection lead; unverified | Unmatched; not processed |
| foceedo.com | Manufacturer roundup article; company role unverified | Unmatched; not processed |
| plunge.com | Historical development supplier's product lineup | Exact master host; not processed |
| colderatti.com | Product-company lead; unverified | Exact master host; not processed |
| calorehealthandwellness.com | Product collection; role unverified | Exact master host; not processed |
| us.getvitalplus.com | Regional product page; role unverified | Exact master host; not processed |
| chilltubs.com | Regional company/product page; role unverified | Exact master host; not processed |
| help.plunge.com | Product support/manual | Related master domain; identity unresolved; not processed |
| aurelinewellness.com | Product collection; role unverified | Unmatched; not processed |
| youtube.com | Video/tutorial platform | Blocked; outside selection window, no job skip record |
| amazon.com | Marketplace product listing | Blocked; outside selection window, no job skip record |

Across all raw results: seven exact-master hosts, one related host, four blocked hosts and seven other unmatched hosts. The production job recorded only its selected window: three checked and one blocked skip, leaving fifteen raw hosts outside its result ledger. None was skipped as already in the master during this particular live run because all seven known hosts were beyond that window. Related domains must remain ambiguous until checked.

Only Plunge from the sixteen historical development/anchor sites appeared: **1/11 commercially relevant historical sites surfaced**, and none of the six historically expected-qualified sites. This is retrieval coverage of this saved two-query sample, not web-wide recall or a current qualification score. The frozen labels have previously documented HQ/product ambiguities. No historical final-check host surfaced; labels and previous reports were not changed.

## Demonstrated gaps and next change

The live run demonstrates first-query dominance, editorial/store selection ahead of later apparent company sites, and missing audit records for rows beyond the cutoff. Query words such as “manufacturer” do not prove a supplier role. The existing role guard appropriately prevents automatic qualification of unsupported claims.

A separate **network-blocked synthetic diagnostic** reproduced the pre-master cutoff defect: with a one-candidate limit and ordered results `[known host, unseen candidate]`, the job skips the known host, verifies **zero** sites and reports completed although the unseen candidate was available. This defect did not cause the live sample's three selections; keep the evidence separate. The diagnostic uses synthetic data and mock providers and changes no production code or saved master data.

The next implementation should:

1. Retain a bounded candidate pool from both requested-role queries. Record blocked, master-known, repeated and unselected rows before choosing verification work; known/repeated hosts must not consume that work allowance.
2. Give apparent first-party company/product sources priority over editorial comparisons and multi-brand stores, using explainable discovery hints. Hints affect ordering only; they cannot verify a role, country or supplier identity. Do not add sample-specific domain exceptions.
3. Test selection offline against synthetic ordering/master/duplicate traps and these saved SERPs, then run another three-site preview under the same caps. Test Canada explicitly rather than assuming an allowed country was searched. Directory discovery and broader query variants remain separate follow-ups.

No backend changes have been implemented as part of this baseline. A larger paid search would currently spend more checks without addressing selection quality.

## Validation and cost

**173 offline tests passed.** All nine retained quote observations matched their captured sources and the twelve-word limit; all six page hashes and manifest source hashes matched. The master file hash remained unchanged. The audit checked all eight actors through read-only run API requests: all were terminal and successful, including the actor whose page-level result yielded no usable article evidence.

Final reported actor usage was **$0.018025**; two model calls cost an estimated **$0.03878175** from returned tokens at configured rates. Combined execution was approximately **$0.05680675**, excluding account/storage fees. Conservative reserved exposure was **$4.038782** against the $6 limit. The job used ten external calls: eight actors and two models. Actor billing was rechecked after execution rather than relying on earlier, lower provisional figures.

Private artifacts: `var/eval/cold-plunge-discovery-2026-10-28/baseline-1/` contains the manifest, isolated job database, raw SERPs/selected candidates, captured pages, fetch attempts, model analyses, result, source/provider audit and manual-screen input. `diagnostics/` contains the synthetic cutoff reproduction and its result. The master reference, contacts and raw datasets stay outside Git. No source-list edits, Sheets writes, development servers, pushes, PRs or deployment occurred.
