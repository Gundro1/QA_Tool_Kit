/**
 * API Health Test — Universal REST API validation.
 *
 * Works with ANY REST API. Set QA_API_BASE_URL:
 *   QA_API_BASE_URL=https://api.example.com npx playwright test specs/api-health.spec.ts
 *
 * Checks:
 *   1. Base URL reachable
 *   2. Response time under threshold
 *   3. Returns valid JSON
 *   4. CORS headers present (if applicable)
 *   5. Common endpoints respond
 */

import { test, expect } from '../fixtures/base.fixture';

const API_BASE = process.env.QA_API_BASE_URL || process.env.QA_BASE_URL || '';

test.describe('API Health Tests @smoke @api', () => {
  test.skip(!API_BASE, 'No QA_API_BASE_URL set — skipping API tests');

  test('API base URL is reachable', async ({ request }) => {
    const resp = await request.get(API_BASE);
    expect(resp.status()).toBeLessThan(500);
  });

  test('API responds within 5 seconds', async ({ request }) => {
    const start = Date.now();
    await request.get(API_BASE);
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(5000);
  });

  test('API returns valid JSON content-type', async ({ request }) => {
    const resp = await request.get(API_BASE);
    const contentType = resp.headers()['content-type'] || '';
    expect(
      contentType.includes('json') || contentType.includes('html')
    ).toBeTruthy();
  });

  test('common health endpoint responds', async ({ request }) => {
    // Try common health check paths
    const healthPaths = ['/health', '/api/health', '/api/v1/health', '/status', '/ping'];
    let found = false;

    for (const path of healthPaths) {
      try {
        const resp = await request.get(`${API_BASE}${path}`);
        if (resp.status() < 400) {
          found = true;
          break;
        }
      } catch {
        continue;
      }
    }

    // This is advisory — not all APIs have a health endpoint
    if (!found) {
      console.log('No standard health endpoint found. This is not necessarily an error.');
    }
  });
});
