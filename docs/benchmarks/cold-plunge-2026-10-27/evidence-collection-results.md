# Evidence collection and headquarters checks — 2026-10-27

Latest follow-up: [complete 16-case development rerun on fixed commit `480d5b6`](development-rerun-results.md). Four qualified, eleven review, one fetch retry; BlueCube's HQ remains a manual-review issue. This document preserves the earlier targeted development history.

Local branch: `fix/evidence-collection-and-hq`, based on `0726ee0`.

The targeted checks now collect useful product and headquarters evidence for Coldture and Sun Home. The original shipping-as-headquarters failure is blocked. BlueCube's valid address passes a saved-response replay after deterministic quote shortening. Plunge remains in review for missing headquarters evidence. This is development validation, not a pass of the complete supplier benchmark.

## What changed

- Request HTML and readable output together; preserve navigation/footer anchors and office-location content. Parse visible HTML text separately from links so Markdown emphasis does not invalidate a literal quote. Actor input options were checked against the [Apify input schema](https://apify.com/apify/rag-web-browser/input-schema).
- Follow observed same-site links, including links found on follow-up pages. Keep the existing page, call, runtime and charge caps. Alternate company/product evidence rather than spending all follow-ups on one type.
- Prefer Contact when a homepage city/region hints at a location but does not establish office context. That hint changes routing only; it never qualifies a country claim.
- Prefer relevant product/bundle pages over educational protocols, images, standalone chillers and accessories when the brief requests a complete plunge system. Other briefs retain their own requested-item scope.
- Reserve excerpt space for headquarters, product configuration, role and contacts. Keep headings with their following values and keep product-configuration passages contiguous. Supply observed product links separately.
- Require affirmative company-location or office-address context for country quotes. Shipping, warehouse, showroom, customer, origin/founding and negated location statements do not establish headquarters. These checks do not independently establish legal headquarters or verify geography.
- Preserve failed-quote diagnostics. An overlong location quote can be shortened only when the full quote is literal and already supports a company location, and the shorter contiguous span independently passes the same checks. Keep the original quote for audit. Unsupported/nonliteral claims cannot be repaired into headquarters evidence.

## Validation

All **80 offline tests pass** (58 before this branch). New regressions cover HTML/footer links, empty image-alt attributes, product routing, secondary links and page limits, navigation-only browser fallback, product/HQ excerpt selection, HQ heading/value cards, shipping/warehouse/customer/negation failures, contextual office addresses, safe quote shortening and protection of final-check cases in the preview runner.

| Development case | Earlier result | Latest check | Evidence / limitation |
| --- | --- | --- | --- |
| Coldture | Review: product not established | **Qualified in live preview** | Homepage HQ FAQ, cold-plunge collection, and an actual tub + Chiller Pro bundle page |
| Sun Home | Review: HQ not established | **Qualified in live preview** | About-page HQ card and integrated-chiller product page |
| BlueCube | Qualified before these changes | **Qualified in offline replay of saved live evidence** | Contact page was fetched; the live model's overlong address quote was shortened to a literal ten-word address. No new model/provider calls in replay |
| Plunge | Review: HQ not established | **Review in live controls** | Complete-product evidence retained; origin/manufacturing statements do not substitute for HQ |

The BlueCube control first exposed a routing regression (About instead of Contact), then a model quote longer than the twelve-word limit. Both issues have explicit regressions. Its final replay is distinguished from a fresh live qualification. Coldture/Sun Home live checks preceded the last Contact-selection and quote-shortening refinements; source hashes preserve each version.

Settings: seed-only, preview-only, discovery/Shopping/Shopify/browser fallback off, two sites per batch, at most three pages per site and six pages per batch, 600-second runtime limit, twenty service calls and a $4 conservative execution ceiling per batch. Each actor run had a $0.50 provider charge cap. The earlier benchmark used two pages per site, so these observations measure the combined evidence changes and revised page allowance, not an isolated A/B comparison.

No final-check cases ran in this work. No Sheets writes, source-list edits, development servers, deployments or pull requests were involved.

## Costs and saved evidence

All six debugging/validation rounds together used 32 actor runs and 10 model calls. Final provider verification reported **$0.0661** in actor usage; model usage was **$0.1677935 estimated at configured rates**. Combined execution cost was approximately **$0.234**, excluding account/storage fees. This includes unsuccessful development rounds, not just successful checks. No actor runs remained active at verification.

Results are in ignored `var/eval/cold-plunge-2026-10-27/evidence-collection/`:

| Round | Job | Purpose |
| --- | --- | --- |
| `html-navigation-1` | `evidence-6d293abd288f` | Found empty HTML image-alt handling error; saved responses were replayed locally |
| `html-navigation-2` | `evidence-5dd4240963fe` | Found poor product-page ranking and separated HQ heading/value windows |
| `html-navigation-3` | `evidence-15474c72ae50` | Validated collection evidence; found HQ quote spanning separate HTML blocks |
| `final-evidence-1` | `evidence-472555cfa565` | Coldture and Sun Home live qualifications |
| `final-controls-1` | `evidence-1bf0778abb31` | Exposed BlueCube Contact-routing regression; Plunge stayed in review |
| `final-controls-2` | `evidence-cb0170602b61` | Correct Contact routing; saved BlueCube address quote then passed offline revalidation |

Each round retains request settings, code/source/label hashes, captured pages, job decisions and provider run/build/dataset identifiers. `provider_verification.json` records final charges and run states. BlueCube's offline replay is in `final-controls-2/offline_location_revalidation.json`. The runner refuses existing round names and final-check IDs, preventing accidental repeat charges or evaluation on protected cases.

## Benchmark scoring and next work

The earlier 1/11 development+anchor figure counts eleven commercially relevant suppliers, including five explicitly labelled `expected_status=review` because headquarters are unknown. Only six are labelled expected-qualified. Report qualification coverage against those six separately from the useful-but-unverified review queue. Also recheck labels that infer a bundle from separate tubs/chillers or HQ from manufacturing history.

No new full-cohort precision/recall estimate is made from these adaptive development checks or the single original acceptance. Redwood, Penguin and LeisureCraft have not been rerun on this branch. Discovery and catalogue-assisted qualification also remain unmeasured. Run those development checks next, then use fresh independent final cases: the original final-check group already appeared in the first baseline.
