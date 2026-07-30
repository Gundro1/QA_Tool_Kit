#!/usr/bin/env node
/**
 * Universal QA Toolkit — Lightweight HTTP URL Content Extractor (url-fetch.js)
 * Fetches web pages, APIs, and XML sitemaps without browser overhead.
 * Author: Azeez
 */

const https = require('https');
const http = require('http');
const { URL } = require('url');
const fs = require('fs');

function fetchUrl(targetUrl, headers = {}) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(targetUrl);
    const client = parsed.protocol === 'https:' ? https : http;

    const reqOptions = {
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
      path: parsed.pathname + parsed.search,
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) QA-Toolkit/1.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,json/application;q=0.8,*/*;q=0.8',
        ...headers
      }
    };

    const req = client.request(reqOptions, (res) => {
      let data = '';
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        const redirectUrl = new URL(res.headers.location, targetUrl).href;
        return resolve(fetchUrl(redirectUrl, headers));
      }

      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          body: data
        });
      });
    });

    req.on('error', (err) => reject(err));
    req.end();
  });
}

function htmlToMarkdown(html) {
  let text = html;
  // Remove script and style tags
  text = text.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  text = text.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
  
  // Format headings
  text = text.replace(/<h1[^>]*>(.*?)<\/h1>/gi, '\n# $1\n');
  text = text.replace(/<h2[^>]*>(.*?)<\/h2>/gi, '\n## $1\n');
  text = text.replace(/<h3[^>]*>(.*?)<\/h3>/gi, '\n### $1\n');
  text = text.replace(/<p[^>]*>(.*?)<\/p>/gi, '\n$1\n');
  text = text.replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1\n');
  
  // Strip all remaining HTML tags
  text = text.replace(/<[^>]+>/g, '');
  
  // Decode HTML entities
  text = text.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"');

  // Collapse multiple empty lines
  return text.split('\n').map(line => line.trim()).filter(line => line).join('\n\n');
}

function extractJsonLd(html) {
  const jsonLdBlocks = [];
  const regex = /<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = regex.exec(html)) !== null) {
    try {
      jsonLdBlocks.push(JSON.parse(match[1].trim()));
    } catch (e) {
      jsonLdBlocks.push({ raw: match[1].trim(), error: "Invalid JSON" });
    }
  }
  return jsonLdBlocks;
}

async function main() {
  const args = process.argv.slice(2);
  let targetUrl = '';
  let format = 'markdown'; // markdown, jsonld, raw, json
  let outputFile = '';

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--url' && args[i + 1]) {
      targetUrl = args[i + 1];
      i++;
    } else if (args[i] === '--format' && args[i + 1]) {
      format = args[i + 1].toLowerCase();
      i++;
    } else if (args[i] === '--output' && args[i + 1]) {
      outputFile = args[i + 1];
      i++;
    }
  }

  if (!targetUrl) {
    console.error('Usage: node url-fetch.js --url "https://example.com" [--format markdown|jsonld|raw|json] [--output file.ext]');
    process.exit(1);
  }

  try {
    const res = await fetchUrl(targetUrl);
    let outputContent = '';

    if (format === 'markdown') {
      outputContent = htmlToMarkdown(res.body);
    } else if (format === 'jsonld') {
      const jsonLd = extractJsonLd(res.body);
      outputContent = JSON.stringify(jsonLd, null, 2);
    } else if (format === 'json') {
      try {
        const parsed = JSON.parse(res.body);
        outputContent = JSON.stringify(parsed, null, 2);
      } catch (e) {
        outputContent = res.body;
      }
    } else {
      outputContent = res.body;
    }

    if (outputFile) {
      fs.writeFileSync(outputFile, outputContent, 'utf-8');
      console.log(`Saved output to '${outputFile}' (${outputContent.length} bytes)`);
    } else {
      console.log(outputContent);
    }
  } catch (err) {
    console.error(`Fetch Error: ${err.message}`);
    process.exit(1);
  }
}

main();
