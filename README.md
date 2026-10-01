# Universal QA & Data Engineering Tool Kit (v2.0)

A universal, project-independent QA automation and data engineering toolkit for use with Claude Code, Antigravity, and any AI coding assistant.
Built by Azeez — works for any project (web apps, data pipelines, REST APIs, or Excel audits).

---

## ✨ Enterprise Architecture & Tools

### 🌐 Playwright Automation & Test Runner (NEW in v2.0)
- `playwright.config.ts` — Cross-browser Playwright test configuration (Chromium, Firefox, WebKit, Mobile viewports)
- `fixtures/base.fixture.ts` — Dependency-injected base fixture pattern for Playwright tests
- `specs/smoke.spec.ts` — Universal web smoke test suite (HTTP 200, title, console errors, broken images, internal links, mobile responsiveness)
- `specs/api-health.spec.ts` — Universal REST API health & performance test spec

### 🏛️ Core Architecture & Foundation (NEW in v2.0)
- `config/env.py` — Centralized, typed environment configuration (`QA_BASE_URL`, `QA_API_BASE_URL`, timeouts, output paths)
- `core/base_api_client.py` — Generic `BaseApiClient` stdlib REST wrapper with retries, timing (`elapsed_ms`), and typed `ApiResponse`
- `core/builders.py` — Fluent `Builder` and `TypedBuilder` test-data construction patterns
- `conftest.py` — Shared `pytest` fixtures for Python QA tools
- `.github/workflows/ci.yml` — Automated GitHub Actions CI pipeline for Python tests and Playwright smoke tests
- `AGENTS.md` — AI agent governance specification (5-role division, repair philosophy hierarchy, pre-commit checklist)

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
- `fast-dns-verifier.py` — Parallel DNS verifier for 1,000+ domains (bypasses Cloudflare 403/429 bot blocks)
- `brand-existence-checker.py` — Keyword screening for B2B misrepresentation, hotel taxonomy and location-suffixed brand names
- `fuzzy-dedup.py` — Fast fuzzy duplicate and spelling-variant detector using address and website evidence (`rapidfuzz`)
- `taxonomy-aligner.py` — Intra-franchise subcategory consistency aligner
- `excel-ops.py` — Read, write, merge, deduplicate, and clean Excel/CSV workbooks
- `url-fetch.js` — Lightweight HTTP URL content fetcher (Markdown, JSON-LD, XML) without browser overhead
- `web-scraper.js` — Playwright store locator scraper for dynamic JS pages & JSON-LD data
- `pdf-print.py` — Headless Edge/Chrome HTML-to-PDF report printer
- `address-parser.py` — Postal code-to-province mapping & address standardizer
- `data-validator.py` — Pre-audit sanity checker (null counts, duplicates, encoding corruptions)
- `qa_common.py` — Shared loader and helpers for all data tools

---

## 📘 Comprehensive Architecture & Teaching Guides
- 🎓 [AI-ASSISTANT-GUIDE.md](AI-ASSISTANT-GUIDE.md) — Comprehensive guide on configuring any AI Assistant (Claude Code, Cursor, Copilot) with anti-hallucination habits and tools.
- 🏛️ [AGENTS.md](AGENTS.md) — AI Agent Governance rules, repair philosophy, and pre-commit review checklist.
- 📐 [TOOLKIT-GAP-ANALYSIS.md](TOOLKIT-GAP-ANALYSIS.md) — Architectural breakdown of Frontend UI QA vs. Data Pipeline QA capabilities.

---

## 🚀 Quickstart & Setup

```bash
# 1. Clone Repository
git clone https://github.com/Gundro1/QA_Tool_Kit.git
cd QA_Tool_Kit

# 2. Install Node.js Dependencies & Browsers
npm install
npx playwright install chromium

# 3. Install Python Dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 💻 Running Tests & CLI Tools

### Playwright Web & API Automation
```bash
# Target any site or API via environment variables
QA_BASE_URL="https://example.com" npx playwright test

# Run API Health tests
QA_API_BASE_URL="https://api.example.com" npm run test:api

# Run UI Mode / Headed
npm run test:ui
```

### Python Data Tools Test Suite
```bash
# Run pytest on core modules (API client, builders, env config)
python -m pytest tests/ -v
```

### Data Engineering CLI Tools
```bash
# Verify 1,000+ web domains in seconds using zero-cost network sockets
python fast-dns-verifier.py "dataset.xlsx" --column "website" --workers 50

# Screen every franchise brand for B2B misrepresentation and naming problems
python brand-existence-checker.py "dataset.xlsx" --country CH --auditor Azeez

# Find typo duplicates (e.g. "McDonalds Zurich" vs "McDonald's Zürich")
python fuzzy-dedup.py "dataset.xlsx" --threshold 0.85

# Auto-correct minority subcategory misclassifications across franchise chains
python taxonomy-aligner.py "dataset.xlsx" --output "cleaned_dataset.xlsx"

# Duplicates on a key, postal codes per row country, franchise and website rules
python data-validator.py "dataset.xlsx" --dedup-key "business_name,address,city"

# Read Excel/CSV into JSON statistics
python excel-ops.py read "data.xlsx" --stats
```

---

## 📜 License
MIT © Azeez
