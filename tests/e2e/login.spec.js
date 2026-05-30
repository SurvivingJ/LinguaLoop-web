/**
 * E2E — Login journey
 *
 * Validates the unauthenticated redirect and the login page structure.
 * Does NOT go through OTP (auth state is handled by auth.setup.js).
 */

import { test, expect } from '@playwright/test';

// These tests run without stored auth state — override storageState to empty.
test.use({ storageState: { cookies: [], origins: [] } });

test.describe('Login page', () => {
  test('unauthenticated visit to / redirects to /login', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });

  test('login page has email input and submit button', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#email-form button[type="submit"]')).toBeVisible();
  });

  test('OTP step is hidden until email is submitted', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('#otp-step')).toBeHidden();
    await expect(page.locator('#email-step')).toBeVisible();
  });

  test('empty email shows validation state (HTML5 required)', async ({ page }) => {
    await page.goto('/login');
    await page.click('#email-form button[type="submit"]');
    // Email field should fail HTML5 validation — OTP step should remain hidden
    await expect(page.locator('#otp-step')).toBeHidden();
  });
});
