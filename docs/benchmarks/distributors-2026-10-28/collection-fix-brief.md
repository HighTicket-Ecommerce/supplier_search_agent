# Distributor collection follow-up — 2026-10-28

The [original feasibility results](results.md) remain unchanged. This follow-up uses the same two supplied companies, Fire Magic gas-grill product phrase, structured exclusions and Distributor-only role policy. It tests collection improvements, not automatic brand authorization.

Changes under test:

- Exclusion tails in the product phrase do not create positive navigation terms. Structured exclusions demote matching category/accessory links, while potentially relevant dual-purpose product pages remain available for product analysis.
- Whole-word product matching and decoded category facets prioritize gas grills over fireplaces, unrelated products and accessory facets.
- Distributor-only checks prioritize About for company context and can collect one public trade/account-entry page for policy evidence. Generic account actions remain excluded. No authentication, form submission or registration occurs.
- Literal wholesale-policy passages are included in the model's evidence windows. Qualification and company/brand relationship rules are unchanged.

Before live execution, the twelve new regressions and existing suite must pass. A network-blocked comparison of eighteen saved navigation traces (sixteen cold-plunge development/anchor sites plus these two distributors) must show the two expected distributor route changes; missing saved pages are recorded, not invented.

Live limits: **seven page attempts total, four per company, twelve external calls, 600 seconds, $4 conservative exposure and $0.50 per actor**. First-site consumption can leave only three attempts for the second site. Browser fallback counts against these same limits. These differ from the original six-page/three-per-company preview so it can collect company, product and policy evidence. Report the cap change explicitly; any outcome difference is not attributable to ranking alone.

Discovery, Shopping, Shopify catalogue analysis and exports remain disabled. Use an isolated job database and a fresh round name. Record raw model responses, actual routes, quotes/hashes and terminal actor status/charges. A review result can still demonstrate better evidence collection; do not claim distributor qualification or authorization when a separate gate remains unresolved.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/benchmarks/distributors-2026-10-28/run_preview.py --round collection-fix-1 --pages-per-site 4 --max-pages 7
```
