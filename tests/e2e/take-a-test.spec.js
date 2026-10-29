/**
 * E2E — Take-a-test journey
 *
 * Authenticated user opens the test list, picks the first test in the browse
 * grid, starts it from the preview page, and answers a question.
 *
 * Uses the browse grid rather than "Today's Test Load": daily cards jump
 * straight into type-specific trainers (pinyin, pitch accent), so where they
 * land depends on the day's load. Grid cards always go through /preview.
 *
 * Runs with auth state from playwright/.auth/user.json (set by auth.setup.js).
 */

import { test, expect } from '@playwright/test';

const firstCard = (page) => page.locator('#tests-grid .test-card').first();

async function openPreview(page) {
  await page.goto('/tests');
  await firstCard(page).click();
  await expect(page).toHaveURL(/\/test\/[^/]+\/preview/);
}

async function startTest(page) {
  await openPreview(page);
  // startTest() needs the test details the preview fetches; clicking earlier is a no-op.
  await expect(page.locator('#testTitle')).not.toHaveText('Loading...', { timeout: 15_000 });
  await page.locator('#startTestBtn').click();
  await expect(page).toHaveURL(/\/test\/[^/?]+\?type=/);
}

test.describe('Take-a-test journey', () => {
  test('test list page loads and shows at least one test', async ({ page }) => {
    await page.goto('/tests');
    // Should NOT redirect to login or the language picker
    await expect(page).toHaveURL(/\/tests/);
    await expect(firstCard(page)).toBeVisible({ timeout: 10_000 });
  });

  test('clicking a test opens its preview', async ({ page }) => {
    await openPreview(page);
    await expect(page.locator('#testTitle')).not.toHaveText('Loading...', { timeout: 15_000 });
    await expect(page.locator('#startTestBtn')).toBeVisible();
  });

  test('starting a test renders its questions', async ({ page }) => {
    await startTest(page);
    await expect(page.locator('#questionsContainer .answer-option').first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('choosing an answer marks it selected', async ({ page }) => {
    await startTest(page);
    const option = page.locator('#answers-0 .answer-option').first();
    await option.click({ timeout: 15_000 });
    await expect(option).toHaveClass(/selected/);
    await expect(option.locator('input[type="radio"]')).toBeChecked();
  });
});
