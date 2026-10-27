# Exact supplier-role evidence — 2026-10-27

**Company roles now need evidence for the specific classification.** Design alone cannot establish Manufacturer; contact text, store titles and product lists cannot establish a role. Unsupported classifications stay in review. A bounded source-only repair can recover an explicit quote for the same proposed role from captured pages, without another provider call.

Final application: `e0cb37e2bb74e7f83dd95c27e30acb45fa0a4761`, branch `fix/supplier-role-evidence`, based on `6486a27`. The first preview used guard-only `97b5a18`; the second preview and Redwood saved-page reanalysis used the final application. Sun Home's final quote repair was validated against its first preview captures, without another paid run. This is targeted development validation, not a new full-cohort score.

## What changed

- Manufacturer requires self-attributed physical production/building, an explicit manufacturer description, or production in the company's own facility. Design and engineering alone do not establish production.
- Brand owner accepts explicit own-brand statements or the company's own product design/creation. Contract design for other brands, brand directories/partners, and generic retail/store text are insufficient. This is an operational product-brand classification, not a legal trademark-ownership check.
- Distributor requires third-party supply and an explicit business/wholesale channel. An isolated Wholesale label or an own-brand dealer program is insufficient. Retailer, Marketplace and Media/Blog also need specific self-attributed role evidence before they can cause exclusion.
- Negation, future plans, historical statements, customer/dealer attribution, separate source blocks and misleading phrases such as “build relationships” or “manufacturer representative” cannot substitute for role proof.
- Unsupported roles become `Unknown`, preserving `model_supplier_type`, role diagnostics and rejected quotes. Contradictory non-product-company booleans cause review rather than an unsupported exclusion. Irrelevant role quotes are removed from retained evidence even when another quote supports the role.

When the model misses an available role statement, recovery checks at most 96 candidate windows per page and retains at most two literal quotes, each no longer than twelve words. The same role guard revalidates each candidate against its source. Recovered entries carry `evidence_origin=captured_source_role_repair`; the result records `source_repair_used` and the original model-evidence status. Recovery never changes the proposed role. Role excerpts now also reserve space for distribution/reselling statements. No structured-output schema change or additional model call was added to qualification.

## Offline validation

All **120 tests pass**, including sixteen new regression methods. Tests first reproduced unsupported qualification/exclusion and role confusion, then checked exact classifications, attribution, negation, source boundaries, literal quote recovery, unchanged role proposals and retained diagnostics. Network access is blocked in these tests.

Final replay covers **31 saved results, 29 replayable analyses and two fetch failures without model evidence**. Compared with `6486a27`, only Redwood's earlier design-only Manufacturer qualification changes status, to review. Eleven other accepted observations across four distinct suppliers remain qualified; repeated observations are not eleven suppliers. Four existing review reasons become role-specific. No new exclusion is introduced.

The initial guard-only replay also rejected Sun Home's store/contact-only role evidence. The final repair restores that case from actual product-creation statements already in the captured sources, while continuing to reject the irrelevant quotes. Replay reconstructs saved analysis fields, using `is_product_company=True` and `owns_brand=None`; it makes no new model judgments and does not measure fresh-site accuracy.

## Targeted results and limits

| Supplier | Mode and verified role | Qualification result |
| --- | --- | --- |
| Sun Home | First preview on `97b5a18`, then final saved-response replay: **Brand owner**, supported by company-attributed crafting/design statements recovered from captured pages | Raw preview: role review. Final replay: **qualified** with recovered source quotes; no second live run |
| Coldture | Final live preview: **Brand owner**, explicitly a Canadian brand engineering its products | **Qualified**, with complete-system and Vaughan HQ evidence retained |
| Penguin | Final live preview: **Manufacturer**, explicitly manufactures chillers | **Review for HQ**, despite passing role and complete-system checks. Model chose manufacturing country basis and origin quotes instead of the available office evidence |
| Redwood | Live fetch returned no usable page evidence: **retry needed**. One new model analysis on three saved pages correctly selects **Brand owner**, supported by its design statement | Saved-page analysis: **review for HQ**. A literal, labelled Kent office address is retained, but model country/basis remain unknown. This is not a successful fresh fetch |

The role results agree with manual review of the quoted statements. They do not justify describing all four suppliers as qualified. The remaining office/HQ inconsistency is now explicit: the benchmark permits labelled company-office support, while new model answers sometimes insist on a global-HQ statement even when the prompt and source validator permit office evidence. That issue needs its own regression and fix.

All **18 retained quotes in raw new results**, plus the **two recovered Sun Home quotes** in final replay, match captured sources under the existing URL-alias and Unicode/whitespace rules. The final twenty quotes include six role quotes. Source hashes match the exact application version recorded for each run; final replay hashes match `e0cb37e`.

## Execution and cost

| Round | Job | Mode | Elapsed |
| --- | --- | --- | --- |
| `role-evidence-1` | `evidence-a14b751e0310` | Redwood/Sun Home seed-only live preview on `97b5a18` | 72.38 s |
| `role-evidence-2` | `evidence-b870e885e04e` | Penguin/Coldture seed-only live preview on `e0cb37e` | 80.38 s |
| `role-evidence-redwood-reanalysis` | `evidence-0a7017009ea9` | One new model call on three saved Redwood pages, no page requests | 5.26 s |

Live pairs retained three pages/site, six total, twenty external calls, 600 seconds, a $4 exposure ceiling and $0.50 cap per actor. Saved-page reanalysis used a $0.50 exposure ceiling, one external call and 90 seconds. All runs were preview-only; discovery, Shopping, catalogue analysis and browser fallback were disabled.

Total: **ten actor runs, four model calls and fourteen external calls**. Ten page attempts yielded nine usable live captures; Redwood reanalysis supplied three existing pages separately. Read-only provider verification found all actors terminal and no missing usage values. No limit was reached.

- Reported Apify usage: **$0.019350**.
- Model usage: **$0.069748 estimated at configured rates**.
- Combined execution: **$0.089098**, approximately **$0.089**, excluding account/storage fees.
- Reservations: $2.016287 and $3.037880 for live pairs; $0.015580 for saved-page reanalysis. Reservations are not spend.

No final-check cases, exports, source-list edits, dev servers, pushes, pull requests or deployment.

## Records and next work

Ignored records are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `role-evidence-tests.log`, `role-evidence-offline-replay.json`, the saved replay/reanalysis helpers, `role-evidence-source-audit.json`, `role-evidence-provider-verification.json`, `role-evidence-final-validation.json`, and the three round folders containing manifests, isolated jobs, results, captures and evidence audits. Original labels and earlier results remain unchanged.

Next, resolve office/HQ evidence and model-basis inconsistency using these saved Penguin/Redwood cases before another paid check. Then test bounded fetch fallback, including Redwood's new empty result and Morozko's earlier timeout. Distributor rules have offline regression coverage but no live distributor case yet. Role proof is company-level; requested-product manufacturing, legal brand ownership, parent/brand relationships, unfamiliar wording/languages, catalogue coverage and fresh independent final cases still need separate evaluation.
