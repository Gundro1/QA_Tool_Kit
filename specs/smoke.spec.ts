/**
 * Smoke Test — Universal website health check.
 *
 * Works with ANY website. Set QA_BASE_URL to target it:
 *   QA_BASE_URL=https://example.com npx playwright test specs/smoke.spec.ts
 *
 * Checks:
 *   1. Homepage loads (200)
 *   2. Page title exists
 *   3. No console errors
 *   4. No broken images
 *   5. All internal links respond
 *   6. Basic mobile responsiveness
 */

import { test, expect } from '../fixtures/base.fixture';

test.describe('Smoke Tests @smoke', () => {
  test('homepage loads successfully', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
  });

  test('page has a title', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });

  test('no critical console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Filter out known benign errors (analytics, third-party scripts)
    const criticalErrors = errors.filter(
      e => !e.includes('favicon') && !e.includes('analytics') && !e.includes('gtag')
    );
    expect(criticalErrors).toEqual([]);
  });

  test('no broken images on homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const images = page.locator('img[src]');
    const count = await images.count();

    for (let i = 0; i < count; i++) {
      const img = images.nth(i);
      const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth);
      const src = await img.getAttribute('src');
      expect(naturalWidth, `Image broken: ${src}`).toBeGreaterThan(0);
    }
  });

  test('internal links return valid responses', async ({ page, request }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const links = await page.locator('a[href]').evaluateAll((anchors: HTMLAnchorElement[]) =>
      anchors
        .map(a => a.href)
        .filter(href => href.startsWith(window.location.origin))
        .filter((href, idx, arr) => arr.indexOf(href) === idx) // unique
        .slice(0, 20) // cap at 20 to avoid timeout
    );

    for (const link of links) {
      const resp = await request.get(link);
      expect(resp.status(), `Broken link: ${link}`).toBeLessThan(400);
    }
  });

  test('page is responsive at mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 }); // iPhone X
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check no horizontal overflow
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = 375;
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10); // 10px tolerance
  });
});
