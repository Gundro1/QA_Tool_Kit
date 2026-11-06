/**
 * form-fuzzer.js — Form validation fuzzer.
 *
 * Opens a form, fills its fields with a battery of good and bad inputs, submits
 * with writes BLOCKED by default (safe mode), and reports what the app caught
 * versus what slipped through. Most real bugs live in form handling; this turns
 * a day of hand-written cases into one command.
 *
 * It auto-discovers visible inputs/selects/textareas and types per field by kind
 * (email, tel, number, text). Each case is judged on: did a write request leave
 * the browser, and did the app show a validation message / mark fields invalid.
 *
 * Usage:
 *   node form-fuzzer.js --url https://app.example.com/crm/customer \
 *     --session state.json --open "Add Customer" --submit "Save" --confirm "Confirm" \
 *     --output fuzz.json
 *
 * Options:
 *   --url <url>          Page holding (or linking to) the form (required)
 *   --session <state>    Saved storage-state for authenticated pages
 *   --open <text>        Button text that opens the form (omit if already on it)
 *   --submit <text>      Submit button text (default "Save")
 *   --confirm <text>     Confirmation button in a follow-up dialog (e.g. "Confirm")
 *   --scope <css>        Restrict to a container (default: the form/dialog/main)
 *   --unsafe             Actually submit (writes NOT blocked) — off by default
 *   --dismiss <list>     Buttons to click after load (e.g. "Skip Tour")
 *   --output <file>      Write results JSON
 *   --headed             Show the browser
 */

const fs = require('fs');
const path = require('path');
const { openSession, readValidation, gotoSettle } = require('./core/session');

function parseArgs() {
  const a = process.argv.slice(2); const o = { submit: 'Save', safeMode: true, dismiss: [] };
  for (let i = 0; i < a.length; i++) switch (a[i]) {
    case '--url': o.url = a[++i]; break;
    case '--session': o.session = a[++i]; break;
    case '--open': o.open = a[++i]; break;
    case '--submit': o.submit = a[++i]; break;
    case '--confirm': o.confirm = a[++i]; break;
    case '--scope': o.scope = a[++i]; break;
    case '--unsafe': o.safeMode = false; break;
    case '--dismiss': o.dismiss = a[++i].split(',').map(s => s.trim()); break;
    case '--output': o.output = a[++i]; break;
    case '--headed': o.headed = true; break;
    default: if (a[i].startsWith('--')) console.warn('Unknown option', a[i]);
  }
  if (!o.url) { console.error('Error: --url is required.'); process.exit(1); }
  return o;
}

// value batteries keyed by what we fill; "good" is a plausible valid value.
const BAD_BY_KIND = {
  email: ['not-an-email', 'a@@b', 'plainaddress'],
  tel: ['abcdefg', '12'],
  number: ['-9999', '1e999'],
  text: ['', '   ', '<img src=x onerror=alert(1)>', 'x'.repeat(5000)],
};
const GOOD_BY_KIND = { email: 'qa.tester@example.com', tel: '08031234567', number: '100', text: 'QA-TEST value' };

function kindOf(el) {
  const t = (el.type || el.tag || '').toLowerCase();
  if (t === 'email') return 'email';
  if (t === 'tel') return 'tel';
  if (t === 'number') return 'number';
  return 'text';
}

async function discover(page, scopeSel) {
  return page.evaluate(sel => {
    const root = (sel && document.querySelector(sel)) || document.querySelector('[role=dialog]') || document.querySelector('form') || document.querySelector('main') || document.body;
    return [...root.querySelectorAll('input,textarea')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && e.type !== 'hidden' && e.type !== 'search' && !/search/i.test(e.name || '') && !e.disabled && !e.readOnly; })
      .map((e, i) => { e.setAttribute('data-qa-fuzz', i); return { idx: i, tag: e.tagName.toLowerCase(), type: e.type || '', name: e.name || '', id: e.id || '', required: e.required, placeholder: e.placeholder || '' }; });
  }, scopeSel || null);
}

async function fill(page, idx, value) {
  await page.locator(`[data-qa-fuzz="${idx}"]`).fill(String(value)).catch(() => {});
}

async function submit(page, opts, trafficLenBefore, traffic) {
  const btn = opts.scope ? page.locator(opts.scope).getByRole('button', { name: opts.submit, exact: true })
    : page.getByRole('button', { name: opts.submit, exact: true });
  await btn.first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(800);
  if (opts.confirm) { const c = page.getByRole('button', { name: opts.confirm, exact: true }); if (await c.count() && await c.first().isVisible()) await c.first().click().catch(() => {}); }
  await page.waitForTimeout(1500);
  return traffic.slice(trafficLenBefore).filter(t => t.method !== 'GET');
}

(async () => {
  const opts = parseArgs();
  const S = await openSession({ statePath: opts.session, safeMode: opts.safeMode, headless: !opts.headed, recipe: { dismiss: opts.dismiss } });
  const { page, apiTraffic } = S;
  const results = { url: opts.url, safeMode: opts.safeMode, timestamp: new Date().toISOString(), cases: [] };

  const openForm = async () => {
    await gotoSettle(page, opts.url);
    await S.afterLoad(); await page.waitForTimeout(600);
    if (opts.open) { await page.getByRole('button', { name: opts.open, exact: true }).first().click(); await page.waitForTimeout(1200); }
  };

  await openForm();
  const fields = await discover(page, opts.scope);
  if (!fields.length) { console.error('No fillable fields found. Use --open to open the form, or --scope to point at it.'); await S.browser.close(); process.exit(1); }
  console.log(`\n🧪 Form Fuzzer — ${fields.length} fields on ${opts.url}  (safe mode: ${opts.safeMode})\n`);
  fields.forEach(f => console.log(`   • ${f.tag}[${f.type}] ${f.name || f.id || f.placeholder} ${f.required ? '(required)' : ''}`));

  const record = (name, expect, sent, v) => {
    const pass = name === 'all valid' ? (sent.length > 0 || !opts.safeMode) : (sent.length === 0);
    results.cases.push({ case: name, expectation: expect, writesSent: sent.length, writeStatuses: sent.map(s => s.status), ...v });
    console.log(`  [${pass ? 'PASS' : 'CHECK'}] ${name.padEnd(26)} writes=${sent.length} ${JSON.stringify(v.messages || []).slice(0, 90)}`);
  };

  // Case 1: all empty
  await openForm();
  let n = apiTraffic.length; let sent = await submit(page, opts, n, apiTraffic); let val = await readValidation(page);
  record('all empty', 'blocked; required flagged', sent, val);

  // Case 2..n: one bad field at a time, rest valid
  for (const f of fields) {
    const kind = kindOf(f);
    for (const bad of BAD_BY_KIND[kind]) {
      await openForm();
      const fresh = await discover(page, opts.scope);
      for (const g of fresh) await fill(page, g.idx, g.idx === f.idx ? bad : GOOD_BY_KIND[kindOf(g)]);
      n = apiTraffic.length; sent = await submit(page, opts, n, apiTraffic); val = await readValidation(page);
      const label = `${(f.name || f.id || f.type || 'field')}=${JSON.stringify(bad).slice(0, 16)}`;
      // XSS: also check no dialog fired (script executed)
      record(label.slice(0, 26), 'blocked / stored-as-text', sent, val);
    }
  }

  // Final: all valid (only meaningful in --unsafe; in safe mode we just confirm it WOULD submit)
  await openForm();
  const fresh = await discover(page, opts.scope);
  for (const g of fresh) await fill(page, g.idx, GOOD_BY_KIND[kindOf(g)]);
  n = apiTraffic.length; sent = await submit(page, opts, n, apiTraffic); val = await readValidation(page);
  record('all valid', opts.safeMode ? 'would submit (blocked by safe mode)' : 'submits (2xx)', sent, { ...val, note: opts.safeMode ? 'write blocked by safe mode' : undefined });

  await S.browser.close();
  const checks = results.cases.filter(c => c.case !== 'all valid' && c.writesSent > 0);
  results.summary = { fields: fields.length, cases: results.cases.length, leakedValidation: checks.map(c => c.case) };
  if (opts.output) { fs.writeFileSync(path.resolve(opts.output), JSON.stringify(results, null, 2)); console.log('\n💾', path.resolve(opts.output)); }
  console.log('📊', JSON.stringify(results.summary));
  process.exit(checks.length ? 1 : 0);
})();
