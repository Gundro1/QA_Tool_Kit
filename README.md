# Universal QA & Data Engineering Tool Kit

A universal, project-independent QA automation and data engineering toolkit for use with Claude Code, Antigravity, and any AI coding assistant.
Built by Azeez — works for any project.

---

## ✨ Full Tool Arsenal (17 Tools)

### 🎨 Frontend & UI Testing
- `browser-test.js` — Screenshots, link checks, form interactions, mobile responsiveness views
- `web-search.js` — Lightweight web search scraper
- `accessibility-check.js` — WCAG accessibility automated audits via `axe-core`
- `visual-diff.js` — Pixel-by-pixel image comparison (`pixelmatch`)
- `report-generator.js` — HTML + PDF QA audit report generator

### 📊 Document & Visual Preview
- `docx_preview.py` — High-fidelity Word (`.docx`) to PNG page rendering via Office COM
- `xlsx_preview.py` — High-fidelity Excel (`.xlsx`) to PNG sheet rendering via Office COM

### ⚡ Data Pipeline & Smart Engineering
- `fast-dns-verifier.py` — Parallel DNS verifier for 1,000+ domains (bypasses Cloudflare 403/429 bot blocks); confirms failures over DNS-over-HTTPS so a flaky local resolver never marks a live site dead; optional `--http` probe
- `brand-existence-checker.py` — Keyword screening for B2B misrepresentation, hotel taxonomy and location-suffixed brand names (advisory: it does not verify presence online); rules configurable per country
- `fuzzy-dedup.py` — Fast fuzzy duplicate and spelling-variant detector that uses address and website as evidence (rapidfuzz)
- `taxonomy-aligner.py` — Intra-franchise subcategory consistency (classifies outliers before changing anything) and exact check against a reference taxonomy
- `excel-ops.py` — Read, write, merge, deduplicate, and clean Excel/CSV workbooks
- `url-fetch.js` — Lightweight HTTP URL content fetcher (Markdown, JSON-LD, XML) without browser overhead
- `web-scraper.js` — Playwright store locator scraper for dynamic JS pages & JSON-LD data
- `pdf-print.py` — Headless Edge/Chrome HTML-to-PDF report printer
- `address-parser.py` — Postal code-to-province mapping & address standardizer
- `data-validator.py` — Pre-audit sanity checker (null counts, duplicates, encoding corruptions, country-aware postal codes, franchise rules, website and address checks)
- `qa_common.py` — Shared loader and helpers for the data tools (every data sheet, real row numbers, normalisation, domains, logging)

---

## 📘 Comprehensive Architecture & Teaching Guides
- 🎓 [AI-ASSISTANT-GUIDE.md](AI-ASSISTANT-GUIDE.md) — Comprehensive guide on configuring any AI Assistant (Claude Code, Cursor, Copilot) with anti-hallucination habits and tools.
- 📐 [TOOLKIT-GAP-ANALYSIS.md](TOOLKIT-GAP-ANALYSIS.md) — Architectural breakdown of Frontend UI QA vs. Data Pipeline QA capabilities.

---

## 🚀 Quickstart & Setup

```bash
# 1. Clone Repository
git clone https://github.com/Gundro1/QA_Tool_Kit.git
cd QA_Tool_Kit

# 2. Install Node.js Dependencies
npm install
npx playwright install chromium

# 3. Install Python Dependencies
pip install -r requirements.txt

# 4. (Contributors) Run the tests
pip install -r requirements-dev.txt
python -m pytest tests
```

---

## 🧪 Data tools: shared behaviour

- **Every data sheet is checked.** A workbook with `Franchise` and `Solo` sheets is read in full; companion sheets without the data columns (`Change log`, `Issues log`) are skipped and logged. `--sheet NAME` checks one sheet.
- **Row numbers are real Excel rows**, reported as `Sheet!row`.
- **`--output file.csv|json`** writes every finding, not just the console sample.
- **Logs go to stderr** with per-stage timings (`-v` for debug, `-q` for warnings only); results stay on stdout.
- **Large datasets:** with `python-calamine` and `rapidfuzz` installed (both in `requirements.txt`), 67,533 rows take about 12 s in `data-validator.py` and 16 s in `fuzzy-dedup.py`. Without them the tools still run, more slowly.

[docs/FIELD-ISSUES.md](docs/FIELD-ISSUES.md) lists the false positives, gaps and bugs found on real datasets, and what was changed for each.

---

## 💻 CLI Usage Examples

### 1. Fast DNS Socket Domain Verifier (`fast-dns-verifier.py`)
```bash
# Verify 1,000+ web domains in seconds using zero-cost network sockets
python fast-dns-verifier.py "dataset.xlsx" --column "website" --workers 50

# Also probe each live site over HTTP and save every domain with its rows
python fast-dns-verifier.py "dataset.xlsx" --http --output domains.csv
```
Statuses: `resolves`, `nxdomain` (confirmed dead), `no_address`, `unknown` (could not check; **not** evidence of a dead site), `social_listing`.

### 2. Brand Existence & Misrepresentation Checker (`brand-existence-checker.py`)
```bash
# Screen every franchise brand for B2B misrepresentation and naming problems
python brand-existence-checker.py "dataset.xlsx" --country CH --auditor Azeez

# Other countries: override the keyword lists and choose where the report goes
python brand-existence-checker.py "dataset.xlsx" --country SI --rules si_rules.json --output-dir reports/
```
`No Flags` means no rule matched; presence is not checked online. `--rules` takes a JSON object with any of `b2b_keywords`, `hotel_brands`, `hotel_words`, `accommodation_words`, `edit_instructions`.

### 3. Fuzzy Duplicate Detector (`fuzzy-dedup.py`)
```bash
# Find typo duplicates (e.g. "McDonalds Zurich" vs "McDonald's Zürich")
python fuzzy-dedup.py "dataset.xlsx" --threshold 0.85 --output pairs.csv
```
Tiers: `same_address_duplicate` (likely one branch listed twice), `spelling_variant` (`Bags & More` / `Bags&More`, `X Ltd.` / `X`), `similar_name` (review). Pairs with different website domains, or one website at different addresses, are counted as suppressed (`--show-suppressed` lists them; `--keep-different-domains` reports them).

### 4. Intra-Franchise Taxonomy Aligner (`taxonomy-aligner.py`)
```bash
# Auto-correct minority subcategory misclassifications across franchise chains
python taxonomy-aligner.py "dataset.xlsx" --output "cleaned_dataset.xlsx"

# Keep intentionally mixed-format brands untouched and check against the official taxonomy
python taxonomy-aligner.py "dataset.xlsx" --allowlist mixed_brands.txt --taxonomy categories.xlsx --report outliers.csv
```
Only `realign` rows (clear majority, same storefront name) are changed; `format_variant`, `mixed_review` and `allowlisted` rows are reported for review. `--output` keeps every sheet and format of the input.

### 5. Data Validator (`data-validator.py`)
```bash
# Duplicates on a key, postal codes per row country, franchise and website rules
python data-validator.py "dataset.xlsx" --dedup-key "business_name,address,city" --output findings.csv
```
The postal format comes from each row's `country_code` (or `--country`). Franchise checks run when `franchise_flag` and `franchise_name` exist (`--flag-values Y,N`).

### 6. Excel Operations (`excel-ops.py`)
```bash
# Read Excel/CSV into JSON statistics
python excel-ops.py read "data.xlsx" --stats

# Merge multiple Excel files and deduplicate by composite key
python excel-ops.py merge "v1.xlsx" "v2.xlsx" --dedup-key "franchise_name,address,postal_code" --output "v3.xlsx"
```

---

## 📜 License
MIT © Azeez
