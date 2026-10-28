# Supplier research agent — step-by-step plan

Updated: 2026-10-28

**Goal:** find more relevant suppliers, verify the requested products and company identities, and produce useful evidence with predictable research costs.

**Current phase:** [candidate selection](docs/benchmarks/cold-plunge-discovery-2026-10-28/selection-fix-results.md) is prepared on `fix/discovery-candidate-selection`. Exact master/seen hosts are filtered before allocating checks, queries rotate within source-priority tiers, and a durable selection ledger explains every retained result. 192 tests pass, including nineteen new regressions. Network-blocked replay of the original nineteen rows keeps three checks while representing both queries, recording seven known/four blocked skips and all nineteen decisions; no provider calls or supplier judgments. Qualification rules and frozen labels are unchanged. Next: commit and run one fresh bounded three-site preview, then audit the outcomes/costs. Canada discovery, directory verification, named-SKU/brand relationships, other category scopes, Rutherford's location context and independent final cases remain pending. No exports, push, PR or deployment.

## Already completed

- [x] Product-specific supplier qualification with source URLs and literal quote checks.
- [x] Separate qualified, review-needed and excluded results.
- [x] Shared runtime, page, service-call and execution-budget controls.
- [x] Durable jobs, partial results, stop handling and explicit Sheets export.
- [x] Master-list import and conservative website/name matching.
- [x] Distributor brand extraction with source and coverage information.
- [x] Bounded Shopify catalogue extraction and product/variant checks.
- [x] Observed prices separated by currency; accessories and services handled separately.
- [x] Optional browser fallback and sourced company contacts.
- [x] Initial live previews: 13,267 master records, 157 directory observations and 20 Shopify products.
- [x] Offline regression suite rerun on 2026-10-26: 48 tests passed.
- [x] Security review of the October 2026 incidents (Railway variables, Node.js, certificate authority, npm/PyPI packages). No compromised packages or committed credentials were found; the findings drive Steps 0, 2 and 3.
- [x] Master-list comparison profiled on 2,000 real master rows; the gaps found drive Step 4.

Evidence: [validation report from 2026-10-14](docs/validation-2026-10-14.md). Those previews establish working examples, not overall search accuracy.

## Decisions (2026-10-26)

- Discovered sites whose website is already in the master list are skipped before any paid check and listed as skipped. Websites you supply are always checked.
- The backend is publicly reachable on Railway, so API authentication comes before the dependency and matching work.
- The quick security audit ([Cloudflare security-audit skill](https://github.com/cloudflare/security-audit-skill)) runs after the baseline is merged.

## How changes are made

- Branch names start with `feat/`, `fix/`, `chore/` or `docs/`, never `codex/` or `claude/`.
- One topic per branch, with tests. Each branch updates this plan's checkboxes and progress log.
- Merge only after the offline suite (and CI, once added) passes and you approve.
- `.env`, `service_account.json`, `var/` and editor settings never enter Git.

## Step 0 — security response outside the repository (owner: you)

- [x] Rotate the credentials stored in Railway and `.env` (OpenAI, Apify, Google service account) and set provider spending limits. Reported done on 2026-10-26.
- [ ] Upgrade Node.js. On 2026-10-26 `node@22` was 22.22.3 and Homebrew `node` was 23.10.0 (end-of-life, no fix). Fixed versions for CVE-2026-111497: 22.23.4, 24.22.1 or 26.12.1.
- [ ] Pin MCP server versions in `~/.cursor/mcp.json` (currently unversioned or `@latest`).
- [ ] Until Step 2 is deployed, remove the backend's public Railway domain or keep it on private networking only.

**Done when:** `node -v` shows a fixed version, MCP servers are pinned, and the backend cannot be used without authentication.

## Step 1 — preserve the baseline (branch `feat/supplier-research-controls`)

- [x] Run the offline regression suite — 48 tests passed on 2026-10-26.
- [x] Keep credentials, local job/reference data and editor settings out of Git (`.idea/` added to `.gitignore`).
- [x] Commit the reviewed implementation locally.
- [ ] Push and open the pull request when allowed; merge after your approval.
- [ ] After the merge, run the quick security audit and turn confirmed findings into `fix/` branches.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

**Done when:** the suite passes and the diff contains no `.env`, `service_account.json`, `var/` or editor files.

## Step 2 — protect the public API and exports (branch `fix/api-and-export-safety`)

- [x] Require an `X-API-Key` header (`SUPPLIER_API_KEY`) on every backend endpoint except `/health`, checked before routing and body parsing. Refuse all requests (503) when no key is configured.
- [x] Send the key from the Streamlit UI and show a clear message when it is missing or wrong.
- [x] Add an optional UI password (`SUPPLIER_UI_PASSWORD`) for the public Streamlit page.
- [x] Neutralize spreadsheet formulas in CSV downloads (values starting with `=`, `+`, `-`, `@`, tab or carriage return).
- [ ] Set `SUPPLIER_API_KEY` (and optionally `SUPPLIER_UI_PASSWORD`) on both Railway services before deploying. Without the key the deployed backend returns 503 for everything except `/health`.
- [ ] Push and open the pull request when allowed; merge after your approval.

**Done when:** requests without the key get 401, `/health` still works, and a supplier named `=HYPERLINK(...)` downloads as plain text.

## Step 3 — dependency security and CI (branch `fix/dependency-security`)

- [x] Add a GitHub Actions workflow with read-only permissions, actions pinned to commit hashes and no secrets. It runs the offline suite and `pip-audit`.
- [x] Upgrade packages with published advisories (FastAPI 0.162.0 / Starlette 1.10.0, Streamlit 1.66.1, requests 2.34.2, python-dotenv 1.2.4) and require `certifi>=2026.10.19`. NumPy is 2.2.6 because Streamlit's pyarrow no longer imports on 1.26.
- [x] Remove unused packages (`tenacity`, `beautifulsoup4`, `apify-client`, `apify-shared`) and unused files (`backend/intent_agent.py`, `backend/brand_utils.py`, `prompt/extract_supplier.md`).
- [x] Confirm the OpenAI structured-output schemas are unchanged after the upgrade.
- [ ] Push and open the pull request when allowed; merge after your approval. Recreate `.venv` from `requirements.txt` after this lands.

**Done when:** the suite passes on the upgraded packages and `pip-audit` reports no known vulnerabilities.

## Step 4 — master-list comparison and discovery filter (branch `fix/master-matching`)

- [x] Match blocked domains on whole domain labels, so `fellowes.com` and `championtarget.com` are no longer filtered as Lowe's and Target.
- [x] Record every skipped candidate with its reason (blocked domain, already in the master list) instead of dropping it silently.
- [x] Skip discovered candidates whose website host is already in the master list; still check supplied websites.
- [x] Compare both the submitted and the final (redirected) website with the master list.
- [x] Add `related_domain_needs_verification` (same registrable domain, different host) and `name_match_different_website` (same name, different website).
- [x] Treat legal-suffix differences on the same website (for example "Homecraft Inc.") as the same company and record the name relation.
- [ ] Push and open the pull request when allowed; merge after your approval.

**Done when:** the existing matching trap tests still pass, the 2,000-row profile shows the subdomain and legal-suffix cases under the right statuses, and no candidate disappears without a recorded reason.

## Step 5 — build the supplier benchmark

First category: **complete cold-plunge systems, with supplier headquarters in the United States or Canada**. Labelling can start now; agent runs wait for Steps 2–4.

- [x] Write down the exact brief: permitted company roles, exclusions and required product contents. A complete system must include a tub and chiller, or an integrated chiller. Dealer-program evidence is useful but optional.
- [x] Select 24 sites covering genuine suppliers, chillers-and-complete-systems, unrelated businesses, overseas headquarters and blocked hosts.
- [x] Keep Homecraft and Coldture as regression anchors, separate from new evaluation sites.
- [x] Before reading agent decisions, manually label each site's product fit, company role, headquarters evidence and expected master-list relationship. Official URLs, quotes and the 2026-10-27 review date are in the labels file. Missing evidence stays unknown.
- [x] Split new sites into a 14-site development group and an 8-site final-check group. Labels and brief were frozen before any agent run. The first baseline included the final-check cases; later fixes have used development/anchor cases only. A fresh independent final set is still needed.
- [x] Save the versioned benchmark under `docs/benchmarks/cold-plunge-2026-10-27/`. No private contacts were copied.

**Done when:** each case has an evidence-backed expected outcome, or an explicit unknown/review label. A master CSV country field alone is insufficient headquarters evidence.

## Step 6 — test qualification on supplied sites

- [x] Record the local commit used for benchmark runs (`ae3439b` on `fix/master-matching`).
- [x] Run the benchmark sites in small, seed-only batches with additional discovery disabled and preview-only enabled. First 8-site batch hit the $8 reservation cap; later batches used 2 pages/site and $10.
- [x] Use an isolated evaluation job database; preserve existing application jobs and source files.
- [x] Keep page, call, runtime and provider charge caps enabled. Record the settings before each batch, including any changes needed after a limit stops a job.
- [ ] Test company qualification first, then enable catalogue analysis on selected product/variant cases to measure its additional benefit and cost. Qualification-only so far.
- [x] Save job IDs, request settings and decisions under `var/eval/` and the summary in the results report.
- [x] Record stopped, limited, unprocessed and extraction-failed cases separately. They must not silently become negative supplier labels.

**Done when:** every selected case has either a saved decision or a documented execution limitation. No Sheets writes are needed for this phase.

## Step 7 — test discovery separately

- [x] Run the same brief through country-targeted discovery without supplying benchmark seeds: first US-localized [preview](docs/benchmarks/cold-plunge-discovery-2026-10-28/results.md), nineteen raw hosts, three checks, zero qualified. Canada did not run because US candidates filled the global check allowance.
- [x] Manually review the three selected sites and screen remaining raw titles/snippets/paths. Two company-role holds and one editorial fetch failure; unfetched sites remain unverified.
- [x] Compare raw hits with historical development/anchor labels and review additional checked candidates. Only Plunge surfaced (1/11 commercially relevant historical sites); none of six historically expected-qualified sites. This is sample retrieval coverage, not independent accuracy or web recall. No final-check host surfaced.
- [x] Check all nineteen raw hosts and three selected candidates against the master. Seven exact known hosts, one related host, four blocked hosts and seven other unmatched hosts; selected three unmatched, none confirmed new.
- [x] Review the job's skipped list: only The Spruce recorded blocked; seven known hosts and three additional blocked hosts fell outside the selection window. No paid known-host checks occurred. A separate synthetic offline diagnostic reproduces the pre-master cutoff defect.
- [ ] Confirm the candidate-selection fix live: filtering, query rotation, source hints, full ledger, nineteen regressions and saved-SERP replay are complete locally; one fresh bounded preview and final audit remain. [Preparation/results](docs/benchmarks/cold-plunge-discovery-2026-10-28/selection-fix-results.md).
- [ ] Test Canada-localized discovery explicitly and assess country/query allocation under a shared budget.
- [ ] Test directory-to-official-site verification on a small sample in a relevant category. Keep distributor labels and verified suppliers separate.

**Done when:** there is a manually reviewed shortlist, an explanation for missed known suppliers and a list of duplicate/ambiguous identities. Coverage of this benchmark is not recall across the whole web.

## Step 8 — score the results

- [x] Report development qualified precision: 4/4 match frozen commercial-eligibility labels, but only 3/4 have clear HQ/office support on inspection; BlueCube needs manual review. This does not establish production precision.
- [x] Report development qualification coverage against `expected_status=qualified`: 4/6 (67%) frozen-label coverage, or 3/6 with clear HQ/office evidence; all 16 development/anchor cases attempted. Separately report relevant review cases and the extraction failure.
- [x] Count eligible suppliers left in review, incorrect exclusions, extraction failures, duplicate qualified companies and uncertain master matches for the development cohort.
- [x] Compare development master-list outcomes: all 16 known hosts recognized; eleven existing-domain matches and five unresolved name conflicts. No silent drops or wrong automatic merges observed.
- [ ] Check product/variant relevance, literal source quotes, explicit currencies and price-sample coverage.
- [x] Record development elapsed time, reported actor charges, estimated model cost, conservative reservations and cost per qualified supplier, distinguishing frozen labels from inspected HQ support. Approximately $0.324 combined execution for this rerun.
- [ ] Show counts alongside percentages and score the untouched final-check group separately.

Initial quality targets to assess on the labelled cohort:

| Check | Target |
| --- | --- |
| Qualified precision | At least 90%; always show the underlying counts |
| Coverage of cases labelled expected-qualified | At least 80%; report missing/limited cases separately |
| Accepted suppliers supported only by accessory/service evidence | Zero |
| Duplicate qualified companies | Zero unresolved duplicates |
| Accepted evidence and price observations | Verified quotes, source URLs, explicit currency and honest coverage labels |
| Master-list comparison | Zero wrong merges; every labelled master supplier flagged; zero candidates dropped without a reason |
| Source-list edits or Sheets writes during evaluation | Zero |

These are initial acceptance targets, not measured results or statistical guarantees. A small, deliberately mixed benchmark does not establish production-wide accuracy.

Scoring correction (2026-10-27): the previous development+anchor denominator of 11 commercially relevant sites includes five labelled `expected_status=review` with unknown headquarters. Six cases are labelled expected-qualified. Keep the historical 1/11 result, but do not treat those five correct review outcomes as failed automatic qualifications. Recheck any label that infers a complete bundle merely from separate tubs/chillers or headquarters from manufacturing history.

**Done when:** a results report explains both successful cases and failures, with an evidence-backed shortlist and observed costs.

## Step 9 — fix the largest observed problems

- [x] Rank failures: missing source links, inadequate product/HQ excerpts, and permissive headquarters validation are the first priorities.
- [x] Capture navigation/footer HTML anchors separately, follow observed company/product links within existing limits, and preserve contiguous heading/value and product-configuration windows.
- [x] Require affirmative company-location/office context. Reject shipping, warehouse, showroom, customer, origin/founding and negated location statements; retain diagnostics for failed quotes.
- [x] Complete targeted development previews and record both improvements and review cases, including BlueCube's source-checked address-quote replay. [Results](docs/benchmarks/cold-plunge-2026-10-27/evidence-collection-results.md). Qualification requirements remain in force.
- [x] Rerun the remaining development cases and refresh all four prior controls on fixed commit `480d5b6`. [Full development results](docs/benchmarks/cold-plunge-2026-10-27/development-rerun-results.md): four qualified, eleven review, one retry. No full/final benchmark pass claimed.
- [x] Penalize replacement-filter/accessory links that contain strong complete-system keywords; replay Penguin's saved navigation before paid retesting. On `fix/product-page-selection`, 84 tests pass and only Penguin's route changes in the saved 16-case replay. Complete tubs with included accessories and explicit filter briefs retain priority.
- [x] Confirm Penguin's changed destination and Redwood's control result in a bounded live preview. Both qualified; Penguin's collection explicitly describes a complete integrated-chiller/tub system. [Results](docs/benchmarks/cold-plunge-2026-10-27/product-page-selection-results.md). Six actor runs + two model calls, approximately $0.045 combined execution; all actor runs terminal, no exports.
- [x] Separate HQ/office from workshop/factory/showroom locations in the source validator, preserving location type in country evidence/diagnostics. Contact/About URLs and unlabeled addresses cannot establish office context. All 92 offline tests pass; BlueCube's workshop claim is rejected in saved evidence replay while valid HQ/office claims remain. LeisureCraft's unlabeled address is retained as a lead and routes to Contact, without being promoted into HQ proof.
- [x] Confirm the HQ/location-context change with bounded live previews for BlueCube, Penguin, LeisureCraft and Sun Home. [Results](docs/benchmarks/cold-plunge-2026-10-27/headquarters-context-results.md): BlueCube review; Penguin/Sun Home qualified; LeisureCraft head office verified but its automatic qualification held for product review. Twelve actor runs + four model calls, approximately $0.096 combined execution; all runs terminal, no exports.
- [x] Verify supplied components independently of the model's complete-system verdict. Compartments, compatibility, optional/separate chillers, cross-block quotes and generic component catalogues cannot establish a complete cold-plunge system. Preserve source-specific inclusion support and the raw model verdict when overridden. Twelve new regressions; 104 tests pass. Saved-analysis replay downgrades only LeisureCraft's unsupported qualification; valid paired/integrated systems remain supported.
- [x] Confirm component verification with bounded live previews for LeisureCraft, Penguin, Sun Home and Coldture. [Results](docs/benchmarks/cold-plunge-2026-10-27/component-evidence-results.md). On fixed `7ff1170`: LeisureCraft review, three controls qualified; twelve actor runs + four model calls, approximately $0.102 combined execution. Final paragraph/list guard refinement on `3b5952c` preserves these decisions in saved-response replay. All actor runs terminal, no exports.
- [x] Require source-local evidence for the exact company-role classification. Contact lines, generic product lists, third-party statements, negation, plans and role-service labels cannot establish a supplier role. Design/engineering alone cannot establish manufacturing; third-party supply and a business channel are required for Distributor. Unsupported roles stay in review with the raw model classification preserved. Sixteen new regression tests; 120 tests pass. A bounded source-only repair can recover at most two literal quotes for the same proposed role from captured pages, without new provider calls or automatic role changes. It restores Sun Home's missing role proof; Redwood's design-only Manufacturer verdict still needs review.
- [x] Complete targeted role validation for Redwood, Sun Home, Penguin and Coldture. [Results](docs/benchmarks/cold-plunge-2026-10-27/role-evidence-results.md). Final application `e0cb37e`: Coldture Brand owner qualified live; Penguin Manufacturer role verified but HQ review; Redwood Brand owner verified in a new model call on saved pages after an unsuccessful live fetch, also HQ review. Sun Home qualifies in final source-repair replay of first-preview captures. Ten actor runs + four model calls, approximately $0.089; all actors terminal, no exports. Distributor classification has regression coverage but no live case yet.
- [x] Resolve labelled-office evidence and model-country/basis inconsistency using saved Penguin and Redwood cases. Verify country from explicit country names or recognized US/Canadian region addresses; retain `office`, `headquarters` or `company_base` and original model fields. Bounded recovery uses existing captures only. Stronger HQ evidence wins; conflicts and unknown geography stay in review. Planned/former/negated, employee/third-party and office-goods statements cannot establish location. Seventeen new regression methods; 137 tests pass. Replay changes only the two intended reviews to qualified and preserves eleven accepted observations across four suppliers.
- [x] Confirm the final office-country fix with bounded Penguin/Coldture live previews and one Redwood model reanalysis on saved pages. [Results](docs/benchmarks/cold-plunge-2026-10-27/office-country-results.md). On `e4d32e2`, all three qualify: Penguin/Redwood `office`, Coldture `headquarters`; new model answers also select those bases directly. Twenty-four quotes verified, six actor runs + three model calls, approximately $0.075; all actors terminal, no exports. Redwood's earlier failed fetch remains separate from saved-page qualification.
- [x] Test bounded browser fallback for Morozko and Redwood, recording raw versus browser attempts and costs separately. [Results](docs/benchmarks/cold-plunge-2026-10-27/fetch-fallback-results.md). On `a4cf388`, ordinary raw fetches were healthy: four pages each, Redwood qualified, Morozko role review. Two controlled saved-timeout + fresh-browser probes both recovered homepages, with no model/classification in probes. Six new regressions, 143 tests pass. Browser actor usage $0.0047; all new execution approximately $0.059, ten actor runs + two model calls, all actors terminal, no exports. Existing production fallback remains opt-in; no natural live failure was reproduced.
- [ ] Adjudicate Morozko's captured manufacturing-role statements (historical purpose and passive product construction) and current company-location evidence separately. Do not treat founding in Phoenix as current HQ/base proof or relax the role guard merely because fetching succeeded.
- [x] Attempt bounded live Distributor qualification: [two Fire Magic leads](docs/benchmarks/distributors-2026-10-28/results.md), both review; six successful raw pages, missing policy/product collection and a too-narrow role guard. No discovery or broad accuracy claim.
- [x] Improve page selection for distributor research: separate positive brief terms from exclusions; prioritize relevant products/categories and collect targeted public wholesale/account policies and About evidence. Thirteen regressions, eighteen saved routes and [bounded live follow-ups](docs/benchmarks/distributors-2026-10-28/collection-fix-results.md) confirm collection. This does not establish distributor qualification or exact SKU verification.
- [ ] Fix the demonstrated Rutherford location-context rejection: explicit HQ in an About paragraph is classified as shipping/returns because delivery/warehouse language shares the context. Add a saved-source regression before changing location guards; keep Gas Equipment's unlabelled address unknown.
- [x] Add a first requested-product role guard for complete cold-plunge/ice-bath systems, separate from company-role and component checks. [Validation](docs/benchmarks/cold-plunge-2026-10-27/product-role-results.md): Penguin component-maker facts retained but qualification held; Coldture remains qualified live. Fifteen new regressions, 173 tests; 48 saved records/44 analyses, only five Penguin qualifications become review, fifteen other qualified observations preserved. The scoped guard makes no extra provider calls; six actor/two model live confirmation approximately $0.053, all terminal.
- [ ] Extend company/product role checks beyond this first category and support explicit named-model/brand relationships with sourced records. Preserve supplier-reported versus brand-confirmed evidence and territory/date; category evidence does not prove a role for every SKU or legal ownership/authorization. Distributor relationships remain optional and separate.
- [ ] Adjudicate ambiguous HQ/product labels in a new version; preserve this frozen benchmark and its results.
- [ ] Add evidence-backed aliases and parent/brand relationships where identity mismatches recur; retain separate identities unless a relationship is verified.
- [ ] Improve catalogue coverage or add platform/directory adapters where current extraction misses relevant products or brands.
- [ ] Add regression cases for each concrete failure and rerun affected checks.
- [ ] Measure changes on development cases, then run the untouched final-check group. Once a final-check case is used to tune a fix, treat it as development data for subsequent evaluations.
- [ ] Prepare fresh independent final-check cases before a release claim; the original final-check group was already included in the first baseline.

**Done when:** the targeted failures improve without introducing new incorrect qualifications, duplicate identities or unsupported price claims.

## Step 10 — use the workflow for regular research

- [x] Default UI/API research and discovery queries to manufacturers and brand owners; keep Distributor explicitly selectable for optional review. Offline job-to-actor query tests preserve official-brand lookup and explicit role choices; UI/API smoke check confirms both paths. No paid rerun required for this settings/routing change.
- [x] Publish an [optional distributor review guide](docs/distributor-workflow.md) with tested settings, clear evidence limits and no automatic authorization/outreach/export claims.
- [ ] Publish a short operating guide: brief → discover/import → compare → verify → review → export selected results.
- [ ] Review the final shortlist and explicitly select any Google Sheets export.
- [ ] Save the evaluated implementation and update this plan with the report and commit references.
- [ ] Prioritize additional categories and automatic job resumption after the evaluated workflow is reliable. Resumption must avoid repeating uncertain billable operations or exports.

**Done when:** the workflow produces a useful, reviewed shortlist consistently, with traceable evidence and known costs.

## Progress log

| Date | Work | Result / evidence |
| --- | --- | --- |
| 2026-10-28 | Candidate-selection fix prepared on `fix/discovery-candidate-selection` | [Brief](docs/benchmarks/cold-plunge-discovery-2026-10-28/selection-fix-brief.md), [offline results](docs/benchmarks/cold-plunge-discovery-2026-10-28/selection-fix-results.md). Known/seen filtering before allocation, source-tier query rotation, duplicate/late-skip ledger, API/UI and stop/failure provenance. Nineteen new regressions; 192 tests pass. Same nineteen saved rows now select from both queries, record seven known/four blocked skips and all nineteen decisions with unchanged three-check allowance. No providers or supplier judgments in replay; live confirmation pending |
| 2026-10-28 | First no-seed manufacturer discovery preview on `83365b3` | [Results and next change](docs/benchmarks/cold-plunge-discovery-2026-10-28/results.md). Nineteen US-localized organic hosts across two queries; three checks all selected from the first query. Cold Plunge Store and Titan need company-role review, Men's Fitness fetch failed; zero qualified/excluded. One blocked skip recorded; seven master-known hosts and three other blocked hosts outside the window. All three selected sites unmatched, not confirmed new. Network-blocked synthetic diagnostic reproduces known-first cutoff. 173 tests pass; nine quotes/six page hashes/implementation hashes verified, master unchanged. Eight actors + two models approximately $0.057, all actors terminal. Backend unchanged; candidate selection fix and Canada preview next; no exports, final-check hosts or deployment |
| 2026-10-28 | Requested-product role confirmed on `35a9304` | [Results](docs/benchmarks/cold-plunge-2026-10-27/product-role-results.md). Penguin Manufacturer/company and complete-system product facts preserved, requested-category role Unknown → review; Coldture Brand owner/complete bundle/Canadian HQ qualifies live. Fifteen regressions, 173 tests pass. Offline: 48 records, 44 analyses, only five Penguin qualifications held, fifteen other qualified observations preserved; Renu review reason becomes role-specific, no new exclusions. 215 offline and eleven live retained quotes verified; six live page hashes/implementation hashes match. Six actors + two model calls, approximately $0.053, all actors terminal. Actual API result renders offline with distinct company/requested-product role fields. No exports, final-check runs or deployment |
| 2026-10-28 | Requested-product role check prepared on `fix/requested-product-role` | [Follow-up brief](docs/benchmarks/cold-plunge-2026-10-27/product-role-brief.md). First scope: complete cold-plunge/ice-bath systems for Manufacturer/Brand owner; company role remains distinct from requested-category role. Fifteen new regressions reproduce Penguin's component-to-system inference and protect direct primary-role evidence. Saved development replay: 48 records/44 analyses/four collection failures; only five Penguin qualifications become review, fifteen qualified observations across three supplier websites preserved, no provider calls. All 173 tests pass; bounded live confirmation pending |
| 2026-10-28 | Manufacturer/brand-owner defaults on `fix/manufacturer-first-research` | UI and API defaults exclude Distributor until selected. Search queries now follow requested company roles, while official-brand identity lookup keeps its explicit query. Existing distributor role tests now opt in explicitly; supported distributor evidence is outside the default brief and remains eligible when requested. 158 tests pass, plus an offline UI/API payload check for default and distributor-only requests. README, optional workflow and plan updated; saved jobs unchanged, no provider calls, servers, exports or deployment |
| 2026-10-28 | Distributor collection confirmed on `ab50ba4` and `124050d` | [Results](docs/benchmarks/distributors-2026-10-28/collection-fix-results.md), [optional workflow](docs/distributor-workflow.md). Correct gas-grill categories now collected; final Rutherford pass gathers About, Gas Grills and public wholesale policy within four pages. Both suppliers remain in role review. Thirteen new regressions, 156 tests pass; all sixteen prior cold-plunge routes preserved. Sixteen raw/eight retained quote observations, eleven page hashes and implementation hashes verified. Eleven actors + three model calls, approximately $0.082; all terminal, no exports. New remaining blocker documented: explicit Rutherford HQ rejected because nearby delivery language contaminates context; brand/product/authorization scope also remains unresolved |
| 2026-10-28 | First distributor collection preview on `ab50ba4` and targeted priority refinement | Seven fresh raw pages succeeded; Rutherford About and Gas Grills, and Gas Equipment's grill page now collected. Both remain in role review. Rutherford's location routing hint stayed false despite actual HQ text, scheduling Contact before policy; changed only trade scheduling to prioritize the missing policy after a company/product pass. Thirteenth regression added; final Rutherford-only preview pending. Location and qualification guards unchanged |
| 2026-10-28 | Distributor collection fix prepared on `fix/distributor-page-selection` | Twelve new regressions cover positive/excluded terms, whole-word gas matching, decoded facets, complete products with extras, dual-purpose products, public trade-policy bounds, navigation-only labels, policy excerpts and cache isolation. Network-blocked replay preserves all sixteen saved cold-plunge routes and changes both distributor routes as intended. [Follow-up brief](docs/benchmarks/distributors-2026-10-28/collection-fix-brief.md): seven attempts, four per site, same $4 ceiling; live confirmation pending. Qualification rules unchanged |
| 2026-10-28 | Distributor feasibility preview on `0b64f7c` | [Results and proposed workflow](docs/benchmarks/distributors-2026-10-28/results.md). Two Fire Magic leads, both review, no exclusions/qualifications. Six raw pages succeeded; collector missed wholesale policy/appropriate product pages, and role evidence across distinct assertions remains unsupported by the guard. A test phrase containing exclusions biased ranking; clean-phrase offline reranking helps Rutherford but leaves other ties. Seven retained quotes and six hashes verified. Saved Penguin result shows component-manufacturer versus complete-product role gap. Six actors + two model calls, approximately $0.043, all actors terminal; 143 tests pass, production unchanged, no exports |
| 2026-10-14 | Feature upgrades and initial controlled previews | [Validation report](docs/validation-2026-10-14.md); 48 tests passed at that time |
| 2026-10-26 | Added this tracking plan and reran the offline suite | 48 tests passed; no new paid run started |
| 2026-10-26 | Security review of the October incidents | No compromised packages or committed credentials. Exposed: public backend without authentication, Node 22.22.3/23.10.0, `certifi` and `pip` in `.venv` that still trust the eMudhra roots, advisories in Starlette, Streamlit, requests and python-dotenv |
| 2026-10-26 | Master-list comparison profiled on 2,000 real master rows | Known supplier on a subdomain with " Inc." added to its name: 1,997 reported as unmatched (new). Same website with " Inc.": 1,997 name conflicts. Same name on an unrelated website and on a sub-site get the same label. `fellowes.com` and `championtarget.com` blocked as retailers. Skipped candidates leave no record |
| 2026-10-26 | Plan reorganized; baseline committed locally on `feat/supplier-research-controls` | 48 tests passed; branch renamed from `codex/`; pull request pending because PRs are on hold |
| 2026-10-26 | Step 2 on local branch `fix/api-and-export-safety` (based on the baseline commit `f1e5b38`) | 52 tests passed (4 new: API key before body parsing, 503 without a configured key, formula-safe CSV, UI password and rejected-key message). Railway variables still to set |
| 2026-10-27 | Step 3 on local branch `fix/dependency-security` | 53 tests passed on upgraded packages; OpenAI schemas unchanged; `pip-audit` clean. CI workflow added (read-only, hash-pinned actions). Unused Apify SDK, tenacity, BeautifulSoup and three unused files removed |
| 2026-10-27 | Step 4 on local branch `fix/master-matching` | 56 tests passed. 2,000-row profile: shop-host + " Inc." → 2,000 `related_domain_needs_verification`; same host + " Inc." → 1,996 existing (was 1,997 name conflicts); same name on another site → 1,998 `name_match_different_website`. `fellowes.com` and `championtarget.com` no longer blocked. Four remaining blocked master hosts are actual retailers |
| 2026-10-27 | Cold-plunge benchmark labelled and run | [Results](docs/benchmarks/cold-plunge-2026-10-27/results.md). 24 sites, seed-only, preview-only. Precision 1/1; coverage 1/14 eligible. Did not pass. No PRs. No Sheets writes |
| 2026-10-27 | HQ pages and per-claim quotes on `fix/hq-pages-and-quotes` | About/contact/FAQ ranked above product paths. HQ excerpts follow the brief countries. One bad quote no longer voids the rest. Origin “born in / made in” quotes are not HQ. 58 tests passed |
| 2026-10-27 | Development rerun after HQ/quote fixes | [Results](docs/benchmarks/cold-plunge-2026-10-27/results.md). Precision 1/1; coverage 1/11 eligible development+anchor sites. Coldture HQ now verified; Plunge no longer false-qualifies. Final-check not rerun. No PRs |
| 2026-10-27 | Evidence collection and contextual HQ validation on `fix/evidence-collection-and-hq` | [Targeted results](docs/benchmarks/cold-plunge-2026-10-27/evidence-collection-results.md). 80 tests pass. Coldture/Sun Home qualified live; BlueCube qualified in saved-evidence replay after safe address shortening; Plunge stayed in review. All debugging/preview execution approximately $0.234. No final-check runs, PRs or Sheets writes |
| 2026-10-27 | All 16 development/anchor cases rerun on unchanged `480d5b6` | [Complete results](docs/benchmarks/cold-plunge-2026-10-27/development-rerun-results.md). Four qualified, eleven review, one retry; frozen-label coverage 4/6 versus 1/6 previously. BlueCube needs manual HQ review, leaving three clear HQ/office qualifications. Penguin picked a filter; LeisureCraft chose manufacturing over its captured address; Morozko timed out. 46 actor runs + 15 model calls, approximately $0.324 combined execution, all actor runs terminal. No final-check runs, exports, PRs or deployment |
| 2026-10-27 | Accessory-page ranking fix on `fix/product-page-selection` | Four new regressions reproduce Penguin's filter-selection bug and protect complete tubs with included accessories and explicit filter briefs. All 84 tests pass. Offline replay of 16 saved navigation traces changes only Penguin: cold-therapy collection replaces all-in-one filter; zero provider calls. Bounded live confirmation pending |
| 2026-10-27 | Page-selection live confirmation on `7c440a2` | [Results](docs/benchmarks/cold-plunge-2026-10-27/product-page-selection-results.md). Penguin review → qualified from Summit integrated-chiller/tub evidence; Redwood stays qualified. Eleven retained quotes matched saved sources. Six actor runs + two model calls, approximately $0.045 combined execution. All runs terminal, no exports or final-check cases. Full-cohort score preserved; HQ/location types and exact claim/role semantics remain next |
| 2026-10-27 | HQ/location context on `fix/headquarters-location-context` | Eight new regression tests; 92 offline tests pass. Eighteen saved decisions revalidated with zero provider calls: only BlueCube loses retained country evidence, typed as workshop. Five accepted observations across four other suppliers retain HQ/office support. Unlabeled LeisureCraft address stays unknown. Five of sixteen saved navigation routes change; live confirmation pending |
| 2026-10-27 | HQ/location-context live confirmation on `136cd51` | [Results](docs/benchmarks/cold-plunge-2026-10-27/headquarters-context-results.md). BlueCube correctly needs HQ review; Penguin/Sun Home remain qualified. LeisureCraft Contact establishes head office, but a compartment is incorrectly treated by the model as an included chiller: raw qualification held for manual product review. Twenty-eight retained quotes matched saved sources. Twelve actor runs + four model calls, approximately $0.096 combined execution; all runs terminal, no exports or final-check cases. Product/role claim semantics is next |
| 2026-10-27 | Component-evidence guard on `fix/complete-system-components` | 102 tests pass, including ten new regressions for actual included components, scope, negation, separate product cards, optional variants and trademarked product titles. Twenty-two saved results inspected; 21 analyses replayed with no providers. Only LeisureCraft loses an unsupported qualification; seven accepted observations across four other suppliers are preserved. Three existing review reasons become component-specific. Bounded live confirmation pending |
| 2026-10-27 | Component-evidence live confirmation and final passage checks | [Results](docs/benchmarks/cold-plunge-2026-10-27/component-evidence-results.md). On `7ff1170`, LeisureCraft review and Penguin/Sun Home/Coldture qualified. Final source-block/list refinement on `3b5952c` preserves all four live responses in offline replay. 104 tests pass; 26 saved results inspected, 25 replayed and ten accepted observations across four suppliers preserved. Twelve actor runs + four model calls, approximately $0.102 combined execution; all actor runs terminal, no exports or final-check cases. Exact role evidence remains next |
| 2026-10-27 | Exact role evidence on `fix/supplier-role-evidence` | Fifteen new regression tests reproduce unsupported qualification/exclusion and exact-role mistakes; 119 tests pass. Network-blocked replay: 26 saved results, 25 analyses, only Redwood's design-only Manufacturer and Sun Home's store/contact-only Brand owner qualifications become review. Eight other accepted observations across four suppliers are preserved. Five existing review reasons become role-specific; no exclusions introduced. Bounded live confirmation pending |
| 2026-10-27 | First role preview and bounded source-only quote repair | Live on `97b5a18`: Redwood returned no usable page evidence; Sun Home's store/contact quotes were rejected despite stronger source text. Source-only quote recovery now restores Sun Home in offline replay, preserving the guard and model role. Sixteen new tests; 120 pass. Replay covers 28 saved results/26 analyses/two fetch failures; only Redwood's earlier design-only Manufacturer qualification changes to review, ten other accepted observations across four suppliers preserved. Final controls and Redwood saved-page reanalysis pending |
| 2026-10-27 | Final role controls and saved-page reanalysis on `e0cb37e` | [Results](docs/benchmarks/cold-plunge-2026-10-27/role-evidence-results.md). Coldture Brand owner qualifies live; Penguin Manufacturer passes role checks but remains in HQ review. Redwood's saved-page model analysis correctly selects Brand owner, also HQ review; its failed fresh fetch remains recorded. Sun Home's final quote recovery qualifies in offline replay. 120 tests pass; 31 saved results/29 analyses/two fetch failures, only the earlier unsupported Redwood Manufacturer qualification changes status, eleven accepted observations across four suppliers preserved. Twenty final quotes verified, including six role quotes. Ten actor runs + four model calls, approximately $0.089; all actors terminal, no exports/final-check cases. Office/HQ evidence-basis consistency is next |
| 2026-10-28 | Office-country consistency on `fix/office-country-evidence` | Seventeen new regression methods; 137 tests pass. Source-verified country and location basis replace inconsistent model fields while preserving them for audit. Office remains distinct from global HQ; explicit HQ outranks offices, conflicts/unknown geography require review. Recovery uses existing pages only. Replayed 31 saved results/29 analyses/two fetch failures against `6559079`: only latest Penguin and Redwood HQ reviews qualify with US office evidence; eleven other accepted observations across four suppliers preserved. No provider calls in replay; final bounded previews pending |
| 2026-10-28 | Final office-country validation on `e4d32e2` | [Results](docs/benchmarks/cold-plunge-2026-10-27/office-country-results.md). Penguin qualifies live with US office evidence, Coldture retains Canadian HQ; Redwood qualifies in one new model call on saved pages using its US office. Earlier fetch failure preserved. All new model bases agree with verified location types. Twenty-four quotes verified; 137 tests pass; BlueCube's actual workshop pages remain insufficient. Six actor runs + three model calls, approximately $0.075, all actors terminal, no exports/final-check cases. Bounded fetch fallback is next |
| 2026-10-28 | Bounded fallback test preparation on `fix/bounded-fetch-fallback` | Existing actor datasets confirm Morozko/Redwood page-level timeouts (HTTP 500, failed crawl) inside terminal successful actors. Added opt-in runner flag and durable raw/browser fetch-attempt traces; production fetch logic unchanged. Six new regressions, 143 tests pass. Single-site live checks will retain four page attempts, no actor retries, $0.50 actor caps and a $3 exposure ceiling; no discovery/exports |
| 2026-10-28 | Bounded fallback validation on `a4cf388` | [Results](docs/benchmarks/cold-plunge-2026-10-27/fetch-fallback-results.md). Eight fresh raw pages returned across two previews; Redwood qualifies, Morozko needs role review. Both controlled historical-timeout + fresh-browser probes recover a homepage; no natural fallback or probe qualification claimed. Nine retained supplier quotes verified. Ten new actor runs + two model calls, browser usage $0.0047 and combined execution approximately $0.059. All actors terminal, no exports/final-check cases. Production backend remains unchanged and fallback opt-in; 143 tests pass |

Update the checkboxes and this log after each completed step. Add result/report paths, unresolved issues and the next action; leave incomplete work unchecked.
