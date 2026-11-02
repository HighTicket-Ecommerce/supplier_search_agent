# Optional distributor research workflow

Use distributors as a small, review-led source of additional suppliers. New UI and API searches default to manufacturers and brand owners; distributor searches require an explicit role selection. Discovery queries follow those selected roles. Saved jobs and explicit role settings are preserved. The [live collection results](benchmarks/distributors-2026-10-28/collection-fix-results.md) show what works and what remains uncertain.

## Set up a small check

1. Choose **Find suppliers** under **Tool** in the sidebar and select only **Distributor** under **Supplier type**. This enables bounded collection of public wholesale/account-entry policy text; it does not log in or submit forms.
2. Enter a short product phrase in **Product types**, such as `Fire Magic outdoor gas grills`. Put `accessories, replacement parts, charcoal grills, electric grills` in **Exclude products** on the main form.
3. Under **More options**, supply one or two relevant official company/catalogue URLs. Start with candidates from a brand's distributor page or a distributor's own catalogue. Keep **Discover additional suppliers** off for this validation pass. Select a saved master reference in the sidebar if you want identity comparison; an unchecked or unmatched lead is not confirmed new.
4. The UI automatically allows **four pages per supplier** for a distributor-only search. The overall page, call and runtime bounds come from API defaults; adjust **Search budget ($)** when needed. The default UI budget is $5. The historical two-site benchmark used seven total pages, twelve calls, 600 seconds and a $4 exposure ceiling; reproduce those exact settings through the API or retained benchmark helper.
5. Leave **Allow Google Sheets export after review** off for a preview. Shopping and Shopify catalogue analysis stay off by default. Browser fallback can be requested through the API for a specialized check. The recorded actor cap is $0.50 per run; actual spend and conservative exposure are different figures.

The **Extract distributor brands** sidebar tool has a different purpose: it collects brand labels and optionally looks up official brand sites. A directory observation does not verify that the distributor is authorized to supply that brand or a particular model.

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

The recorded evaluation left the tested distributors in **review**. Its role guard does not yet combine separate wholesale and brand/product assertions, and Rutherford exposed a company-location context false rejection. Raw model fields or notes must not be treated as verified outcomes. Review rows are useful leads, not ready-to-export verified distributors.

When public evidence ends, record the missing question for manual confirmation. No outreach, applications or exports are sent automatically. Additional discovery and brand-side verification are later steps; their accuracy has not been measured by this two-site check.
