/**
 * Universal Web Search Tool
 * 
 * Search the web without any API key — uses DuckDuckGo Lite.
 * 
 * Usage:
 *   node web-search.js --query "business name Angola"
 *   node web-search.js --query "Candando supermarket closed" --results 5
 *   node web-search.js --query "PrimBooks ERP" --output results.json
 * 
 * Options:
 *   --query <text>       Search query (required)
 *   --results <n>        Number of results to return (default: 10)
 *   --output <path>      Save results to JSON file
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { query: null, results: 10, output: null };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--query': case '-q': opts.query = args[++i]; break;
      case '--results': case '-n': opts.results = parseInt(args[++i]); break;
      case '--output': case '-o': opts.output = args[++i]; break;
    }
  }

  if (!opts.query) {
    console.error('Error: --query is required');
    console.log('Usage: node web-search.js --query "search terms" [--results 10] [--output file.json]');
    process.exit(1);
  }
  return opts;
}

async function searchDuckDuckGo(query, maxResults) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  // Try DuckDuckGo lite (most reliable for scraping)
  const searchUrl = `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`;

  try {
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);

    // DuckDuckGo Lite uses a table-based layout
    const results = await page.evaluate((max) => {
      const items = [];
      
      // Method 1: Try lite format (table rows with links)
      const links = document.querySelectorAll('a.result-link, table a[href^="http"]');
      const snippets = document.querySelectorAll('.result-snippet, td.result-snippet');
      
      if (links.length > 0) {
        links.forEach((link, i) => {
          if (i >= max) return;
          const href = link.href || link.getAttribute('href') || '';
          if (href && !href.includes('duckduckgo.com') && href.startsWith('http')) {
            items.push({
              rank: items.length + 1,
              title: link.textContent.trim() || '(no title)',
              url: href,
              snippet: snippets[i] ? snippets[i].textContent.trim() : '',
            });
          }
        });
      }

      // Method 2: Fallback — get all external links from the page
      if (items.length === 0) {
        const allLinks = document.querySelectorAll('a[href^="http"]');
        allLinks.forEach((link, i) => {
          const href = link.href || '';
          if (href && !href.includes('duckduckgo') && !href.includes('duck.co') && items.length < max) {
            const text = link.textContent.trim();
            if (text && text.length > 3) {
              items.push({
                rank: items.length + 1,
                title: text.substring(0, 200),
                url: href,
                snippet: '',
              });
            }
          }
        });
      }

      return items;
    }, maxResults);

    // If still no results, try getting the page text for debugging
    if (results.length === 0) {
      // Fallback: try Bing
      console.log('  DuckDuckGo returned no results, trying Bing...');
      const bingUrl = `https://www.bing.com/search?q=${encodeURIComponent(query)}`;
      await page.goto(bingUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);

      const bingResults = await page.evaluate((max) => {
        const items = [];
        const entries = document.querySelectorAll('.b_algo, li.b_algo');
        entries.forEach((entry, i) => {
          if (i >= max) return;
          const linkEl = entry.querySelector('h2 a, a');
          const snippetEl = entry.querySelector('.b_caption p, p');
          if (linkEl) {
            items.push({
              rank: i + 1,
              title: linkEl.textContent.trim(),
              url: linkEl.href,
              snippet: snippetEl ? snippetEl.textContent.trim() : '',
            });
          }
        });
        return items;
      }, maxResults);

      await browser.close();
      return bingResults;
    }

    await browser.close();
    return results;
  } catch (err) {
    await browser.close();
    throw err;
  }
}

async function run() {
  const opts = parseArgs();

  console.log(`\n🔍 Web Search Tool`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Query: "${opts.query}"`);
  console.log(`Max results: ${opts.results}`);
  console.log();

  const results = await searchDuckDuckGo(opts.query, opts.results);

  if (results.length === 0) {
    console.log('⚠️  No results found from any search engine.');
  } else {
    console.log(`Found ${results.length} results:\n`);
    for (const r of results) {
      console.log(`  ${r.rank}. ${r.title}`);
      console.log(`     ${r.url}`);
      if (r.snippet) console.log(`     ${r.snippet}`);
      console.log();
    }
  }

  if (opts.output) {
    const outputPath = path.resolve(opts.output);
    fs.writeFileSync(outputPath, JSON.stringify({ query: opts.query, timestamp: new Date().toISOString(), results }, null, 2));
    console.log(`💾 Results saved: ${outputPath}`);
  }

  console.log(`✅ Done.`);
}

run().catch(err => {
  console.error(`❌ Search failed: ${err.message}`);
  process.exit(1);
});
