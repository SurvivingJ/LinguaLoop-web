/* Walks every view and state of the real DT guided self-repair sheet (static/js/dt-repair-sheet.js
   + static/css/dt-repair.css, with the app's Bootstrap and Still Water CSS underneath) against the
   stand-in API in mock-api.js, and asserts the no-scroll rule on each one. A port of
   wiki/design/dt-feedback/option-2-guided-self-repair/verify.cjs to the real UI.

   Run (no server needed):
     NODE_PATH=/opt/node-tools/node_modules node tests/e2e/dt-repair/noscroll.cjs [--quick]
   Prints "N checks, M failures" and exits non-zero on any failure.
   --quick: 390x844 + 375x340 light only (smoke). */
const path = require('path');
const fs = require('fs');
// Prefer the Playwright on NODE_PATH (the preinstalled one that matches the preinstalled Chromium)
// over a repo-local node_modules copy of a different version.
const { chromium } = (() => {
  for (const p of (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)) {
    try { return require(path.join(p, 'playwright')); } catch { /* try the next entry */ }
  }
  return require('playwright');
})();

const ROOT = path.join(__dirname, '..', '..', '..');
const URL = 'file://' + path.join(__dirname, 'harness.html');
const QUICK = process.argv.includes('--quick');
const BUNDLES = {};
for (const l of ['en', 'zh', 'ja']) BUNDLES[l] = JSON.parse(fs.readFileSync(path.join(ROOT, 'static/i18n', l + '.json'), 'utf8'));

const VIEWPORTS = [
  { name: '390x844', width: 390, height: 844, touch: true },
  { name: '375x667', width: 375, height: 667, touch: true },
  { name: '1280x800', width: 1280, height: 800, touch: false },
];
const KEYBOARD = [
  { name: '390x500-kb', width: 390, height: 500, touch: true },
  { name: '375x340-kb', width: 375, height: 340, touch: true },
];
const FIX = {
  en_errors: [['sick', 'great'], ['without it', 'with it']],
  zh_errors: [['一个', '一件'], ['洗很多次', '洗了很多次']],
  daily_en: [['learn on', 'learn about'], [null, null]],
  daily_zh: [['洗很多次', '洗了很多次'], ['收藏下来', '收藏起来']],
  en_unsure: [['an enjoyable', 'a fun']],
  zh_unsure: [['轻松', '放松']],
};
const TAGS = { en: ['You wrote', 'Answer'], zh: ['你写的', '答案'], ja: ['あなたの文', '答え'] };
let checks = 0;
const failures = [];

/* ------------------------------------------------------------------ assertions */
async function assertStep(page, tag, expectFocus, ui) {
  const r = await page.evaluate(
    ([expectFocus, tags]) => {
      const out = [];
      const se = document.scrollingElement;
      const W = innerWidth;
      const H = innerHeight;
      if (se.scrollHeight > H) out.push(`page scrolls vertically (${se.scrollHeight} > ${H})`);
      if (se.scrollWidth > W) out.push(`page scrolls horizontally (${se.scrollWidth} > ${W})`);
      if (scrollY !== 0 || scrollX !== 0) out.push('page is scrolled');
      const sheet = document.querySelector('#dtr-sheet');
      const open = !!sheet;
      const root = open ? sheet : document.querySelector('#ex');
      const box = open ? sheet.getBoundingClientRect() : { left: 0, top: 0, right: W, bottom: H };
      const vis = (el) => {
        const c = getComputedStyle(el);
        const b = el.getBoundingClientRect();
        return c.display !== 'none' && c.visibility !== 'hidden' && b.width > 1 && b.height > 1 && !el.closest('.dtr-sr');
      };
      const name = (el) => (el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + el.className);
      for (const el of root.querySelectorAll('*')) {
        if (!vis(el) || (el.closest('svg') && el.tagName !== 'svg')) continue;
        const b = el.getBoundingClientRect();
        if (b.left < box.left - 0.5 || b.right > box.right + 0.5 || b.top < box.top - 0.5 || b.bottom > box.bottom + 0.5) out.push(`${name(el)} outside the screen`);
        if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== 'visible' && el.tagName !== 'TEXTAREA') out.push(`${name(el)} overflows horizontally`);
      }
      if (open) {
        const view = sheet.dataset.view;
        const i = Number(sheet.dataset.i);
        const mock = window.H.mock;
        const src = mock.session ? mock.session.steps : mock.items;
        const stepData = src && src[i];
        const st = stepData && mock.state[stepData.item_id];
        if (view === 'reveal' || view === 'alt') {
          const mine = sheet.querySelector('#dtr-cmp-mine');
          const ans = sheet.querySelector('#dtr-cmp-ans');
          const lbl = (b, t) => b && vis(b) && b.querySelector('.dtr-tag')?.textContent.trim() === t && b.querySelector('.dtr-sent')?.textContent.trim().length > 5;
          if (!lbl(mine, tags[0])) out.push('answer step: visible "You wrote" block missing');
          if (!lbl(ans, tags[1])) out.push('answer step: visible "Answer" block missing');
          if (mine && ans) {
            const point = st && st.x.point != null;
            const del = mine.querySelector('del');
            const bb = ans.querySelector('b');
            if (!point && (!del || !vis(del))) out.push('answer step: problem part not marked in "You wrote"');
            if (!bb || !vis(bb)) out.push('answer step: corrected part not marked in "Answer"');
            if (mine.getBoundingClientRect().bottom > ans.getBoundingClientRect().top + 1) out.push('answer step: blocks not stacked in order');
            if (!point && del && !getComputedStyle(del).textDecorationLine.includes('line-through')) out.push('answer step: marking relies on colour alone (del)');
            if (bb && !getComputedStyle(bb).textDecorationLine.includes('underline')) out.push('answer step: marking relies on colour alone (b)');
            const tx = (s) => s.textContent.trim();
            if (tx(mine.querySelector('.dtr-sent')) === tx(ans.querySelector('.dtr-sent'))) out.push('answer step: both sentences identical');
            if (stepData && tx(mine.querySelector('.dtr-sent')) !== stepData.learner_sentence) out.push('answer step: "You wrote" is not the original submission');
            if (st && tx(ans.querySelector('.dtr-sent')) !== st.x.ref) out.push('answer step: "Answer" is not the reference sentence');
            const why = sheet.querySelector('.dtr-why');
            if (!why || !vis(why)) out.push('answer step: explanation line missing');
          }
        }
        const stage = sheet.querySelector('#dtr-stage');
        const act = sheet.querySelector('#dtr-act').getBoundingClientRect();
        const stb = stage.getBoundingClientRect();
        if (stage.scrollHeight > stage.clientHeight + 1) out.push(`stage content taller than its area (${stage.scrollHeight} > ${stage.clientHeight})`);
        if (act.bottom > box.bottom + 0.5) out.push('action area off screen');
        for (const el of stage.querySelectorAll('*')) {
          if (!vis(el) || el.closest('.dtr-mirror') || (el.closest('svg') && el.tagName !== 'svg')) continue;
          const b = el.getBoundingClientRect();
          if (b.bottom > act.top + 0.5) out.push(`${name(el)} clipped behind the action area (${Math.round(b.bottom)} > ${Math.round(act.top)})`);
          if (b.bottom > stb.bottom + 0.5) out.push(`${name(el)} clipped by the stage`);
        }
        for (const el of stage.querySelectorAll('.dtr-slot, .dtr-moment, .dtr-orig, .dtr-lab, .dtr-eyebrow, .dtr-cmp')) if (vis(el) && el.scrollHeight > el.clientHeight + 1) out.push(`${name(el)} text clipped (${el.scrollHeight} > ${el.clientHeight})`);
        const m = stage.querySelector('#dtr-mirror');
        if (m && m.scrollHeight > m.clientHeight + 1) out.push('field text does not fit the field');
        const ta = stage.querySelector('#dtr-ta');
        if (ta && ta.getBoundingClientRect().bottom > box.top + (box.bottom - box.top) * 0.62 && !sheet.classList.contains('dtr-kb')) out.push('field is not in the upper part of the screen');
        if (sheet.querySelectorAll('.dtr-act .dtr-btn.dtr-primary').length > 1) out.push('more than one primary button');
        if ([...sheet.querySelectorAll('.dtr-act .dtr-txt')].filter(vis).length > 2) out.push('more than two quiet actions');
        const above = [...stage.children].filter((e) => vis(e) && e.id !== 'dtr-field' && e.id !== 'dtr-slot').length;
        if (stage.querySelector('#dtr-field') && above > 3) out.push('more than 3 text elements above the input');
        // the field is a real labelled control
        if (ta) {
          const lab = sheet.querySelector('label[for="dtr-ta"]');
          if (!lab || !lab.textContent.trim()) out.push('field has no real label');
          if (parseFloat(getComputedStyle(ta).fontSize) < 15) out.push('field type below 15px');
        }
        // focus placement after the transition
        const a = document.activeElement;
        if (expectFocus === 'h2' && !(a && a.tagName === 'H2' && sheet.contains(a))) out.push(`focus should be on the view heading, is on ${a && (a.id || a.tagName)}`);
        if (expectFocus === 'label' && !(a && a.id === 'dtr-lab')) out.push(`focus should be on the label, is on ${a && (a.id || a.tagName)}`);
        if (expectFocus === 'ta' && !(a && a.id === 'dtr-ta')) out.push(`focus should be on the field, is on ${a && (a.id || a.tagName)}`);
        if (expectFocus === 'field') {
          const want = matchMedia('(pointer: fine)').matches ? 'dtr-ta' : 'dtr-lab';
          if (!(a && a.id === want)) out.push(`focus should be on #${want}, is on ${a && (a.id || a.tagName)}`);
        }
        if (expectFocus && !sheet.contains(a)) out.push('focus escaped the sheet');
      }
      for (const el of root.querySelectorAll('button, select')) {
        if (!vis(el)) continue;
        const b = el.getBoundingClientRect();
        if ((b.height < 43.5 || b.width < 43.5) && !el.classList.contains('dtr-prompt')) out.push(`${name(el)} touch target ${Math.round(b.width)}x${Math.round(b.height)}`);
      }
      return out;
    },
    [expectFocus || null, TAGS[ui] || TAGS.en]
  );
  checks++;
  if (r.length) failures.push(`${tag}: ${[...new Set(r)].join('; ')}`);
}

/* ------------------------------------------------------------------ runner */
async function run(browser, vp, scheme, fn, { ui = 'en', shots = null, reduced = false } = {}) {
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    colorScheme: scheme,
    reducedMotion: reduced ? 'reduce' : 'no-preference',
    hasTouch: vp.touch,
    isMobile: vp.touch,
    deviceScaleFactor: shots ? 2 : 1,
  });
  await ctx.addInitScript((b) => { window.__I18N = b; }, BUNDLES);
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  let n = 0;
  const T = {
    page, vp, ui, scheme,
    goto: async (scenario, q = '') => {
      await page.goto(`${URL}?fast&scenario=${scenario}&ui=${ui}${scheme === 'dark' ? '&theme=midnight' : ''}${q}`);
    },
    step: async (label, focus) => {
      await page.waitForTimeout(40);
      await assertStep(page, `${vp.name} ${scheme} ${ui} ${label}`, focus, ui);
      if (shots) await page.screenshot({ path: path.join(shots, `${String(++n).padStart(2, '0')}-${label.replace(/[^a-z0-9]+/gi, '-')}.png`) });
    },
    view: (v) => page.waitForSelector(`#dtr-sheet[data-view="${v}"]`, { timeout: 5000 }),
    submit: async () => { await page.click('#submit'); await page.waitForSelector('#dtr-sheet.dtr-on'); },
    edit: (from, to) =>
      page.evaluate(([a, b]) => {
        const ta = document.querySelector('#dtr-ta');
        ta.value = a === null ? ta.value + b : ta.value.replace(a, b);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }, [from, to]),
    append: (s) => T.edit(null, s),
    settle: () => page.waitForFunction(() => { const s = document.querySelector('#dtr-sheet'); return !s || s.dataset.fieldState !== 'checking'; }),
    check: async () => { await page.click('#dtr-check'); await T.settle(); },
    click: (sel) => page.click(sel),
    slotHas: (re) => page.waitForFunction((r) => new RegExp(r).test((document.querySelector('#dtr-slot') || {}).textContent || ''), re.source),
    closed: () => page.waitForSelector('#dtr-sheet', { state: 'detached' }),
    fail: (action, ...kinds) => page.evaluate(([a, k]) => window.H.mock.fail(a, ...k), [action, kinds]),
  };
  await fn(T);
  if (errs.length) failures.push(`${vp.name} ${scheme} ${ui}: page errors ${errs.join(' | ')}`);
  await ctx.close();
}

/* ------------------------------------------------------------------ paths */
const finish = async (T) => {
  await T.view('summary'); await T.step('summary', 'h2');
  await T.click('#dtr-done'); await T.closed();
  await T.step('closed');
  if (await T.page.evaluate(() => document.activeElement && document.activeElement.id) !== 'submit' && await T.page.evaluate(() => document.activeElement && document.activeElement.id) !== 'daily') failures.push(`${T.vp.name} ${T.scheme} ${T.ui}: focus not returned to the host after close`); else checks++;
};

const firstTry = (scen) => async (T) => {
  await T.goto(scen); await T.step('start');
  await T.submit(); await T.view('result'); await T.step('result', 'h2');
  await T.click('#dtr-go');
  for (let i = 0; i < 2; i++) {
    await T.view('fix'); await T.step(`fix${i + 1}`, 'field');
    await T.edit(...FIX[scen][i]); await T.step(`fix${i + 1} edited`);
    await T.check(); await T.view('ok'); await T.step(`fix${i + 1} fixed`, 'h2');
    await T.click('#dtr-next');
  }
  await finish(T);
};

const allHints = (scen) => async (T) => {
  await T.goto(scen); await T.submit(); await T.click('#dtr-go'); await T.view('fix');
  for (let h = 1; h <= 3; h++) { await T.click('#dtr-hint'); await T.slotHas(/./); await T.step(`hint${h}`); }
  await T.check(); await T.step('same-sentence');
  await T.append(' x'); await T.check(); await T.slotHas(/./); await T.step('still-not-quite', 'ta');
  await T.click('#dtr-hint'); await T.view('reveal'); await T.step('answer', 'h2');
  await T.click('#dtr-next'); await T.view('fix'); await T.step('s2', 'field');
  await T.click('#dtr-hint'); await T.slotHas(/./); await T.step('s2 hint1');
  await T.click('#dtr-fine'); await T.view('reveal'); await T.step('s2 disputed', 'h2');
  await T.click('#dtr-next'); await finish(T);
};

const stillThenFixed = (scen) => async (T) => {
  await T.goto(scen); await T.submit(); await T.click('#dtr-go'); await T.view('fix');
  await T.click('#dtr-hint'); await T.slotHas(/./);
  await T.append(' really'); await T.check(); await T.slotHas(/./); await T.step('still', 'ta');
  await T.append(' '); await T.step('typing clears the message');
  await T.page.evaluate(([a, b]) => { const ta = document.querySelector('#dtr-ta'); ta.value = ta.value.replace(' really', '').trim().replace(a, b); ta.dispatchEvent(new Event('input', { bubbles: true })); }, FIX[scen][0]);
  await T.check(); await T.view('ok'); await T.step('fixed after still', 'h2');
};

const autoAnswerAndAlt = (scen) => async (T) => {
  await T.goto(scen); await T.submit(); await T.click('#dtr-go'); await T.view('fix');
  for (let k = 0; k < 4; k++) { await T.append('x'); await T.check(); if (k < 3) { await T.slotHas(/./); await T.step(`failed-check${k + 1}`, 'ta'); } }
  await T.view('reveal'); await T.step('auto-answer', 'h2');
  await T.click('#dtr-next'); await T.view('fix');
  await T.edit(FIX[scen][1][0], scen === 'en_errors' ? 'using this' : '洗过许多次'); await T.check(); await T.view('alt'); await T.step('no-issue-found', 'h2');
  await T.click('#dtr-next'); await T.view('summary'); await T.step('summary', 'h2');
};

const clean = (scen) => async (T) => {
  await T.goto(scen); await T.submit(); await T.view('clean'); await T.step('clean', 'h2');
  await T.click('#dtr-done'); await T.closed(); await T.step('closed');
};

const unsure = (scen) => async (T) => {
  await T.goto(scen); await T.submit(); await T.view('result'); await T.step('unsure result', 'h2');
  await T.click('#dtr-go'); await T.view('fix'); await T.step('unsure fix', 'field');
  await T.click('#dtr-fine'); await T.view('kept'); await T.step('unsure kept', 'h2');
  await T.click('#dtr-next'); await T.view('summary'); await T.step('unsure summary', 'h2');
  await T.click('#dtr-done'); await T.closed();
  await T.submit(); await T.click('#dtr-go'); await T.view('fix');
  await T.edit(...FIX[scen][0]); await T.step('unsure edited');
  await T.check(); await T.view('ok'); await T.step('unsure fixed', 'h2');
};

const apiErrors = (scen) => async (T) => {
  await T.goto(scen); await T.submit(); await T.click('#dtr-go'); await T.view('fix');
  await T.fail('check', 'network', 'http500', 'timeout');
  await T.append('x'); await T.check(); await T.slotHas(/./); await T.step('check error 1', 'ta');
  await T.check(); await T.step('check error 2 -> show answer');
  const label = await T.page.textContent('#dtr-check');
  if (label.trim() !== BUNDLES[T.ui]['dt_repair.show_answer']) failures.push(`${T.vp.name} ${T.scheme} ${T.ui}: primary did not become Show answer after 2 errors (is "${label}")`); else checks++;
  await T.fail('reveal', 'network');
  await T.click('#dtr-check'); await T.view('answer_failed'); await T.step('answer failed', 'h2');
  await T.click('#dtr-retry'); await T.view('reveal'); await T.step('answer after retry', 'h2');
  await T.click('#dtr-next'); await T.view('fix');
  await T.fail('hint', 'network', 'network');
  await T.click('#dtr-hint'); await T.slotHas(/./); await T.step('hint failed 1');
  await T.click('#dtr-hint'); await T.step('hint failed 2');
  await T.fail('dispute', 'http500');
  await T.click('#dtr-fine'); await T.view('answer_failed'); await T.step('dispute failed', 'h2');
  await T.click('#dtr-skip'); await T.view('summary'); await T.step('summary after skip', 'h2');
};

const mixed = () => async (T) => {
  await T.goto('en_mixed'); await T.submit(); await T.view('result'); await T.step('mixed result', 'h2');
  await T.click('#dtr-go'); await T.view('fix'); await T.edit('sick', 'great'); await T.check(); await T.view('ok'); await T.step('mixed 1 fixed', 'h2');
  await T.click('#dtr-next'); await T.view('reveal'); await T.step('mixed 2 direct answer', 'h2');
  await T.click('#dtr-next'); await T.view('fix'); await T.step('mixed 3 fix', 'field');
  await T.click('#dtr-hint'); await T.slotHas(/./); await T.step('mixed 3 point marker');
  await T.append('x'); await T.check(); await T.slotHas(/./); await T.step('mixed 3 still point', 'ta');
  await T.edit('Arduino board.x', 'an Arduino board.'); await T.check(); await T.view('ok'); await T.step('mixed 3 fixed', 'h2');
  await T.click('#dtr-next'); await T.view('fix'); await T.step('mixed 4 unsure', 'field');
  await T.append(' '); await T.step('unsure typed');
  await T.click('#dtr-fine'); await T.view('kept'); await T.step('mixed 4 kept', 'h2');
  await T.click('#dtr-next'); await T.view('summary'); await T.step('mixed summary', 'h2');
};

const daily = (lang) => async (T) => {
  const sc = 'daily_' + lang;
  await T.page.goto(`${URL}?fast&daily=${lang}&ui=${T.ui}${T.scheme === 'dark' ? '&theme=midnight' : ''}`);
  await T.click('#daily'); await T.page.waitForSelector('#dtr-sheet.dtr-on'); await T.view('fix'); await T.step('daily fix1', 'field');
  await T.edit(...FIX[sc][0]); await T.check(); await T.view('ok'); await T.step('daily fixed', 'h2');
  await T.click('#dtr-next'); await T.view('fix'); await T.step('daily fix2', 'field');
  await T.click('#dtr-hint'); await T.slotHas(/./); await T.step('daily hint2');
  await T.click('#dtr-hint'); await T.slotHas(/./); await T.step('daily hint3');
  await T.click('#dtr-hint'); await T.view('reveal'); await T.step('daily answer', 'h2');
  await T.click('#dtr-next'); await T.view('summary'); await T.step('daily summary', 'h2');
  await T.click('#dtr-done'); await T.closed();
  const done = await T.page.evaluate(() => window.__done);
  if (!(done.length === 1 && done[0].completed === 2 && done[0].closedEarly === false)) failures.push(`${T.vp.name} daily onDone ${JSON.stringify(done)}`); else checks++;
};

const stress = (lang) => async (T) => {
  await T.goto('stress_' + lang); await T.submit(); await T.view('result'); await T.click('#dtr-go'); await T.view('fix'); await T.step(`stress-${lang} fix`, 'field');
  if (await T.page.$('#dtr-prompt.dtr-more')) { await T.click('#dtr-prompt'); await T.page.waitForSelector('.dtr-full'); await T.step(`stress-${lang} full-prompt`); await T.click('.dtr-full'); await T.page.waitForSelector('.dtr-full', { state: 'detached' }); }
  for (let h = 1; h <= 3; h++) { await T.click('#dtr-hint'); await T.slotHas(/./); await T.step(`stress-${lang} hint${h}`); }
  await T.append('x'); await T.check(); await T.slotHas(/./); await T.step(`stress-${lang} still`, 'ta');
  await T.click('#dtr-hint'); await T.view('reveal'); await T.step(`stress-${lang} answer`, 'h2');
  if (await T.page.$('.dtr-cmp.dtr-more')) { await T.click('.dtr-cmp.dtr-more'); await T.page.waitForSelector('.dtr-full'); await T.step(`stress-${lang} full-sentence`); await T.page.keyboard.press('Escape'); await T.page.waitForSelector('.dtr-full', { state: 'detached' }); checks++; }
};

const closeEarly = (T) => T.goto('en_errors').then(async () => {
  await T.submit(); await T.click('#dtr-go'); await T.view('fix');
  await T.click('#dtr-close'); await T.closed(); await T.step('closed early');
  const done = await T.page.evaluate(() => window.__done);
  const fin = await T.page.evaluate(() => window.H.mock.callsTo(/finish/).map((c) => c.body));
  if (!(done.length === 1 && done[0].closedEarly === true && fin.length === 1 && fin[0].closed_early === true)) failures.push(`${T.vp.name} close-early: ${JSON.stringify([done, fin])}`); else checks++;
});

/* ------------------------------------------------------------------ main */
(async () => {
  const browser = await chromium.launch();
  const schemes = QUICK ? ['light'] : ['light', 'dark'];
  const full = QUICK ? [VIEWPORTS[0]] : VIEWPORTS;
  const kb = QUICK ? [KEYBOARD[1]] : KEYBOARD;
  for (const scheme of schemes) {
    for (const vp of full) {
      for (const scen of ['en_errors', 'zh_errors']) {
        for (const p of [firstTry, allHints, stillThenFixed, autoAnswerAndAlt, apiErrors]) await run(browser, vp, scheme, p(scen));
      }
      for (const scen of ['en_clean', 'zh_clean']) await run(browser, vp, scheme, clean(scen));
      for (const scen of ['en_unsure', 'zh_unsure']) await run(browser, vp, scheme, unsure(scen));
      await run(browser, vp, scheme, mixed());
      for (const lang of ['en', 'zh']) await run(browser, vp, scheme, daily(lang));
      for (const lang of ['en', 'zh', 'ja']) await run(browser, vp, scheme, stress(lang));
      await run(browser, vp, scheme, closeEarly);
    }
    for (const vp of kb) {
      for (const lang of ['en', 'zh', 'ja']) await run(browser, vp, scheme, stress(lang));
      for (const scen of ['en_unsure', 'zh_unsure']) await run(browser, vp, scheme, async (T) => { await T.goto(scen); await T.submit(); await T.click('#dtr-go'); await T.view('fix'); await T.step('unsure fix', 'field'); });
      for (const lang of ['en', 'zh']) await run(browser, vp, scheme, daily(lang));
      await run(browser, vp, scheme, firstTry('en_errors'));
      await run(browser, vp, scheme, allHints('zh_errors'));
      await run(browser, vp, scheme, mixed());
    }
    // the interface in Chinese and Japanese (longer chrome strings)
    for (const ui of ['zh', 'ja']) {
      for (const vp of QUICK ? [VIEWPORTS[0]] : [VIEWPORTS[0], VIEWPORTS[1], KEYBOARD[1]]) {
        await run(browser, vp, scheme, firstTry('en_errors'), { ui });
        await run(browser, vp, scheme, allHints('en_errors'), { ui });
        await run(browser, vp, scheme, autoAnswerAndAlt('en_errors'), { ui });
        await run(browser, vp, scheme, unsure('en_unsure'), { ui });
        await run(browser, vp, scheme, clean('en_clean'), { ui });
        await run(browser, vp, scheme, daily('en'), { ui });
      }
    }
  }

  // auto-advance after Fixed (no ?noauto), and none under reduced motion
  { const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } }); await ctx.addInitScript((b) => { window.__I18N = b; }, BUNDLES);
    const page = await ctx.newPage();
    await page.goto(`${URL}?fast&scenario=en_errors&auto=150`); await page.click('#submit'); await page.click('#dtr-go'); await page.fill('#dtr-ta', "It's a great way to learn by doing."); await page.click('#dtr-check');
    try { await page.waitForSelector('#dtr-sheet[data-view="fix"][data-i="1"]', { timeout: 4000 }); checks++; } catch { failures.push('auto-advance did not happen'); }
    await ctx.close(); }
  { const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' }); await ctx.addInitScript((b) => { window.__I18N = b; }, BUNDLES);
    const page = await ctx.newPage();
    await page.goto(`${URL}?scenario=en_errors&auto=150`); await page.click('#submit'); await page.click('#dtr-go'); await page.fill('#dtr-ta', "It's a great way to learn by doing."); await page.click('#dtr-check');
    await page.waitForSelector('#dtr-sheet[data-view="ok"]'); await page.waitForTimeout(700);
    if (await page.getAttribute('#dtr-sheet', 'data-view') !== 'ok') failures.push('reduced motion: auto-advance happened'); else checks++;
    await page.click('#dtr-next'); await page.waitForSelector('#dtr-sheet[data-view="fix"][data-i="1"]'); checks++;
    await ctx.close(); }

  await browser.close();
  console.log(`${checks} checks, ${failures.length} failures`);
  for (const f of failures) console.log('FAIL ' + f);
  process.exit(failures.length ? 1 : 0);
})();
