# 🛠️ QA Toolkit

A universal, project-independent QA automation toolkit for use with Claude Code and any AI coding assistant.

Built by **Azeez** — works for any project (BisViews, PrimBooks, or anything else).

## ✨ Features

| Tool | Description |
|------|-------------|
| `browser-test.js` | Navigate any website, take screenshots, check links/images, fill forms, extract content |
| `web-search.js` | Search the web (DuckDuckGo + Bing fallback) — no API key needed |
| `report-generator.js` | Generate professional HTML + PDF reports from JSON data (4 themes) |
| `accessibility-check.js` | WCAG accessibility audits using axe-core |
| `visual-diff.js` | Compare screenshots pixel-by-pixel for visual regression |
| `docx_preview.py` | Render a Word document to page images for real visual verification (Python, Windows/Word only) |
| `xlsx_preview.py` | Render an Excel workbook (or one sheet) to page images for real visual verification (Python, Windows/Excel only) |

## 🚀 Setup

```bash
git clone https://github.com/YOUR_USERNAME/qa-toolkit.git
cd qa-toolkit
npm install
npx playwright install chromium
```

### Python tool setup (docx_preview.py / xlsx_preview.py)
These are the Python tools in this toolkit — everything else here is Node. They convert through Office itself via COM automation (Word for `.docx`, Excel for `.xlsx`), so the preview closely matches what the app renders. Windows + the relevant Office app required.
```bash
pip install -r requirements.txt
```

## 📖 Usage

### Browser Test
```bash
# Screenshot + link check
node browser-test.js --url "https://example.com" --screenshot --check-links

# Mobile view + extract forms
node browser-test.js --url "https://example.com" --mobile --extract-forms

# Fill and submit a form
node browser-test.js --url "https://example.com" --fill '{"#email":"test@test.com"}' --click "#submit"
```

### Web Search
```bash
node web-search.js --query "business name status" --results 10
node web-search.js --query "PrimBooks ERP" --output results.json
```

### Report Generator
```bash
# From JSON data file
node report-generator.js --title "QA Audit Report" --input data.json --output report

# Themes: dark (default), light, blue, green
node report-generator.js --title "Entity Audit" --author "Azeez" --input findings.json --output audit --theme blue
```

### Accessibility Check
```bash
node accessibility-check.js --url "https://example.com"
node accessibility-check.js --url "https://example.com" --report a11y-audit
```

### Visual Diff
```bash
node visual-diff.js --baseline before.png --current after.png --output diff.png
```

### Document Preview
```bash
# Render every page of a Word doc to PNGs, for actually looking at an edit
python docx_preview.py "report.docx"

# Just specific pages
python docx_preview.py "report.docx" --pages 1,3-5

# Custom output folder and resolution
python docx_preview.py "report.docx" -o previews --dpi 200
```

### Spreadsheet Preview
```bash
# Render every sheet of a workbook to PNGs, for actually looking at the styling
python xlsx_preview.py "tracker.xlsx"

# Just one sheet
python xlsx_preview.py "tracker.xlsx" --sheet Summary

# Custom output folder and resolution
python xlsx_preview.py "tracker.xlsx" -o previews --dpi 150
```
Each sheet is set to fit-to-width so columns aren't split across pages. Colours are close to Excel's screen rendering but not always pixel-exact — for final colour sign-off, the file open in Excel is ground truth.

## 🔧 Claude Code Integration

### Custom Commands
Copy `.claude/commands/` to your home directory to get:
- `/qa-test <url>` — Full QA audit
- `/generate-report <file>` — Create HTML+PDF report
- `/search-web <query>` — Search the web

### MCP Server
Copy `.claude/mcp.json` to `~/.claude/` to give Claude Code native URL fetching.

## 📄 License

MIT
