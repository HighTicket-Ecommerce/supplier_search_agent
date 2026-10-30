# Distributor feasibility preview — 2026-10-28

This exploratory development sample tests the existing application, without changing production code. It is not a distributor-discovery benchmark or a release accuracy score.

Requested product: **Fire Magic outdoor gas grills**, excluding replacement parts, accessories, charcoal grills and electric grills. Permitted company role: Distributor. Company-location policy accepts US/Canadian headquarters, offices or an explicit company base. A geographic address by itself is not HQ proof.

Two supplied official sites are checked in one isolated preview. Limits: six page attempts total, three per site (including conditional browser fallback), twelve external calls, 600 seconds, $4 conservative execution exposure and $0.50 per actor. Discovery, Shopping, Shopify catalogue analysis and exports are disabled. Seeds are always checked even if already in the master reference.

Pre-run source review supports keeping both as relevant leads. Rutherford's public account page explicitly describes a wholesale distributor; its brand catalogue lists Fire Magic. Gas Equipment Distributors presents Fire Magic in its grill range and explicitly restricts sales to wholesale trade. Neither observation alone establishes brand authorization, current inventory, a particular gas-grill SKU, territory, reseller approval, dropshipping or commercial terms. Those remain separate questions.

Source URLs and observations are frozen in `cases.json` before the application preview. A named brand catalogue is weaker than a matching product page. A historical partnership announcement is dated evidence, not automatic proof of a current exclusive territory. Missing brand-side confirmation remains unknown, rather than becoming a negative supplier label.

The application currently has company-role and product-match fields but no company–brand–product relationship record. This preview measures that limitation; it must not describe an ordinary `qualified` result as a brand-confirmed distributorship. A previously saved Penguin/Beyond Cold case is also inspected offline as a manufacturing-versus-selling control, without another provider run.

Run from the repository root with a fresh round name:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/benchmarks/distributors-2026-10-28/run_preview.py --round distributor-1
```

The runner claims its output directory before any provider call, saves source hashes, request settings, model analyses, fetch attempts and pages, and uses its own SQLite database under ignored `var/eval/`. Existing rounds are never repeated automatically.
