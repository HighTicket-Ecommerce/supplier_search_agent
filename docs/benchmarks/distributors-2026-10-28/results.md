# Distributor feasibility results — 2026-10-28

**Finding distributors is feasible; reliable automatic verification needs a separate relationship check.** Two bounded live application checks produced two review results and no qualifications or exclusions. Useful evidence exists, but collection and the company-role guard both missed parts of it. Production code is unchanged.

## What was tested

The [brief](brief.md) and [cases](cases.json) were saved before the run on local commit `0b64f7c`. The requested product was Fire Magic outdoor gas grills. Only Distributor was permitted, with US/Canadian headquarters, office or company-base evidence required. This was a two-site exploratory development sample, supplied as seeds, not a search/discovery accuracy benchmark.

Job `distributor-94d40d502f48` completed in 47.25 seconds with six raw page fetches and two model calls. All six actor runs were terminal and successful when checked through Apify's read-only run API. Conditional browser fallback was enabled but never triggered.

| Site / relationship | Existing application outcome | Inspected evidence and remaining gaps |
| --- | --- | --- |
| Rutherford Equipment → Fire Magic | Review: `supplier_role_not_established`; raw model role Unknown; product not established | The brand catalogue is a genuine lead, but collection visited Contact and a Grill Parts and Accessories facet. The About and public account-policy pages were not collected. A gas-grill category link was present but not selected. Brand authorization and exact gas-grill SKU verification remain unknown. |
| Gas Equipment Distributors → Fire Magic | Review: `supplier_role_not_established`; raw model Distributor and primary product supported | Saved homepage explicitly offers Fire Magic grills in natural/propane gas and has a wholesale-trade-only policy. The model's role quotes and source-only recovery did not satisfy the existing single-passage role guard. HQ/office evidence is also missing; the address must remain a location lead. Exact SKU and brand-side authorization remain unknown. |

The collector also selected Fireplaces and Outdoor Products on the second site, leaving its Gas & Primo Grills page unvisited. All returned pages were usable; these failures do not justify changing scraping actors yet.

Seven retained model evidence quotes were checked against their captured sources and the twelve-word limit. All six page-text hashes matched. Quote verification establishes that the text exists, not that every retained claim proves eligibility. In particular, Rutherford's accessory quotes do not establish a complete gas grill, and its product status remained `not_established`.

## Test-design limitation and offline diagnosis

The test product phrase included “excluding accessories, replacement parts, charcoal grills and electric grills,” in addition to the structured exclusions field. The current keyword ranker treats those exclusion words as positive search terms. That biased the test toward accessories.

Re-ranking the saved Rutherford links with the clean product phrase `Fire Magic outdoor gas grills` moves Gas Grills ahead of accessories, without changing backend code or making provider calls. Gas, charcoal and electric facets still tie in the primary rank; a remaining tie-break happens to favor the gas URL. This is not robust product-type discrimination. On Gas Equipment Distributors, Fireplaces, Outdoor Products and Gas & Primo Grills still tie. A clean brief alone does not solve page selection.

These findings support a collection fix and a better brief format. They do not measure distributor recall or establish that either company is unsuitable.

## Public source review, separate from the application run

- [Rutherford's public account page](https://www.rutherfordequipment.com/account/login) describes wholesale-only distribution and no general-public sales. Its [About page](https://www.rutherfordequipment.com/static/about-us) explicitly places headquarters in Covington, Georgia. These were found in source review, not collected in the six-page preview, and were not silently added to its decision.
- [Rutherford's Fire Magic catalogue](https://www.rutherfordequipment.com/brandsupplier/fire-magic) lists the brand and a gas-grill category, alongside many parts/accessories. This supports a brand-catalogue observation; it does not itself prove authorization, inventory or commercial access.
- [Gas Equipment Distributors](https://gasequipmentdistributors.com/) presents the brand within its grill range and limits sales to wholesale trade. Its live saved page gives stronger gas-grill evidence than the older search-index excerpt, which illustrates why live captures matter. No brand-side Fire Magic confirmation was established in this bounded investigation.
- An official [Ortal announcement](https://www.linkedin.com/posts/ortal-usa_ortal-and-rutherford-equipment-announce-activity-7103401642003202048-9V2Z) describes a Rutherford distribution partnership effective September 2023. Its search-index excerpt was available; opening the post failed. Treat it as a dated lead for a different brand, not a freshly verified current agreement or evidence for Fire Magic.

## Existing product/brand control: Penguin → Beyond Cold Summit

Offline inspection of `office-country-1` preserves its earlier qualified Manufacturer outcome as historical data. The role evidence establishes Penguin manufacturing **chillers**; the product evidence establishes a complete Summit cold plunge sold on its site. The model's own notes leave ownership of Beyond Cold unknown. The [current product page](https://penguinchillers.com/products/summit-cold-plunge) also presents the two names together, but co-branding alone does not establish ownership or who makes the entire system.

The missing inference is specific: company-level chiller manufacturing must not automatically label Penguin the manufacturer of every complete plunge it sells. Keep the useful product lead, while leaving its role for that full product unverified. No new Penguin provider call or decision rewrite occurred.

## Proposed workflow and implementation order

1. **Collect the right evidence first.** Keep a short positive product/category field and separate brand, exclusions and target territory. Prioritize matching complete-product/category links over parts, unrelated categories and account utilities. Add bounded collection of public wholesale/account-policy and About pages when role or location evidence is missing. Do not log in, submit applications or follow generic account pages indiscriminately.
2. **Store a relationship, not only a company label.** Record company, brand, product family/model, relationship type, source side, evidence URL/quote, territory, source date and last check. Separate `lists_brand`, `offers_product`, `wholesale_supplier`, `brand_confirmed_distributor`, `brand_owner` and `manufacturer_of_product`. A company can hold different roles for different brands/products.
3. **Verify each assertion independently.** An explicit wholesale policy can establish the business channel; a named brand/product page can establish what that same company offers. Preserve the distinct source quotes and identity link between them. Do not splice text into an invented assertion or demand that every fact appear in one sentence. Brand authorization requires brand-side confirmation or an explicit dated confirmation; a retail dealer locator must not be upgraded to wholesale-distributor evidence.
4. **Search from brands as well as product categories.** Start with relevant brands, inspect their distributor/where-to-buy/territory pages, then check the candidate's catalogue and compare its identity with the master reference. Also use verified distributor catalogues to discover more brands. Search results and directories create leads; official evidence upgrades each relationship.
5. **Keep unresolved leads useful.** Show supplier-reported, brand-confirmed, conflicting and unknown relationship evidence separately. Track location eligibility independently. If public evidence stops short, prepare a short verification checklist for the user: current brand appointment, territory, reseller eligibility, MOQ, dropshipping and stock/lead times. Do not claim these terms or send outreach automatically.

The immediate next change should be **brief-aware page selection and targeted policy collection**, tested against these saved traces before another paid preview. After that, add the relationship schema/check and use Penguin as an ambiguity control. Preserve these exploratory cases as development data and add independent cases before making any accuracy claim.

## Cost, artifacts and validation

Apify reported **$0.012750** usage for six runs. The two model calls cost an estimated **$0.02989875** from returned tokens at configured rates. Combined execution was approximately **$0.04265**; conservative job exposure was $3.029899 against the $4 cap. Account/storage fees are excluded.

Private run records are under `var/eval/distributors-2026-10-28/distributor-1/`: manifest with request/source hashes, isolated jobs SQLite, result, model analyses, captured pages, fetch attempts, source audit and provider verification. No master reference was applied in this preview, so neither lead was classified as new or existing.

The existing **143 tests passed**. No production/backend changes, development servers, source-list edits, Sheets writes, pull requests or deployment occurred. The repository additions are this test specification/runner, report and plan update.
