# Requested-product role verification — 2026-10-28

**Penguin now stays in review for a complete cold-plunge request, while Coldture remains qualified.** The fix prevents a company's component-manufacturing claim from automatically establishing its role for a whole product it sells.

Local application: `35a9304`, branch `fix/requested-product-role`, based on `01065cd`. The [follow-up brief](product-role-brief.md) was saved before live execution. This is a targeted development check, not a new discovery, full-cohort accuracy or release evaluation.

## What changed

Company role, product/configuration evidence and role for the requested category are separate checks. For **complete cold-plunge/ice-bath systems requiring a tub and chiller**, Manufacturer/Brand owner qualification now needs an explicit company-attributed production or own-product creation statement naming the primary cold-plunge/ice-bath category.

Chiller/filter/accessory work, components used in plunges, selling another product, another company's production and adjacent catalogue cards do not establish that link. Contract design for other brands does not become own-brand work merely because the company also owns a brand. Truncated role contexts cannot provide positive scope evidence. Identical repeated source passages are deduplicated.

Results preserve the factual company role and product match. The additive `product_role_verification` field records scope, supporting/rejected observations and source-only repair. `requested_product_supplier_type` stays Unknown when linkage is missing; the row becomes `review / requested_product_role_not_established`, rather than being excluded or automatically reclassified as a distributor.

A bounded recovery can add one literal, at-most-twelve-word role quote from already captured pages, scanning at most 96 candidate windows per page. It uses the same attribution/negation checks and makes no provider/model call. Explicit physical-product “makes” statements can support the existing own-creation definition of Brand owner; they do not by themselves establish manufacturing. Ice-bath vocabulary is recognized alongside cold plunges. The model prompt also asks for the narrower role evidence while retaining supported company-level facts.

**Scope limit:** this first guard checks the requested product category, not ownership/manufacture of every named SKU. Other categories and Distributor relationships explicitly report `not_required` for this guard and retain their existing checks. It does not resolve named-model/brand aliases, legal ownership, supplier authorization or the Rutherford HQ-context issue.

## Offline validation

**173 tests passed**, including fifteen new regression methods. They cover the literal Penguin capture, affirmative primary production/creation, component/purpose and other-company leakage, multiple predicates, contract design, negation/history/testimonials, paragraph boundaries, truncated/repeated contexts, recovery bounds and scope limits.

Existing component tests now use an explicit category-role statement so their synthetic setup isolates component inclusion. The old thin Coldture fixture retains its historical `expected` field and adds a current-policy review expectation: generic brand engineering and a catalogue vendor field do not establish own creation of the requested category. Its captured source text and the frozen benchmark labels remain unchanged. Stronger, later Coldture captures continue to qualify.

A network-blocked before/after replay against `01065cd` inspected **48 saved development/anchor observations: 44 reconstructed analyses and four collection failures without analyses**. Only five historical Penguin qualifications become review. Fifteen qualified observations across the Coldture, Redwood and Sun Home websites are preserved; repeated observations and Coldture name variants are not new suppliers. No new exclusions occur. One Renu review changes its reason from missing headquarters to missing requested-product role.

All **215 retained quote observations** in replay matched captured sources and the twelve-word limit. Replay reconstructed `is_product_company=True`, `owns_brand=None` and original analysis fields from saved results/diagnostics, omitting contacts. It makes no new model judgments and does not re-test navigation or measure independent accuracy. Final-check cases were excluded. The four collection failures remain recorded rather than becoming negative supplier labels.

## Live confirmation

Job `evidence-ccc3fe1a4091`, round `product-role-1`, completed in **58.73 seconds** on unchanged `35a9304`.

| Case | Company-level fact | Requested-product result |
| --- | --- | --- |
| Penguin Chillers | Manufacturer role supported for chillers; captured pages also support a complete Summit tub/chiller configuration | **Review.** Manufacturer role for the complete plunge category remains Unknown. Existing company/product facts are preserved; selling the complete system does not bridge the gap. |
| Coldture Wellness | Brand owner, complete tub/chiller bundle and Canadian headquarters supported | **Qualified.** Explicit Coldture creation of cold plunges supports the requested-category role. The model supplied this narrower role quote directly; no scoped source repair was needed. |

Penguin's raw model still proposed Manufacturer at company level. The deterministic guard correctly held the row for missing product-role linkage. Its retained office quote is still a labelled-office observation; the later country resolver was not reached after the new role hold, so the raw country fields are not a separate new location-verification result.

The preview used the current **Manufacturer/Brand owner** policy through `--primary-roles-only`; this does not rewrite the frozen benchmark's broader allowed-role list. Both cases were supplied seeds. Limits: three page attempts per company, six total, twenty external calls, 600 seconds, $4 conservative exposure and $0.50 per actor. Discovery, Shopping, catalogue analysis, browser fallback and exports were disabled. All six pages returned through raw HTTP.

Eleven retained live quotes and all six page hashes matched captured sources. Every manifest implementation hash matched the recorded Git commit, and the backend remained unchanged through final audit. An offline Streamlit check rendered the actual API result and confirmed that Penguin's company Manufacturer and requested-product Unknown remain distinct in the review table.

## Cost and records

Six Apify runs reported **$0.012750** usage. Two model calls cost an estimated **$0.040152** from returned tokens at configured rates. Combined execution was approximately **$0.052902**; conservative exposure was $3.040152 against the $4 cap. Account/storage fees are excluded. All six actors were terminal and successful when checked through the read-only run API.

Ignored artifacts are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `product-role-offline/` holds before/after records, source hashes, replay helper and quote audit; `product-role-1/` holds manifest/settings, isolated jobs, raw model analyses, captured pages, fetch attempts, result and provider/source validation. Source hashes, run/build/dataset provenance and response IDs are preserved. No master reference was applied to this pair, so no new/existing supplier claim is made.

No development servers, source-list edits, Sheets writes, pushes, pull requests or deployment occurred. Historical reports and frozen labels remain intact. The next useful validation is a small manufacturer/brand-owner discovery run without supplied websites, followed by manual product/role/location and master-list review. Broader relationship coverage and independent final cases remain required before an overall accuracy claim.
