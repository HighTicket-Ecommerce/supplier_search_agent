# Complete-system component evidence — 2026-10-27

**LeisureCraft now stays in review because a chiller compartment or optional chiller does not establish a supplied tub-and-chiller system.** Penguin, Sun Home and Coldture retain supported complete-system evidence and qualify in the targeted previews. This fixes the product-evidence gap identified in the [HQ/context check](headquarters-context-results.md).

Final application commit: `3b5952c78f1cb96d493feead69cced6390e5a8f5`, branch `fix/complete-system-components`, based on `44c36bc`. The two paid previews ran on `7ff1170b695a5fcf2e71e2bacca0a2d79e62cc25`. A subsequent paragraph-boundary/catalogue-list refinement was tested offline, including replay of all four new live responses; there was no additional provider run after that refinement. These are targeted development checks, not a new full-cohort benchmark pass.

## What changed

Recognized complete cold-plunge/ice-bath briefs now require evidence of both a tub and an included or integrated chiller. A deterministic guard checks the model's literally verified product quotes against their source passages and matched product pages. It accepts an explicit supplied combination, or an included/integrated chiller on an identified primary plunge product.

Compatibility, readiness, compartments, hoses, controls, optional add-ons and separately sold or excluded chillers cannot supply the missing proof. Neither can generic lists of tubs and chillers, or quotes that join separate product cards or paragraph blocks. Evidence stays tied to its source and configuration; a separate product cannot repair a tub-only quote.

Missing component proof returns review with `complete_system_components_not_established`; the raw model verdict and diagnostic observations remain available. If the model already reports product fit as unestablished, the existing `requested_product_not_established` review path applies, as it did for LeisureCraft in the new live check. Other product categories and standalone accessory/chiller requests retain their existing scope. No extra model call or structured-output schema change was added.

## Offline validation

All **104 tests pass**, including twelve new regression tests. They cover false high-confidence model claims, included and integrated systems, clipped negation, compatibility and optional variants, separate cards/pages, generic catalogues, brief scope and preservation of supporting source quotes. Sun Home's trademarked product title remains recognizable. A post-preview regression reproduced a false qualification from a literal quote spanning separate cards; the final paragraph/list safeguards reject it.

The network-blocked replay inspected **26 saved results**, replayed **25 analyses** and skipped Morozko's original fetch failure, which contained no model evidence. Compared with `44c36bc`, only the earlier unsupported LeisureCraft qualification changes status, to review. Ten other previously accepted observations across four distinct suppliers—Redwood, Coldture, Penguin and Sun Home—remain qualified. Three existing review outcomes receive more specific component reasons without becoming exclusions.

Replay reconstructs saved analysis fields, setting `is_product_company=True` and `owns_brand=None`; it makes no new model judgments. It validates this component guard against captured data, not general role accuracy or fresh-site performance. The final source hashes match the replay record. Frozen labels and historical job results remain unchanged, including LeisureCraft's disputed expected-qualified label.

## Live checks

| Case | Automatic result | Component evidence |
| --- | --- | --- |
| LeisureCraft | **Review** | Tub, compatibility, optional chiller and concealed compartment passages do not establish an included chiller. Contact still establishes the Melancthon head office |
| Penguin | **Qualified** | The Summit collection passage explicitly combines an integrated chiller and stainless tub; the actual product page is also fetched |
| Sun Home | **Qualified** | The identified primary plunge product explicitly describes an integrated chiller |
| Coldture | **Qualified** | The barrel + Chiller Pro bundle explicitly includes the water chiller |

All four decisions match manual component review. The final offline refinement preserves these four live decisions. All **33 retained quotes** were literally matched to captured sources, allowing requested/redirected URL aliases and Unicode/whitespace normalization. Literal matching alone does not establish company-role meaning; that remains the next task.

Both batches were seed-only and preview-only. Discovery, Shopping, catalogue analysis and browser fallback were disabled. Each pair used at most three pages/site, six pages total, twenty external calls, 600 seconds, a $4 exposure ceiling and $0.50 charge cap per actor.

| Round | Job | Cases | Elapsed |
| --- | --- | --- | --- |
| `component-evidence-1` | `evidence-5790a036ba0b` | LeisureCraft, Penguin | 65.08 seconds |
| `component-evidence-2` | `evidence-767a72dd2f1e` | Sun Home, Coldture | 66.24 seconds |

The completed jobs used twelve actor runs, four model calls, twelve pages and sixteen external calls. Read-only provider verification found every actor run terminal, no missing usage values and no reached limits.

- Reported Apify usage: **$0.025500**.
- Model usage: **$0.076475 estimated at configured rates**.
- Combined execution: **$0.101975**, approximately **$0.102**, excluding account/storage fees.
- Conservative reservations: $3.034853 and $3.041622; reservations are not spend.

No final-check cases, exports, source-list edits, dev servers, pushes, pull requests or deployment were part of this validation.

## Records and next work

Ignored records are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `component-evidence-offline-replay.json`, `component-evidence-provider-verification.json`, `component-evidence-final-validation.json`, and the two round folders containing manifests, isolated databases, captured pages, results and evidence audits. Live source hashes match `7ff1170`; final replay hashes match `3b5952c`.

This is a conservative category-specific text guard. Fragmented or unfamiliar valid configurations can still require review. It does not establish variant availability, bundle pricing or complete catalogue coverage. Next, validate the meaning and exact classification of company-role evidence: contact lines and product lists cannot establish manufacturing or distribution, and design alone does not distinguish a manufacturer from a brand owner. Morozko's bounded browser fallback, discovery/catalogue evaluation and fresh independent final cases follow.
