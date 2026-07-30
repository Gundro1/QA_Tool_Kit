# Universal QA & Data Engineering Tool Kit

A universal, project-independent QA automation and data engineering toolkit for use with Claude Code, Antigravity, and any AI coding assistant.
Built by Azeez — works for any project (BisViews, PrimBooks, or enterprise data pipeline audits).

---

## ✨ Full Tool Arsenal (13 Tools)

### 🎨 Frontend & UI Testing
- `browser-test.js` — Screenshots, link checks, form interactions, mobile responsiveness views
- `web-search.js` — Lightweight web search scraper
- `accessibility-check.js` — WCAG accessibility automated audits via `axe-core`
- `visual-diff.js` — Pixel-by-pixel image comparison (`pixelmatch`)
- `report-generator.js` — HTML + PDF QA audit report generator

### 📊 Document & Visual Preview
- `docx_preview.py` — High-fidelity Word (`.docx`) to PNG page rendering via Office COM
- `xlsx_preview.py` — High-fidelity Excel (`.xlsx`) to PNG sheet rendering via Office COM

### ⚡ Data Pipeline & Engineering (NEW)
- `excel-ops.py` — Read, write, merge, deduplicate, and clean Excel/CSV workbooks
- `url-fetch.js` — Lightweight HTTP URL content fetcher (Markdown, JSON-LD, XML) without browser overhead
- `web-scraper.js` — Playwright store locator scraper for dynamic JS pages & JSON-LD data
- `pdf-print.py` — Headless Edge/Chrome HTML-to-PDF report printer
- `address-parser.py` — Belgian/general postal code-to-province mapping & address standardizer
- `data-validator.py` — Pre-audit sanity checker (null counts, duplicates, encoding corruptions)

---

## 📘 Comprehensive Architecture & Teaching Guide
For an in-depth educational guide on the difference between Frontend UI QA and Data Pipeline QA, read:
👉 **[TOOLKIT-GAP-ANALYSIS.md](./TOOLKIT-GAP-ANALYSIS.md)**

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

### 1. Excel Operations (`excel-ops.py`)
```bash
# Read Excel/CSV into JSON statistics
python excel-ops.py read "data.xlsx" --stats

# Merge multiple Excel files and deduplicate by composite key
python excel-ops.py merge "v1.xlsx" "v2.xlsx" --dedup-key "franchise_name,address,postal_code" --output "v3.xlsx"

# Clean strings (trim whitespace, titlecase addresses)
python excel-ops.py clean "data.xlsx" --trim --title-case "address,city" --output "cleaned.xlsx"
```

### 2. Lightweight HTTP Fetch (`url-fetch.js`)
```bash
# Fetch web page text as clean Markdown (no browser needed)
node url-fetch.js --url "https://example.com" --format markdown

# Extract JSON-LD structured data
node url-fetch.js --url "https://example.com/store" --format jsonld --output data.json
```

### 3. Store Locator Web Scraper (`web-scraper.js`)
```bash
# Extract dynamic store locator cards using Playwright
node web-scraper.js --url "https://brand.be/stores" --selector "div.store-card" --fields "name:h3,address:.addr,phone:.tel" --output stores.json

# Extract schema JSON-LD store markers
node web-scraper.js --url "https://brand.be/locations" --strategy json-ld --output stores.json
```

### 4. Headless PDF Generator (`pdf-print.py`)
```bash
# Print HTML report to A4 PDF using MS Edge/Chrome
python pdf-print.py "audit.html" --output "audit.pdf"
```

### 5. Address Parser & Province Mapper (`address-parser.py`)
```bash
# Lookup Belgian province from 4-digit postal code
python address-parser.py --country BE --postal 1000
# Output: {"postal_code": "1000", "country": "BE", "is_valid": true, "province": "Brussels-Capital Region"}
```

### 6. Data Integrity Pre-Audit Checker (`data-validator.py`)
```bash
# Check null counts, fuzzy duplicates, and encoding issues in dataset
python data-validator.py "dataset.xlsx" --dedup-key "name,address"
```

---

## 🛠 Custom Claude Code Slash Commands
Copy `.claude/commands/` to your home directory (`~/.claude/commands/`) to get instant access in Claude Code:
- `/qa-test <url>` — Execute browser UI testing audit
- `/generate-report <file>` — Generate HTML & PDF reports
- `/search-web <query>` — Search the web
- `/excel-merge <files>` — Programmatically merge Excel datasets

---

## 📜 License
MIT © Azeez
