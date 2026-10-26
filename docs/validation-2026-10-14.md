# Matching and catalogue upgrade validation — 2026-10-14

The application now supports master-list comparison, distributor brand extraction, bounded Shopify product/variant analysis, observed currency-specific prices, sourced contacts and optional browser fallback. Preview and explicit export controls remain in place.

## Automated checks

48 unittest methods cover the original research controls and the new workflows. They use temporary SQLite databases/references, a network guard and provider mocks. Streamlit AppTest exercises supplier research, list comparison and directory extraction. Captured product and directory fixtures verify schema handling and filtering; mocked model decisions do not measure classification accuracy. Syntax, whitespace and real-credential scans passed.

## Live application checks

| Check | Observed result | Meaning |
| --- | --- | --- |
| Master import | 13,267 records from the user's CSV | Minimal local reference; original CSV unchanged |
| Identity comparison | Homecraft website match; SaunaSpace ambiguous; Harman stoves and Summit unmatched; Fire Magic name match | No automatic alias/parent merges or confirmed-new claims |
| Arizona Fireplaces | 37 brand labels through its public catalogue API | Its reported 1,708-product total was not scraped as 1,708 products |
| Rutherford | 120 labels through a bounded 2 GB RAG browser run | Direct access timed out; the initial 1 GB browser run timed out, prompting the memory fix |
| Combined directories | 157 observations, 148 distinct normalized labels | 45 exact normalized name matches need verification; 112 observations are unmatched, not confirmed new |
| Coldture Shopify sample | 20 usable products: 1 eligible, 2 uncertain bundles, 17 excluded for this product request | Accessories, assembly services and adjacent wellness products did not set complete-plunge prices |
| Observed price | CAD 12,999 for two available variants of one eligible product | This is a bounded sample, not the minimum of the full catalogue or market |
| Supplier qualification | Coldture remained in review for missing headquarters evidence | The master CSV's Canada field did not override the official-page evidence requirement |

Five Apify runs, including the initial timed-out browser attempt, reported $0.024875 total usage after billing verification. Five model calls had an estimated $0.03056725 cost from returned tokens at configured standard rates. Combined execution cost was approximately $0.05544, excluding account/storage fees. Every actor run had a $0.50 provider charge cap, and all runs were terminal at verification. Conservative reservations were higher than actual usage.

No development server was started, and no Google Sheets writes occurred. No repository development servers were running when inspected. The imported master is available through **Load saved master lists** once the app is started normally.

Full local run results, run/build/dataset IDs, source hashes and provider verification are saved under the task's `second-slice-smoke` artifact directory. Live previews used an isolated job database. Existing application jobs were not overwritten.

## Limits still present

Catalogue coverage is deliberately partial. Additional platform/directory adapters, evidence-backed alias and parent-company relationships, broader labelled accuracy evaluation and automatic job resumption remain future work. Browser fallback improves access but cannot guarantee it.
