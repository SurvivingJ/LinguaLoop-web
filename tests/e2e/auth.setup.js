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
 * Automated runs: set TEST_USER_EMAIL + TEST_USER_PASSWORD (plus SUPABASE_URL
 * and SUPABASE_KEY) to mint a fresh token for the dedicated test account via
 * Supabase's password grant — see scripts/mint_test_token.py.
 */

import { test as setup, expect } from '@playwright/test';
import { existsSync, statSync } from 'node:fs';

const AUTH_FILE = 'playwright/.auth/user.json';
const EMAIL = 'jamesccmcb@gmail.com';
const BASE_URL = process.env.BASE_URL || 'http://localhost:5000';

// If CI injects a ready-made JWT, skip the OTP dance entirely.
const PRE_ISSUED_TOKEN = process.env.TEST_JWT_TOKEN;

const { TEST_USER_EMAIL, TEST_USER_PASSWORD, SUPABASE_URL, SUPABASE_KEY } = process.env;
const CAN_MINT = !!(TEST_USER_EMAIL && TEST_USER_PASSWORD && SUPABASE_URL && SUPABASE_KEY);

async function mintTestToken() {
  const res = await fetch(`${SUPABASE_URL.replace(/\/$/, '')}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: SUPABASE_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: TEST_USER_EMAIL, password: TEST_USER_PASSWORD }),
  });
  if (!res.ok) throw new Error(`[auth-setup] password login failed: ${res.status} ${await res.text()}`);
  return (await res.json()).access_token;
}

setup('authenticate', async ({ page }) => {
  // Skip if auth file exists and is less than 55 minutes old (JWT TTL)
  if (!PRE_ISSUED_TOKEN && !CAN_MINT && existsSync(AUTH_FILE)) {
    const ageMs = Date.now() - statSync(AUTH_FILE).mtimeMs;
    if (ageMs < 55 * 60 * 1000) {
      console.log('[auth-setup] Reusing existing auth state (< 55 min old).');
      return;
    }
  }

  if (PRE_ISSUED_TOKEN || CAN_MINT) {
    // Token path: inject the token directly, no OTP needed.
    const token = PRE_ISSUED_TOKEN || (await mintTestToken());
    await page.goto(BASE_URL + '/login');
    // Pick a study language too, or a fresh account lands on /language-selection.
    await page.evaluate(
      ([t, lang]) => {
        localStorage.setItem('jwt_token', t);
        if (!localStorage.getItem('selectedLanguageId')) localStorage.setItem('selectedLanguageId', lang);
      },
      [token, process.env.TEST_LANGUAGE_ID || '1']
    );
    await page.goto(BASE_URL + '/');
    await page.context().storageState({ path: AUTH_FILE });
    console.log(
      `[auth-setup] auth state saved via ${PRE_ISSUED_TOKEN ? 'TEST_JWT_TOKEN' : 'test-account password login'}.`
    );
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
  console.log(
    `\n[auth-setup] OTP sent to ${EMAIL}. Type it into the browser, then click Resume in the Playwright Inspector.\n`
  );
  await page.pause();

  // Wait for successful login — base.html stores jwt_token and navigates away
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30_000 });

  // Persist cookies + localStorage for all subsequent specs
  await page.context().storageState({ path: AUTH_FILE });
  console.log('[auth-setup] Auth state saved to ' + AUTH_FILE);
});
