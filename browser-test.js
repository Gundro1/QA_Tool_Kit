/**
 * Universal Browser Test Tool
 * 
 * A general-purpose Playwright browser automation script.
 * Works with any website — BisViews, PrimBooks, or anything else.
 * 
 * Usage:
 *   node browser-test.js --url "https://example.com" [options]
 * 
 * Options:
 *   --url <url>              Target URL (required)
 *   --screenshot <path>      Save full-page screenshot (default: screenshot.png)
 *   --element <selector>     Screenshot a specific element
 *   --check-links            Check all links on the page for broken ones
 *   --check-images           Check all images load correctly
 *   --extract-text           Extract all visible text from the page
 *   --extract-headings       Extract heading structure (h1-h6)
 *   --extract-forms          Extract all form fields
 *   --fill <json>            Fill form fields: '{"#email":"test@example.com"}'
 *   --click <selector>       Click an element
 *   --wait <ms>              Wait time after page load (default: 2000)
 *   --viewport <WxH>         Set viewport size (default: 1920x1080)
 *   --mobile                 Use mobile viewport (375x812)
 *   --output <path>          Save results JSON to file
 *   --headed                 Run with visible browser (not headless)
 *   --pdf <path>             Save page as PDF
 *   --cookies <path>         Load cookies from JSON file
 *   --auth <user:pass>       HTTP basic auth
 *   --user-agent <string>    Custom user agent
 *   --timeout <ms>           Navigation timeout (default: 30000)
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Parse CLI arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    url: null,
    screenshot: null,
    element: null,
    checkLinks: false,
    checkImages: false,
    extractText: false,
    extractHeadings: false,
    extractForms: false,
    fill: null,
    click: null,
    wait: 2000,
    viewport: { width: 1920, height: 1080 },
    mobile: false,
    output: null,
    headed: false,
    pdf: null,
    cookies: null,
    auth: null,
    userAgent: null,
    timeout: 30000,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--url': opts.url = args[++i]; break;
      case '--screenshot': opts.screenshot = args[++i] || 'screenshot.png'; break;
      case '--element': opts.element = args[++i]; break;
      case '--check-links': opts.checkLinks = true; break;
      case '--check-images': opts.checkImages = true; break;
      case '--extract-text': opts.extractText = true; break;
      case '--extract-headings': opts.extractHeadings = true; break;
      case '--extract-forms': opts.extractForms = true; break;
      case '--fill': opts.fill = JSON.parse(args[++i]); break;
      case '--click': opts.click = args[++i]; break;
      case '--wait': opts.wait = parseInt(args[++i]); break;
      case '--viewport': {
        const [w, h] = args[++i].split('x').map(Number);
        opts.viewport = { width: w, height: h };
        break;
      }
      case '--mobile': opts.mobile = true; opts.viewport = { width: 375, height: 812 }; break;
      case '--output': opts.output = args[++i]; break;
      case '--headed': opts.headed = true; break;
      case '--pdf': opts.pdf = args[++i]; break;
      case '--cookies': opts.cookies = args[++i]; break;
      case '--auth': opts.auth = args[++i]; break;
      case '--user-agent': opts.userAgent = args[++i]; break;
      case '--timeout': opts.timeout = parseInt(args[++i]); break;
    }
  }

  if (!opts.url) {
    console.error('Error: --url is required');
    console.log('Usage: node browser-test.js --url "https://example.com" [options]');
    console.log('Run with --help for all options');
    process.exit(1);
  }

  // Default: take screenshot if no other action specified
  const hasAction = opts.screenshot || opts.checkLinks || opts.checkImages || 
    opts.extractText || opts.extractHeadings || opts.extractForms || 
    opts.fill || opts.click || opts.pdf;
  if (!hasAction) {
    opts.screenshot = 'screenshot.png';
  }

  return opts;
}

async function run() {
  const opts = parseArgs();
  const results = {
    url: opts.url,
    timestamp: new Date().toISOString(),
    status: null,
    title: null,
    actions: [],
    errors: [],
  };

  console.log(`\n🌐 Browser Test Tool`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Target: ${opts.url}`);
  console.log(`Viewport: ${opts.viewport.width}x${opts.viewport.height}`);
  console.log();

  const browser = await chromium.launch({ headless: !opts.headed });
  const context = await browser.newContext({
    viewport: opts.viewport,
    userAgent: opts.userAgent || undefined,
    httpCredentials: opts.auth ? {
      username: opts.auth.split(':')[0],
      password: opts.auth.split(':').slice(1).join(':'),
    } : undefined,
  });

  // Load cookies if provided
  if (opts.cookies) {
    const cookies = JSON.parse(fs.readFileSync(opts.cookies, 'utf-8'));
    await context.addCookies(cookies);
    console.log(`🍪 Loaded ${cookies.length} cookies`);
  }

  const page = await context.newPage();

  // Track console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  // Navigate
  try {
    const response = await page.goto(opts.url, {
      waitUntil: 'networkidle',
      timeout: opts.timeout,
    });
    results.status = response?.status();
    results.title = await page.title();
    console.log(`✅ Loaded (HTTP ${results.status}): ${results.title}`);
  } catch (err) {
    results.errors.push(`Navigation failed: ${err.message}`);
    console.error(`❌ Navigation failed: ${err.message}`);
    await browser.close();
    process.exit(1);
  }

  // Wait
  if (opts.wait > 0) {
    await page.waitForTimeout(opts.wait);
  }

  // Fill form fields
  if (opts.fill) {
    console.log(`\n📝 Filling form fields...`);
    for (const [selector, value] of Object.entries(opts.fill)) {
      try {
        await page.fill(selector, value);
        console.log(`  ✅ Filled ${selector}`);
        results.actions.push({ action: 'fill', selector, value, success: true });
      } catch (err) {
        console.log(`  ❌ Failed to fill ${selector}: ${err.message}`);
        results.actions.push({ action: 'fill', selector, value, success: false, error: err.message });
      }
    }
  }

  // Click element
  if (opts.click) {
    console.log(`\n👆 Clicking: ${opts.click}`);
    try {
      await page.click(opts.click);
      await page.waitForTimeout(1000);
      console.log(`  ✅ Clicked`);
      results.actions.push({ action: 'click', selector: opts.click, success: true });
    } catch (err) {
      console.log(`  ❌ Click failed: ${err.message}`);
      results.actions.push({ action: 'click', selector: opts.click, success: false, error: err.message });
    }
  }

  // Screenshot
  if (opts.screenshot) {
    const screenshotPath = path.resolve(opts.screenshot);
    if (opts.element) {
      const el = await page.$(opts.element);
      if (el) {
        await el.screenshot({ path: screenshotPath });
        console.log(`📸 Element screenshot saved: ${screenshotPath}`);
      } else {
        console.log(`❌ Element not found: ${opts.element}`);
      }
    } else {
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`📸 Full-page screenshot saved: ${screenshotPath}`);
    }
    results.actions.push({ action: 'screenshot', path: screenshotPath });
  }

  // PDF
  if (opts.pdf) {
    const pdfPath = path.resolve(opts.pdf);
    await page.pdf({ path: pdfPath, format: 'A4', printBackground: true });
    console.log(`📄 PDF saved: ${pdfPath}`);
    results.actions.push({ action: 'pdf', path: pdfPath });
  }

  // Check links
  if (opts.checkLinks) {
    console.log(`\n🔗 Checking links...`);
    const links = await page.$$eval('a[href]', anchors =>
      anchors.map(a => ({ text: a.textContent.trim().substring(0, 50), href: a.href }))
    );
    const linkResults = [];
    let broken = 0;
    for (const link of links.slice(0, 50)) { // Cap at 50 links
      try {
        const res = await page.request.get(link.href, { timeout: 5000 });
        const ok = res.status() < 400;
        if (!ok) broken++;
        linkResults.push({ ...link, status: res.status(), ok });
        console.log(`  ${ok ? '✅' : '❌'} [${res.status()}] ${link.href}`);
      } catch (err) {
        broken++;
        linkResults.push({ ...link, status: 0, ok: false, error: err.message });
        console.log(`  ❌ [FAIL] ${link.href}`);
      }
    }
    console.log(`\n  Total: ${links.length} links, ${broken} broken`);
    results.links = { total: links.length, checked: linkResults.length, broken, details: linkResults };
  }

  // Check images
  if (opts.checkImages) {
    console.log(`\n🖼️  Checking images...`);
    const images = await page.$$eval('img', imgs =>
      imgs.map(img => ({
        src: img.src,
        alt: img.alt || '(no alt text)',
        naturalWidth: img.naturalWidth,
        complete: img.complete,
      }))
    );
    let brokenImages = 0;
    let missingAlt = 0;
    for (const img of images) {
      const isBroken = img.complete && img.naturalWidth === 0;
      if (isBroken) brokenImages++;
      if (!img.alt || img.alt === '(no alt text)') missingAlt++;
      console.log(`  ${isBroken ? '❌' : '✅'} ${img.src.substring(0, 80)} | alt: ${img.alt}`);
    }
    console.log(`\n  Total: ${images.length} images, ${brokenImages} broken, ${missingAlt} missing alt text`);
    results.images = { total: images.length, broken: brokenImages, missingAlt, details: images };
  }

  // Extract headings
  if (opts.extractHeadings) {
    console.log(`\n📋 Heading structure:`);
    const headings = await page.$$eval('h1,h2,h3,h4,h5,h6', els =>
      els.map(el => ({ tag: el.tagName.toLowerCase(), text: el.textContent.trim().substring(0, 100) }))
    );
    for (const h of headings) {
      const indent = '  '.repeat(parseInt(h.tag[1]) - 1);
      console.log(`  ${indent}${h.tag}: ${h.text}`);
    }
    results.headings = headings;
  }

  // Extract forms
  if (opts.extractForms) {
    console.log(`\n📝 Forms found:`);
    const forms = await page.$$eval('form', formEls =>
      formEls.map((form, i) => ({
        index: i,
        action: form.action,
        method: form.method,
        fields: Array.from(form.querySelectorAll('input,select,textarea')).map(f => ({
          tag: f.tagName.toLowerCase(),
          type: f.type || '',
          name: f.name || '',
          id: f.id || '',
          placeholder: f.placeholder || '',
          required: f.required,
        })),
      }))
    );
    for (const form of forms) {
      console.log(`  Form #${form.index}: ${form.method.toUpperCase()} ${form.action}`);
      for (const f of form.fields) {
        console.log(`    - ${f.tag}[${f.type}] name="${f.name}" ${f.required ? '(required)' : ''}`);
      }
    }
    results.forms = forms;
  }

  // Extract text
  if (opts.extractText) {
    const text = await page.innerText('body');
    results.text = text;
    console.log(`\n📄 Page text (${text.length} chars):`);
    console.log(text.substring(0, 2000));
    if (text.length > 2000) console.log(`\n... (${text.length - 2000} more chars)`);
  }

  // Console errors
  if (consoleErrors.length > 0) {
    console.log(`\n⚠️  Console errors (${consoleErrors.length}):`);
    for (const err of consoleErrors.slice(0, 20)) {
      console.log(`  ❌ ${err}`);
    }
    results.consoleErrors = consoleErrors;
  }

  // Save results JSON
  if (opts.output) {
    const outputPath = path.resolve(opts.output);
    fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
    console.log(`\n💾 Results saved: ${outputPath}`);
  }

  await browser.close();
  console.log(`\n✅ Done.`);
}

run().catch(err => {
  console.error(`\n❌ Fatal error: ${err.message}`);
  process.exit(1);
});
