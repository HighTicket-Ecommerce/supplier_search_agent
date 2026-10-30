# Greptile repair round — 2026-10-30

All 32 initial inline findings across the 18-PR stack have corresponding repairs and offline regression coverage. All eighteen rebased tracked snapshots pass independently; the final application snapshot passes **229 tests**, up from 194. Automated review of the updated remote heads is a separate result and must be checked before merging.

No paid Apify/OpenAI supplier runs, source-list changes, Sheets writes, dev servers, merges or deployments were used for this repair round. Original labels, historical captures and reports remain intact. The fallback report adds reproduction instructions without replacing its historical measurements.

| PR | Repair | Regression coverage |
| --- | --- | --- |
| [#1](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/1) | Connect public reads to the checked IP with original-host TLS; use the priced model snapshot; preserve supporting pages on ordinary failure; append country Shopping batches; allow a different identity hint with job-local page reuse and the shared check cap. | [test_review_foundation.py](../tests/test_review_foundation.py) |
| [#3](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/3) | Freeze both complete outbound schemas reconstructed from the pre-upgrade source with Pydantic 2.8.2. | [test_schema_compatibility.py](../tests/test_schema_compatibility.py) |
| [#4](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/4) | Preserve Unicode letters in legal-suffix matching; include skips in completed progress; require an explicit validated benchmark master-reference ID. | [test_review_master.py](../tests/test_review_master.py) |
| [#6](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/6) | Retain table/definition-list word boundaries, contracted location negation, explicit co-located company HQ, and spelled-out self-location regions. | [test_review_location.py](../tests/test_review_location.py) |
| [#7](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/7) | Remove negative brief terms from navigation ranking and preserve explicit tub/chiller bundles that list extras. | [test_review_product_routes.py](../tests/test_review_product_routes.py) |
| [#8](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/8) | Inspect the location subject after a clipped quote and bind positive location checks to the relevant sentence. | [test_review_location.py](../tests/test_review_location.py) |
| [#9](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/9) | Reject catalogue inventory as a supplied configuration and inspect negative/optional inclusion headings. | [test_review_configuration.py](../tests/test_review_configuration.py) |
| [#10](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/10) | Require direct company attribution for manufacturer labels; scope future-role wording; use requested physical-product terms while preserving service/figurative exclusions. | [test_review_roles.py](../tests/test_review_roles.py) |
| [#11](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/11) | Resolve a full bound address before selecting a short quote; retain unknown split HQ cards; keep current HQ separate from a future-office sentence. | [test_review_country.py](../tests/test_review_country.py) |
| [#12](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/12) | Commit the bounded raw-timeout/browser probe and sanitized response-shape fixture, with offline success/failure/limit/reused-round tests. | [test_review_probe.py](../tests/test_review_probe.py) |
| [#13](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/13) | Record an explicit whitelist of effective model settings in preview manifests without credentials. | [test_review_manifest.py](../tests/test_review_manifest.py) |
| [#14](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/14) | Keep distinct public trade-policy candidates until policy text is collected; restrict only duplicate account-entry attempts. | [test_review_trade.py](../tests/test_review_trade.py) |
| [#16](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/16) | Check the primary grammatical product object through adjectives and purpose clauses; share self-attributed manufacturer-label grammar. | [test_review_product_role.py](../tests/test_review_product_role.py) |
| [#17](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/17) | Capture raw website actor inputs/items/errors before parsing; retain rejected HTTP-500 results; keep original SERP audit compatibility and record model settings. | [test_review_raw_capture.py](../tests/test_review_raw_capture.py) |
| [#18](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/18) | Recover checking/pending ledger rows on startup without changing completed states; preserve different-hint identity retries through discovery prefilters. | [test_review_restart.py](../tests/test_review_restart.py); [test_review_foundation.py](../tests/test_review_foundation.py) |

## Verification and limits

Each topic branch was extracted from tracked Git files into its own source directory and tested with the current local virtual environment. Counts and exact application snapshots are in the [stack index](pull-request-stack-2026-10-30.md). Private preparation records, logs, original remote heads and rebase backups remain local under ignored `var/` or local Git refs. No private data appears in any published tree.

The pre-upgrade schemas were reconstructed during review from source `a7ba0572fd463ec82f38bc2a46b57fc602e50148` using the original Pydantic 2.8.2 pin in an isolated directory. This is not a claim that provider requests were captured before upgrading. The later intentional addition of `office` and `company_base` in PR #11 is an explicit, limited expectation in the compatibility test.

The unconfigured default uses the already supported `gpt-5.2-2025-12-11` snapshot. Its existing pricing matches the [official model page](https://developers.openai.com/api/docs/models/gpt-5.2). Pinned-IP HTTPS transport follows [urllib3’s documented custom SNI/Host pattern](https://urllib3.readthedocs.io/en/stable/advanced-usage.html#custom-sni-hostname), retaining original-host certificate verification.

The upgraded requirements are unchanged by this round; the clean pip-audit result from 2026-10-30 still applies. The compatibility tests verify schema construction and SDK serialization offline; they do not claim a new live model compatibility trial. The offline regressions address the reported cases, without establishing population-wide supplier precision or broader category/brand authorization coverage.

## Original findings

| PR | Greptile finding |
| --- | --- |
| #1 | [Directory requests reach private services](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/1#discussion_r4422651514) |
| #1 | [Default model cannot analyze suppliers](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/1#discussion_r4422651527) |
| #1 | [One page failure loses evidence](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/1#discussion_r4422651531) |
| #1 | [Earlier Shopping hints disappear](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/1#discussion_r4422651542) |
| #1 | [Wrong hints block real brands](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/1#discussion_r4422651550) |
| #3 | [Schema changes escape tests](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/3#discussion_r4422635730) |
| #4 | [Different names lose conflict warnings](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/4#discussion_r4422641732) |
| #4 | [Finished searches show incomplete progress](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/4#discussion_r4422641746) |
| #4 | [Benchmark silently changes master lists](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/4#discussion_r4422641757) |
| #6 | [Table text loses word boundaries](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/6#discussion_r4422640365) |
| #6 | [Denied locations pass country checks](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/6#discussion_r4422640372) |
| #6 | [Shared headquarters gets rejected](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/6#discussion_r4422640382) |
| #6 | [Full region names get rejected](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/6#discussion_r4422640393) |
| #7 | [Excluded filters still get priority](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/7#discussion_r4422639607) |
| #7 | [Complete bundles lose priority](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/7#discussion_r4422639615) |
| #8 | [Factory locations pass as headquarters](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/8#discussion_r4422639215) |
| #8 | [Shipping text overrides headquarters proof](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/8#discussion_r4422639223) |
| #9 | [Separate products qualify together](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/9#discussion_r4422637334) |
| #9 | [Excluded components count as included](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/9#discussion_r4422637341) |
| #10 | [Resellers pass as manufacturers](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/10#discussion_r4422644887) |
| #10 | [Valid role statements fail](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/10#discussion_r4422644895) |
| #10 | [Other product searches lose suppliers](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/10#discussion_r4422644903) |
| #11 | [Clear addresses appear to conflict](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/11#discussion_r4422654803) |
| #11 | [Office bypasses unresolved headquarters](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/11#discussion_r4422654812) |
| #11 | [Future office hides current headquarters](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/11#discussion_r4422654824) |
| #12 | [Timeout probes cannot be repeated](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/12#discussion_r4422637259) |
| #13 | [Saved model settings are incomplete](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/13#discussion_r4422639054) |
| #14 | [Wholesale policy gets skipped](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/14#discussion_r4422646349) |
| #16 | [Component makers still qualify](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/16#discussion_r4422648673) |
| #16 | [Clear manufacturer claims get rejected](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/16#discussion_r4422648684) |
| #17 | [Raw website results are lost](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/17#discussion_r4422643892) |
| #18 | [Checks stay active after restart](https://github.com/HighTicket-Ecommerce/supplier_search_agent/pull/18#discussion_r4422649439) |
