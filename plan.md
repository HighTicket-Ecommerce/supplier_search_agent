# Supplier research agent — step-by-step plan

Updated: 2026-10-26

**Goal:** find more relevant suppliers, verify the requested products and company identities, and produce useful evidence with predictable research costs.

**Current phase:** securing and preserving the baseline before the benchmark. The offline suite passes (48 tests). Pull requests are on hold, so each change is prepared and tested on its own local branch. The next research task is the 20–30-site cold-plunge benchmark (Step 5). Broader research accuracy is still unmeasured.

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

- [ ] Write down the exact brief: permitted company roles, exclusions and required product contents. A complete system must include a tub and chiller, or an integrated chiller. Dealer-program evidence is useful but optional.
- [ ] Select 20–30 sites covering genuine suppliers, accessories/components, installation services, unrelated businesses and ambiguous identities.
- [ ] Keep previously tested examples such as Homecraft and Coldture as regression anchors; identify them separately from new evaluation sites.
- [ ] Before reading agent decisions, manually label each site's product fit, company role, headquarters evidence and expected master-list relationship (existing, related domain, name only, same name on a different website, or unmatched). Save official URLs, quotes and review dates. Missing evidence stays unknown.
- [ ] Split new sites into a development group and an untouched final-check group. Freeze the labels and brief before running the agent.
- [ ] Save a versioned benchmark manifest and labels. Keep private source lists and contacts out of public fixtures.

**Done when:** each case has an evidence-backed expected outcome, or an explicit unknown/review label. A master CSV country field alone is insufficient headquarters evidence.

## Step 6 — test qualification on supplied sites

- [ ] Record the merged commit used for benchmark runs so results can be reproduced.
- [ ] Run the benchmark sites in small, seed-only batches with additional discovery disabled and preview-only enabled.
- [ ] Use an isolated evaluation job database; preserve existing application jobs and source files.
- [ ] Keep page, call, runtime and provider charge caps enabled. Record the settings before each batch, including any changes needed after a limit stops a job.
- [ ] Test company qualification first, then enable catalogue analysis on selected product/variant cases to measure its additional benefit and cost.
- [ ] Save job IDs, request settings, source timestamps/hashes, actor run/build/dataset IDs, model identity, decisions and reasons.
- [ ] Record stopped, limited, unprocessed and extraction-failed cases separately. They must not silently become negative supplier labels.

**Done when:** every selected case has either a saved decision or a documented execution limitation. No Sheets writes are needed for this phase.

## Step 7 — test discovery separately

- [ ] Run the same brief through country-targeted discovery without supplying the benchmark sites as seeds.
- [ ] Review proposed official sites and distinguish manufacturers/brand owners/distributors from retailers, marketplaces and unrelated businesses.
- [ ] Compare results with the independently labelled known-positive sites, and manually verify any additional discoveries.
- [ ] Check every candidate against the master reference. Unmatched names are research candidates, not confirmed new suppliers.
- [ ] Review the skipped list: sites skipped as already known and sites blocked as retailers or marketplaces.
- [ ] Test directory-to-official-site verification on a small sample in a relevant category. Keep distributor labels and verified suppliers separate.

**Done when:** there is a manually reviewed shortlist, an explanation for missed known suppliers and a list of duplicate/ambiguous identities. Coverage of this benchmark is not recall across the whole web.

## Step 8 — score the results

- [ ] Report qualified precision: manually confirmed eligible suppliers / all automatically qualified suppliers.
- [ ] Report known-positive coverage: automatically qualified known-positive sites / all labelled eligible sites actually evaluated. Also report how much of the planned cohort was evaluated.
- [ ] Count eligible suppliers left in review, incorrect exclusions, extraction failures, duplicate qualified companies and uncertain master matches.
- [ ] Compare each candidate's master-list status with its label: wrong merges, labelled master suppliers reported as new, and candidates skipped or blocked by mistake.
- [ ] Check product/variant relevance, literal source quotes, explicit currencies and price-sample coverage.
- [ ] Record elapsed time, reported actor charges, estimated model cost, conservative reservations and cost per manually confirmed qualified supplier as distinct values.
- [ ] Show counts alongside percentages and score the untouched final-check group separately.

Initial quality targets to assess on the labelled cohort:

| Check | Target |
| --- | --- |
| Qualified precision | At least 90%; always show the underlying counts |
| Coverage of labelled eligible sites | At least 80%; report missing/limited cases separately |
| Accepted suppliers supported only by accessory/service evidence | Zero |
| Duplicate qualified companies | Zero unresolved duplicates |
| Accepted evidence and price observations | Verified quotes, source URLs, explicit currency and honest coverage labels |
| Master-list comparison | Zero wrong merges; every labelled master supplier flagged; zero candidates dropped without a reason |
| Source-list edits or Sheets writes during evaluation | Zero |

These are initial acceptance targets, not measured results or statistical guarantees. A small, deliberately mixed benchmark does not establish production-wide accuracy.

**Done when:** a results report explains both successful cases and failures, with an evidence-backed shortlist and observed costs.

## Step 9 — fix the largest observed problems

- [ ] Rank failures by their effect on supplier quality and research effort.
- [ ] Improve headquarters/source-page retrieval if legitimate suppliers repeatedly lack usable evidence. Page selection and headquarters excerpts in `backend/web_fetcher.py` currently rely on fixed words (`sauna`, `plunge`, `fireplace`, `heater`, `Surrey`); make them follow the brief before adding categories.
- [ ] Add evidence-backed aliases and parent/brand relationships where identity mismatches recur; retain separate identities unless a relationship is verified.
- [ ] Improve catalogue coverage or add platform/directory adapters where current extraction misses relevant products or brands.
- [ ] Add regression cases for each concrete failure and rerun affected checks.
- [ ] Measure changes on development cases, then run the untouched final-check group. Once a final-check case is used to tune a fix, treat it as development data for subsequent evaluations.

**Done when:** the targeted failures improve without introducing new incorrect qualifications, duplicate identities or unsupported price claims.

## Step 10 — use the workflow for regular research

- [ ] Publish a short operating guide: brief → discover/import → compare → verify → review → export selected results.
- [ ] Review the final shortlist and explicitly select any Google Sheets export.
- [ ] Save the evaluated implementation and update this plan with the report and commit references.
- [ ] Prioritize additional categories and automatic job resumption after the evaluated workflow is reliable. Resumption must avoid repeating uncertain billable operations or exports.

**Done when:** the workflow produces a useful, reviewed shortlist consistently, with traceable evidence and known costs.

## Progress log

| Date | Work | Result / evidence |
| --- | --- | --- |
| 2026-10-14 | Feature upgrades and initial controlled previews | [Validation report](docs/validation-2026-10-14.md); 48 tests passed at that time |
| 2026-10-26 | Added this tracking plan and reran the offline suite | 48 tests passed; no new paid run started |
| 2026-10-26 | Security review of the October incidents | No compromised packages or committed credentials. Exposed: public backend without authentication, Node 22.22.3/23.10.0, `certifi` and `pip` in `.venv` that still trust the eMudhra roots, advisories in Starlette, Streamlit, requests and python-dotenv |
| 2026-10-26 | Master-list comparison profiled on 2,000 real master rows | Known supplier on a subdomain with " Inc." added to its name: 1,997 reported as unmatched (new). Same website with " Inc.": 1,997 name conflicts. Same name on an unrelated website and on a sub-site get the same label. `fellowes.com` and `championtarget.com` blocked as retailers. Skipped candidates leave no record |
| 2026-10-26 | Plan reorganized; baseline committed locally on `feat/supplier-research-controls` | 48 tests passed; branch renamed from `codex/`; pull request pending because PRs are on hold |
| 2026-10-26 | Step 2 on local branch `fix/api-and-export-safety` (based on the baseline commit `f1e5b38`) | 52 tests passed (4 new: API key before body parsing, 503 without a configured key, formula-safe CSV, UI password and rejected-key message). Railway variables still to set |
| 2026-10-27 | Step 3 on local branch `fix/dependency-security` | 53 tests passed on upgraded packages; OpenAI schemas unchanged; `pip-audit` clean. CI workflow added (read-only, hash-pinned actions). Unused Apify SDK, tenacity, BeautifulSoup and three unused files removed |
| 2026-10-27 | Step 4 on local branch `fix/master-matching` | 56 tests passed. 2,000-row profile: shop-host + " Inc." → 2,000 `related_domain_needs_verification`; same host + " Inc." → 1,996 existing (was 1,997 name conflicts); same name on another site → 1,998 `name_match_different_website`. `fellowes.com` and `championtarget.com` no longer blocked. Four remaining blocked master hosts are actual retailers |

Update the checkboxes and this log after each completed step. Add result/report paths, unresolved issues and the next action; leave incomplete work unchecked.
