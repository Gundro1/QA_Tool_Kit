# QA Toolkit Gap Analysis & Capabilities Roadmap

## Executive Overview
This document provides a comprehensive comparison between standard web UI testing tools and the data engineering capabilities required for enterprise-grade data audits (such as the BisViews national franchise audits). It serves as an architectural blueprint and educational guide for QA engineers, data auditors, and AI assistant prompt engineers.

---

## 1. The Core Functional Difference

Modern QA automation spans two distinct domains:

```
┌───────────────────────────────────────────────────────────────────────┐
│                          QA AUTOMATION HUB                            │
├───────────────────────────────────┬───────────────────────────────────┤
│        1. FRONTEND / UI QA        │       2. DATA PIPELINE QA         │
│   (Browser-Test, Accessibility)   │   (Scraping, ETL, Data Auditing)  │
├───────────────────────────────────┼───────────────────────────────────┤
│ • Page visual regression          │ • Store locator web scraping      │
│ • User flow verification (login)  │ • Multi-source dataset merging    │
│ • DOM element accessibility       │ • Geo-integrity & address parsing │
│ • Cross-device responsiveness     │ • Anomaly & fuzzy duplicate audit │
└───────────────────────────────────┴───────────────────────────────────┘
```

A complete QA toolkit must bridge **both domains** so that AI agents and human auditors can seamlessly scrape, transform, validate, and publish reports without manual intervention.

---

## 2. Capability Matrix Comparison

| Capability Domain | Baseline UI Toolkit | Advanced Data Pipeline Toolkit | Educational Context & Use Cases |
| :--- | :---: | :---: | :--- |
| **Browser UI Testing** | ✅ | ✅ | End-to-end user flows, button clicks, screenshot capture |
| **Accessibility (WCAG)** | ✅ | ✅ | axe-core automated page accessibility audits |
| **Visual Regression** | ✅ | ✅ | Pixelmatch image comparison (baseline vs current) |
| **Document Preview** | ✅ | ✅ | Office COM automation (DOCX/XLSX to PNG rendering) |
| **Lightweight Web Fetch** | ❌ | ✅ | Fast HTTP URL content/JSON fetch without browser overhead |
| **Store Locator Scraping** | ❌ | ✅ | Extracting structured branch locations from JS store locators |
| **Excel ETL Operations** | ❌ | ✅ | Programmatic reading, merging, deduplication, and cleaning |
| **Address Normalization** | ❌ | ✅ | Postal code-to-province mapping & street format validation |
| **Data Integrity Auditing** | ❌ | ✅ | Multi-rule data verification, null detection, taxonomy check |
| **Headless PDF Printing** | ❌ | ✅ | Native Edge/Chrome HTML-to-PDF conversion |

---

## 3. Detailed Tool Specifications to Add

### Tool 1: `excel-ops.py` (Excel ETL & Merging Engine)
- **Problem:** Excel data cannot be modified or merged programmatically without custom code.
- **Solution:** A CLI tool to read Excel/CSV into JSON, merge multiple workbooks, deduplicate rows by custom composite keys, clean strings (trim, title case), and export formatted Excel workbooks.
- **CLI Commands:**
  - `python excel-ops.py read data.xlsx --sheet Franchise --format json`
  - `python excel-ops.py merge file1.xlsx file2.xlsx --dedup-key "franchise_name,address,postal_code" --output v3.xlsx`
  - `python excel-ops.py clean data.xlsx --trim --title-case address,city --output clean.xlsx`

### Tool 2: `url-fetch.js` (Lightweight HTTP Content Extractor)
- **Problem:** Launching a full Playwright browser to fetch text or JSON from simple web pages is slow and resource-heavy.
- **Solution:** A lightweight Node.js fetch tool using `node-fetch`, `cheerio`, and `turndown` to instantly download web pages, convert HTML to clean markdown, extract metadata, or parse XML sitemaps.
- **CLI Commands:**
  - `node url-fetch.js --url "https://example.com" --format markdown`
  - `node url-fetch.js --url "https://example.com/sitemap.xml" --format json`

### Tool 3: `web-scraper.js` (Structured Store Locator Scraper)
- **Problem:** Chain stores and franchise brand locations are usually rendered dynamically via JavaScript or API feeds.
- **Solution:** A Playwright-powered CLI scraper capable of handling dynamic rendering, pagination, table extraction, card layouts, and JSON-LD embedded data.
- **CLI Commands:**
  - `node web-scraper.js --url "https://brand.be/stores" --strategy json-ld --output stores.json`
  - `node web-scraper.js --url "https://brand.be/locator" --selector "div.store-card" --fields "name:h3,address:.addr,phone:.tel"`

### Tool 4: `pdf-print.py` (Headless Edge/Chrome PDF Compiler)
- **Problem:** HTML QA reports need to be converted to stakeholder-ready PDF documents without layout breakage.
- **Solution:** Direct invocation of Microsoft Edge or Chrome in `--headless --print-to-pdf` mode to generate pixel-perfect A4 PDFs.
- **CLI Commands:**
  - `python pdf-print.py input.html --output report.pdf --paper A4`

### Tool 5: `address-parser.py` (Geographic Normalization & Postal Mapping)
- **Problem:** Address strings from scraped websites often lack province/region details or contain concatenated postal codes.
- **Solution:** Country-configurable postal code-to-province mapping engine and street address formatter.
- **CLI Commands:**
  - `python address-parser.py --country BE --postal 1000` (Returns Brussels-Capital Region)

### Tool 6: `data-validator.py` (Quick Dataset Sanity Checker)
- **Problem:** Engineers need instant sanity checks on raw datasets before running heavy audit scripts.
- **Solution:** Quick CLI checker for null counts, fuzzy duplicates, character encoding corruptions (mojibake), and schema validation.
- **CLI Commands:**
  - `python data-validator.py dataset.xlsx --checks nulls,dupes,encoding`

---

## 4. Implementation & Upgrade Roadmap

```
Phase 1: Dependencies & Gap Documentation (Completed)
  ├── Add TOOLKIT-GAP-ANALYSIS.md
  ├── Update requirements.txt (pandas, openpyxl, requests, bs4)
  └── Update package.json (node-fetch, cheerio, turndown)

Phase 2: Data Pipeline & HTTP Engines
  ├── Create excel-ops.py
  ├── Create url-fetch.js
  └── Create pdf-print.py

Phase 3: Scraping & Address Parsing Engines
  ├── Create web-scraper.js
  ├── Create address-parser.py
  └── Create data-validator.py

Phase 4: Integration & Custom Slash Commands
  ├── Update README.md with comprehensive CLI examples
  └── Update .claude/commands/ for AI Assistant Slash commands
```

---
*Created by Azeez — Universal QA & Data Engineering Tool Kit.*
