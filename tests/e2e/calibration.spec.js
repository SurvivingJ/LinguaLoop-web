/**
 * E2E — Calibration: prefetch (TASK-771) and learner-paced advance (TASK-775).
 *
 * Two things are worth driving a real browser for, because neither is visible
 * from the server side:
 *
 *   1. A WRONG answer must stop and wait for the learner. It used to be replaced
 *      by a 1,300 ms timer, and that is the one moment in a run where there is
 *      something to read.
 *   2. A CORRECT answer must not stop, and the next word must already be in
 *      hand — the whole point of the queue is that no answer is followed by a
 *      network wait.
 *
 * Runs with auth state from playwright/.auth/user.json (set by auth.setup.js).
 *
 * !! THIS SUITE WRITES REAL CALIBRATION DATA FOR THE TEST ACCOUNT !!
 *
 * Every run opens sessions and answers items essentially at random. Those answers
 * are pooled by `pooled_ability()` across ALL of a user's sessions, so left behind
 * they would drag that account's measured vocabulary level toward chance. The runs
 * never call /end, so `user_calibration_state` and the rating writer are not
 * reached — but the responses are still there waiting for the next real /end.
 *
 * Clean up after running against an account whose calibration data matters:
 *
 *   delete from calibration_response_options ro using calibration_responses r
 *    where ro.response_id = r.id and r.session_id in (
 *      select id from calibration_sessions where started_at > '<run start>');
 *   delete from calibration_responses where session_id in (
 *      select id from calibration_sessions where started_at > '<run start>');
 *   delete from calibration_sessions where started_at > '<run start>';
 */

import { test, expect } from '@playwright/test';

const OPTION = '#calOptions .cal-option';

/**
 * Wait for a FRESH item and return its four option buttons.
 *
 * "Four options exist" is not enough: between an advance and the re-render, the
 * previous item's four buttons are still in the DOM, disabled and carrying their
 * .correct/.wrong marks. Clicking one of those does nothing and the test then
 * waits forever for a reveal that was never requested. The honest condition is
 * four options that are enabled and unmarked.
 */
async function waitForItem(page) {
  await expect(page.locator('#calStage')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator(OPTION)).toHaveCount(4, { timeout: 20_000 });
  await expect(page.locator(OPTION + '.correct')).toHaveCount(0, { timeout: 20_000 });
  await expect(page.locator(OPTION + '.wrong')).toHaveCount(0, { timeout: 20_000 });
  await expect(page.locator(OPTION + ':disabled')).toHaveCount(0, { timeout: 20_000 });
  return page.locator(OPTION);
}

test.describe('Calibration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/calibration');
  });

  test('serves an item without redirecting to login', async ({ page }) => {
    await expect(page).not.toHaveURL(/\/login/);
    const options = await waitForItem(page);
    await expect(options.first()).toBeVisible();
    await expect(page.locator('#calPrompt')).not.toBeEmpty();
  });

  test('items are prefetched, so the first /next is the only one awaited', async ({ page }) => {
    await waitForItem(page);
    // The queue is primed at first paint and topped up in the background.
    const queued = await page.evaluate(() => {
      // eslint-disable-next-line no-undef
      return window.performance
        .getEntriesByType('resource')
        .filter((r) => r.name.includes('/api/calibration/next')).length;
    });
    expect(queued).toBeGreaterThan(0);
  });

  test('a wrong answer waits for the learner instead of advancing itself', async ({ page }) => {
    const options = await waitForItem(page);
    const prompt = await page.locator('#calPrompt').textContent();

    // Answer every option until one of them is wrong. With four options and one
    // key, the first two tries cannot both be right.
    for (let i = 0; i < 4; i += 1) {
      await options.nth(i).click();
      await expect(page.locator(OPTION + '.correct')).toHaveCount(1, { timeout: 15_000 });
      const wrong = await page.locator(OPTION + '.wrong').count();
      if (wrong === 1) break;
      // That one was right: it advances on its own, so pick up the next item.
      await waitForItem(page);
    }

    // The Next button is showing, "I don't know" is not, and nothing has moved.
    await expect(page.locator('#calNextBtn')).toBeVisible();
    await expect(page.locator('#calSkipBtn')).toBeHidden();
    await page.waitForTimeout(2500); // well past the old 1,300 ms timer
    await expect(page.locator(OPTION + '.correct')).toHaveCount(1);

    // ...until the learner asks for the next word.
    await page.locator('#calNextBtn').click();
    await waitForItem(page);
    await expect(page.locator('#calNextBtn')).toBeHidden();
    await expect(page.locator('#calSkipBtn')).toBeVisible();
    await expect(page.locator('#calPrompt')).not.toHaveText(prompt ?? '');
  });

  test('a skip also waits, and reveals the answer', async ({ page }) => {
    await waitForItem(page);
    await page.locator('#calSkipBtn').click();

    await expect(page.locator(OPTION + '.correct')).toHaveCount(1, { timeout: 15_000 });
    await expect(page.locator('#calNextBtn')).toBeVisible();
    await page.waitForTimeout(2000);
    await expect(page.locator(OPTION + '.correct')).toHaveCount(1);
  });

  test('Enter advances from a revealed answer, and consumes exactly one item', async ({ page }) => {
    await waitForItem(page);
    await page.locator('#calSkipBtn').click();
    await expect(page.locator('#calNextBtn')).toBeVisible({ timeout: 15_000 });

    const answeredBefore = await page.locator('#calAnswered').textContent();

    // Two presses in quick succession must not burn two items: the timer, the
    // button and the key all go through one guarded advance().
    await page.keyboard.press('Enter');
    await page.keyboard.press('Enter');
    await waitForItem(page);

    // Still exactly one answer recorded — the second Enter did nothing.
    await expect(page.locator('#calAnswered')).toHaveText(answeredBefore ?? '');
  });

  test('a correct answer advances on its own', async ({ page }) => {
    const options = await waitForItem(page);

    for (let i = 0; i < 4; i += 1) {
      const prompt = await page.locator('#calPrompt').textContent();
      await options.nth(i).click();
      await expect(page.locator(OPTION + '.correct')).toHaveCount(1, { timeout: 15_000 });

      if ((await page.locator(OPTION + '.wrong').count()) === 0) {
        // Right answer: no button, and it moves on by itself.
        await expect(page.locator('#calNextBtn')).toBeHidden();
        await waitForItem(page);
        await expect(page.locator('#calPrompt')).not.toHaveText(prompt ?? '');
        return;
      }
      await page.locator('#calNextBtn').click();
      await waitForItem(page);
    }
    test.skip(true, 'four wrong answers in a row — no correct answer to observe');
  });
});
