# Office-country evidence consistency — 2026-10-28

Follow-up: [bounded fetch-fallback validation](fetch-fallback-results.md) checks fresh Morozko/Redwood fetching and controlled timeout-to-browser recovery. The location results below remain unchanged.

**Penguin and Redwood now qualify from verified US office evidence without being described as confirmed global headquarters.** Coldture retains its Canadian HQ basis. This resolves the model-country/basis inconsistency recorded in the [role-validation report](role-evidence-results.md).

Application: `e4d32e2239b850d8b1b45324643e8a88f72e5e92`, branch `fix/office-country-evidence`, based on `6559079`. Application files stayed unchanged throughout final validation. These are targeted development checks, not a new full-cohort or final-check benchmark pass.

## What changed

Final country and location basis now come from verified company-location statements rather than inconsistent model fields. The existing policy permits labelled company offices, explicit headquarters and company-based-in statements. Their output bases remain distinct: `office`, `headquarters` and `company_base`. An office does not independently establish global legal HQ.

The model schema now accepts `office` and `company_base` alongside its previous country-basis values. The prompt explicitly explains office eligibility and asks for the office address rather than a manufacturing-origin substitute. Final results preserve the original `model_country` and `model_country_basis`, plus location-support observations and source quotes.

A bounded scan can recover location evidence from existing captures: at most 256 candidate windows per page, with up to two supporting quotes of at most twelve words. It makes no additional model or page request. Geography must be established by an explicit recognized country name or a supported US/Canadian region-address pattern; the model's country guess, currency, TLD, shipping markets and master-list fields cannot fill that gap. Postal context distinguishes Ontario, California from Ontario province.

Explicit HQ outranks office evidence; offices outrank generic company-base statements. Different countries at the same priority cause review, including when both countries are allowed. An unresolved higher-priority HQ cannot be bypassed with an allowed-country office. Foreign HQ evidence therefore takes precedence over a US office.

The shared location guard also rejects contracted negation, planned/former locations, employee/partner/supplier locations and office-goods phrases, including clipped quotes. “Headquartered” is correctly typed as HQ. “Repair at HQ” is not a location value. Manufacturing sites, workshops, warehouses, returns and unlabeled addresses remain insufficient.

## Offline validation

All **137 tests pass**, including seventeen new regression methods. Tests first reproduced the Redwood unknown-country and Penguin manufacturing-basis failures, then covered literal recovery, raw model-field preservation, both new schema values, geography conflicts, HQ precedence, address-card boundaries, non-current and third-party locations, and the existing workshop restrictions. The older bad-citation test continues to reject invented product evidence; independently recovered country evidence is separately tested and never validates an invented quote.

The network-blocked replay reuses **31 saved results: 29 analyses and two unchanged fetch failures**. Compared with `6559079`, only the latest Penguin and Redwood review decisions become qualified, both on US office evidence. All eleven previously accepted observations across four distinct suppliers remain qualified. No other status changes or new exclusions occur. Repeated observations are not additional suppliers.

The baseline supplier and location validators were restored from `6559079` for comparison. Replay reconstructs saved analysis fields with `is_product_company=True` and `owns_brand=None`; it makes no new model judgments and does not retest navigation. A separate source-only check on BlueCube's actual captured workshop pages still returns no acceptable company-location proof.

## Final checks

| Supplier | Mode | Verified result |
| --- | --- | --- |
| Penguin | New live preview, three pages | **Qualified — United States, office.** Manufacturer and complete-system proof retained. Knoxville office quote establishes location; global HQ is not claimed |
| Coldture | New live preview, three pages | **Qualified — Canada, headquarters.** Own-brand, tub/chiller bundle and Vaughan HQ evidence retained |
| Redwood | One new model call on three previously captured pages | **Qualified — United States, office.** Brand owner, complete-system and labelled Kent office evidence retained. The earlier failed fresh fetch remains recorded |

All three new model answers also selected the correct location basis directly. The deterministic resolver separately fixes their earlier inconsistent saved answers. All **24 retained quotes** matched captured sources, including URL aliases and Unicode/whitespace normalization; supporting country statements were manually checked for the stated location type and geography. Live/reanalysis manifests and replay hashes match the application commit above.

## Execution and cost

| Round | Job | Elapsed |
| --- | --- | --- |
| `office-country-1` | `evidence-fc4d14a7934b` — Penguin/Coldture live pair | 86.63 s |
| `office-country-redwood-reanalysis` | `evidence-fdbd4c4729b1` — saved-page model analysis | 6.95 s |

The live pair retained three pages/site, six total, twenty external calls, 600 seconds, a $4 exposure ceiling and $0.50 cap per actor. Redwood reanalysis retained one external call, 90 seconds and a $0.50 exposure ceiling, with zero page requests. Discovery, Shopping, catalogue analysis and browser fallback were off. Both jobs were preview-only.

Total: **six actor runs, three model calls, six new pages and nine external calls**. Read-only provider verification found all actors terminal, no missing usage values and no reached limits.

- Reported Apify usage: **$0.012750**.
- Model usage: **$0.061859 estimated at configured rates**.
- Combined execution: **$0.074609**, approximately **$0.075**, excluding account/storage fees.
- Reservations: $3.044058 for the live pair and $0.017801 for saved-page analysis; reservations are not spend.

No final-check cases, exports, source-list edits, dev servers, pushes, pull requests or deployment.

## Records and next work

Ignored records are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `office-country-tests.log`, `office-country-replay.py`, `office-country-offline-replay.json`, `office-country-bluecube-source-control.json`, `office-country-source-audit.json`, `office-country-provider-verification.json`, `office-country-final-validation.json`, the saved-page reanalysis helper, and both job folders containing manifests, isolated databases, captures, results and quote audits. Historical reports, frozen labels and earlier raw results remain unchanged.

This is a conservative text/address resolver, not general geocoding or an independent legal-HQ audit. Unrecognized geography, ambiguous address structures or conflicting offices can still require review. Next, test bounded fetch fallback for Morozko's timeout and Redwood's empty-evidence result. Live distributor validation, requested-product/brand role relationships, discovery/catalogue evaluation and fresh independent final cases remain pending.
