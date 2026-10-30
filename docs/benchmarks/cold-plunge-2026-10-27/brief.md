# Cold-plunge benchmark brief

Frozen: 2026-10-27  
Code under test: local branch `fix/master-matching` (commit recorded at run time).  
Labels were written from official pages before any agent run.

## Request

Find companies that supply **complete cold-plunge systems**, with headquarters in the **United States or Canada**.

A complete system is a plunge tub **and** a chiller, or a tub with an **integrated** chiller. A tub that needs bagged ice, a chiller sold without a tub, filters, chemicals, covers, or installation labour does not establish a complete system.

## Allowed company roles

Manufacturer, brand owner, distributor.

Retailers, marketplaces, media, and installation-only businesses are outside the brief.

## Exclusions

Replacement filters, assembly or electrical services, chillers sold without a tub, inflatable or stock-tank tubs without a chiller, sauna heaters, hot tubs, swim spas, whole-body cryotherapy chambers, and unrelated goods (grills, audio, furniture).

Dealer-program evidence is useful and optional. It never substitutes for product, role, or headquarters evidence.

## Headquarters

Needs an explicit based-in / headquarters / office-address statement on an official page. Manufacturing, “made in”, shipping markets, currency, and the master-list country field are not enough.

## How to read a label

- `eligible`: this company belongs on a reviewed shortlist for the brief, even if the agent should leave it in review because a required quote is missing from the fetched pages.
- `expected_status`: what a correct agent should return from the pages it is likely to fetch (`qualified`, `review`, `excluded`, `retry_needed`).
- `master_relationship`: existing, related_domain, name_only, name_different_website, unmatched.
- Missing evidence stays `unknown`.

Homecraft and Coldture are **regression anchors**. They are scored separately from new sites. New sites are split into a **development** group and an untouched **final-check** group. Do not use a final-check case to tune a fix.

## Run settings (qualification only)

Seed-only, discovery off, preview-only, no Shopify catalogue, no browser fallback, no Sheets export. Isolated job database under `var/eval/`. Shared page, call, runtime and cost caps stay on.
