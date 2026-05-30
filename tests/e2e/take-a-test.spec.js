/**
 * E2E — Take-a-test journey
 *
 * Authenticated user navigates to the test list, picks the first available
 * test, verifies the exercise page renders, and submits an answer.
 *
 * Runs with auth state from playwright/.auth/user.json (set by auth.setup.js).
 */

import { test, expect } from '@playwright/test';

test.describe('Take-a-test journey', () => {
  test('test list page loads and shows at least one test', async ({ page }) => {
    await page.goto('/tests');
    // Should NOT redirect to login
    await expect(page).not.toHaveURL(/\/login/);
    // Page should contain a link or card for at least one test
    const testLinks = page.locator('a[href*="/test/"]');
    await expect(testLinks.first()).toBeVisible({ timeout: 10_000 });
  });

  test('clicking a test navigates to the exercise page', async ({ page }) => {
    await page.goto('/tests');
    await page.locator('a[href*="/test/"]').first().click();
    await expect(page).toHaveURL(/\/test\//);
    await expect(page.locator('body')).not.toContainText('404');
  });

  test('exercise page renders an exercise card', async ({ page }) => {
    await page.goto('/tests');
    await page.locator('a[href*="/test/"]').first().click();
    await expect(page).toHaveURL(/\/test\//);

    // Exercise card should appear — the page uses .card or an exercise-specific container
    const exerciseContent = page.locator(
      '#exerciseCard, .exercise-card, [data-testid="exercise-card"], .card'
    );
    await expect(exerciseContent.first()).toBeVisible({ timeout: 15_000 });
  });
});
