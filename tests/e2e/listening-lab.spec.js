/**
 * E2E — Listening Lab journey
 *
 * Authenticated user navigates to the listening lab, verifies the page loads
 * and the audio player / episode list is present.
 *
 * Runs with auth state from playwright/.auth/user.json (set by auth.setup.js).
 */

import { test, expect } from '@playwright/test';

test.describe('Listening Lab journey', () => {
  test('listening lab list page loads without redirecting to login', async ({ page }) => {
    await page.goto('/listening-lab');
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.locator('body')).not.toContainText('404');
  });

  test('listening lab page has a main content area', async ({ page }) => {
    await page.goto('/listening-lab');
    // The page should render something beyond a blank body
    const body = page.locator('body');
    await expect(body).not.toBeEmpty();
    // A heading or episode list should be present
    const heading = page.locator('h1, h2, h3, .listening-lab-title, [data-testid="lab-heading"]');
    await expect(heading.first()).toBeVisible({ timeout: 10_000 });
  });

  test('clicking an episode navigates to its player page', async ({ page }) => {
    await page.goto('/listening-lab');
    const episodeLink = page.locator('a[href*="/listening-lab/"]').first();

    // Skip if there are no episodes (empty DB state in some environments)
    const count = await episodeLink.count();
    if (count === 0) {
      test.skip(true, 'No listening lab episodes found — skipping navigation test.');
      return;
    }

    await episodeLink.click();
    await expect(page).toHaveURL(/\/listening-lab\/.+/);
    await expect(page.locator('body')).not.toContainText('404');
  });
});
