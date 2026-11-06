/**
 * app-auditor.js — Authenticated deep page auditor.
 *
 * Logs into a web app once (or reuses a saved session), then walks a list of
 * routes and, for each page, records: HTTP status, load time, console errors,
 * failed/slow API calls, "bad text" (NaN / undefined / [object Object] / blank
 * states), accessibility violations (axe), mobile horizontal overflow, and a
 * screenshot. Optionally verifies that plan/permission-locked routes are blocked
 * (403 / redirect), not silently served.
 *
 * This is the behind-the-login complement to browser-test.js's shallow public
 * --routes sweep. Project-independent: app specifics come from a login recipe
 * or saved session and a routes file — nothing is hard-coded.
 *
 * Usage:
 *   # with a login recipe (reads $QA_USER / $QA_PASS from the environment)
 *   QA_USER=you@x.com QA_PASS=secret \
 *   node app-auditor.js --base-url https://app.example.com \
 *     --login examples/login-recipe.example.json \
 *     --routes examples/routes.example.json \
 *     --axe --mobile --api-host api.example.com \
 *     --output audit.json --report app-audit
 *
 *   # with an already-saved Playwright storage-state
 *   node app-auditor.js --base-url https://app.example.com \
 *     --session state.json --routes /dashboard,/customers --output audit.json
 *
 * Options:
 *   --base-url <url>       App origin (required)
 *   --routes <file|list>   JSON array file OR comma-separated routes (required)
 *   --login <recipe.json>  Login recipe (see core/session.js); or use --session
 *   --session <state.json> Saved storage-state instead of logging in
 *   --api-host <host>      Host that serves the API (for API error/timing capture)
 *   --axe                  Run accessibility (axe-core) on every page
 *   --mobile               Also load each page at phone size and flag overflow
 *   --gate <list>          Comma-separated routes that SHOULD be blocked (plan/permission)
 *   --slow-api-ms <n>      Flag API calls slower than this (default 1500)
 *   --screenshot-dir <d>   Where to save per-route screenshots (default ./audit-screens)
 *   --output <file>        Write results JSON
 *   --report <name>        Generate <name>.html/.pdf via report-generator.js
 *   --headed               Show the browser
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { login, openSession, gotoSettle } = require('./core/session');

const AXE = (() => { try { return fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8'); } catch { return null; } })();
const BAD = /\bNaN\b|\bundefined\b|\bnull\b|Invalid Date|\[object Object\]|something went wrong|unexpected error|failed to (load|fetch)/i;

function parseArgs() {
  const a = process.argv.slice(2); const o = { slowApiMs: 1500, screenshotDir: 'audit-screens', gate: [] };
  for (let i = 0; i < a.length; i++) switch (a[i]) {
    case '--base-url': o.baseUrl = a[++i]; break;
    case '--routes': o.routesArg = a[++i]; break;
    case '--login': o.login = a[++i]; break;
    case '--session': o.session = a[++i]; break;
    case '--api-host': o.apiHost = a[++i]; break;
    case '--axe': o.axe = true; break;
    case '--mobile': o.mobile = true; break;
    case '--gate': o.gate = a[++i].split(',').map(s => s.trim()).filter(Boolean); break;
    case '--slow-api-ms': o.slowApiMs = parseInt(a[++i]); break;
    case '--screenshot-dir': o.screenshotDir = a[++i]; break;
    case '--output': o.output = a[++i]; break;
    case '--report': o.report = a[++i]; break;
    case '--headed': o.headed = true; break;
    default: if (a[i].startsWith('--')) console.warn('Unknown option', a[i]);
  }
  if (!o.baseUrl || !o.routesArg) { console.error('Error: --base-url and --routes are required.'); process.exit(1); }
  if (!o.login && !o.session) console.warn('No --login or --session given: auditing as a logged-OUT user.');
  o.routes = o.routesArg.endsWith('.json') ? JSON.parse(fs.readFileSync(path.resolve(o.routesArg), 'utf8'))
    : o.routesArg.split(',').map(s => s.trim()).filter(Boolean);
  return o;
}

async function auditOne(S, base, route, opts) {
  const { page, consoleErrors, apiTraffic, afterLoad } = S;
  const before = { c: consoleErrors.length, a: apiTraffic.length };
  const url = route.startsWith('http') ? route : base + (route.startsWith('/') ? route : '/' + route);
  const rec = { route, url };
  const t = Date.now();
  try {
    const resp = await gotoSettle(page, url);
    rec.status = resp && resp.status(); rec.loadMs = Date.now() - t;
    await afterLoad(); await page.waitForTimeout(700);
    rec.finalUrl = page.url().replace(base, '');
    const body = await page.innerText('body').catch(() => '');
    rec.heading = (await page.locator('main h1, main h2, h1').first().innerText({ timeout: 800 }).catch(() => '')).slice(0, 70);
    const m = body.match(new RegExp('.{0,45}(' + BAD.source + ').{0,45}', 'i'));
    rec.badText = m ? m[0].replace(/\s+/g, ' ').trim() : null;
    rec.dialog = await page.evaluate(() => [...document.querySelectorAll('[role=dialog],[role=alertdialog]')].map(d => d.innerText.replace(/\s+/g, ' ').slice(0, 160)));
    if (opts.axe && AXE) {
      await page.addScriptTag({ content: AXE });
      rec.axe = await page.evaluate(async () => (await axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] })).violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })));
    }
    const fn = route.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'root';
    await page.screenshot({ path: path.join(opts.screenshotDir, `${fn}.png`) });
  } catch (e) { rec.error = e.message.slice(0, 180); }
  rec.consoleErrors = consoleErrors.slice(before.c);
  const newApi = apiTraffic.slice(before.a);
  rec.apiErrors = newApi.filter(x => typeof x.status !== 'number' || x.status >= 400).map(x => `${x.status} ${x.method} ${x.url}`);
  rec.slowApi = newApi.filter(x => x.ms > opts.slowApiMs).map(x => `${x.ms}ms ${x.url}`);
  // plan/permission gate check
  if (opts.gate.includes(route)) {
    const blocked = (rec.apiErrors.some(e => e.startsWith('403')) || /\/login$/.test(rec.finalUrl || '') || (rec.dialog || []).some(d => /plan|upgrade|not included|permission/i.test(d)));
    rec.gateExpected = true; rec.gateBlocked = blocked;
  }
  return rec;
}

(async () => {
  const opts = parseArgs();
  fs.mkdirSync(path.resolve(opts.screenshotDir), { recursive: true });
  // --login always logs in; --session is where the session is saved (or, without
  // --login, an already-saved session to reuse).
  let statePath = opts.session;
  const recipe = opts.login ? require('./core/session').loadRecipe(opts.login) : null;
  if (opts.login) { console.log('🔑 Logging in…'); statePath = await login(recipe, { statePath: opts.session, headless: !opts.headed }); console.log('   session saved →', statePath); }

  console.log(`\n🔎 Authenticated App Audit`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Base: ${opts.baseUrl}   Routes: ${opts.routes.length}   axe:${!!opts.axe} mobile:${!!opts.mobile}\n`);

  const results = { base: opts.baseUrl, timestamp: new Date().toISOString(), authenticated: !!statePath, pages: [] };
  const S = await openSession({ statePath, apiHost: opts.apiHost, recipe, headless: !opts.headed });
  let Sm = opts.mobile ? await openSession({ statePath, apiHost: opts.apiHost, recipe, mobile: true, headless: !opts.headed }) : null;

  for (const route of opts.routes) {
    const rec = await auditOne(S, opts.baseUrl.replace(/\/+$/, ''), route, opts);
    if (Sm && !rec.error) {
      try {
        await gotoSettle(Sm.page, (route.startsWith('http') ? route : opts.baseUrl.replace(/\/+$/, '') + route));
        await Sm.afterLoad(); await Sm.page.waitForTimeout(500);
        rec.mobileOverflow = await Sm.page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      } catch { rec.mobileOverflow = null; }
    }
    results.pages.push(rec);
    if (opts.output) fs.writeFileSync(path.resolve(opts.output), JSON.stringify(results, null, 2));
    const flags = [rec.error && 'ERROR', rec.badText && 'BAD-TEXT', rec.apiErrors.length && `api:${rec.apiErrors.length}`, rec.slowApi.length && `slow:${rec.slowApi.length}`, rec.consoleErrors.length && `console:${rec.consoleErrors.length}`, rec.mobileOverflow && 'overflow', (rec.axe || []).length && `axe:${rec.axe.length}`, rec.gateExpected && (rec.gateBlocked ? 'gate:ok' : 'gate:LEAK')].filter(Boolean).join(' ');
    console.log(`  ${String(rec.status || '—').padEnd(3)} ${String(rec.loadMs || '').padStart(6)}ms  ${route.padEnd(40)} ${flags}`);
  }
  await S.browser.close(); if (Sm) await Sm.browser.close();

  // summary
  const P = results.pages;
  results.summary = {
    pages: P.length,
    errors: P.filter(p => p.error).length,
    badText: P.filter(p => p.badText).length,
    pagesWithApiErrors: P.filter(p => p.apiErrors.length).length,
    pagesWithConsoleErrors: P.filter(p => p.consoleErrors.length).length,
    mobileOverflow: P.filter(p => p.mobileOverflow).length,
    gateLeaks: P.filter(p => p.gateExpected && !p.gateBlocked).map(p => p.route),
    axeByImpact: P.flatMap(p => p.axe || []).reduce((m, v) => (m[v.impact] = (m[v.impact] || 0) + v.nodes, m), {}),
  };
  if (opts.output) fs.writeFileSync(path.resolve(opts.output), JSON.stringify(results, null, 2));
  console.log('\n📊 Summary:', JSON.stringify(results.summary));
  if (opts.output) console.log('💾', path.resolve(opts.output));

  if (opts.report && opts.output) {
    const sections = [
      { heading: 'Summary', type: 'key-value', data: results.summary },
      { heading: 'Pages', type: 'table', data: P.map(p => ({ route: p.route, status: p.status ?? (p.error ? 'ERR' : '—'), loadMs: p.loadMs ?? '', apiErrors: p.apiErrors.length, console: p.consoleErrors.length, badText: p.badText ? 'yes' : '', overflow: p.mobileOverflow ? 'yes' : '', axe: (p.axe || []).reduce((s, v) => s + v.nodes, 0) })) },
    ];
    const tmp = path.resolve(`${opts.report}.sections.json`);
    fs.writeFileSync(tmp, JSON.stringify({ sections }));
    execSync(`node "${path.join(__dirname, 'report-generator.js')}" --title "Authenticated App Audit: ${opts.baseUrl}" --input "${tmp}" --output "${opts.report}" --theme light`, { stdio: 'inherit' });
    fs.unlinkSync(tmp);
  }
  // non-zero exit if anything hard failed, so CI can gate on it
  const hard = results.summary.errors + results.summary.badText + results.summary.gateLeaks.length;
  process.exit(hard > 0 ? 1 : 0);
})();
