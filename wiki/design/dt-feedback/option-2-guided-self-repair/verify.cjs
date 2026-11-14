/* Walks every step of every flow of mockup.html and asserts the no-scroll rule.
   Run: NODE_PATH=/opt/node-tools/node_modules node verify.cjs [--shots]
   Writes steps/*.png, mobile.png, desktop.png when --shots is given. */
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const DIR = __dirname, URL = 'file://' + path.join(DIR, 'mockup.html');
const SHOTS = process.argv.includes('--shots');

const VIEWPORTS = [
  { name: '390x844', width: 390, height: 844, touch: true },
  { name: '375x667', width: 375, height: 667, touch: true },
  { name: '1280x800', width: 1280, height: 800, touch: false },
];
const KEYBOARD = [ // phone with the on-screen keyboard open (visual viewport shrunk)
  { name: '390x500-kb', width: 390, height: 500, touch: true },
  { name: '375x340-kb', width: 375, height: 340, touch: true },
];
const FIX = {
  en: [["sick", "great"], ["without it", "with it"]],
  zh: [["一个", "一件"], ["洗很多次", "洗了很多次"]],
  daily_en: [["learn on", "learn about"], ["need Arduino", "need an Arduino"]],
  daily_zh: [["洗很多次", "洗了很多次"], ["收藏下来", "收藏起来"]],
  unsure_en: [["an enjoyable", "a fun"]], unsure_zh: [["轻松", "放松"]],
};
let checks = 0; const failures = [];

async function assertStep(page, tag) {
  const r = await page.evaluate(() => {
    const out = [], se = document.scrollingElement, W = innerWidth, H = innerHeight;
    if (se.scrollHeight > H) out.push(`page scrolls vertically (${se.scrollHeight} > ${H})`);
    if (se.scrollWidth > W) out.push(`page scrolls horizontally (${se.scrollWidth} > ${W})`);
    if (scrollY !== 0 || scrollX !== 0) out.push('page is scrolled');
    const sheet = document.querySelector('#sheet'), open = !sheet.hidden;
    const root = open ? sheet : document.querySelector('#ex');
    const box = open ? sheet.getBoundingClientRect() : { left: 0, top: 0, right: W, bottom: H };
    const vis = el => { const c = getComputedStyle(el); const b = el.getBoundingClientRect(); return c.display !== 'none' && c.visibility !== 'hidden' && b.width > 0 && b.height > 0 && !el.closest('.sr'); };
    const name = el => el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + el.className;
    for (const el of root.querySelectorAll('*')) {
      if (!vis(el) || el.closest('svg') && el.tagName !== 'svg') continue;
      const b = el.getBoundingClientRect();
      if (b.left < box.left - .5 || b.right > box.right + .5 || b.top < box.top - .5 || b.bottom > box.bottom + .5) out.push(`${name(el)} outside the screen`);
      if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== 'visible' && el.tagName !== 'TEXTAREA') out.push(`${name(el)} overflows horizontally`);
    }
    if (open) {
      const stage = sheet.querySelector('#stage'), act = sheet.querySelector('#act').getBoundingClientRect(), st = stage.getBoundingClientRect();
      if (stage.scrollHeight > stage.clientHeight + 1) out.push(`stage content taller than its area (${stage.scrollHeight} > ${stage.clientHeight})`);
      if (act.bottom > box.bottom + .5) out.push('action area off screen');
      for (const el of stage.querySelectorAll('*')) {
        if (!vis(el) || el.closest('.mirror') || el.closest('svg') && el.tagName !== 'svg') continue;
        const b = el.getBoundingClientRect();
        if (b.bottom > act.top + .5) out.push(`${name(el)} clipped behind the action area (${Math.round(b.bottom)} > ${Math.round(act.top)})`);
        if (b.bottom > st.bottom + .5) out.push(`${name(el)} clipped by the stage`);
      }
      // text clipped inside its own box (the field may scroll inside itself only at the smallest type step)
      for (const el of stage.querySelectorAll('.slot, .moment, .orig, .lab, .eyebrow')) if (vis(el) && el.scrollHeight > el.clientHeight + 1) out.push(`${name(el)} text clipped (${el.scrollHeight} > ${el.clientHeight})`);
      const m = stage.querySelector('#mirror'); if (m && m.scrollHeight > m.clientHeight + 1) out.push('field text does not fit the field');
      const ta = stage.querySelector('#ta'); if (ta && ta.getBoundingClientRect().bottom > box.top + (box.bottom - box.top) * .62 && !sheet.classList.contains('kb')) out.push('field is not in the upper part of the screen');
      const prim = sheet.querySelectorAll('.act .btn.primary').length; if (prim > 1) out.push('more than one primary button');
      const quiet = [...sheet.querySelectorAll('.act .txt')].filter(vis).length; if (quiet > 2) out.push('more than two quiet actions');
      const above = [...stage.children].filter(e => vis(e) && e.id !== 'field' && e.id !== 'slot').length; if (stage.querySelector('#field') && above > 3) out.push('more than 3 text elements above the input');
    }
    for (const el of root.querySelectorAll('button, select')) { if (!vis(el)) continue; const b = el.getBoundingClientRect(); if (b.height < 43.5 || b.width < 43.5) if (!el.classList.contains('prompt') || el.classList.contains('more')) { if (!el.classList.contains('prompt')) out.push(`${name(el)} touch target ${Math.round(b.width)}x${Math.round(b.height)}`); } }
    return out;
  });
  checks++;
  if (r.length) failures.push(`${tag}: ${[...new Set(r)].join('; ')}`);
}

async function run(browser, vp, scheme, fn, { shots } = {}) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, colorScheme: scheme, hasTouch: vp.touch, isMobile: vp.touch, deviceScaleFactor: shots ? 2 : 1 });
  const page = await ctx.newPage(); const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  let n = 0;
  const T = {
    page, vp,
    goto: async (q = '') => { await page.goto(URL + '?fast&noauto' + q); },
    step: async (label) => { await page.waitForTimeout(60); await assertStep(page, `${vp.name} ${scheme} ${label}`); if (shots) await page.screenshot({ path: path.join(shots, `${String(++n).padStart(2, '0')}-${label.replace(/[^a-z0-9]+/gi, '-')}.png`) }); },
    view: async v => { await page.waitForSelector(`#sheet.on[data-view="${v}"]`); },
    submit: async () => { await page.click('#submit'); await page.waitForSelector('#sheet.on'); },
    edit: async (from, to) => { await page.evaluate(([a, b]) => { const ta = document.querySelector('#ta'); ta.value = ta.value.replace(a, b); ta.dispatchEvent(new Event('input')); }, [from, to]); },
    check: async () => { await page.click('#check'); },
  };
  await fn(T);
  if (errs.length) failures.push(`${vp.name} ${scheme}: page errors ${errs.join(' | ')}`);
  await ctx.close();
}

/* ---------- the paths ---------- */
const firstTry = lang => async T => {
  await T.goto('&lang=' + lang); await T.step(`${lang} start`);
  await T.submit(); await T.view('result'); await T.step(`${lang} result`);
  await T.page.click('#go');
  for (let i = 0; i < 2; i++) {
    await T.view('fix'); await T.step(`${lang} fix${i + 1}`);
    await T.edit(...FIX[lang][i]); await T.step(`${lang} fix${i + 1} edited`);
    await T.check(); await T.view('ok'); await T.step(`${lang} fix${i + 1} fixed`);
    await T.page.click('#next');
  }
  await T.view('summary'); await T.step(`${lang} summary`);
  await T.page.click('#done'); await T.page.waitForSelector('#sheet', { state: 'hidden' }); await T.step(`${lang} closed`);
};
const allHints = lang => async T => {
  await T.goto('&lang=' + lang); await T.submit(); await T.page.click('#go'); await T.view('fix');
  for (let h = 1; h <= 3; h++) { await T.page.click('#hint'); await T.step(`${lang} hint${h}`); }
  await T.check(); await T.step(`${lang} same-sentence`);
  await T.edit(/$/, ' x'); await T.check(); await T.page.waitForFunction(() => document.querySelector('#slot').textContent.includes('Still')); await T.step(`${lang} still-not-quite`);
  await T.page.click('#hint'); await T.view('reveal'); await T.step(`${lang} answer`);
  await T.page.click('#next'); await T.view('fix');
  await T.page.click('#hint'); await T.step(`${lang} s2 hint1`);
  await T.page.click('#fine'); await T.view('reveal'); await T.step(`${lang} s2 disputed`);
  await T.page.click('#next'); await T.view('summary'); await T.step(`${lang} summary-help`);
};
const autoAnswerAndAlt = lang => async T => {
  await T.goto('&lang=' + lang); await T.submit(); await T.page.click('#go'); await T.view('fix');
  for (let k = 0; k < 4; k++) { await T.edit(/$/, 'x'); await T.check(); if (k < 3) { await T.page.waitForFunction(() => document.querySelector('#check').getAttribute('aria-busy') === 'false'); await T.step(`${lang} failed-check${k + 1}`); } }
  await T.view('reveal'); await T.step(`${lang} auto-answer`);
  await T.page.click('#next'); await T.view('fix');
  await T.edit(FIX[lang][1][0], lang === 'en' ? 'using this' : '洗过许多次'); await T.check(); await T.view('alt'); await T.step(`${lang} no-issue-found`);
};
const clean = lang => async T => {
  await T.goto('&lang=' + lang); await T.page.selectOption('#scen', 'clean'); await T.step(`${lang} clean start`);
  await T.submit(); await T.view('clean'); await T.step(`${lang} clean`);
};
const unsure = lang => async T => {
  await T.goto('&lang=' + lang); await T.page.selectOption('#scen', 'unsure'); await T.step(`${lang} unsure start`);
  await T.submit(); await T.view('result'); await T.step(`${lang} unsure result`);
  await T.page.click('#go'); await T.view('fix'); await T.step(`${lang} unsure fix`);
  await T.page.click('#fine'); await T.view('kept'); await T.step(`${lang} unsure kept`);
  await T.page.click('#next'); await T.view('summary'); await T.step(`${lang} unsure summary`);
  await T.page.click('#done'); await T.submit(); await T.page.click('#go'); await T.view('fix');
  await T.edit(...FIX['unsure_' + lang][0]); await T.step(`${lang} unsure edited`);
  await T.check(); await T.view('ok'); await T.step(`${lang} unsure fixed`);
};
const daily = lang => async T => {
  await T.goto('&lang=' + lang); await T.page.click('#daily'); await T.view('fix'); await T.step(`${lang} daily fix1`);
  await T.edit(...FIX['daily_' + lang][0]); await T.check(); await T.view('ok'); await T.step(`${lang} daily fixed`);
  await T.page.click('#next'); await T.view('fix'); await T.step(`${lang} daily fix2`);
  await T.page.click('#hint'); await T.step(`${lang} daily hint2`);
  await T.page.click('#hint'); await T.step(`${lang} daily hint3`);
  await T.page.click('#hint'); await T.view('reveal'); await T.step(`${lang} daily answer`);
  await T.page.click('#next'); await T.view('summary'); await T.step(`${lang} daily summary`);
};
const stress = lang => async T => { // longest gold sentence in the language
  await T.goto('&stress=' + lang); await T.view('result'); await T.page.click('#go'); await T.view('fix'); await T.step(`stress-${lang} fix`);
  if (await T.page.$('#prompt.more')) { await T.page.click('#prompt'); await T.step(`stress-${lang} full-prompt`); await T.page.click('.full'); }
  for (let h = 1; h <= 3; h++) { await T.page.click('#hint'); await T.step(`stress-${lang} hint${h}`); }
  await T.edit(/$/, 'x'); await T.check(); await T.page.waitForFunction(() => document.querySelector('#slot').textContent.includes('Still')); await T.step(`stress-${lang} still`);
  await T.page.click('#hint'); await T.view('reveal'); await T.step(`stress-${lang} answer`);
};

(async () => {
  const browser = await chromium.launch();
  for (const scheme of ['light', 'dark']) {
    for (const vp of VIEWPORTS) {
      for (const lang of ['en', 'zh']) for (const p of [firstTry, allHints, autoAnswerAndAlt, clean, unsure, daily]) await run(browser, vp, scheme, p(lang));
      for (const lang of ['en', 'zh', 'ja']) await run(browser, vp, scheme, stress(lang));
    }
    for (const vp of KEYBOARD) {
      for (const lang of ['en', 'zh', 'ja']) await run(browser, vp, scheme, stress(lang));
      for (const lang of ['en', 'zh']) { await run(browser, vp, scheme, async T => { await T.goto('&lang=' + lang); await T.page.selectOption('#scen', 'unsure'); await T.submit(); await T.page.click('#go'); await T.view('fix'); await T.step(`${lang} unsure fix`); }); await run(browser, vp, scheme, daily(lang)); }
    }
  }
  // auto-advance (no ?noauto): the success moment moves on by itself
  { const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } }); const page = await ctx.newPage();
    await page.goto(URL + '?fast'); await page.click('#submit'); await page.click('#go'); await page.fill('#ta', "It's a great way to learn by doing."); await page.click('#check');
    try { await page.waitForSelector('#sheet[data-view="fix"][data-i="1"]', { timeout: 4000 }); checks++; } catch { failures.push('auto-advance did not happen'); }
    const ev = await page.evaluate(() => window.__events.map(e => e.kind).join(','));
    if (ev !== 'revision_checked,episode_closed') failures.push('events not recorded: ' + ev); else checks++;
    await ctx.close(); }

  if (SHOTS) {
    const steps = path.join(DIR, 'steps'); fs.rmSync(steps, { recursive: true, force: true }); fs.mkdirSync(steps);
    const tmp = fs.mkdtempSync(path.join(require('os').tmpdir(), 'dt-'));
    const m = VIEWPORTS[0], d = VIEWPORTS[2];
    // steps/: the en flow, hints path on sentence 1, first-try on sentence 2
    await run(browser, m, 'light', async T => {
      await T.goto('&lang=en'); await T.step('start'); await T.submit(); await T.view('result'); await T.step('result');
      await T.page.click('#go'); await T.view('fix'); await T.step('fix-1');
      await T.page.click('#hint'); await T.step('fix-1-hint-where'); await T.page.click('#hint'); await T.step('fix-1-hint-kind'); await T.page.click('#hint'); await T.step('fix-1-hint-clue');
      await T.edit('sick', 'cool'); await T.page.evaluate(() => { document.documentElement.classList.remove('noanim'); });
      await T.page.evaluate(() => { const b = document.querySelector('#check'); b.ariaBusy = 'true'; b.innerHTML = '<span class="spin"></span>Checking…'; }); await T.step('fix-1-checking');
      await T.page.evaluate(() => { const b = document.querySelector('#check'); b.ariaBusy = 'false'; b.textContent = 'Check'; document.documentElement.classList.add('noanim'); });
      await T.edit('cool', 'sick'); await T.edit(/$/, ' '); await T.edit('sick', 'cool'); await T.page.evaluate(() => { const ta = document.querySelector('#ta'); ta.value = ta.value.trim().replace('cool', 'sick') + ' really'; ta.dispatchEvent(new Event('input')); });
      await T.check(); await T.page.waitForFunction(() => document.querySelector('#slot').textContent.includes('Still')); await T.step('fix-1-still-not-quite');
      await T.page.click('#hint'); await T.view('reveal'); await T.step('fix-1-answer');
      await T.page.click('#next'); await T.view('fix'); await T.step('fix-2');
      await T.edit('without it', 'with it'); await T.check(); await T.view('ok'); await T.step('fix-2-fixed');
      await T.page.click('#next'); await T.view('summary'); await T.step('summary');
      await T.page.click('#done'); await T.page.selectOption('#scen', 'unsure'); await T.submit(); await T.page.click('#go'); await T.view('fix'); await T.step('unsure');
      await T.page.click('#close'); await T.page.selectOption('#scen', 'clean'); await T.submit(); await T.view('clean'); await T.step('clean');
      await T.page.click('#done'); await T.page.click('#daily'); await T.view('fix'); await T.step('daily');
    }, { shots: steps });
    for (const [vp, sub] of [[m, 'm-zh'], [d, 'd']]) { fs.mkdirSync(path.join(tmp, sub));
      await run(browser, vp, sub === 'd' ? 'light' : 'dark', async T => {
        await T.goto('&lang=' + (sub === 'd' ? 'en' : 'zh')); await T.submit(); await T.view('result'); await T.step('result');
        await T.page.click('#go'); await T.view('fix'); await T.step('fix'); await T.page.click('#hint'); await T.page.click('#hint'); await T.page.click('#hint'); await T.step('clue');
        await T.page.click('#hint'); await T.view('reveal'); await T.step('answer');
        await T.page.click('#next'); await T.view('fix'); await T.edit(...FIX[sub === 'd' ? 'en' : 'zh'][1]); await T.check(); await T.view('ok'); await T.step('fixed');
        await T.page.click('#next'); await T.view('summary'); await T.step('summary');
      }, { shots: path.join(tmp, sub) }); }
    fs.mkdirSync(path.join(tmp, 'kb'));
    await run(browser, KEYBOARD[0], 'light', async T => { await T.goto('&stress=ja'); await T.page.click('#go'); await T.view('fix'); await T.page.click('#hint'); await T.page.focus('#ta'); await T.step('keyboard'); }, { shots: path.join(tmp, 'kb') });
    const img = f => `data:image/png;base64,${fs.readFileSync(f).toString('base64')}`;
    const sheet = async (files, cols, w, out, caps) => {
      const ctx = await browser.newContext({ viewport: { width: cols * (w + 24) + 24, height: 600 }, deviceScaleFactor: 1 }); const page = await ctx.newPage();
      await page.setContent(`<body style="margin:0;padding:24px 12px;background:#cfd8d6;font:600 22px system-ui;color:#13282b;display:grid;grid-template-columns:repeat(${cols},${w}px);gap:28px 24px;justify-content:center;align-items:start">${files.map((f, i) => `<figure style="margin:0"><figcaption style="padding:0 0 10px">${caps[i]}</figcaption><img src="${img(f)}" style="width:${w}px;display:block;border-radius:12px;box-shadow:0 4px 14px #0003"></figure>`).join('')}</body>`);
      await page.screenshot({ path: path.join(DIR, out), fullPage: true }); await ctx.close();
    };
    const S = n => path.join(steps, fs.readdirSync(steps).find(f => f.includes(n)));
    const Tm = (sub, n) => path.join(tmp, sub, fs.readdirSync(path.join(tmp, sub)).find(f => f.includes(n)));
    await sheet([S('-start'), S('-result'), S('fix-1.png'), S('hint-clue'), S('checking'), S('still'), S('fix-1-answer'), S('fix-2-fixed'), S('-summary'), S('unsure'), S('daily'), Tm('m-zh', 'clue'), Tm('m-zh', 'answer'), Tm('kb', 'keyboard')], 5, 780, 'mobile.png',
      ['0 · Exercise, Submit', '1 · Result pops up', '2 · Fix step', '3 · Hint replaces hint', '4 · Checking', '5a · Still not quite', '6 · Answer shown', '5b · Fixed, auto-advances', '7 · Summary', 'Uncertain flag', 'Daily practice', '中文 · dark · clue', '中文 · dark · answer', 'Keyboard open · longest 日本語']);
    await sheet(['result', 'fix', 'clue', 'answer', 'fixed', 'summary'].map(n => Tm('d', n)), 3, 1280, 'desktop.png', ['1 · Result', '2 · Fix step', '3 · Clue', '6 · Answer', '5b · Fixed', '7 · Summary']);
  }
  await browser.close();
  console.log(`${checks} checks, ${failures.length} failures`);
  for (const f of failures) console.log('FAIL ' + f);
  process.exit(failures.length ? 1 : 0);
})();
