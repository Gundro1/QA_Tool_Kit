# AGENTS.md — AI Agent Governance for QA Toolkit

> This document defines the rules for any AI agent (human or automated) working in this repository. Every contributor — whether a person, Copilot, Claude Code, or Antigravity — follows these rules.

---

## Stack
- **Python 3.10+** — Data validation, Excel ops, address parsing, DNS verification
- **Node 20+ / Playwright** — Browser testing, accessibility, visual regression, web scraping
- **Test runners:** pytest (Python), @playwright/test (TypeScript)
- **CI:** GitHub Actions

---

## Folder Structure

```
QA_Tool_Kit/
├── AGENTS.md              # This file — rules for all contributors
├── AI-ASSISTANT-GUIDE.md  # Teaching guide for configuring AI assistants
├── config/                # Centralized environment config (env.py)
├── core/                  # Shared foundation: BaseApiClient, Builder, types
├── fixtures/              # Playwright test fixtures (base.fixture.ts)
├── specs/                 # Playwright test specs (smoke.spec.ts, api-health.spec.ts)
├── tests/                 # Python pytest test files
├── docs/                  # Documentation and field issue logs
├── .github/workflows/     # CI pipeline
│
├── browser-test.js        # UI: screenshots, links, forms, mobile
├── accessibility-check.js # UI: WCAG accessibility audits (axe-core)
├── visual-diff.js         # UI: pixel comparison (pixelmatch)
├── report-generator.js    # Reporting: HTML/PDF audit reports
├── url-fetch.js           # Data: lightweight HTTP content fetch
├── web-scraper.js         # Data: JS-rendered page scraping
├── web-search.js          # Data: web search scraping
│
├── data-validator.py      # Data: integrity checks, dedup, encoding
├── fuzzy-dedup.py         # Data: fuzzy duplicate detection (rapidfuzz)
├── taxonomy-aligner.py    # Data: subcategory consistency alignment
├── brand-existence-checker.py  # Data: brand misrepresentation screening
├── fast-dns-verifier.py   # Data: parallel domain verification
├── excel-ops.py           # Data: read/write/merge/clean Excel
├── address-parser.py      # Data: postal-to-province mapping
├── pdf-print.py           # Reporting: HTML-to-PDF via headless browser
├── docx_preview.py        # Preview: Word doc rendering
├── xlsx_preview.py        # Preview: Excel sheet rendering
└── qa_common.py           # Shared: loader, helpers, normalization
```

---

## AI Agent Roles

### 1. Analyst
- Explore the target system (website, API, dataset)
- Identify test scenarios, risks, edge cases
- Produce test plans in `specs/` (Markdown, not code)
- **Never generate automation code**

### 2. Builder
- Convert Analyst plans into working automation
- Reuse existing tools — **never duplicate**
- Follow this repo's patterns exactly
- **Ask before creating new files**

### 3. Healer
- Diagnose failures in existing tools
- Fix the **smallest possible unit**
- Preserve original tool intent
- **Never weaken assertions or hide failures**

### 4. Reviewer
- Verify new code follows this repo's architecture
- Check for duplicate implementations
- Verify SOLID, DRY, and separation of concerns
- **Block merges that violate these rules**

---

## Repair Philosophy

When fixing a broken tool, repair in this order (smallest first):

1. **Input/argument** — wrong flag or path?
2. **Selector/locator** — element changed on the page?
3. **Parser/regex** — data format changed?
4. **API endpoint** — URL or response shape changed?
5. **Logic** — business rule changed?
6. **Architecture** — fundamental design issue?

**Never modify a higher layer when a lower layer solves the problem.**

---

## Coding Conventions

### Python
- Use `config.env` for environment variables — **never `os.environ` directly**
- Use `core.base_api_client` for HTTP calls — **never raw `urllib`/`requests` in scripts**
- Use `core.builders` for test data construction
- File names: `kebab-case.py` (existing) or `snake_case.py`
- All tools must work as standalone CLI scripts **and** as importable modules

### TypeScript / Playwright
- Import `test`/`expect` from `fixtures/base.fixture` — **never from `@playwright/test` directly**
- Specs live in `specs/` with `.spec.ts` extension
- Use `test.describe` per feature area
- Use web-first assertions (`expect(locator).toBeVisible()`)
- **No `page.waitForTimeout`** — use locator auto-waiting
- **No hardcoded URLs** — use `QA_BASE_URL` env var

### General
- Every tool must have a `--help` / docstring explaining usage
- Never hardcode file paths — accept them as arguments
- Never commit `.env`, credentials, or auth tokens
- Never commit generated reports, screenshots, or PDFs (they're in `.gitignore`)

---

## Anti-Hallucination Protocol

1. **Read before you write** — Never assume file contents from memory
2. **Run, then quote output** — Never claim success without evidence
3. **Verify against source** — Compare against original data, not your own summaries
4. **Use the exact tool specified** — Don't substitute similar scripts
5. **Set country/locale explicitly** — Defaults are almost always wrong

---

## Commands

```bash
# ── Python tools ──────────────────────────────────
python data-validator.py "data.xlsx" --dedup-key "name,address"
python fast-dns-verifier.py "data.xlsx" --column "website" --workers 50
python fuzzy-dedup.py "data.xlsx" --threshold 0.85
python taxonomy-aligner.py "data.xlsx" --output "cleaned.xlsx"
python excel-ops.py read "data.xlsx" --stats

# ── Node.js tools ─────────────────────────────────
node browser-test.js --url "https://example.com" --screenshot
node accessibility-check.js --url "https://example.com"
node visual-diff.js --baseline a.png --current b.png
node report-generator.js --input data.json
node url-fetch.js --url "https://example.com" --format markdown
node web-scraper.js --url "https://example.com" --strategy json-ld

# ── Playwright test specs ─────────────────────────
QA_BASE_URL=https://example.com npx playwright test
npx playwright test --project=chromium
npx playwright test specs/smoke.spec.ts
npx playwright test --grep "@smoke"
npx playwright test --ui

# ── Python tests ──────────────────────────────────
python -m pytest tests/ -v
python -m pytest tests/test_core.py -v

# ── Quality gates ─────────────────────────────────
npx tsc --noEmit          # TypeScript type check
```

---

## Code Review Checklist

Before any change is considered complete:

- [ ] Existing tools reused (not duplicated)
- [ ] No hardcoded paths, URLs, or credentials
- [ ] No hardcoded waits (`waitForTimeout`)
- [ ] CLI help/docstring updated if args changed
- [ ] Tests pass (`pytest` + `playwright test`)
- [ ] Works as both CLI script and importable module
- [ ] Country/locale is a parameter, not a default
- [ ] `.gitignore` covers any new generated artifacts

---

*Universal QA & Data Engineering Toolkit — Built by Azeez*
