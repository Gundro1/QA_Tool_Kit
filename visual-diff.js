/**
 * Visual Diff / Regression Tool
 * 
 * Compare two screenshots pixel-by-pixel to detect visual changes.
 * 
 * Usage:
 *   node visual-diff.js --baseline before.png --current after.png
 *   node visual-diff.js --baseline before.png --current after.png --output diff.png --threshold 0.1
 * 
 * Options:
 *   --baseline <path>    Baseline/reference screenshot (required)
 *   --current <path>     Current screenshot to compare (required)
 *   --output <path>      Save diff image (default: diff-output.png)
 *   --threshold <0-1>    Pixel matching threshold (default: 0.1, lower = stricter)
 */

const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const pixelmatch = require('pixelmatch');

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { baseline: null, current: null, output: 'diff-output.png', threshold: 0.1 };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--baseline': case '-b': opts.baseline = args[++i]; break;
      case '--current': case '-c': opts.current = args[++i]; break;
      case '--output': case '-o': opts.output = args[++i]; break;
      case '--threshold': case '-t': opts.threshold = parseFloat(args[++i]); break;
    }
  }

  if (!opts.baseline || !opts.current) {
    console.error('Error: --baseline and --current are required');
    console.log('Usage: node visual-diff.js --baseline before.png --current after.png [options]');
    process.exit(1);
  }
  return opts;
}

function run() {
  const opts = parseArgs();

  console.log(`\n🔍 Visual Diff Tool`);
  console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Baseline: ${opts.baseline}`);
  console.log(`Current:  ${opts.current}`);
  console.log(`Threshold: ${opts.threshold}`);
  console.log();

  // Read images
  const baselineData = fs.readFileSync(path.resolve(opts.baseline));
  const currentData = fs.readFileSync(path.resolve(opts.current));
  const baseline = PNG.sync.read(baselineData);
  const current = PNG.sync.read(currentData);

  // Check dimensions
  if (baseline.width !== current.width || baseline.height !== current.height) {
    console.log(`⚠️  Images have different dimensions:`);
    console.log(`   Baseline: ${baseline.width}x${baseline.height}`);
    console.log(`   Current:  ${current.width}x${current.height}`);
    console.log(`   Resizing comparison to smaller dimensions...`);
  }

  const width = Math.min(baseline.width, current.width);
  const height = Math.min(baseline.height, current.height);

  // Create diff image
  const diff = new PNG({ width, height });

  const numDiffPixels = pixelmatch(
    baseline.data, current.data, diff.data,
    width, height,
    { threshold: opts.threshold, includeAA: true }
  );

  const totalPixels = width * height;
  const diffPercent = ((numDiffPixels / totalPixels) * 100).toFixed(2);

  // Save diff image
  const outputPath = path.resolve(opts.output);
  fs.writeFileSync(outputPath, PNG.sync.write(diff));

  // Report
  console.log(`📊 Results:`);
  console.log(`   Image size: ${width}x${height}`);
  console.log(`   Total pixels: ${totalPixels.toLocaleString()}`);
  console.log(`   Different pixels: ${numDiffPixels.toLocaleString()}`);
  console.log(`   Difference: ${diffPercent}%`);
  console.log();

  if (numDiffPixels === 0) {
    console.log(`✅ Images are identical — no visual changes detected.`);
  } else if (parseFloat(diffPercent) < 1) {
    console.log(`🟡 Minor differences detected (${diffPercent}%) — likely sub-pixel rendering.`);
  } else if (parseFloat(diffPercent) < 5) {
    console.log(`🟠 Moderate differences detected (${diffPercent}%) — review the diff image.`);
  } else {
    console.log(`🔴 Significant differences detected (${diffPercent}%) — visual regression likely.`);
  }

  console.log(`\n📸 Diff image saved: ${outputPath}`);
  console.log(`✅ Done.`);

  // Exit with code 1 if significant diff
  if (parseFloat(diffPercent) >= 5) {
    process.exit(1);
  }
}

run();
