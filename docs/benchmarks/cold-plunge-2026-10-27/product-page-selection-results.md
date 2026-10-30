# Accessory-page selection fix — 2026-10-27

Later follow-up: [HQ/location-context validation](headquarters-context-results.md) keeps BlueCube in HQ review and verifies LeisureCraft's head office while flagging its unproven complete-system configuration. This document preserves the earlier page-selection result.

**Penguin now qualifies from complete-system evidence instead of spending its last page on a replacement filter.** Redwood remains qualified in the live control. This is a targeted development check, not a new complete benchmark result.

Code: `7c440a2853d15c985df81eac1586253c767eb93d`, branch `fix/product-page-selection`, based on `d12579d`. The [preceding 16-case report](development-rerun-results.md) remains the full-cohort result for its earlier version.

## Problem and change

Penguin's `all-in-one-cold-plunge-filter` contained both an accessory word and a complete-system keyword. The old rule let “all-in-one” cancel the component penalty, placing this replacement filter above the observed cold-therapy collection.

For a complete cold-plunge brief, explicit accessory names now receive lower priority even when they contain “bundle,” “integrated” or “all-in-one.” The rule checks the decoded item slug and anchor label with word boundaries. It separates accessories from standalone chillers, so a real tub/chiller bundle retains its priority. Included extras after “with,” “including” or “includes” do not make a complete tub an accessory. An explicitly requested filter/accessory remains searchable.

This changes navigation order only. Accessory pages remain available; neither qualification requirements nor page, service-call and cost limits were relaxed. These name heuristics do not establish what a product actually includes; qualification still requires source evidence.

## Offline validation

All **84 tests pass**, including four new regression tests. The new tests first reproduced the filter-selection failure. They cover Penguin's destination under a three-page cap, accessory names that contain complete-system keywords, tubs with included accessories, and explicit filter briefs.

A network-blocked replay compared the preceding code with the fix using all 16 saved development/anchor captures. Only Penguin's requested route changed:

| Version | Pages requested |
| --- | --- |
| Before | Homepage → Contact → all-in-one replacement filter |
| After | Homepage → Contact → cold-therapy collection |

The other 15 routes remained identical. The new collection was absent from those saved captures, so this replay verifies destination selection, not collection content or qualification. It made zero provider calls; the subsequent live check supplied the missing page.

## Live confirmation

Round `product-selection-1`, job `evidence-fa9ebf34c1e7`, ran on the committed code above. Both cases completed and qualified:

| Case | Previous decision | New decision | Evidence |
| --- | --- | --- | --- |
| Penguin Chillers | Review: requested product not established | **Qualified** | Cold-therapy collection describes Summit with an integrated chiller and stainless tub; manufacturer evidence and a labelled Knoxville office address are retained |
| Redwood Outdoors | Qualified | **Qualified** | All-in-one tub/chiller collection, Denali product and labelled Kent office address |

Penguin's homepage and Contact text hashes were identical to the preceding run; all three Redwood source-text hashes were also identical. The changed Penguin destination supplies the new complete-system evidence. All 11 retained quotes were independently matched against the saved captures, checking requested and redirected URLs.

The exact role classification still needs work: Redwood was labelled `Manufacturer` here versus `Brand owner` before, although its design statement clearly supports a brand role and does not by itself establish manufacturing. Both roles are permitted by this brief, so the qualification control remains valid; this is a concrete example for the pending claim-semantics work.

Settings stayed seed-only and preview-only, with discovery, Shopping, catalogue extraction and browser fallback off. Two sites, three pages/site, six total pages, twenty-call maximum, 600-second runtime limit and $4 execution exposure ceiling; each actor had a $0.50 charge cap. No final-check cases, Sheets exports, servers, deployment, push or pull request were involved.

## Cost and saved records

The job used six actor runs and two model calls, completed in **72.68 seconds**, and stayed within all limits. Final read-only provider verification found all six actor runs terminal and no missing usage values.

- Reported Apify usage: **$0.012750**.
- Model usage: **$0.03236975 estimated at configured rates**.
- Combined execution: approximately **$0.04512**, excluding account/storage fees.
- Conservative reservation: **$3.03237** within the $4 ceiling; this is not actual spend.

Ignored records are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `product-selection-offline-replay.json`, `product-selection-provider-verification.json`, and `product-selection-1/` with its manifest, database, result, captured pages, evidence audit and source comparison. Source hashes match the committed application files.

## Next

Separate HQ/office evidence from workshop/factory/showroom locations, starting with BlueCube's saved response. Improve LeisureCraft's address-quote selection and resolve its product-configuration ambiguity. Then validate claim meaning and exact role classification, followed by bounded fetch fallback for Morozko. Preserve frozen labels and the earlier full-cohort score; this two-case confirmation does not establish that the complete current-version benchmark passes.
