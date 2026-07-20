/**
 * Universal Report Generator
 * 
 * Generates professional, styled HTML + PDF reports from JSON data.
 * Works for any project — QA audits, entity checks, test results, anything.
 * 
 * Usage:
 *   node report-generator.js --title "QA Audit Report" --input data.json --output report
 *   node report-generator.js --title "Entity Audit" --author "Azeez" --input findings.json --output audit
 *   node report-generator.js --title "Test Results" --sections '[{"heading":"Summary","body":"All passed"}]'
 * 
 * Options:
 *   --title <text>       Report title (required)
 *   --author <name>      Author name (default: Azeez)
 *   --input <path>       JSON data file to include
 *   --sections <json>    Inline sections as JSON array
 *   --output <name>      Output base name (creates <name>.html and <name>.pdf)
 *   --date <text>        Report date (default: today)
 *   --logo <path>        Logo image path (optional)
 *   --theme <name>       Color theme: dark, light, blue, green (default: dark)
 *   --no-pdf             Skip PDF generation (HTML only)
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    title: null,
    author: 'Azeez',
    input: null,
    sections: null,
    output: 'report',
    date: new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }),
    logo: null,
    theme: 'dark',
    noPdf: false,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--title': opts.title = args[++i]; break;
      case '--author': opts.author = args[++i]; break;
      case '--input': opts.input = args[++i]; break;
      case '--sections': opts.sections = JSON.parse(args[++i]); break;
      case '--output': opts.output = args[++i]; break;
      case '--date': opts.date = args[++i]; break;
      case '--logo': opts.logo = args[++i]; break;
      case '--theme': opts.theme = args[++i]; break;
      case '--no-pdf': opts.noPdf = true; break;
    }
  }

  if (!opts.title) {
    console.error('Error: --title is required');
    console.log('Usage: node report-generator.js --title "Report Title" [options]');
    process.exit(1);
  }
  return opts;
}

const THEMES = {
  dark: {
    bg: '#0f0f23', cardBg: '#1a1a2e', text: '#e0e0e0', heading: '#ffffff',
    accent: '#00d4ff', accent2: '#7c3aed', border: '#2a2a4a',
    tableBg: '#16162a', tableStripe: '#1e1e38', success: '#22c55e',
    warning: '#f59e0b', error: '#ef4444',
  },
  light: {
    bg: '#f8fafc', cardBg: '#ffffff', text: '#334155', heading: '#0f172a',
    accent: '#2563eb', accent2: '#7c3aed', border: '#e2e8f0',
    tableBg: '#ffffff', tableStripe: '#f1f5f9', success: '#16a34a',
    warning: '#d97706', error: '#dc2626',
  },
  blue: {
    bg: '#0c1222', cardBg: '#131d35', text: '#cbd5e1', heading: '#f1f5f9',
    accent: '#38bdf8', accent2: '#818cf8', border: '#1e3a5f',
    tableBg: '#0f1a2e', tableStripe: '#152238', success: '#34d399',
    warning: '#fbbf24', error: '#f87171',
  },
  green: {
    bg: '#0a1612', cardBg: '#0f2318', text: '#d1d5db', heading: '#f0fdf4',
    accent: '#4ade80', accent2: '#2dd4bf', border: '#1a3a2a',
    tableBg: '#0d1f16', tableStripe: '#132e1f', success: '#22c55e',
    warning: '#fbbf24', error: '#f87171',
  },
};

function buildSections(opts) {
  let sections = [];

  // From --sections flag
  if (opts.sections) {
    sections = opts.sections;
  }

  // From --input JSON file
  if (opts.input) {
    const raw = JSON.parse(fs.readFileSync(path.resolve(opts.input), 'utf-8'));

    if (Array.isArray(raw)) {
      // Array of objects → table
      sections.push({
        heading: 'Data',
        type: 'table',
        data: raw,
      });
    } else if (raw.sections) {
      // Structured report format
      sections = sections.concat(raw.sections);
    } else {
      // Key-value summary
      sections.push({
        heading: 'Summary',
        type: 'key-value',
        data: raw,
      });
    }
  }

  if (sections.length === 0) {
    sections.push({ heading: 'Report', body: 'No data provided. Use --input or --sections to add content.' });
  }

  return sections;
}

function renderSection(section, theme) {
  const t = THEMES[theme];
  let content = '';

  if (section.type === 'table' && Array.isArray(section.data) && section.data.length > 0) {
    const keys = Object.keys(section.data[0]);
    content = `
      <table>
        <thead><tr>${keys.map(k => `<th>${k}</th>`).join('')}</tr></thead>
        <tbody>
          ${section.data.map((row, i) => `
            <tr style="background:${i % 2 === 0 ? t.tableBg : t.tableStripe}">
              ${keys.map(k => {
                let val = row[k];
                // Color-code status fields
                if (typeof val === 'string') {
                  if (['pass', 'ok', 'true', 'yes', 'active', 'found'].includes(val.toLowerCase())) {
                    val = `<span style="color:${t.success};font-weight:600">✅ ${val}</span>`;
                  } else if (['fail', 'error', 'false', 'no', 'closed', 'not found'].includes(val.toLowerCase())) {
                    val = `<span style="color:${t.error};font-weight:600">❌ ${val}</span>`;
                  } else if (['warning', 'pending', 'unknown', 'mismatch'].includes(val.toLowerCase())) {
                    val = `<span style="color:${t.warning};font-weight:600">⚠️ ${val}</span>`;
                  }
                }
                return `<td>${val}</td>`;
              }).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } else if (section.type === 'key-value' && section.data) {
    content = `<div class="kv-grid">
      ${Object.entries(section.data).map(([k, v]) => `
        <div class="kv-key">${k}</div>
        <div class="kv-val">${typeof v === 'object' ? JSON.stringify(v) : v}</div>
      `).join('')}
    </div>`;
  } else if (section.type === 'list' && Array.isArray(section.items)) {
    content = `<ul>${section.items.map(item => `<li>${item}</li>`).join('')}</ul>`;
  } else if (section.body) {
    content = `<p>${section.body.replace(/\n/g, '<br>')}</p>`;
  }

  return `
    <div class="section">
      <h2>${section.heading || 'Section'}</h2>
      ${content}
    </div>`;
}

function generateHTML(opts) {
  const t = THEMES[opts.theme] || THEMES.dark;
  const sections = buildSections(opts);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${opts.title}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: ${t.bg};
      color: ${t.text};
      line-height: 1.6;
      padding: 40px;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    
    /* Header */
    .header {
      background: linear-gradient(135deg, ${t.cardBg}, ${t.bg});
      border: 1px solid ${t.border};
      border-radius: 16px;
      padding: 48px;
      margin-bottom: 32px;
      position: relative;
      overflow: hidden;
    }
    .header::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 4px;
      background: linear-gradient(90deg, ${t.accent}, ${t.accent2});
    }
    .header h1 {
      font-size: 2.2rem;
      font-weight: 700;
      color: ${t.heading};
      margin-bottom: 16px;
    }
    .header-meta {
      display: flex;
      gap: 32px;
      color: ${t.text};
      opacity: 0.8;
      font-size: 0.9rem;
    }
    .header-meta span { display: flex; align-items: center; gap: 6px; }
    
    /* Sections */
    .section {
      background: ${t.cardBg};
      border: 1px solid ${t.border};
      border-radius: 12px;
      padding: 32px;
      margin-bottom: 24px;
    }
    .section h2 {
      font-size: 1.3rem;
      font-weight: 600;
      color: ${t.accent};
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid ${t.border};
    }
    .section p { font-size: 0.95rem; line-height: 1.8; }
    .section ul { padding-left: 24px; }
    .section li { margin-bottom: 8px; }
    
    /* Tables */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      border-radius: 8px;
      overflow: hidden;
    }
    th {
      background: linear-gradient(135deg, ${t.accent}22, ${t.accent2}22);
      color: ${t.accent};
      font-weight: 600;
      text-align: left;
      padding: 12px 16px;
      border-bottom: 2px solid ${t.border};
      white-space: nowrap;
    }
    td {
      padding: 10px 16px;
      border-bottom: 1px solid ${t.border};
      max-width: 300px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    
    /* Key-Value Grid */
    .kv-grid {
      display: grid;
      grid-template-columns: 200px 1fr;
      gap: 1px;
      background: ${t.border};
      border-radius: 8px;
      overflow: hidden;
    }
    .kv-key {
      background: ${t.tableStripe};
      padding: 12px 16px;
      font-weight: 600;
      color: ${t.accent};
      font-size: 0.9rem;
    }
    .kv-val {
      background: ${t.tableBg};
      padding: 12px 16px;
      font-size: 0.9rem;
    }
    
    /* Footer */
    .footer {
      text-align: center;
      padding: 24px;
      color: ${t.text};
      opacity: 0.5;
      font-size: 0.8rem;
    }
    
    @media print {
      body { padding: 20px; background: white; color: #333; }
      .section { break-inside: avoid; border-color: #ddd; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${opts.title}</h1>
      <div class="header-meta">
        <span>📋 Author: ${opts.author}</span>
        <span>📅 Date: ${opts.date}</span>
        <span>🏷️ Generated by QA Toolkit</span>
      </div>
    </div>
    
    ${sections.map(s => renderSection(s, opts.theme)).join('\n')}
    
    <div class="footer">
      Generated by QA Toolkit • ${opts.date}
    </div>
  </div>
</body>
</html>`;
}

async function run() {
  const opts = parseArgs();

  console.log(`\n📊 Report Generator`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Title: ${opts.title}`);
  console.log(`Author: ${opts.author}`);
  console.log(`Theme: ${opts.theme}`);
  console.log();

  const html = generateHTML(opts);
  const htmlPath = path.resolve(`${opts.output}.html`);
  fs.writeFileSync(htmlPath, html);
  console.log(`📄 HTML report saved: ${htmlPath}`);

  if (!opts.noPdf) {
    console.log(`📄 Generating PDF...`);
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle' });
    const pdfPath = path.resolve(`${opts.output}.pdf`);
    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true,
      margin: { top: '20px', bottom: '20px', left: '20px', right: '20px' },
    });
    await browser.close();
    console.log(`📄 PDF report saved: ${pdfPath}`);
  }

  console.log(`\n✅ Done.`);
}

run().catch(err => {
  console.error(`❌ Report generation failed: ${err.message}`);
  process.exit(1);
});
