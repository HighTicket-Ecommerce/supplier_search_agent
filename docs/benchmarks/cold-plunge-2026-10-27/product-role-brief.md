# Requested-product role follow-up — 2026-10-28

Problem: saved Penguin decisions qualify the company as a Manufacturer of a complete cold plunge using role statements about making chillers. Product evidence establishes a complete Summit system sold on the site; it does not establish who manufactures that whole product or owns its brand.

This first guard covers **complete cold-plunge/ice-bath systems requiring a tub and chiller**, for Manufacturer and Brand owner roles. Company role, product match/configuration and role for the requested category remain separate facts. Other product categories and Distributor relationships explicitly return `not_required` for this new guard; their existing checks remain in place. It does not verify named-model aliases, legal brand ownership or brand authorization.

The company role must already pass its exact-role/source checks. The new guard then requires a company-attributed production or own-product creation statement about cold plunges/ice baths. Component manufacture/design, uses of components in systems, selling another product, another company's production and nearby catalogue cards cannot fill that relationship. Truncated contexts cannot establish it. Missing linkage leads to review, with company role/product facts preserved and requested-product role Unknown.

At most one additional literal role quote can be recovered from captured pages, scanning at most 96 candidate windows per page. It must pass the same role attribution checks and name the primary category. No new model/provider call or role reclassification occurs. Literal physical-product “makes” statements can support Brand owner under the existing own-creation policy; this does not establish manufacturing. Ice-bath wording is recognized alongside cold plunges.

Fifteen new regressions include literal Penguin paragraph excerpts, primary production/creation controls, component/purpose/other-company cases, negation, source blocks, recovery bounds and scope limits. Component-only synthetic tests now supply an explicit category role to isolate inclusion checks. The old thin Coldture fixture preserves its historical expected outcome but adds a current-policy review expectation: its generic brand statement and vendor data alone do not establish the new role link. Frozen benchmark labels/brief and historical reports remain unchanged.

Before live confirmation, run the complete offline suite and a network-blocked before/after replay against `01065cd`, restricted to saved development/anchor cases. Inspect every changed qualification; do not count repeated observations as new companies or use them as an independent accuracy set.

Live confirmation: **Penguin and Coldture**, supplied seeds, Manufacturer/Brand owner only, preview-only, no discovery/Shopping/catalogue analysis/browser fallback. Three page attempts per company, six total, twenty external calls, 600 seconds, $4 conservative exposure and $0.50 cap per actor. Use an isolated job database and a fresh round. Save raw model analyses, source hashes and fetch traces; verify quotes, terminal runs and charges. Expected behavior is Penguin review unless fresh primary-role evidence exists, with Coldture as a positive control when explicit own-creation evidence is captured. Missing/failing collection must remain an execution limitation, not a negative supplier label.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/benchmarks/cold-plunge-2026-10-27/run_evidence_check.py --cases dev-penguin anchor-coldture --round product-role-1 --pages-per-site 3 --budget 4 --primary-roles-only
```
