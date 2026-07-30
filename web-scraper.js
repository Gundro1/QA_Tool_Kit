#!/usr/bin/env node
/**
 * Universal QA Toolkit — Structured Web & Store Locator Scraper (web-scraper.js)
 * Extract structured records from JS-rendered web pages, store locators, and tables using Playwright.
 * Author: Azeez
 */

const { chromium } = require('playwright');
const fs = require('fs');

async function scrapePage(options) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  console.log(`Navigating to ${options.url}...`);
  await page.goto(options.url, { waitUntil: 'networkidle', timeout: 30000 });

  if (options.waitSelector) {
    await page.waitForSelector(options.waitSelector, { timeout: 10000 }).catch(() => {});
  }

  let records = [];

  if (options.strategy === 'json-ld') {
    const scripts = await page.$$eval('script[type="application/ld+json"]', elements =>
      elements.map(e => e.textContent)
    );
    for (const text of scripts) {
      try {
        const parsed = JSON.parse(text);
        if (Array.isArray(parsed)) {
          records.push(...parsed);
        } else if (parsed['@graph']) {
          records.push(...parsed['@graph']);
        } else {
          records.push(parsed);
        }
      } catch (e) {}
    }
  } else if (options.selector) {
    records = await page.$$eval(options.selector, (elements, fieldMap) => {
      return elements.map(el => {
        if (!fieldMap) return { text: el.textContent.trim() };
        const record = {};
        for (const [key, selector] of Object.entries(fieldMap)) {
          const target = el.querySelector(selector);
          record[key] = target ? target.textContent.trim() : '';
        }
        return record;
      });
    }, options.fields);
  } else {
    // Default fallback: extract visible text and headings
    records = await page.evaluate(() => {
      const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent.trim());
      return { title: document.title, headings };
    });
  }

  await browser.close();
  return records;
}

async function main() {
  const args = process.argv.slice(2);
  let options = {
    url: '',
    strategy: 'dom', // dom, json-ld
    selector: '',
    fields: null,
    output: '',
    waitSelector: ''
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--url' && args[i + 1]) {
      options.url = args[i + 1]; i++;
    } else if (args[i] === '--strategy' && args[i + 1]) {
      options.strategy = args[i + 1]; i++;
    } else if (args[i] === '--selector' && args[i + 1]) {
      options.selector = args[i + 1]; i++;
    } else if (args[i] === '--fields' && args[i + 1]) {
      // Format: "name:h3,address:.addr,phone:.tel"
      const pairs = args[i + 1].split(',');
      options.fields = {};
      pairs.forEach(p => {
        const [k, v] = p.split(':');
        if (k && v) options.fields[k.trim()] = v.trim();
      });
      i++;
    } else if (args[i] === '--output' && args[i + 1]) {
      options.output = args[i + 1]; i++;
    } else if (args[i] === '--wait' && args[i + 1]) {
      options.waitSelector = args[i + 1]; i++;
    }
  }

  if (!options.url) {
    console.error('Usage: node web-scraper.js --url "https://example.com/stores" [--strategy json-ld|dom] [--selector "div.store-card"] [--fields "name:h3,address:.addr"] [--output stores.json]');
    process.exit(1);
  }

  try {
    const results = await scrapePage(options);
    const outputText = JSON.stringify(results, null, 2);

    if (options.output) {
      fs.writeFileSync(options.output, outputText, 'utf-8');
      console.log(`Extracted ${Array.isArray(results) ? results.length : 1} records → Saved to '${options.output}'`);
    } else {
      console.log(outputText);
    }
  } catch (err) {
    console.error(`Scraping Error: ${err.message}`);
    process.exit(1);
  }
}

main();
