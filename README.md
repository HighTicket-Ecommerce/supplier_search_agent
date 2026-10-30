# Supplier Research Agent

Streamlit + FastAPI supplier research with product-specific qualification and review before export.

Track completed work and the next evaluation steps in [plan.md](plan.md).

## Run locally

Install `requirements.txt` in a Python virtual environment. Copy `.env.example` to `.env`, fill the API credentials, and keep credentials out of Git.

```sh
uvicorn backend.main:app --host 127.0.0.1 --port 8000
streamlit run ui/streamlit_app.py
```

Set `SUPPLIER_API_KEY` to a long random value. The backend refuses every request except `/health` without it (401), or with 503 when it has no key configured. The UI reads the same variable and sends it automatically. On Railway, set the same value on both services. Set `SUPPLIER_UI_PASSWORD` to require a password before the Streamlit page loads; use a long one, since attempts are not rate-limited.

Use **one backend worker**. SQLite jobs live in ignored `var/research_jobs.sqlite`; override with `SUPPLIER_JOB_DB`. Restarting the backend marks unfinished jobs interrupted and preserves their partial results. It does not automatically resume or repeat billable work. Use the saved job ID to load results in the UI.

## Research workflow

1. Enter the requested product, exclusions and allowed supplier headquarters.
2. Optionally supply website URLs. Seeds are processed before discovery; disable additional discovery for a seed-only run.
3. Google Search discovers candidates in each selected country, one results page per query. Shopping is optional and off by default. Shopping titles, merchants and product URLs are hints, not verified brands or official supplier sites. When enabled, additional searches propose company sites and qualification requires identity evidence.
4. Fetch the supplied page and relevant same-site product/About/Contact links. Page selection uses real links; there is no broad recursive crawl. Static RAG fetching is the default. An optional bounded browser retry handles empty, thin or JavaScript-shell evidence; both attempts count toward the page limits.
5. The model receives the product, exclusions, allowed roles, headquarters countries and attributed excerpts. Strict output validation and literal source-quote checks separate qualified candidates, review-needed cases and exclusions. Missing product/country evidence and extraction failures do not silently count as accepted suppliers.
6. Every research job collects results without writing to Sheets. Preview-only is the default and prevents Sheets export. To export, disable preview before starting the job, review the qualified candidates and explicitly select rows to export. Repeated exports skip previously claimed records. Uncertain Google writes require manual reconciliation before retrying.

Qualified means the supplied evidence passed the research checks. It does not establish dealer-account availability, complete catalogue coverage or verified commercial terms. Model confidence alone never accepts a supplier. Dealer evidence is optional. Prices and margins are not guessed by the model; unverified Shopping price hints remain separate.

## Compare with your master list

In **Master supplier list**, import a UTF-8 CSV or load a previously imported reference, then select it under **Compare against**. Importing stores an immutable, minimal local reference in ignored `var/references/`; it never edits the source CSV. Name, website, product types, country and source row are retained. Private contact columns are not copied. Override the directory with `SUPPLIER_REFERENCE_DIR`.

The matcher distinguishes exact website-host matches, website matches with conflicting names, exact normalized names needing verification, ambiguity and unmatched records. It removes leading `www.` and normalizes spacing/punctuation in names; it does not merge company suffixes, similar names, alternate domains or parent/brand relationships. A content hash plus source row identifies a reference record, not a permanent business identity. Unmatched does **not** mean confirmed new. Master country data never substitutes for current headquarters evidence.

Choose **Compare supplier lists** for a deterministic comparison of up to 2,000 supplied rows, using a CSV or one name per line. It uses no actor/model calls and produces observations rather than qualified suppliers. CSV headers may be `Supplier`, `supplier_name`, `SUPPLIERS`, `name` or `brand`, plus optional `Website`/`url`. Master imports allow up to 50,000 rows and 15 MB.

## Distributor research

Choose **Extract distributor brands**, enter directory URLs and optionally select a master reference. Extraction preserves each label and its source before any official-site qualification. It deduplicates repeated links within a directory while retaining aliases as separate observations.

The current adapters handle static `/brandsupplier/`, `/brand/`, `/brands/` and manufacturer links, plus Arizona Fireplaces' public brand-facet API. Arizona's reported catalogue total is a source statistic; it is not a count of products extracted. Unsupported layouts and failed requests produce explicit warnings. With browser fallback enabled, a failed/empty HTML directory gets one capped RAG browser attempt. This can still fail on blocked or slow sites. The compute-priced Web Scraper actor is not enabled in the charge-capped runner.

**Find official sites and verify listed brands** adds bounded Google searches in the first selected country and verifies identity, requested product, company role and headquarters on candidate sites. Directory labels alone never enter the qualified group. Additional directory adapters and evidence-backed aliases/parent relationships remain future work.

## Shopify products and observed prices

Enable **Check Shopify product catalogue** to use the benchmarked [Trove Vault actor](https://apify.com/trovevault/shopify-products-scraper/input-schema). The app runs it only when Shopify markers appear in fetched evidence or the website is explicitly listed under **Known Shopify websites**. Each store receives a positive product cap (20 by default, at most 50), disabled inventory enrichment, a run timeout and a provider charge cap. The actor's internal catalogue pagination is bounded by product count/time/charge, not the app's website-page counter; one catalogue fetch counts as one evidence operation.

Product batches receive the actual request and exclusions. Strict product/variant IDs and literal quotes are checked before a classification can contribute evidence or prices. A complete cold-plunge system requires a tub with an included or integrated chiller. Accessories, separate chillers, installation services, unrelated categories and bundles with unclear contents stay separate. Classification applies to the requested item, so an explicitly requested accessory can itself be primary.

Price ranges use only selected eligible, available variants with explicit currencies, grouped by currency. Trove Vault prices are major decimal units; another actor's cents are not interpreted using this adapter. Unsupported/unknown currencies remain raw observations. No currency conversion, margin estimate or claim of cheapest market price is made. Every range includes product/variant IDs and source URLs and is labelled a bounded sample with incomplete catalogue coverage. Samples and completed classification batches persist even if a later limit stops the job. General contacts retain source URLs; year ranges are not accepted as phone numbers.

## Limits and cost accounting

All research stages share candidate, service-call, runtime and execution-budget limits. The service-call counter includes actor runs, model requests and direct public directory requests; Apify metadata/polling calls are internal to a bounded actor operation. The page limit counts evidence-page attempts, directory requests and catalogue fetch operations, including cache hits; search pages are separately bounded to one page per query. Shopping is bounded by result count, runtime and provider charge cap. A stop request is checked between bounded network calls; an active Apify run receives an abort request. An in-flight model request can finish before stop takes effect. Limits retain partial results.

The public Apify API supplies server-side timeouts and `maxTotalChargeUsd`, which the pinned SDK cannot set. Only actors with current pay-per-event pricing are enabled by this path. Current Google Search, Burbn Shopping and RAG actors were checked on 2026-10-14. Provider run/build/dataset IDs and reported charges are saved in job operations.

Execution budgeting is intentionally conservative: each actor's maximum charge stays reserved for the whole job because provider billing can lag. It is **not** presented as actual spend. Model input is bounded using request byte length and a completion-token cap; returned token usage settles the model reservation at uncached standard rates. Storage/account fees and manual Sheets exports are outside this execution budget. Provider-supported charge caps and their billing rules still apply.

The configured GPT-5.2 snapshot has standard input/output rates supplied in config, verified on 2026-10-14. Other models require explicit `OPENAI_INPUT_USD_PER_MILLION` and `OPENAI_OUTPUT_USD_PER_MILLION` settings; model requests stay in review if pricing is missing. Keep these rates current. See [OpenAI pricing](https://developers.openai.com/api/docs/models/gpt-5.2) and [Apify run options](https://docs.apify.com/api/v2/actors-runs-post).

## API

Every endpoint except `/health` requires the `X-API-Key` header. The key is checked before routing or reading the request body; `/docs` and `/openapi.json` are covered too.

- `GET /health`: credential-presence flags, never credential values.
- `POST /research/start`: validated request; returns a queued job ID.
- `GET /research/status/{job_id}`: progress, counts and limits.
- `GET /research/result/{job_id}`: saved qualified/review/excluded results, sources and run operations.
- `POST /research/stop/{job_id}`: request stop, including queued jobs.
- `POST /research/export/{job_id}` with `selected_urls`: explicitly export selected qualified rows from a non-preview job after it stops.
- `POST /references/master` with `filename` and `csv_content`: import a minimal master reference; returns its content ID and row count.
- `GET /references/master`: list saved references without supplier/contact contents.

New request options include `research_mode` (`supplier_search`, `distributor_brands`, `list_compare`), `master_reference_id`, `comparison_rows`, `directory_urls`, `verify_directory_brands`, `max_directory_entries`, `use_shopify_catalogue`, `shopify_catalogue_urls`, `max_catalogue_products` and `allow_browser_fallback`. Result payloads include `master_match` per candidate/observation, `directory_coverage`, saved `catalogues` and warnings. Comparison rows are objects with `supplier_name` and optional `url`. Distributor mode requires directory URLs; comparison mode requires an imported master and comparison rows. Extraction and list comparison do not run generic supplier discovery.

Example seed-only preview:

```json
{
  "product": "Sauna heaters",
  "candidate_urls": ["https://homecraftsaunas.com/"],
  "use_apify": false,
  "preview_only": true,
  "allowed_countries": ["Canada", "United States"],
  "target_suppliers": 1,
  "max_candidate_domains": 3,
  "max_pages": 3,
  "max_execution_cost_usd": 2
}
```

`use_apify` is retained as the discovery switch for compatibility. It disables search/Shopping discovery, while seeded-site fetching still uses Apify. Invalid or zero limits are rejected. Legacy unbounded paid diagnostic GET endpoints were removed; use a bounded research preview instead.

For Sheets export, configure the existing Google service-account credentials and share the destination sheet with that account. Preview research does not require Google credentials. Existing sheet columns remain compatible; full evidence stays in the API result and downloadable CSV. Sheets rows are written as raw values. CSV downloads prefix text cells starting with `=`, `+`, `-`, `@`, tab or carriage return with an apostrophe, so spreadsheets show them as text instead of running them as formulas.

## Tests

```sh
python -m unittest discover -s tests -v
```

GitHub Actions runs the same suite plus `pip-audit` on every push to `main` and every pull request. The workflow has read-only permissions and pins Actions to commit hashes.

Tests use temporary SQLite databases/references, mocked actor/model/Sheets calls and a network guard. They cover captured Shopping/Shopify/directory schemas, real supplier-page pilot fixtures, master identity traps, product/variant/currency checks, malformed output, citations, market targeting, shared limits, partial catalogue durability, stop/abort behavior, explicit exports, API-key and UI-password checks, spreadsheet-safe CSV values and all three Streamlit workflows. Fixture model responses are mocked, not a live accuracy estimate.

## Remaining work

Evidence-backed aliases/parent-company verification, additional catalogue/directory adapters, complete catalogue coverage and automatic job resumption remain future work. The current browser fallback is one bounded retry, not a guarantee of access. Existing experimental benchmark reports are separate from application tests.
