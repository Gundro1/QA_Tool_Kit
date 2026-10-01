/**
 * Base Fixture — the ONLY file that imports from @playwright/test directly.
 *
 * Every spec file imports { test, expect } from here, not from Playwright.
 * This lets us extend the test object project-wide without touching every spec.
 *
 * Usage in spec files:
 *   import { test, expect } from '../fixtures/base.fixture';
 */

import { test as base, expect } from '@playwright/test';

// Extend with custom fixtures here as needed.
// Example:
//   export const test = base.extend<{ apiClient: ApiClient }>({
//     apiClient: async ({ request }, use) => {
//       await use(new ApiClient(request));
//     },
//   });

export const test = base.extend({});
export { expect };
