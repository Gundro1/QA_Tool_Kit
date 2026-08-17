# Universal QA & Data Engineering Tool Kit

A universal, project-independent QA automation and data engineering toolkit for use with Claude Code, Antigravity, and any AI coding assistant.
Built by Azeez — works for any project (BisViews, PrimBooks, or enterprise data pipeline audits).

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
- `fast-dns-verifier.py` — Zero-cost 10ms OS DNS socket verifier for 1,000+ domains (bypasses Cloudflare 403/429 bot blocks)
- `brand-existence-checker.py` — Full dataset brand presence & B2B misrepresentation verification engine
- `fuzzy-dedup.py` — High-speed Levenshtein & token-sort fuzzy duplicate store listing detector
- `taxonomy-aligner.py` — Intra-franchise subcategory majority taxonomy auto-aligner
- `excel-ops.py` — Read, write, merge, deduplicate, and clean Excel/CSV workbooks
- `url-fetch.js` — Lightweight HTTP URL content fetcher (Markdown, JSON-LD, XML) without browser overhead
- `web-scraper.js` — Playwright store locator scraper for dynamic JS pages & JSON-LD data
- `pdf-print.py` — Headless Edge/Chrome HTML-to-PDF report printer
- `address-parser.py` — Postal code-to-province mapping & address standardizer
- `data-validator.py` — Pre-audit sanity checker (null counts, duplicates, encoding corruptions)

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
```

---

## 💻 CLI Usage Examples

### 1. Fast DNS Socket Domain Verifier (`fast-dns-verifier.py`)
```bash
# Verify 1,000+ web domains in seconds using zero-cost network sockets
python fast-dns-verifier.py "dataset.xlsx" --column "website" --workers 50
```

### 2. Brand Existence & Misrepresentation Checker (`brand-existence-checker.py`)
```bash
# Audit 100% of dataset franchise brands for physical presence vs. B2B misrepresentation
python brand-existence-checker.py "dataset.xlsx" --country CH --auditor Azeez
```

### 3. Fuzzy Duplicate Detector (`fuzzy-dedup.py`)
```bash
# Find typo duplicates (e.g. "McDonalds Zurich" vs "McDonald's Zürich")
python fuzzy-dedup.py "dataset.xlsx" --threshold 0.85
```

### 4. Intra-Franchise Taxonomy Aligner (`taxonomy-aligner.py`)
```bash
# Auto-correct minority subcategory misclassifications across franchise chains
python taxonomy-aligner.py "dataset.xlsx" --output "cleaned_dataset.xlsx"
```

### 5. Excel Operations (`excel-ops.py`)
```bash
# Read Excel/CSV into JSON statistics
python excel-ops.py read "data.xlsx" --stats

# Merge multiple Excel files and deduplicate by composite key
python excel-ops.py merge "v1.xlsx" "v2.xlsx" --dedup-key "franchise_name,address,postal_code" --output "v3.xlsx"
```

---

## 📜 License
MIT © Azeez
