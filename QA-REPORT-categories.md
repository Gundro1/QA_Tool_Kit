# QA Report — Categories Page

**Target:** https://staging.bisviews.com/categories
**Date:** 2026-07-20
**Tools:** `browser-test.js` + `accessibility-check.js` (Playwright + axe-core)
**Overall verdict:** 🟢 Page is healthy and functional — HTTP 200, renders correctly. Some accessibility fixes recommended.

---

## 📸 Screenshot

[![Categories page screenshot](categories-screenshot.png)](categories-screenshot.png)

> Click the image to open the full-page capture.

---

## ✅ What passed

| Check | Result |
|---|---|
| Page load | HTTP 200 — title "BisViews" |
| Links | **284 checked, 0 broken** |
| Images | All load, all have alt text |
| Heading content | Clean H1 → H2 → H3 across 25 category cards |
| Accessibility rules | 35 axe rules passed |

---

## ⚠️ Accessibility violations (5)

| # | Severity | Rule | Elements | Issue |
|---|---|---|---|---|
| 1 | 🔴 Critical | `button-name` | 25 | Buttons have no discernible text — screen readers announce nothing. Add `aria-label`. |
| 2 | 🟠 Serious | `list` | 25 | `<ul>` elements contain non-`<li>` children — breaks list semantics. |
| 3 | 🟡 Moderate | `landmark-one-main` | 1 | No `<main>` landmark on the page. |
| 4 | 🟡 Moderate | `region` | 56 | Content sits outside any landmark region. |
| 5 | 🟡 Moderate | `heading-order` | 1 | Heading levels skip (footer `<h5>` with no intervening levels). |

---

## 🐞 Other findings

- **Console error — HTTP 401:** One resource request is rejected as Unauthorized on this otherwise-public page. Worth tracing.
- **Alt-text typo:** Logo alt reads `"inViews Logo"` — likely should be `"BisViews Logo"`.

---

## 🎯 Priorities

1. 🔴 Fix `button-name` — 25 unlabeled buttons (biggest a11y impact).
2. 🐞 Trace the 401 console error.
3. 🟠 Fix list markup, then landmarks/heading order.

---

## 📁 Artifacts

| File | Contents |
|---|---|
| [categories-screenshot.png](categories-screenshot.png) | Full-page screenshot |
| [categories-a11y.json](categories-a11y.json) | Raw axe-core results |
| [categories-results.json](categories-results.json) | Links / headings / console data |
