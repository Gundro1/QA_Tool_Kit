import { defineConfig, devices } from '@playwright/test';
import path from 'path';

/**
 * QA Toolkit — Playwright Configuration
 *
 * This config supports testing ANY website. Set the target URL via:
 *   - QA_BASE_URL env var
 *   - .env file
 *   - CLI: npx playwright test --config playwright.config.ts
 *
 * Usage:
 *   QA_BASE_URL=https://example.com npx playwright test
 *   npx playwright test --project=chromium
 *   npx playwright test --ui
 */

// Load .env if present
const envFile = path.resolve(__dirname, '.env');
try {
  const { readFileSync, existsSync } = require('fs');
  if (existsSync(envFile)) {
    for (const line of readFileSync(envFile, 'utf-8').split('\n')) {
      const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?$/);
      if (match) {
        const [, key, value = ''] = match;
        process.env[key] ??= value.replace(/^['"]|['"]$/g, '');
      }
    }
  }
} catch {}

export default defineConfig({
  testDir: './specs',
  testMatch: '**/*.spec.ts',
  timeout: parseInt(process.env.QA_TIMEOUT_MS || '30000'),
  fullyParallel: true,

  // Fail CI if test.only is committed
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: process.env.CI
    ? [['html', { open: 'never' }], ['json', { outputFile: 'reports/results.json' }]]
    : 'html',

  use: {
    baseURL: process.env.QA_BASE_URL || '',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
});
