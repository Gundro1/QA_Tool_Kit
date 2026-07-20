/**
 * Universal Accessibility Checker
 * 
 * Runs WCAG accessibility audits on any webpage using axe-core.
 * 
 * Usage:
 *   node accessibility-check.js --url "https://example.com"
 *   node accessibility-check.js --url "https://example.com" --output a11y-report.json
 *   node accessibility-check.js --url "https://example.com" --report a11y-audit
 * 
 * Options:
 *   --url <url>          Target URL (required)
 *   --output <path>      Save raw results to JSON file
 *   --report <name>      Generate HTML+PDF report (uses report-generator.js)
 *   --tags <tags>        Comma-separated axe rule tags (default: wcag2a,wcag2aa,best-practice)
 *   --timeout <ms>       Page load timeout (default: 30000)
 */

const { chromium } = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    url: null,
    output: null,
    report: null,
    tags: ['wcag2a', 'wcag2aa', 'best-practice'],
    timeout: 30000,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--url': opts.url = args[++i]; break;
      case '--output': opts.output = args[++i]; break;
      case '--report': opts.report = args[++i]; break;
      case '--tags': opts.tags = args[++i].split(','); break;
      case '--timeout': opts.timeout = parseInt(args[++i]); break;
    }
  }

  if (!opts.url) {
    console.error('Error: --url is required');
    console.log('Usage: node accessibility-check.js --url "https://example.com" [options]');
    process.exit(1);
  }
  return opts;
}

function severityIcon(impact) {
  switch (impact) {
    case 'critical': return '🔴';
    case 'serious': return '🟠';
    case 'moderate': return '🟡';
    case 'minor': return '🟢';
    default: return '⚪';
  }
}

async function run() {
  const opts = parseArgs();

  console.log(`\n♿ Accessibility Checker`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Target: ${opts.url}`);
  console.log(`Standards: ${opts.tags.join(', ')}`);
  console.log();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(opts.url, { waitUntil: 'networkidle', timeout: opts.timeout });
  } catch (err) {
    console.error(`❌ Failed to load page: ${err.message}`);
    await browser.close();
    process.exit(1);
  }

  const title = await page.title();
  console.log(`Page: ${title}\n`);

  // Run axe audit
  const axeResults = await new AxeBuilder({ page })
    .withTags(opts.tags)
    .analyze();

  const { violations, passes, incomplete } = axeResults;

  // Summary
  console.log(`📊 Results Summary:`);
  console.log(`  ✅ Passed: ${passes.length} rules`);
  console.log(`  ❌ Violations: ${violations.length} rules`);
  console.log(`  ⚠️  Incomplete: ${incomplete.length} rules`);
  console.log();

  // Violations detail
  if (violations.length > 0) {
    console.log(`❌ Violations:`);
    for (const v of violations) {
      console.log(`\n  ${severityIcon(v.impact)} [${v.impact?.toUpperCase()}] ${v.id}`);
      console.log(`     ${v.description}`);
      console.log(`     Help: ${v.helpUrl}`);
      console.log(`     Affected elements: ${v.nodes.length}`);
      for (const node of v.nodes.slice(0, 3)) {
        console.log(`       → ${node.target.join(' > ')}`);
        if (node.failureSummary) {
          console.log(`         ${node.failureSummary.split('\n')[0]}`);
        }
      }
      if (v.nodes.length > 3) {
        console.log(`       ... and ${v.nodes.length - 3} more`);
      }
    }
  } else {
    console.log(`🎉 No accessibility violations found!`);
  }

  // Save raw results
  if (opts.output) {
    const outputPath = path.resolve(opts.output);
    const summary = {
      url: opts.url,
      title,
      timestamp: new Date().toISOString(),
      tags: opts.tags,
      summary: {
        passed: passes.length,
        violations: violations.length,
        incomplete: incomplete.length,
      },
      violations: violations.map(v => ({
        id: v.id,
        impact: v.impact,
        description: v.description,
        help: v.help,
        helpUrl: v.helpUrl,
        affectedElements: v.nodes.length,
        nodes: v.nodes.map(n => ({
          target: n.target.join(' > '),
          html: n.html?.substring(0, 200),
          failureSummary: n.failureSummary,
        })),
      })),
      passes: passes.map(p => ({ id: p.id, description: p.description })),
    };
    fs.writeFileSync(outputPath, JSON.stringify(summary, null, 2));
    console.log(`\n💾 Raw results saved: ${outputPath}`);
  }

  // Generate HTML/PDF report
  if (opts.report) {
    const reportData = {
      sections: [
        {
          heading: 'Audit Summary',
          type: 'key-value',
          data: {
            'URL': opts.url,
            'Page Title': title,
            'Standards Tested': opts.tags.join(', '),
            'Rules Passed': `✅ ${passes.length}`,
            'Violations Found': violations.length > 0 ? `❌ ${violations.length}` : `✅ 0`,
            'Incomplete Checks': `⚠️ ${incomplete.length}`,
            'Date': new Date().toLocaleDateString('en-GB'),
          },
        },
      ],
    };

    if (violations.length > 0) {
      reportData.sections.push({
        heading: 'Violations',
        type: 'table',
        data: violations.map(v => ({
          'Severity': `${severityIcon(v.impact)} ${v.impact}`,
          'Rule': v.id,
          'Description': v.description,
          'Elements': v.nodes.length,
        })),
      });
    }

    const tempJson = path.resolve(path.dirname(opts.report), `_temp_a11y_${Date.now()}.json`);
    fs.writeFileSync(tempJson, JSON.stringify(reportData, null, 2));

    try {
      const reportGen = path.join(__dirname, 'report-generator.js');
      execSync(`node "${reportGen}" --title "Accessibility Audit: ${title}" --input "${tempJson}" --output "${opts.report}" --theme blue`, {
        stdio: 'inherit',
      });
    } finally {
      fs.unlinkSync(tempJson);
    }
  }

  await browser.close();
  console.log(`\n✅ Done.`);
}

run().catch(err => {
  console.error(`❌ Accessibility check failed: ${err.message}`);
  process.exit(1);
});
