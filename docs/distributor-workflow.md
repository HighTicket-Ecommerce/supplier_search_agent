# Optional distributor research workflow

Use distributors as a small, review-led source of additional suppliers. New UI and API searches default to manufacturers and brand owners; distributor searches require an explicit role selection. Discovery queries follow those selected roles. Saved jobs and explicit role settings are preserved. The [live collection results](benchmarks/distributors-2026-10-28/collection-fix-results.md) show what works and what remains uncertain.

## Set up a small check

1. Choose **Research suppliers** and select only **Distributor** under Company roles. This enables bounded collection of public wholesale/account-entry policy text; it does not log in or submit forms.
2. Enter a short product phrase, such as `Fire Magic outdoor gas grills`. Put `accessories, replacement parts, charcoal grills, electric grills` in **Excluded products** under Research controls.
3. Supply one or two relevant official company/catalogue URLs. Start with candidates from a brand's distributor page or a distributor's own catalogue. Keep **Discover additional suppliers** off for this validation pass. Check against the saved master reference if you want identity comparison; an unchecked or unmatched lead is not confirmed new.
4. Allow **four pages per supplier**. For two sites, the tested settings were seven pages across the run, twelve service calls, 600 seconds and a $4 exposure ceiling. The first site can consume four pages, leaving three for the second; browser fallback uses those same page limits. For one site, four total pages is enough to reproduce the targeted Rutherford check.
5. Keep **Preview only** enabled, with Shopping and Shopify catalogue analysis off. Browser fallback is optional. The recorded actor cap is $0.50 per run; actual spend and conservative exposure are different figures.

The **Extract distributor brands** workflow has a different purpose: it collects brand labels and optionally looks up official brand sites. A directory observation does not verify that the distributor is authorized to supply that brand or a particular model.

## Review the evidence

Check the requested product/category, the wholesale-policy statement and company-location evidence independently. Preserve the source URLs and quotes. A headquarters/office claim must come from explicit company context; an address or delivery territory alone is insufficient.

Keep these questions separate:

| Question | Useful evidence |
| --- | --- |
| Does this company offer the brand/category? | Its own relevant catalogue/category or product page |
| Does it supply the wholesale/trade channel? | Explicit company wholesale policy |
| Is it a brand-appointed distributor for the target territory? | Brand-side distributor listing or a current explicit confirmation, with scope/date |
| Can it supply the exact requested model/configuration? | Matching product/model evidence; a brand logo or accessory list is insufficient |
| Will it accept our business and fulfil orders? | Confirmed reseller eligibility, MOQ, stock/lead time, dropshipping and commercial terms |

The current application still leaves the tested distributors in **review**. Its role guard does not yet combine separate wholesale and brand/product assertions, and Rutherford exposed a company-location context false rejection. Raw model fields or notes must not be treated as verified outcomes. Review rows are useful leads, not ready-to-export verified distributors.

When public evidence ends, record the missing question for manual confirmation. No outreach, applications or exports are sent automatically. Additional discovery and brand-side verification are later steps; their accuracy has not been measured by this two-site check.
