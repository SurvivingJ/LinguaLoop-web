/**
 * Playwright global auth setup — Phase 2b
 *
 * Performs a real OTP login with jamesccmcb@gmail.com so all E2E specs can
 * start already authenticated.  Saves the resulting browser state (JWT in
 * localStorage + the HttpOnly refresh cookie) to playwright/.auth/user.json.
 *
 * Run:
 *   npm run test:e2e          — runs setup then specs (setup skipped if user.json is fresh)
 *   npm run test:e2e:headed   — headed browser so you can watch the OTP flow
 *
 * In CI: set TEST_JWT_TOKEN env var to a pre-issued token (bypasses OTP).
 */

import { test as setup, expect } from '@playwright/test';
import { existsSync, statSync } from 'node:fs';

const AUTH_FILE = 'playwright/.auth/user.json';
const EMAIL = 'jamesccmcb@gmail.com';
const BASE_URL = process.env.BASE_URL || 'http://localhost:5000';

// If CI injects a ready-made JWT, skip the OTP dance entirely.
const PRE_ISSUED_TOKEN = process.env.TEST_JWT_TOKEN;

setup('authenticate', async ({ page }) => {
  // Skip if auth file exists and is less than 55 minutes old (JWT TTL)
  if (!PRE_ISSUED_TOKEN && existsSync(AUTH_FILE)) {
    const ageMs = Date.now() - statSync(AUTH_FILE).mtimeMs;
    if (ageMs < 55 * 60 * 1000) {
      console.log('[auth-setup] Reusing existing auth state (< 55 min old).');
      return;
    }
  }

  if (PRE_ISSUED_TOKEN) {
    // CI path: inject the token directly, no OTP needed.
    await page.goto(BASE_URL + '/login');
    await page.addInitScript((token) => {
      localStorage.setItem('jwt_token', token);
    }, PRE_ISSUED_TOKEN);
    await page.goto(BASE_URL + '/');
    await page.context().storageState({ path: AUTH_FILE });
    console.log('[auth-setup] CI: auth state saved via TEST_JWT_TOKEN.');
    return;
  }

  // Interactive path: headed browser — user types OTP directly.
  // Run with: npm run auth:capture
  await page.goto(BASE_URL + '/login');

  // Step 1 — fill email automatically
  await page.fill('#email', EMAIL);
  await page.click('#email-form button[type="submit"]');
  await expect(page.locator('#otp-step')).toBeVisible({ timeout: 10_000 });

  // Step 2 — pause so the user can type the OTP into the browser window.
  // The Playwright Inspector opens; click Resume once you are logged in.
  console.log(`\n[auth-setup] OTP sent to ${EMAIL}. Type it into the browser, then click Resume in the Playwright Inspector.\n`);
  await page.pause();

  // Wait for successful login — base.html stores jwt_token and navigates away
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30_000 });

  // Persist cookies + localStorage for all subsequent specs
  await page.context().storageState({ path: AUTH_FILE });
  console.log('[auth-setup] Auth state saved to ' + AUTH_FILE);
});
