/**
 * One-shot auth state capture — run with `node tests/e2e/capture-auth-once.js`
 * Uses PLAYWRIGHT_OTP env var so it can be driven non-interactively.
 * Delete this file after use (or keep for re-running when the token expires).
 */
import { chromium } from '@playwright/test';

const OTP = process.env.PLAYWRIGHT_OTP;
const EMAIL = 'jamesccmcb@gmail.com';
const BASE_URL = process.env.BASE_URL || 'http://localhost:5000';
const AUTH_FILE = 'playwright/.auth/user.json';

if (!OTP) {
  console.error('Set PLAYWRIGHT_OTP=<6-digit-code> before running.');
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

console.log('[capture-auth] Navigating to login...');
await page.goto(BASE_URL + '/login');

console.log('[capture-auth] Submitting email...');
await page.fill('#email', EMAIL);
await page.click('#email-form button[type="submit"]');
await page.waitForSelector('#otp-step:not(.d-none)', { timeout: 10_000 });

console.log('[capture-auth] Submitting OTP...');
await page.fill('#otp', OTP);
await page.click('#otp-form button[type="submit"]');

// Wait briefly for any error message to appear, or for navigation
await page.waitForTimeout(3000);
const currentUrl = page.url();
console.log('[capture-auth] URL after OTP submit:', currentUrl);

if (currentUrl.includes('/login')) {
  // Check for error message
  const errEl = await page.$('#error-message, .alert-danger, [class*="error"]');
  if (errEl) {
    const errText = await errEl.textContent();
    console.error('[capture-auth] Login error on page:', errText.trim());
  } else {
    console.log('[capture-auth] Still on login page — checking page text for clues...');
    const bodyText = await page.locator('body').innerText();
    console.log('[capture-auth] Body excerpt:', bodyText.substring(0, 400));
  }
  process.exit(1);
}

console.log('[capture-auth] Logged in. Saving state...');

await context.storageState({ path: AUTH_FILE });
console.log('[capture-auth] Auth state saved to ' + AUTH_FILE);

await browser.close();
