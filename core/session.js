/**
 * core/session.js — Shared session + safe-mode helpers for authenticated web QA.
 *
 * The ONLY place login, session reuse, write-blocking and API-traffic capture
 * are implemented, so app-auditor.js, form-fuzzer.js and any future tool behave
 * identically. Project-independent: all app specifics come from a login recipe
 * or a saved storage-state file, never hard-coded here.
 *
 * A login recipe is a small JSON file:
 *   {
 *     "loginUrl":   "https://app.example.com/login",
 *     "fields":     { "#email": "$QA_USER", "#password": "$QA_PASS" },
 *     "submit":     "Login",            // button name (role=button) or CSS selector
 *     "successUrlNot": "/login",        // logged in once the URL no longer matches this
 *     "dismiss":    ["Skip Tour"]       // optional: buttons to click after each load
 *   }
 * Any value starting with "$" is read from the environment, so credentials stay
 * out of the file and out of git.
 */

const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';

function resolveEnv(v) {
  if (typeof v === 'string' && v.startsWith('$')) {
    const val = process.env[v.slice(1)];
    if (val == null) throw new Error(`Login recipe references ${v} but that environment variable is not set.`);
    return val;
  }
  return v;
}

function loadRecipe(file) {
  const r = JSON.parse(fs.readFileSync(path.resolve(file), 'utf8'));
  if (!r.loginUrl || !r.fields || !r.submit) throw new Error('Login recipe needs at least loginUrl, fields and submit.');
  return r;
}

async function clickByNameOrSelector(scope, name) {
  // CSS selector if it looks like one, else a button/role lookup by visible text.
  if (/^[.#\[]/.test(name)) return scope.locator(name).first().click();
  return scope.getByRole('button', { name, exact: true }).first().click();
}

/** Log in using a recipe and return a saved storage-state file path. */
async function login(recipe, { statePath, headless = true } = {}) {
  const r = typeof recipe === 'string' ? loadRecipe(recipe) : recipe;
  const browser = await chromium.launch({ headless });
  const ctx = await browser.newContext({ userAgent: UA, viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(r.loginUrl, { waitUntil: 'domcontentloaded', timeout: 60000 }); await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  for (const [sel, val] of Object.entries(r.fields)) await page.fill(sel, resolveEnv(val));
  await clickByNameOrSelector(page, r.submit);
  const notPattern = r.successUrlNot || '/login';
  await page.waitForURL(u => !u.href.includes(notPattern), { timeout: 45000 })
    .catch(() => { /* fall through; caller verifies */ });
  await page.waitForLoadState('networkidle').catch(() => {});
  const ok = !page.url().includes(notPattern);
  const out = statePath || path.join(require('os').tmpdir(), `qa-session-${Date.now()}.json`);
  if (ok) await ctx.storageState({ path: out });
  await browser.close();
  if (!ok) throw new Error(`Login did not leave ${notPattern} — check credentials/recipe. Landed on: ${r.loginUrl}`);
  return out;
}

/**
 * Open an authenticated context + page.
 *   opts.statePath   saved storage-state (from login() or Playwright)
 *   opts.safeMode    abort every non-GET request (default false) — test destructive flows safely
 *   opts.mobile      use an iPhone 13 profile
 *   opts.recipe      login recipe (so callers can re-dismiss tour popups per page)
 */
async function openSession(opts = {}) {
  const browser = await chromium.launch({ headless: opts.headless !== false });
  const base = opts.mobile ? { ...devices['iPhone 13'] } : { userAgent: UA, viewport: { width: 1440, height: 900 } };
  if (opts.statePath) base.storageState = opts.statePath;
  const ctx = await browser.newContext(base);

  const blockedWrites = [];
  if (opts.safeMode) {
    await ctx.route('**/*', route => {
      const m = route.request().method();
      if (m === 'GET' || m === 'HEAD' || m === 'OPTIONS') return route.continue();
      blockedWrites.push(`${m} ${route.request().url()}`);
      return route.abort();
    });
  }

  const page = await ctx.newPage();
  const consoleErrors = [], apiTraffic = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 260)); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR ' + e.message.slice(0, 260)));

  const apiHost = opts.apiHost || null; // e.g. "api.example.com"; null = capture cross-origin non-same-origin xhr heuristically
  page.on('requestfinished', async rq => {
    const url = rq.url();
    if (apiHost ? !url.includes(apiHost) : !/\/api\//.test(url)) return;
    let res = null, body = '';
    try { res = await rq.response(); if (rq.method() !== 'GET' && res) body = (await res.text()).slice(0, 1200); } catch {}
    apiTraffic.push({ method: rq.method(), url: url.replace(/^https?:\/\/[^/]+/, ''), status: res ? res.status() : null, ms: Math.round(rq.timing().responseEnd), reqBody: rq.method() !== 'GET' ? (rq.postData() || '').slice(0, 1200) : undefined, resBody: body || undefined });
  });

  const dismiss = (opts.recipe && opts.recipe.dismiss) || [];
  async function afterLoad() {
    for (const name of dismiss) await page.getByRole('button', { name }).first().click({ timeout: 700 }).catch(() => {});
  }

  return { browser, ctx, page, consoleErrors, apiTraffic, blockedWrites, afterLoad };
}

/**
 * Navigate robustly: wait for DOM, then a short network settle. Apps with chat
 * widgets, websockets or polling never reach full "networkidle", so a hard
 * networkidle wait would hang — this settles briefly and moves on.
 */
async function gotoSettle(page, url, { timeout = 60000, settle = 8000 } = {}) {
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
  await page.waitForLoadState('networkidle', { timeout: settle }).catch(() => {});
  return resp;
}

/** Visible-error / validation message reader shared by the fuzzer and auditor. */
async function readValidation(page) {
  return page.evaluate(() => {
    const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const sel = '[role=alert],[data-sonner-toast],[aria-live]:not([aria-live=off]) *,.error,.text-red-500,.text-red-600,[class*=error],[class*=destructive]';
    const NAV = /^(log ?out|sign ?out|delete|remove|cancel|close)$/i; // red UI controls that aren't validation
    const errs = [...document.querySelectorAll(sel)].filter(vis).map(e => e.innerText.trim())
      .filter(t => t && t.length < 200 && !NAV.test(t));
    const invalid = [...document.querySelectorAll('[aria-invalid=true]')].map(e => e.name || e.id).filter(Boolean);
    return { messages: [...new Set(errs)], invalidFields: [...new Set(invalid)] };
  });
}

module.exports = { UA, login, loadRecipe, openSession, readValidation, resolveEnv, gotoSettle };
