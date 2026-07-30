# AI Assistant Integration Guide — Making Any AI Coding Agent Work Like a Senior QA Engineer

> This guide explains **why** some AI assistants catch data issues others miss, and **how** to configure any AI coding agent (Claude Code, Cursor, Copilot, Antigravity, etc.) to perform at the highest level of accuracy and reliability for QA and data engineering work.

---

## The 3 Layers of AI Assistant Capability

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI ASSISTANT PERFORMANCE                          │
├──────────────────┬──────────────────┬───────────────────────────────┤
│   Layer 1: TOOLS │ Layer 2: HABITS  │  Layer 3: PLATFORM FEATURES   │
│  (Scriptable)    │ (Promptable)     │  (Architecture-locked)        │
├──────────────────┼──────────────────┼───────────────────────────────┤
│ excel-ops.py     │ Read-before-edit │ Real-time browser sub-agents  │
│ url-fetch.js     │ Verify outputs   │ Image generation              │
│ web-scraper.js   │ Source-vs-memory │ Parallel tool execution       │
│ pdf-print.py     │ Explicit context │ Cross-session memory (KIs)    │
│ data-validator.py│ Country locale   │ Rich artifact rendering       │
│ address-parser.py│                  │                               │
├──────────────────┼──────────────────┼───────────────────────────────┤
│ ✅ You control   │ ✅ You control   │ ❌ Platform-dependent          │
│    this layer    │    this layer    │    (choose your platform)     │
└──────────────────┴──────────────────┴───────────────────────────────┘
```

**Layer 1 (Tools):** The CLI scripts in this toolkit that extend what the AI can do.
**Layer 2 (Habits):** Behavioral instructions you give the AI via config files (e.g., `CLAUDE.md`, `.cursorrules`, system prompts).
**Layer 3 (Platform):** Hardware/runtime-level features baked into specific platforms — you can't replicate these with prompts or scripts.

---

## Layer 1 — Tools (This Toolkit)

This toolkit provides **13 CLI tools** that any AI assistant can invoke via shell commands:

### Frontend & UI QA
| Tool | Command | Purpose |
| :--- | :--- | :--- |
| `browser-test.js` | `node browser-test.js --url "..." --screenshot` | Screenshots, link checks, form filling |
| `web-search.js` | `node web-search.js --query "..."` | Web search result scraping |
| `accessibility-check.js` | `node accessibility-check.js --url "..."` | WCAG accessibility audits |
| `visual-diff.js` | `node visual-diff.js --baseline a.png --current b.png` | Pixel comparison |
| `report-generator.js` | `node report-generator.js --input data.json` | HTML/PDF report generation |

### Document Preview
| Tool | Command | Purpose |
| :--- | :--- | :--- |
| `docx_preview.py` | `python docx_preview.py "file.docx"` | Word doc → PNG rendering |
| `xlsx_preview.py` | `python xlsx_preview.py "file.xlsx"` | Excel → PNG rendering |

### Data Pipeline & Engineering
| Tool | Command | Purpose |
| :--- | :--- | :--- |
| `excel-ops.py` | `python excel-ops.py read "file.xlsx" --stats` | Read/write/merge/clean Excel |
| `url-fetch.js` | `node url-fetch.js --url "..." --format markdown` | HTTP fetch without browser overhead |
| `web-scraper.js` | `node web-scraper.js --url "..." --strategy json-ld` | JS-rendered store locator extraction |
| `pdf-print.py` | `python pdf-print.py "report.html"` | Headless Edge/Chrome PDF generation |
| `address-parser.py` | `python address-parser.py --country BE --postal 1000` | Postal → province mapping |
| `data-validator.py` | `python data-validator.py "data.xlsx" --dedup-key "name,addr"` | Quick integrity checks |

---

## Layer 2 — The 5 Anti-Hallucination Habits

These are behavioral rules that **prevent AI assistants from making things up**. They work with any AI agent that reads a project config file.

### Habit 1: Read Before You Write
```
RULE: Before editing ANY file, you MUST read it first. Never assume file 
contents from memory. Memory drifts over long conversations. Files don't.
```
**Why it matters:** In a 50-message conversation, the AI's "memory" of what a file contains drifts from reality. By forcing a re-read, you ensure edits are based on the actual current state.

### Habit 2: Run, Then Quote The Output
```
RULE: After running ANY command, read and quote the actual terminal output. 
Never say "successfully completed" without showing evidence. If output is 
empty, say so explicitly.
```
**Why it matters:** Without this rule, AI assistants will claim scripts succeeded even when they silently failed, because the model predicts "success" is the most likely next token.

### Habit 3: Verify Against Source, Not Against Your Own Work
```
RULE: When validating data quality, always compare against the ORIGINAL 
raw source file — not against your own summaries or previous outputs. 
Your summaries can contain errors that compound silently.
```
**Why it matters:** If the AI summarized 1,858 rows in message #5 and now needs to verify in message #30, comparing against its own summary from message #5 propagates any error from that summary. Re-reading the source file catches it.

### Habit 4: Use The Exact Tool The User Specifies
```
RULE: When the user references a specific tool by name (e.g., "bisquality"), 
find and use the EXACT file at its EXACT path. Ask for clarification if 
multiple versions exist. Never substitute a similar-looking script.
```
**Why it matters:** Production tools often have country-specific configs, calibrated thresholds, and report templates that quick-and-dirty alternatives don't have. Using the wrong script produces incomplete or misleading results.

### Habit 5: Always Set Country/Locale Context Explicitly
```
RULE: For any data audit, validation, or scraping task, always specify the 
country code explicitly (e.g., --country BE). Never rely on tool defaults.
Defaults are almost always wrong for cross-country work.
```
**Why it matters:** A Belgian postal code is 4 digits. A US ZIP is 5 digits. If the tool defaults to US, every Belgian postal code gets falsely flagged as invalid.

---

## Installing These Habits Into Your AI Assistant

### For Claude Code
Create a file called `CLAUDE.md` in your project root:

```markdown
# Project Intelligence — QA & Data Engineering Standards

## Anti-Hallucination Protocol
1. NEVER claim a file contains something without reading it first.
2. NEVER say a command succeeded without quoting its actual output.
3. NEVER compare data against your own summaries — always re-read the source.
4. When the user says "use bisquality", use the EXACT production path. No substitutes.
5. Always pass --country explicitly to data audit tools. Defaults are wrong.

## QA Toolkit Commands
- Quick URL content: `node url-fetch.js --url "..." --format markdown`
- Store locator scraping: `node web-scraper.js --url "..." --strategy json-ld`
- Excel operations: `python excel-ops.py read "file.xlsx" --stats`
- PDF generation: `python pdf-print.py "report.html" --output "report.pdf"`
- Data validation: `python data-validator.py "data.xlsx" --dedup-key "name,address"`

## Reporting Standards
- All audit reports authored by "Azeez".
- Use professional English. No AI-speak phrases.
- Postal code descriptions in human-readable terms, not raw regex.
```

### For Cursor
Create a `.cursorrules` file in your project root with the same rules.

### For GitHub Copilot / Other Agents
Add the rules to your system prompt or project-level instructions file.

---

## Layer 3 — Platform Features (Not Replicable via Tooling)

These capabilities are **architecturally built into specific platforms** and cannot be replicated with scripts or prompts:

| Feature | What It Enables | Which Platforms Have It |
| :--- | :--- | :--- |
| **Browser sub-agent** | Dedicated AI agent controlling a real browser with its own reasoning loop | Antigravity |
| **Image generation** | Create mockup UIs, diagrams, logos on the fly | Antigravity, ChatGPT |
| **Parallel tool execution** | Run 5 URL fetches or file reads simultaneously | Antigravity |
| **Cross-session memory (Knowledge Items)** | Recall findings from previous conversations without re-reading files | Antigravity |
| **Rich artifact rendering** | Interactive documents with carousels, Mermaid diagrams, file links | Antigravity |
| **Native web search** | Built-in search engine without scripting | Antigravity, ChatGPT, Perplexity |

**Practical impact:** These features make up roughly 10% of the performance difference. The other 90% comes from **tools** (Layer 1) and **habits** (Layer 2) — both of which you fully control.

---

## Teaching Guide for New QA Engineers

### Step 1: Install the Toolkit
```bash
git clone https://github.com/Gundro1/QA_Tool_Kit.git
cd QA_Tool_Kit
npm install && npx playwright install chromium
pip install -r requirements.txt
```

### Step 2: Install the AI Discipline Rules
Copy the `CLAUDE.md` template above into your project root.

### Step 3: Learn the Workflow
1. **Before any audit:** Run `python excel-ops.py read "data.xlsx" --stats` to understand the dataset shape.
2. **For web data collection:** Use `node url-fetch.js` for simple pages, `node web-scraper.js` for JS-heavy store locators.
3. **For data merging:** Use `python excel-ops.py merge file1.xlsx file2.xlsx --dedup-key "name,address" --output merged.xlsx`.
4. **For quality auditing:** Run the production `bisquality.py` with explicit `--country` and `--prepared-by` flags.
5. **For report delivery:** Use `python pdf-print.py` to convert HTML reports to stakeholder-ready PDFs.

### Step 4: Read the Full Architecture Guide
See [`TOOLKIT-GAP-ANALYSIS.md`](./TOOLKIT-GAP-ANALYSIS.md) for the complete educational breakdown.

---

*Built by Azeez — Universal QA & Data Engineering Toolkit, July 2026*
