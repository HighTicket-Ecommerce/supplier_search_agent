# Supplier research follow-up repairs — 2026-10-30

Local implementation and offline verification of the supplied follow-up audit. **35 items fixed, two coverage gaps addressed, one partially fixed policy conflict (P2-4).** Nothing was pushed, merged, deployed, posted to GitHub or checked against live supplier/provider services. No development server was started.

## Results and limits

- All 18 branch heads passed their full offline suites in order; the final application passed **274 tests**, versus **229** at the original final head. There are **45 additional test methods**, with table-driven variants inside them.
- All 18 original heads remain at `refs/fix-backups/2026-10-30/<branch>`. Each layer contains the updated branch immediately below it. Dependencies are unchanged; layers 1–2 used the old pinned environment and layers 3–18 used the separately installed upgraded environment.
- All original `test_review_*` methods remain present and pass. Two existing fixtures changed without dropping assertions: the directory timeout now uses the public-fetch exception contract, and the manifest exact-field test includes the newly required sanitized endpoint.
- Plain primary cold-plunge briefs now receive the same category-role guard as complete-system briefs. Component/accessory briefs and other categories retain their own scope. This does not add a tub-and-chiller inclusion requirement to a plain cold-plunge request.
- Geography and role checks remain conservative text heuristics. Passing synthetic cases is not evidence of measured live precision, supplier authorization, brand relationships or completeness of search.
- The initial repair report describes the earlier 229-test state. This follow-up supersedes its completeness claim; fresh review and a separately authorized bounded evaluation remain pending. GitHub Actions status was not changed or claimed to pass.

## Remaining decision: P2-4 exclusion precedence

The audit asks structured `excluded_products` to always apply, but also prohibits weakening existing tests. `test_explicit_accessory_brief_can_still_find_accessories` explicitly requests `Fire Magic replacement parts` while also excluding `replacement parts`, and requires the parts page to win. Those two requirements cannot both hold for that input.

The implementation fixes post-noun and parenthetical exclusions, preserves the requested system route within three pages, and applies structured exclusions when a broader/multi-category brief merely mentions the excluded category. It preserves the existing single-category accessory exception. Therefore **literal always-wins exclusion precedence remains unresolved**. Before treating P2-4 as fully closed, choose whether explicit structured exclusions override a contradictory primary request; implementing that choice would require changing the existing expectation or validating/rejecting the contradictory input. No test was weakened to conceal the conflict.

## Item-by-item changes

Test paths are `tests/test_followup_<module>.py`; method names below omit the `test_` prefix. All commit IDs are from the final rebased local stack.

| Item | Layer / PR | Fix commit(s) | Regression methods | Before → after | Status |
|---|---|---|---|---|---|
| P0-1 | 10,16 | `9ed26d1`, `09099c8` | roles / product_role: `foreign_manufacturer_and_warranty_labels_cannot_attribute_production`; `foreign_manufacturer_words_cannot_qualify_a_complete_supplier` | Foreign manufacturer/warranty qualified -> review; self labels retained | Fixed |
| P0-2 | 1 | `d18d3ad` | foundation: `transport_and_http_failures_fall_back_without_policy_bypass`; `policy_rejections_are_fatal_even_when_browser_is_enabled`; `disabled_fallback_preserves_failure_cause` | urllib3 errors and HTTP failures escaped -> eligible browser fallback; URL policy still fatal | Fixed |
| P0-3 | 18 | `ebc82b1` | benchmarks: `discovery_audit_accepts_current_items_and_legacy_pages` | Current items capture aborted audit -> both items/pages produce validation.json | Fixed |
| P0-4 | 14 | `c52c613` | benchmarks: `distributor_main_survives_unavailable_git_comparison` | Missing historical SHA crashed preview -> named merge-base or explicit unavailable metadata | Fixed |
| P1-1 | 1 | `68de4da` | foundation: `supplier_failures_are_scoped_and_survive_only_their_own_cache_hit` | Supplier B inherited A failures -> each host retains its own failures, including cache hits | Fixed |
| P1-2 | 1 | `8b60680` | foundation: `international_domains_use_one_ascii_identity_for_dns_host_and_tls` | Unicode header/TLS mismatch -> one IDNA hostname across DNS, Host and TLS | Fixed |
| P1-3 | 6,11 | `fb80a75` | location / country: `self_descriptions_require_a_location_not_an_adjective_or_customer`; `lower_layer_location_repairs_flow_through_country_resolution` | Adjective self-description routed as location -> rejected; geographic self-descriptions retained | Fixed |
| P1-4 | 6,11 | `bb2b236` | location / country: `shared_subjects_do_not_assign_the_factory_country_to_headquarters`; `lower_layer_location_repairs_flow_through_country_resolution` | Toronto/Shenzhen shared subjects assigned one place -> unresolved; no China HQ inference | Fixed |
| P1-5 | 7 | `cdbf0a7` | navigation: `an_accessory_for_a_bundle_remains_an_accessory` | Filter for bundle promoted -> collection selected first | Fixed |
| P1-6 | 7 | `565c134` | navigation: `hyphenated_no_compounds_preserve_the_requested_category` | No-plumbing/no-dig lost positive terms -> requested bundle outranks unrelated items | Fixed |
| P1-7 | 8 | `b7fd132` | location: `shipping_actions_do_not_change_location_subject` | Same-sentence shipping voided base -> company_base; factory subject still factory | Fixed |
| P1-8 | 9 | `7b8f4cd` | configuration: `positive_configuration_headings_can_name_included_extras` | Included accessories/optional upgrade words voided core bundle -> inclusion supported | Fixed |
| P1-9 | 10 | `d3c38a1` | roles: `product_modifiers_cannot_turn_services_into_physical_goods` | Product words promoted tours/trails/workshops/films/communities -> role not established | Fixed |
| P1-10 | 11 | `6987d91` | country: `shipping_after_an_address_is_outside_the_location_card` | Canadian shipping contaminated Kent address -> United States/headquarters | Fixed |
| P1-11 | 16 | `f0a2ffe` | product_role: `a_primary_product_can_be_one_item_in_a_production_list` | Earlier component noun blocked later primary list item -> primary role supported | Fixed |
| P2-1 | 4 | `261378d` | matching: `non_latin_marks_preserve_identity_through_master_matching` | Japanese/Indic distinctions collapsed -> identity preserved; Latin accent folding retained | Fixed |
| P2-2 | 6 | `86bd4f9` | location: `location_negation_handles_contractions_generally` | Unrecognized contractions established a location -> rejected across straight/curly apostrophes | Fixed |
| P2-3 | 6 | `84b636e` | location: `shared_headquarters_grammar_accepts_one_place_and_keeps_other_owners_out` | Valid coordinated variants rejected -> supported; factory-only/third-party owners rejected | Fixed |
| P2-4 | 7,14 | `2f4e716`, `84d74ee` | navigation: `exclusions_apply_to_their_own_noun_phrase_and_keep_system_route`; `structured_exclusions_override_mentions_in_the_brief` | Post-noun exclusions lost system routing -> collection fetched within 3 pages; incidental mentions no longer cancel exclusions. Single-category exception remains (below) | Partial: policy conflict |
| P2-5 | 7 | `f93b35e` | navigation: `complete_bundle_head_can_precede_included_extras` | Bundle/package/combo names with extras buried -> complete bundle outranks collection | Fixed |
| P2-6 | 8,11 | `e90a870` | location / country: `shipping_paragraph_is_not_an_hq_label`; `lower_layer_location_repairs_flow_through_country_resolution` | Separate shipping block lent negative label -> valid Canadian HQ retained | Fixed |
| P2-7 | 8 | `94927bd` | location: `plant_locations_keep_factory_diagnostics` | Plant location unknown -> factory diagnostic; still cannot establish HQ | Fixed |
| P2-8 | 9 | `51dc4b8` | configuration: `exclusion_and_compatibility_headings_do_not_supply_components` | Does not include / contracted / compatibility headings supplied components -> not established | Fixed |
| P2-9 | 9 | `93e47d5`, `5869612` | configuration: `inventory_list_names_do_not_describe_one_configuration`; `product_word_in_non_inventory_heading_does_not_void_inclusion` | Inventory lists established one configuration -> rejected; non-inventory product heading retained | Fixed |
| P2-10 | 10 | `78f7cd7` | roles: `role_tense_and_negation_belong_to_the_production_predicate` | Benefit/logistics/history words voided current maker role -> supported; future/negated maker roles still rejected | Fixed |
| P2-11 | 10 | `33a3eb7` | roles: `physical_product_families_and_build_to_order` | Bicycle synonyms/build to order missed -> supported; service controls retained | Fixed |
| P2-12 | 11 | `6befcc2` | country: `sales_markets_do_not_extend_the_headquarters_address` | Sales regions/full California address conflicted -> United States/headquarters | Fixed |
| P2-13 | 11 | `5d38ee8` | country: `unresolved_headquarters_cards_block_lower_priority_offices` | Unknown HQ card dropped -> unresolved HQ blocks US office fallback; Unicode/caps/inline/HTML supported | Fixed |
| P2-14 | 11 | `b8af9a7` | country: `current_headquarters_survives_separate_future_office_clauses` | Future office clause voided current HQ -> Canada/headquarters | Fixed |
| P2-15 | 16 | `f0dea53`, `65d406e` | product_role: `component_heads_and_other_verbs_cannot_inherit_production`; `plain_primary_category_briefs_also_require_a_product_role` | Component makers/other-verb objects qualified -> review, for complete and plain cold-plunge briefs | Fixed |
| P2-16 | 16 | `4bb78b4` | product_role: `self_manufacturer_descriptions_can_put_category_before_the_role` | Self category-before-role/appositives missed -> supported; foreign makers remain rejected | Fixed |
| P2-17 | 18 | `d1a798e` | recovery: `stopped_jobs_finalize_stale_ledger_rows_once_and_preserve_outcomes` | Stopped job retained pending/checking rows -> not_checked/interrupted, idempotently; terminal outcomes retained | Fixed |
| P3-1 | 12 | `4cd9e61` | benchmarks: `fallback_probe_runs_without_git_metadata` | Missing Git metadata aborted offline probe -> completed with null code_commit | Fixed |
| P3-2 | 13 | `86ee6a6` | benchmarks: `distributor_main_writes_effective_sanitized_model_settings` | Helper-only coverage missed runner/endpoint -> actual main manifest asserts effective model/rates/tokens and sanitized client base URL | Fixed |
| P3-3 | 17,18 | `b0fff28` | benchmarks: `discovery_main_captures_raw_website_items_before_page_rejection` | Existing main wiring already correct -> integration test detects removing web_fetcher.run_actor wrapper | Coverage added |
| P3-4 | 1 | `7b1bd08` | foundation: `directory_identity_retry_reuses_pages_and_counts_each_check` | Existing different-hint retry already correct -> directory-flow test proves 2 checks, 1 website fetch, shared cap | Coverage added |
| P3-5 | 1 | `eb8ce74` | foundation: `identity_retries_reuse_catalogue_work_in_the_same_job` | Repeated catalogue actor/model calls -> one fetch+analysis per job/host; failure does not trigger uncertain repetition | Fixed (optional) |
| P3-6 | 4 | `220ba0e` | matching: `completed_observation_jobs_finish_without_inventing_paid_checks` | Completed observation-only job showed 0% -> 100%; paid processed count stays actual | Fixed (optional) |

## Validation evidence

Each repair was exercised against its failing pre-change implementation and then the full layer suite, with coverage/control exceptions described here. A late integration regression from inventory-heading recognition was repaired at layer 9 and rebased upward before final validation.

Running all 45 new methods against an exported copy of the original layer-18 backup makes **41 methods fail** (157 failed subtest assertions and eight expected error occurrences). Four methods pass on that original backup: the already-working directory retry, the already-working raw-capture wiring, the URL-policy negative control, and the non-inventory-heading control for a regression introduced and corrected during this repair. Thus the literal claim that every new method fails on the original backup would be false. The raw-capture integration test was additionally verified by temporarily removing its main wrapper assignment: the test failed because the raw actor capture was absent; restoring the assignment passed.

The original synthetic verification harness was also rerun. Its unchanged business-case expectations now match; eight legacy harness assertions needed contract updates (five fault injections now use the public-fetch boundary exception, two policy assertions recognize its ValueError subclass, and the removed historical SHA check now checks the named baseline). The updated harness passes **212 checks plus six lifecycle checks**, with zero mismatches. Actual urllib3-to-boundary translation is independently tested through the real public fetcher, rather than inferred from the adapted mocks.

All 18 backups are unchanged, review test methods are retained, forbidden paths are absent from the repair diff, requirements are unchanged on each branch, and executable Python contains no literal Git SHAs. The benchmark-specific city whitelist entry was removed. Historical captures/results were not rewritten.

Validation logs and the original-head manifest are in `/private/tmp/supplier-followup-fixes.Spkicm/`. They are local diagnostics; the tracked tests and the branch/commit table below are the durable reproduction references.

| Layer | Branch | Validated implementation commit | Full suite |
|---|---|---|---|
| 1 | `feat/supplier-research-controls` | `eb8ce74a760d736662b96de2c192cfcac811267b` | 61 passed |
| 2 | `fix/api-and-export-safety` | `385d3b6f505c3ffd88662a80646592fe57122b31` | 65 passed |
| 3 | `fix/dependency-security` | `a80781d5e49c5b8de3c56f775bbf00126cfe7b7b` | 67 passed |
| 4 | `fix/master-matching` | `220ba0eefc5aab9a9b1a58d3b92f328b151bcbac` | 75 passed |
| 5 | `fix/hq-pages-and-quotes` | `307b4f972cff47f766b9e5db9cc7c3fd287c440d` | 77 passed |
| 6 | `fix/evidence-collection-and-hq` | `84b636ed342aea4b8e9e0394da9b0241b9febc7a` | 107 passed |
| 7 | `fix/product-page-selection` | `f93b35e3b3ddb736e5ddb8726471721e3caad252` | 117 passed |
| 8 | `fix/headquarters-location-context` | `94927bd241a276f924cecca86c857a754611917b` | 130 passed |
| 9 | `fix/complete-system-components` | `58696127d974fec98f5b800ddc630831530d3070` | 148 passed |
| 10 | `fix/supplier-role-evidence` | `33a3eb7d90bb7db90162a5c7ca662575bc0736a9` | 171 passed |
| 11 | `fix/office-country-evidence` | `dc3dd254bd8e7079cfea6462cddab40b26df1f1c` | 197 passed |
| 12 | `fix/bounded-fetch-fallback` | `4cd9e61367747d3b940aaf481bccb04f44c91103` | 205 passed |
| 13 | `docs/distributor-feasibility` | `86ee6a62c85828e7d7810923c031a362243ebdb3` | 207 passed |
| 14 | `fix/distributor-page-selection` | `84d74ee00af5165db3f7a64671fce8a81c63565c` | 224 passed |
| 15 | `fix/manufacturer-first-research` | `22cdd6f2a52c793c3ae702e0d255519d8fba1d4c` | 226 passed |
| 16 | `fix/requested-product-role` | `65d406e71e1caad71ef631545b88149d025840f8` | 248 passed |
| 17 | `feat/manufacturer-discovery-evaluation` | `b0fff286f0434bed050145fc0c9ddf06792bd60d` | 250 passed |
| 18 | `fix/discovery-candidate-selection` | `267aabb3dec21b4cf4d76b6a55ef281f15fab50c` | 274 passed |

The layer-18 entry identifies the last executable change tested across the full stack. A later documentation-only commit adds this report and the plan update; the same suite is rerun after that commit.

Run the suite in Python 3.12 with the branch’s installed requirements, fake provider keys, dotenv loading disabled, a temporary job/reference directory, and outbound socket connections blocked. The local diagnostic runner implements those controls around `unittest` discovery. Do not point the tests at production job/reference stores.

## Prepared push commands — NOT executed

These commands use the original remote heads as exact leases. If any remote head changes, stop and review it; do not replace a failed lease with an unconditional force push. Run in stack order only after approval. This report does not approve merging.

```sh
git push --force-with-lease=refs/heads/feat/supplier-research-controls:37d6f94486751d61ea70c06417ec441b2b4ef964 origin feat/supplier-research-controls:refs/heads/feat/supplier-research-controls
git push --force-with-lease=refs/heads/fix/api-and-export-safety:abcac69a68becdeab5faa1adcb2451559705692d origin fix/api-and-export-safety:refs/heads/fix/api-and-export-safety
git push --force-with-lease=refs/heads/fix/dependency-security:3838c514a29671d4ea31565373b9c5ee476dabf7 origin fix/dependency-security:refs/heads/fix/dependency-security
git push --force-with-lease=refs/heads/fix/master-matching:456167b2599cd67847a059a4fa425886e2ff06e1 origin fix/master-matching:refs/heads/fix/master-matching
git push --force-with-lease=refs/heads/fix/hq-pages-and-quotes:00104ac427c259c2c52ceaf9cf96c26704cac25e origin fix/hq-pages-and-quotes:refs/heads/fix/hq-pages-and-quotes
git push --force-with-lease=refs/heads/fix/evidence-collection-and-hq:033d20a96ec199c2b25f0e59b54b62e8ce16771f origin fix/evidence-collection-and-hq:refs/heads/fix/evidence-collection-and-hq
git push --force-with-lease=refs/heads/fix/product-page-selection:fedce67d0ab0d62afbfa650dfe7490e9e259a995 origin fix/product-page-selection:refs/heads/fix/product-page-selection
git push --force-with-lease=refs/heads/fix/headquarters-location-context:eade470e80d21b7390fc564373e795737396ef36 origin fix/headquarters-location-context:refs/heads/fix/headquarters-location-context
git push --force-with-lease=refs/heads/fix/complete-system-components:e8e6fcb85ff705da25fffcf1da0df7e4ec89f0d0 origin fix/complete-system-components:refs/heads/fix/complete-system-components
git push --force-with-lease=refs/heads/fix/supplier-role-evidence:b547bb33a0162f8ec3cb98dde8263c17a23b714d origin fix/supplier-role-evidence:refs/heads/fix/supplier-role-evidence
git push --force-with-lease=refs/heads/fix/office-country-evidence:003badc90f648b2feb7f885dd746045c3cd304ed origin fix/office-country-evidence:refs/heads/fix/office-country-evidence
git push --force-with-lease=refs/heads/fix/bounded-fetch-fallback:079c67e543ced0418b4824f587169d901f5df48c origin fix/bounded-fetch-fallback:refs/heads/fix/bounded-fetch-fallback
git push --force-with-lease=refs/heads/docs/distributor-feasibility:a06e84abdf51fa8f94357dc6ca7d6d4c690c1699 origin docs/distributor-feasibility:refs/heads/docs/distributor-feasibility
git push --force-with-lease=refs/heads/fix/distributor-page-selection:d1fdfcae94961be7904e85806281f3e693f1fea5 origin fix/distributor-page-selection:refs/heads/fix/distributor-page-selection
git push --force-with-lease=refs/heads/fix/manufacturer-first-research:c1a6fc960253a08fc69b89124d447e76373867b8 origin fix/manufacturer-first-research:refs/heads/fix/manufacturer-first-research
git push --force-with-lease=refs/heads/fix/requested-product-role:26c98331950cfc82e70c304fa9bbc76bfdb40df4 origin fix/requested-product-role:refs/heads/fix/requested-product-role
git push --force-with-lease=refs/heads/feat/manufacturer-discovery-evaluation:ba439788933f20ae51649a036db0de438f0de923 origin feat/manufacturer-discovery-evaluation:refs/heads/feat/manufacturer-discovery-evaluation
git push --force-with-lease=refs/heads/fix/discovery-candidate-selection:321bece709837167cfb53dc0b7b05b053dc7286d origin fix/discovery-candidate-selection:refs/heads/fix/discovery-candidate-selection
```

After a separately approved push, request fresh review on the new remote heads, reconcile the P2-4 decision, and inspect the updated diffs in order before merging. A later bounded supplier evaluation should measure candidate relevance, role/country false positives, novel suppliers found, unresolved-review rate and cost per useful verified supplier. It was not run in this repair.
