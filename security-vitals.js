/**
 * security-vitals.js — One-command security + performance quick-scan.
 *
 * For each URL: HTTP→HTTPS redirect, TLS version + certificate expiry, the six
 * standard security headers, server/version disclosure, robots.txt & sitemap.xml,
 * 404 handling, and Core Web Vitals (TTFB / FCP / LCP / CLS) measured in a real
 * browser — optionally throttled to a slow phone. No login required.
 *
 * Usage:
 *   node security-vitals.js --url https://example.com --mobile --output scan.json
 *   node security-vitals.js --url https://a.com,https://b.com --output scan.json
 *
 * Options:
 *   --url <list>     One or more origins, comma-separated (required)
 *   --mobile         Also measure vitals on a throttled 4x-CPU / ~1.6Mbps profile
 *   --output <file>  Write results JSON
 *   --report <name>  Generate <name>.html/.pdf via report-generator.js
 */

const fs = require('fs');
const path = require('path');
const tls = require('tls');
const { execSync } = require('child_process');
const { chromium } = require('playwright');
const { UA } = require('./core/session');

const SEC_HEADERS = ['strict-transport-security', 'content-security-policy', 'x-frame-options', 'x-content-type-options', 'referrer-policy', 'permissions-policy'];

function parseArgs() {
  const a = process.argv.slice(2); const o = {};
  for (let i = 0; i < a.length; i++) switch (a[i]) {
    case '--url': o.urls = a[++i].split(',').map(s => s.trim()).filter(Boolean); break;
    case '--mobile': o.mobile = true; break;
    case '--output': o.output = a[++i]; break;
    case '--report': o.report = a[++i]; break;
    default: if (a[i].startsWith('--')) console.warn('Unknown option', a[i]);
  }
  if (!o.urls || !o.urls.length) { console.error('Error: --url is required.'); process.exit(1); }
  return o;
}

async function httpInfo(url, follow) {
  try {
    const res = await fetch(url, { redirect: follow ? 'follow' : 'manual', headers: { 'user-agent': UA }, signal: AbortSignal.timeout(20000) });
    return { status: res.status, location: res.headers.get('location'), headers: Object.fromEntries(res.headers) };
  } catch (e) { return { error: String(e.cause && e.cause.code || e.message) }; }
}

function cert(host) {
  return new Promise(res => {
    const s = tls.connect(443, host, { servername: host, timeout: 15000 }, () => {
      const c = s.getPeerCertificate();
      const daysLeft = c.valid_to ? Math.round((new Date(c.valid_to) - Date.now()) / 86400000) : null;
      res({ issuer: c.issuer && (c.issuer.O || c.issuer.CN), subject: c.subject && c.subject.CN, validTo: c.valid_to, daysLeft, protocol: s.getProtocol(), authorized: s.authorized });
      s.end();
    });
    s.on('error', e => res({ error: e.message })); s.on('timeout', () => { s.destroy(); res({ error: 'timeout' }); });
  });
}

async function vitals(url, throttle) {
  const b = await chromium.launch();
  const ctx = await b.newContext({ userAgent: UA });
  const p = await ctx.newPage();
  if (throttle) { const c = await ctx.newCDPSession(p); await c.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: 1.6 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 }); await c.send('Emulation.setCPUThrottlingRate', { rate: 4 }); }
  await p.addInitScript(() => { window.__lcp = 0; window.__cls = 0; try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true }); new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true }); } catch {} });
  let v = {};
  try {
    await p.goto(url, { waitUntil: 'load', timeout: 90000 }); await p.waitForTimeout(3500);
    v = await p.evaluate(() => { const n = performance.getEntriesByType('navigation')[0]; const r = performance.getEntriesByType('resource'); const fcp = performance.getEntriesByName('first-contentful-paint')[0]; return { ttfbMs: Math.round(n.responseStart), fcpMs: Math.round(fcp ? fcp.startTime : 0), lcpMs: Math.round(window.__lcp), cls: +window.__cls.toFixed(3), loadMs: Math.round(n.loadEventEnd), requests: r.length + 1, transferKB: Math.round((r.reduce((s, x) => s + (x.transferSize || 0), 0)) / 1024), jsKB: Math.round(r.filter(x => x.initiatorType === 'script').reduce((s, x) => s + (x.transferSize || 0), 0) / 1024) }; });
  } catch (e) { v = { error: e.message.slice(0, 120) }; }
  await b.close(); return v;
}

function grade(r) {
  const issues = [];
  if (r.http && r.http.status !== 301 && r.http.status !== 308) issues.push('HTTP does not 301→HTTPS');
  for (const h of SEC_HEADERS) if (!r.securityHeaders[h]) issues.push(`missing ${h}`);
  if (r.disclosure.server) issues.push(`server version disclosed (${r.disclosure.server})`);
  if (r.disclosure.xPoweredBy) issues.push(`X-Powered-By disclosed (${r.disclosure.xPoweredBy})`);
  if (r.cert && r.cert.daysLeft != null && r.cert.daysLeft < 21) issues.push(`cert expires in ${r.cert.daysLeft}d`);
  if (r.notFound && r.notFound.status !== 404) issues.push(`unknown URL returns ${r.notFound && r.notFound.status}, not 404`);
  const vd = r.vitals && r.vitals.desktop || {};
  if (vd.lcpMs > 2500) issues.push(`LCP ${(vd.lcpMs / 1000).toFixed(1)}s (>2.5s)`);
  if (vd.cls > 0.1) issues.push(`CLS ${vd.cls} (>0.1)`);
  return issues;
}

(async () => {
  const opts = parseArgs();
  const out = { timestamp: new Date().toISOString(), hosts: {} };
  for (const url of opts.urls) {
    const host = new URL(url).host;
    console.log(`\n🔐 ${url}`);
    const r = {};
    r.http = await httpInfo(url.replace(/^https/, 'http'), false);
    const https = await httpInfo(url, true);
    r.securityHeaders = Object.fromEntries(SEC_HEADERS.map(h => [h, (https.headers || {})[h] || null]));
    r.disclosure = { server: (https.headers || {})['server'] || null, xPoweredBy: (https.headers || {})['x-powered-by'] || null };
    r.cert = await cert(host);
    r.robots = (await httpInfo(url.replace(/\/$/, '') + '/robots.txt', true)).status || null;
    r.sitemap = (await httpInfo(url.replace(/\/$/, '') + '/sitemap.xml', true)).status || null;
    r.notFound = await httpInfo(url.replace(/\/$/, '') + '/qa-nonexistent-' + Date.now(), true);
    delete r.notFound.headers;
    r.vitals = { desktop: await vitals(url, false) };
    if (opts.mobile) r.vitals.mobile3G = await vitals(url, true);
    r.issues = grade(r);
    out.hosts[host] = r;
    console.log(`   TLS ${r.cert.protocol || r.cert.error} · cert ${r.cert.daysLeft}d · LCP ${(r.vitals.desktop.lcpMs / 1000 || 0).toFixed(1)}s`);
    console.log(`   issues (${r.issues.length}): ${r.issues.join(' · ') || 'none'}`);
    if (opts.output) fs.writeFileSync(path.resolve(opts.output), JSON.stringify(out, null, 2));
  }
  if (opts.output) console.log('\n💾', path.resolve(opts.output));

  if (opts.report && opts.output) {
    const sections = [{ heading: 'Security & Vitals', type: 'table', data: Object.entries(out.hosts).map(([h, r]) => ({ host: h, tls: r.cert.protocol || 'err', certDays: r.cert.daysLeft, headersMissing: SEC_HEADERS.filter(x => !r.securityHeaders[x]).length, lcpDesktop: (r.vitals.desktop.lcpMs / 1000 || 0).toFixed(1) + 's', issues: r.issues.length })) }];
    for (const [h, r] of Object.entries(out.hosts)) sections.push({ heading: `Issues — ${h}`, type: 'list', items: r.issues.length ? r.issues : ['none'] });
    const tmp = path.resolve(`${opts.report}.sections.json`);
    fs.writeFileSync(tmp, JSON.stringify({ sections }));
    execSync(`node "${path.join(__dirname, 'report-generator.js')}" --title "Security & Vitals Scan" --input "${tmp}" --output "${opts.report}" --theme light`, { stdio: 'inherit' });
    fs.unlinkSync(tmp);
  }
  const total = Object.values(out.hosts).reduce((s, r) => s + r.issues.length, 0);
  process.exit(total ? 1 : 0);
})();
