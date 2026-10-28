# Bounded fetch fallback — 2026-10-28

**Browser fallback returned usable homepages in both controlled timeout probes.** In the ordinary live previews, raw fetching worked for both sites, so the browser correctly stayed idle. Redwood qualified; Morozko remains in role review. Fetch success does not establish supplier eligibility.

Validation commit: `a4cf388ec61daf3c2db2002dbee7f6267b4dda7a`, branch `fix/bounded-fetch-fallback`, based on `96a74d5`. Production backend files are byte-for-byte unchanged. The changes add the development runner's `--browser-fallback` option, durable attempt traces and six regression tests. Application fallback remains opt-in, and qualification requirements are unchanged.

## Preparation and offline checks

Read-only inspection of the earlier actor datasets identified these page failures inside successful, terminal actor runs:

- Morozko, run `fUt6hnKtSwNCss0f8`: HTTP 500, response-stream decoding timeout, failed crawl.
- Redwood, run `RrHj0sxgAIWF6I8fI`: HTTP 500, request timed out after 30 seconds, failed crawl.

The existing fetcher rejects those page responses and, when enabled, can try `browser-playwright` once after an empty/thin raw response. [Apify's input schema](https://apify.com/apify/rag-web-browser/input-schema) confirms both scraping modes and their request/retry settings. Each browser attempt uses the existing shared limits, a 40-second page timeout, 60-second actor timeout and 2048 MB memory. Actor page retries remain zero.

All **143 tests pass**. Six new tests cover the saved HTTP-500 timeout shape followed by a successful browser fetch, healthy raw pages avoiding browser calls, two empty attempts producing retry-needed without a model call, global page limits, external-call limits without retry loops, and rejection of an evaluation configuration with no room for fallback. Earlier per-supplier and navigation-only browser tests remain intact.

## Ordinary live previews

| Supplier | Fetch result | Supplier result |
| --- | --- | --- |
| Morozko | Four raw pages returned; no browser call | **Review: `supplier_role_not_established`**. Model proposed Manufacturer, but the guard did not accept the historical-purpose and passive manufacturing quotes. This needs manual role adjudication; it is not an exclusion |
| Redwood | Four raw pages returned; no browser call | **Qualified**, Brand owner, with complete-system and verified US office evidence |

Morozko's pages now reach the homepage, team, ice-bath product and FAQ. Its raw model country/base fields are not verified on the early role-review path. Founding in Phoenix alone must not become current office/HQ proof. The qualification hold was retained rather than relaxed to make the fetch trial look successful.

All **nine retained model-result quotes** matched their captured sources under the existing URL-alias and Unicode/whitespace rules. No natural raw-fetch failure occurred in these two previews, so they alone do not demonstrate live fallback recovery.

## Controlled fallback probes

To exercise the actual fallback path, each probe supplied the site's exact saved raw-timeout dataset response to the normal parser, then allowed **one fresh browser request**. The raw leg was replayed, not fetched or billed again. Both legs counted toward the two-attempt page budget. The probes performed no model analysis, supplier classification or export.

| Homepage | Healthy raw sample | Fresh browser after replayed timeout | Browser main-text characters |
| --- | --- | --- | --- |
| Morozko | 6.432 s; 2,062 main-text characters | **Recovered**, 24.250 s | 2,085 |
| Redwood | 6.465 s; 19,175 main-text characters | **Recovered**, 30.632 s | 26,418 |

These are two separate captures per homepage, not a general performance benchmark. Morozko's content size was similar; Redwood's browser capture was larger. More text does not establish better qualification accuracy, and browser-only probe pages were not used to reclassify either supplier. The observations support keeping raw-first fetching and enabling conditional browser fallback where needed.

## Execution and cost

| Round | Job | Mode | Elapsed |
| --- | --- | --- | --- |
| `fallback-morozko-1` | `evidence-b064cc62670d` | Normal live supplier preview | 35.21 s |
| `fallback-redwood-1` | `evidence-b4b405f4d2e9` | Normal live supplier preview | 33.21 s |
| `fallback-probe-morozko-1` | `fetch-probe-1dc373b2ad70` | Saved raw timeout + fresh browser | 24.28 s |
| `fallback-probe-redwood-1` | `fetch-probe-8652195dbff1` | Saved raw timeout + fresh browser | 30.66 s |

Each ordinary preview retained four page attempts, twenty external calls, 600 seconds, a $3 exposure ceiling and $0.50 actor caps. Each controlled probe retained two counted page attempts, one paid external call, 90 seconds and a $0.75 exposure ceiling; its replayed raw leg had no new actor charge. All jobs were preview-only, without discovery, Shopping, catalogue analysis or exports.

New execution used **ten actor runs and two model calls**: eight fresh raw fetches and two fresh browser fetches. Twelve logical page attempts include the two replayed raw failures; they are not twelve new paid fetches. Read-only provider verification found every actor terminal, no missing usage values and no reached limits.

- Eight raw actor runs: **$0.017000 reported**.
- Two browser actor runs: **$0.004700 reported**, $0.002350 each.
- Model usage: **$0.037135 estimated at configured rates**.
- Combined new execution: **$0.058835**, approximately **$0.059**, excluding account/storage fees and original historical runs.
- Reservations: $2.017502 and $2.019633 for previews; $0.50 per probe. Reservations are not spend.

No final-check cases, source-list edits, dev servers, pushes, pull requests or deployment.

## Records and next work

Ignored records are under `var/eval/cold-plunge-2026-10-27/evidence-collection/`: `fallback-tests.log`, `fallback-inspection/` containing original failure records, `fallback-source-audit.json`, `fallback-provider-verification.json`, `fallback-final-validation.json`, and the four round folders with manifests, isolated jobs, fetch traces, captures and results. Probe folders also retain the helper source and its hash, the historical response hash and an explicit `saved_raw_failure_then_live_browser_fetch` mode. Application/runner source hashes match the validation commit.

This validates empty/thin page fallback for the tested response shape. It does not guarantee recovery from every actor/API exception or outage; those still use existing retry-needed/stop/limit handling. Fallback remains conditional and opt-in, with both attempts consuming the research page budget.

Next, adjudicate Morozko's captured role evidence and test live distributor/product-brand relationships. Discovery/catalogue evaluation and fresh independent final cases remain pending. Preserve the original failures and frozen labels; the successful raw captures do not prove those earlier failures were permanent or caused by application code.
