# Distributor collection fix — 2026-10-28

**The collector now gathers more useful distributor evidence. Automatic distributor qualification is still unresolved.** Keep this as an optional review lane while manufacturer/brand-owner research remains the main workflow. See the [operating guide](../../distributor-workflow.md).

## Implementation and offline validation

Local branch: `fix/distributor-page-selection`. Initial live implementation: `ab50ba4`; final policy-priority refinement: `124050d`.

- Positive navigation terms ignore explicit exclusion tails. Whole-word matching retains short product words such as gas and avoids treating Fire as a match for fireplaces.
- Decoded category facets and structured exclusions rank gas grills ahead of charcoal/electric/accessory categories. Included accessories do not demote a complete product. Broad category exclusions do not bury a potentially relevant dual-purpose product; its contents remain for product analysis.
- Distributor-only checks prioritize About for company context and can read one public account/trade-entry page for policy text. Unknown account actions remain excluded; no authentication or form submission occurs. Other role selections retain the existing account-page exclusion.
- After a company/product pass, a missing trade policy takes priority over another company page. A page limit still applies to raw and browser attempts together.
- Wholesale-policy passages reach the model's excerpt windows, and cache keys distinguish exclusions and distributor-only collection. UI help explains separate exclusions and the four-page recommendation.

**156 tests passed**, including thirteen new regressions for the observed failures and their boundaries. A network-blocked navigation comparison against `ba6cef9` covers sixteen saved cold-plunge development/anchor cases plus the two distributors. Only the two distributor routes change. Missing saved pages are labelled unavailable; the replay does not invent their bodies or re-score supplier decisions. No final-check cases or provider calls were used in that replay.

## Live results

Both previews used the frozen cases and product phrase from the [original brief](brief.md), with discovery, Shopping, catalogue analysis and exports disabled. Request settings, source hashes and raw model analyses were saved before/through execution in isolated databases.

| Preview | Actual collection | Outcome |
| --- | --- | --- |
| `collection-fix-1`, job `distributor-d88e9a33feea`, `ab50ba4` | Rutherford: brand page → About → Gas Grills facet → Contact. Gas Equipment Distributors: home → Gas & Primo Grills → Gas Logs. Seven raw pages, two model calls, 58.68 seconds. | Both remain `review / supplier_role_not_established`. The requested gas-grill category and relevant company context are now captured. The last Gas Logs page is weakly relevant and adds no demonstrated benefit. |
| `collection-fix-rutherford-2`, job `distributor-47d35429be73`, `124050d` | Rutherford only: brand page → About → Gas Grills facet → public login/policy page. Four raw pages, one model call, 36.49 seconds. | Review remains. The explicit wholesale-only statement is now in the model's evidence. No login or registration occurred. |

The first follow-up raised the page cap from six total/three per company to **seven total/four per company**, while retaining the $4 exposure ceiling. The extra evidence cannot be attributed to ranking alone. The final targeted run had four total/four per company. All eleven fetches returned pages through raw HTTP; optional browser fallback did not trigger.

The first preview exposed the scheduling refinement: the company-location routing hint stayed false on Rutherford About, so it selected another company page before policy. The final regression/follow-up changed scheduling only; location and qualification rules were preserved. Gas Equipment Distributors was sampled on `ab50ba4` and was not freshly re-run after the policy-only priority refinement.

## What remains unresolved

**Rutherford:** the captured policy explicitly states “Rutherford Equipment is a wholesale distributor only.” Its gas-grill brand/category evidence is stronger than the earlier accessory route. The existing exact-role guard still rejects the role evidence: wholesale self-description and named-brand offerings are not combined into a scoped relationship. This is not evidence that the company is unsuitable.

The About page also contains “Our headquarters is in Covington, Georgia.” The unchanged location guard rejects it as `shipping_or_returns` because delivery/warehouse language shares its surrounding context. That is a separate context-classification false rejection for a future fix. The raw model's United States/headquarters fields must not be presented as an accepted location verification.

**Gas Equipment Distributors:** the model now receives both the explicit wholesale-only policy and a Fire Magic Gas Grills heading. The existing role guard still leaves it in review. The model also proposes an office interpretation for an unlabelled Nashville address; the location-evidence validator rejects that quote as unknown. Do not treat it as a verified office.

**Product scope and authorization:** the evidence is still largely brand/category level. Rutherford's model notes that no exact complete gas-grill SKU was established by the supplied excerpts, despite returning product_match supported. Do not count the category filter, manuals or protective-cover examples as verification of a specific unit. No brand-side authorization, current stock, reseller acceptance, MOQ, dropshipping, prices or territory was established. A company's own manufacturing claim also remains insufficient to assign that role to every brand/product it sells; the saved Penguin/Summit ambiguity remains relevant.

## Cost and audit

| Preview | Reported actor usage | Estimated model cost | Combined execution |
| --- | ---: | ---: | ---: |
| Two-site collection follow-up | $0.014875 | $0.03532025 | $0.05019525 |
| Targeted Rutherford confirmation | $0.008500 | $0.02357600 | $0.03207600 |
| Total | **$0.023375** | **$0.05889625** | **$0.08227125** |

Eleven actor runs and three model calls. All actors were terminal/successful when inspected through the read-only Apify run API. Model costs are estimates from returned tokens at configured rates; account/storage fees are excluded. Conservative exposure was $3.535320 and $2.023576 respectively against each $4 ceiling.

Sixteen raw model quotes, including those rejected for semantic reasons, were checked for literal source presence and the twelve-word limit; all passed those literal checks. Eight retained quote observations and all eleven page hashes were also verified. Every manifest source hash matches its recorded Git implementation commit. Literal validity does not establish the claim's meaning or eligibility.

Private artifacts: `var/eval/distributors-2026-10-28/collection-fix-1/`, `collection-fix-rutherford-2/`, `collection-offline/routing-comparison.json`, `collection-audit-summary.json` and `raw-model-source-audit.json`. Provider run IDs, request settings, actor/dataset/build provenance, fetch traces, model responses and validations are retained there. No master reference was used in these previews; neither lead is classified as new or existing.

No development servers, source-list edits, Sheets writes, pull requests or deployment occurred. Code and documentation are saved locally. The original feasibility report and original six-page result remain unchanged.

## Next decision

Use the [optional workflow](../../distributor-workflow.md) to gather and review a few relevant distributor leads. Do not scale broad distributor discovery yet. The next qualification changes need separate regression-backed work: source-local company-location context, company/brand/product relationship evidence and exact product-unit scope. Brand-confirmed authorization should be a separate evidence state, not inferred from a wholesale policy or directory listing.
