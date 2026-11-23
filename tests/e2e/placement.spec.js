/**
 * E2E smoke — Vocabulary placement page (/placement, TASK-1084), at 390 px in light and dark.
 *
 * Read-only: every /api/calibration/placement/* request is answered in the browser by a
 * scripted fake (page.route), so no placement session is opened and nothing is written. The
 * spec checks the page, not the backend: it walks intro → meaning → pinyin (a tone-only miss)
 * → combined reveal → "Stop here and see your result" → result, plus the ja sound-pair probe
 * and the en result, and on every screen: no horizontal overflow, the document does not
 * scroll (task mode), the dock is inside the viewport and tap targets are ≥ 44 px.
 *
 * Runs with the auth state of auth.setup.js like every spec. Against the preview server
 * (tests/e2e/redesign/serve.py: the real app over in-memory fakes) any token works:
 *
 *   python tests/e2e/redesign/serve.py --port 5099 &
 *   BASE_URL=http://127.0.0.1:5099 npx playwright test tests/e2e/placement.spec.js --project=chromium
 *
 * PLACEMENT_SHOTS=<dir> also saves one screenshot per screen.
 */

import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const SHOTS = process.env.PLACEMENT_SHOTS || '';

const item = (o) => ({ band: 1, probe_kind: null, idk_allowed: true, prompt_key: null, ...o });
const ZH_M1 = item({
  response_id: 11,
  vocab_id: 101,
  lemma: '学习',
  kind: 'meaning',
  options: [
    'to study; to learn',
    'to rest; to take a break',
    'to practise; an exercise',
    'to review (a lesson)',
  ],
});
const ZH_R1 = item({
  response_id: 12,
  vocab_id: 101,
  lemma: '学习',
  kind: 'reading',
  options: ['xuěxǐ', 'shuìjiào', 'xuéxí', 'shuījiāo'],
});
const ZH_M2 = item({
  response_id: 13,
  vocab_id: 102,
  lemma: '朋友',
  kind: 'meaning',
  options: ['friend', 'neighbour', 'colleague', 'guest'],
});
const JA_R = item({
  response_id: 21,
  vocab_id: 201,
  lemma: '学校',
  kind: 'reading',
  options: ['がっこう', 'かっこう', 'がくこう', 'がっこ'],
});
const JA_SP = item({
  response_id: 22,
  vocab_id: 201,
  lemma: '学校',
  kind: 'reading',
  probe_kind: 'sound_pair',
  options: ['がっこう', 'がこう'],
});

const part = (o) => ({
  probe_kind: null,
  chosen_text: null,
  is_correct: true,
  tone_only_miss: false,
  ...o,
});

const ZH_RESULT = {
  version: 1,
  word_language_id: 1,
  definition_language_id: 2,
  instrument: 'meaning_bare_v1',
  stop_reason: 'learner',
  ended_early: true,
  fast: false,
  skip_share: 0.41,
  items: { scored: 24, meaning: 16, reading: 8, probes: 1 },
  active_seconds: 170,
  words: { asked: 16, both: 5, tones_not_yet: 2, meaning_only: 1, not_yet: 8 },
  frame_n: 3623,
  this: {
    m: { lo: 900, hi: 1700, label: 'rough' },
    mr: { lo: 500, hi: 1100, label: 'rough' },
    tone_gap: { lo: 60, hi: 420 },
    gap: { lo: 120, hi: 650 },
  },
  combined: { m: { lo: 1000, hi: 1600 }, mr: { lo: 600, hi: 1000, label: 'rough' } },
  previous: {
    session_id: 'old',
    ended_at: '2026-10-02T10:00:00Z',
    mr: { lo: 200, hi: 700 },
    verdict: 'up',
  },
  seen: false,
};
const JA_RESULT = {
  ...ZH_RESULT,
  word_language_id: 3,
  stop_reason: 'cap',
  ended_early: false,
  words: { asked: 40, both: 15, meaning_only: 6, not_yet: 19 },
  frame_n: 3175,
  this: {
    m: { lo: 800, hi: 1500, label: 'rough' },
    mr: { lo: 450, hi: 1000, label: 'rough' },
    gap: { lo: 100, hi: 600 },
  },
  combined: null,
  previous: null,
};
const EN_RESULT = {
  ...JA_RESULT,
  word_language_id: 2,
  words: { asked: 40, both: 22, not_yet: 18 },
  frame_n: 3754,
  this: { m: { lo: 1200, hi: 2000, label: 'medium' }, mr: null, gap: null },
  fast: true,
};

const answered = (o) => ({
  answer: { is_correct: true, skipped: false, kind: 'meaning', probe_kind: null, role: null },
  reveal: null,
  next_item: null,
  done: false,
  result: null,
  can_stop: false,
  needed: 9,
  progress: { scored: 1, cap: 60, minutes_left: 6.6 },
  ...o,
});

/** Answer the placement routes from `script` (arrays are served in order). Returns the log. */
async function fakeApi(page, script) {
  const log = [];
  await page.route('**/api/calibration/placement/**', async (route) => {
    const req = route.request();
    const p = new URL(req.url()).pathname.replace('/api/calibration/placement', '');
    const k = req.method() + ' ' + p;
    log.push(k);
    let r = script[k];
    if (Array.isArray(r)) r = r.shift();
    if (!r)
      return route.fulfill({ status: 500, json: { status: 'error', error: 'no fake for ' + k } });
    const { status = 200, ...body } = r;
    return route.fulfill({ status, json: { status: 'success', ...body } });
  });
  return log;
}

/** Layout facts of the current screen. */
function layout(page) {
  return page.evaluate(() => {
    const se = document.scrollingElement;
    const shown = (el) => {
      for (let n = el; n; n = n.parentElement) if (n.hidden) return false;
      return el.getClientRects().length > 0;
    };
    const dock = document.getElementById('plcDock');
    const dr = dock.getBoundingClientRect();
    const targets = [
      ...document.querySelectorAll(
        '#plcDock .ld-btn, .cal-option, .plc-progress__end, .plc-group__head[type="button"], .plc-action, .plc-confirm .ld-btn'
      ),
    ].filter(shown);
    return {
      horizontalOverflow: se.scrollWidth > window.innerWidth + 1,
      documentScrolls: se.scrollHeight > window.innerHeight + 1,
      dockInView: !shown(dock) || (dr.top >= 0 && dr.bottom <= window.innerHeight + 1),
      small: targets
        .filter((el) => el.getBoundingClientRect().height < 44)
        .map((el) => (el.id || el.className) + ':' + Math.round(el.getBoundingClientRect().height)),
      wide: targets
        .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
        .map((el) => el.id || el.className),
    };
  });
}

async function check(page, name, scheme) {
  const l = await layout(page);
  expect(l.horizontalOverflow, name + ': horizontal overflow').toBe(false);
  expect(l.documentScrolls, name + ': the document scrolls').toBe(false);
  expect(l.dockInView, name + ': dock off-screen').toBe(true);
  expect(l.small, name + ': targets < 44 px').toEqual([]);
  expect(l.wide, name + ': targets wider than the viewport').toEqual([]);
  if (SHOTS) {
    fs.mkdirSync(SHOTS, { recursive: true });
    await page.waitForTimeout(150);
    await page.screenshot({ path: path.join(SHOTS, `${name}-${scheme}.png`) });
  }
}

async function open(page, lang, uiLang = 'en') {
  await page.addInitScript(
    ([l, ui]) => {
      localStorage.setItem('selectedLanguageId', l);
      localStorage.setItem('nativeLanguagePromptDone', '1');
      localStorage.setItem('linguadojo-ui-lang', ui);
    },
    [lang, uiLang]
  );
  await page.goto('/placement');
}

for (const scheme of ['light', 'dark']) {
  test.describe(`placement at 390 px (${scheme})`, () => {
    test.use({ viewport: { width: 390, height: 844 }, colorScheme: scheme });

    test('zh: intro → meaning → pinyin → reveal → stop → result', async ({ page }) => {
      const log = await fakeApi(page, {
        'GET /latest': { result: null, unseen: false },
        'POST /start': {
          status: 201,
          session_id: 's-1',
          item: ZH_M1,
          progress: { scored: 0, cap: 60, minutes_left: 7 },
          resumed: false,
        },
        'POST /answer': [
          answered({ next_item: ZH_R1 }),
          answered({
            answer: {
              is_correct: false,
              skipped: false,
              kind: 'reading',
              probe_kind: null,
              role: 'KT',
            },
            reveal: {
              lemma: '学习',
              reading: 'xuéxí',
              meaning: 'to study; to learn',
              parts: [
                part({ kind: 'meaning', chosen_text: 'to study; to learn' }),
                part({
                  kind: 'reading',
                  is_correct: false,
                  chosen_text: 'xuěxǐ',
                  key_text: 'xuéxí',
                  tone_only_miss: true,
                }),
              ],
            },
            next_item: ZH_M2,
            can_stop: true,
            progress: { scored: 22, cap: 60, minutes_left: 4.2 },
          }),
        ],
        'POST /end': { result: ZH_RESULT },
      });
      await open(page, '1');

      await expect(page.locator('#plcIntro')).toBeVisible();
      await expect(page.locator('#plcIntroTime')).toHaveText('About 7 minutes');
      await check(page, '01-zh-intro', scheme);

      await page.locator('#plcStartBtn').click();
      await expect(page.locator('#plcPrompt')).toHaveText('学习');
      await expect(page.locator('#plcPrompt')).toHaveAttribute('lang', 'zh');
      await expect(page.locator('#plcInstruction')).toHaveText('Choose the meaning');
      await expect(page.locator('#plcItem')).not.toContainText('xuéxí');
      await expect(page.locator('#plcEndBtn')).toBeVisible();
      await check(page, '02-zh-meaning', scheme);

      await page.locator('.cal-option').first().click();
      await expect(page.locator('#plcInstruction')).toHaveText('Choose the pinyin');
      await expect(page.locator('#plcReveal')).toBeHidden();
      await check(page, '03-zh-pinyin', scheme);

      await page.keyboard.press('1');
      await expect(page.locator('#plcReveal')).toBeVisible();
      await expect(page.locator('.plc-part__tones')).toHaveText('Right pinyin, wrong tones');
      await expect(page.locator('#plcNextBtn')).toBeVisible();
      await expect(page.locator('#plcStopBtn')).toBeVisible();
      await check(page, '04-zh-reveal-tone-miss', scheme);

      await page.keyboard.press('Enter');
      await expect(page.locator('#plcPrompt')).toHaveText('朋友');
      await check(page, '05-zh-next-word-can-stop', scheme);

      await page.locator('#plcStopBtn').click();
      await expect(page.locator('#plcResult')).toBeVisible();
      await expect(page.locator('.plc-range__text')).toContainText('500⁠–⁠1,100');
      await expect(page.locator('#plcLangName')).toHaveText('Chinese');
      await expect(page.locator('.plc-retake__verdict')).toHaveText('Clearly up');
      await expect(page.locator('.plc-band circle')).toHaveCount(20);
      await check(page, '06-zh-result', scheme);
      const group = page.locator('.plc-group[data-group="tones_not_yet"]');
      await group.locator('button').click();
      await expect(group.locator('.plc-word__lemma')).toHaveText('学习');
      await page.locator('.plc-how summary').click();
      await page.locator('.plc-flags').scrollIntoViewIfNeeded();
      await check(page, '07-zh-result-bottom', scheme);
      expect(log).toEqual([
        'GET /latest',
        'POST /start',
        'POST /answer',
        'POST /answer',
        'POST /end',
      ]);
    });

    test('ja: reading item, then the 2-option sound-pair probe, and the ja result', async ({
      page,
    }) => {
      await fakeApi(page, {
        'GET /latest': { result: null, unseen: false },
        'POST /start': {
          status: 201,
          session_id: 's-2',
          item: JA_R,
          progress: { scored: 30, cap: 60, minutes_left: 3.4 },
          resumed: true,
        },
        'POST /answer': [
          answered({ next_item: JA_SP }),
          answered({
            reveal: {
              lemma: '学校',
              reading: 'がっこう',
              meaning: 'school',
              parts: [
                part({ kind: 'reading', chosen_text: 'がっこう' }),
                part({ kind: 'reading', probe_kind: 'sound_pair', chosen_text: 'がっこう' }),
              ],
            },
            done: true,
            result: JA_RESULT,
          }),
        ],
      });
      await open(page, '3');
      await page.locator('#plcStartBtn').click();
      await expect(page.locator('#plcInstruction')).toHaveText('Choose the reading');
      await page.locator('.cal-option').first().click();
      await expect(page.locator('#plcProbeBadge')).toHaveText('Extra question — not scored');
      await expect(page.locator('.cal-option')).toHaveCount(2);
      await check(page, '08-ja-sound-pair', scheme);
      await page.locator('.cal-option').first().click();
      // all ✓: the reveal moves on by itself (450 ms) to the result
      await expect(page.locator('#plcResult')).toBeVisible();
      await expect(page.locator('.plc-gap--reading')).toBeVisible();
      await expect(page.locator('.plc-gap--tones')).toHaveCount(0);
      await check(page, '09-ja-result', scheme);
    });

    test('en: an unseen result is shown first; meaning-only copy, fast flag', async ({ page }) => {
      await fakeApi(page, { 'GET /latest': { result: EN_RESULT, unseen: true } });
      await open(page, '2');
      await expect(page.locator('#plcResult')).toBeVisible();
      await expect(page.locator('.plc-group__label')).toHaveText([
        'recognised',
        'not yet recognised',
      ]);
      // Word joiners keep the range on one line.
      await expect(page.locator('.plc-range__text')).toContainText(
        'the meaning of about 1,200⁠–⁠2,000'
      );
      await expect(page.locator('#plcNewBtn')).toBeVisible();
      await check(page, '10-en-result', scheme);
      await page.locator('#plcNewBtn').click();
      await expect(page.locator('#plcIntroTime')).toHaveText('About 5 minutes');
    });

    test('a language that is not enabled says "not available"', async ({ page }) => {
      await page.route('**/api/calibration/placement/**', (route) =>
        route.fulfill({
          status: 404,
          json: { status: 'error', error: 'Not found', error_code: 'NOT_FOUND' },
        })
      );
      await open(page, '3');
      await expect(page.locator('#plcMessage')).toHaveText(
        'The vocabulary placement is not available for this language yet.'
      );
      await check(page, '11-unavailable', scheme);
    });
  });
}
