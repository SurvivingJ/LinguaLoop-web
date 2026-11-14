/* WP-INT: the guided self-repair flow in a real browser against the REAL app.

   Server: tests/e2e/dt-repair/devserver.py - the real Flask app, real templates and static
   files, the real submit route + dt_repair blueprint + repair services, over the in-memory
   store and a rule-based re-check (no Supabase, no OpenRouter, no production access).

     $V/bin/python tests/e2e/dt-repair/devserver.py --port 5055 &
     NODE_PATH=/opt/node-tools/node_modules node tests/e2e/dt-repair/integrated.cjs [--base http://127.0.0.1:5055]

   Per viewport (390x844 and 375x667, touch): the repair pass on /dual-translation (hints,
   still, fixed, reveal, summary, then today's result view from /result), the leak check over
   every response / the DOM / storage before each reveal, a reload that resumes the open pass,
   a clean submission, the three fallbacks to today's result view (flag off, a grade not from
   the single-call grader, repair tables missing), and the daily-practice player. The no-scroll
   rule is asserted on every sheet view. Screenshots go to
   wiki/design/dt-feedback/option-2-guided-self-repair/built-integrated/<viewport>/.
   Prints "N checks, M failures"; exits non-zero on any failure. */
const path = require('path');
const fs = require('fs');
const { chromium } = (() => {
  for (const p of (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)) {
    try {
      return require(path.join(p, 'playwright'));
    } catch {
      /* next */
    }
  }
  return require('playwright');
})();

const ROOT = path.join(__dirname, '..', '..', '..');
const argBase = process.argv.indexOf('--base');
const BASE = argBase > 0 ? process.argv[argBase + 1] : 'http://127.0.0.1:5055';
const SHOTS = path.join(ROOT, 'wiki/design/dt-feedback/option-2-guided-self-repair/built-integrated');
const REPRO =
  "It's a sick way to learn by doing. Arduino is a powerful tool. You can make many things without it. This arm is one idea.";
const GOLD =
  "It's a great way to learn by doing. Arduino is a powerful tool. You can make many things with it. This arm is one idea.";
// What must not reach the browser before the reveal of each sentence.
const SECRETS = {
  0: ["It's a great way to learn by doing.", '“sick” 是俚语', 'Register: “sick”'],
  2: ['You can make many things with it.', '意思反了', 'with it.'],
};
const VIEWPORTS = [
  { name: '390x844', width: 390, height: 844 },
  { name: '375x667', width: 375, height: 667 },
];

let checks = 0;
const failures = [];
function ok(cond, what) {
  checks += 1;
  if (!cond) failures.push(what);
}

async function layout(page, tag) {
  const out = await page.evaluate(() => {
    const o = [];
    const se = document.scrollingElement;
    if (se.scrollHeight > innerHeight + 1) o.push(`page scrolls vertically (${se.scrollHeight} > ${innerHeight})`);
    if (se.scrollWidth > innerWidth + 1) o.push(`page scrolls horizontally (${se.scrollWidth} > ${innerWidth})`);
    if (scrollY !== 0 || scrollX !== 0) o.push('page is scrolled');
    const sheet = document.querySelector('#dtr-sheet');
    if (!sheet) return o;
    const box = sheet.getBoundingClientRect();
    if (box.top < -0.5 || box.bottom > innerHeight + 0.5 || box.right > innerWidth + 0.5) o.push('sheet outside the viewport');
    const vis = (el) => {
      const c = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      return c.display !== 'none' && c.visibility !== 'hidden' && b.width > 1 && b.height > 1 && !el.closest('.dtr-sr');
    };
    const name = (el) => (el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + el.className);
    const stage = sheet.querySelector('#dtr-stage');
    const act = sheet.querySelector('#dtr-act').getBoundingClientRect();
    if (stage.scrollHeight > stage.clientHeight + 1) o.push(`stage taller than its area (${stage.scrollHeight} > ${stage.clientHeight})`);
    if (act.bottom > box.bottom + 0.5) o.push('action area off screen');
    for (const el of sheet.querySelectorAll('*')) {
      if (!vis(el) || (el.closest('svg') && el.tagName !== 'svg')) continue;
      const b = el.getBoundingClientRect();
      if (b.left < box.left - 0.5 || b.right > box.right + 0.5 || b.top < box.top - 0.5 || b.bottom > box.bottom + 0.5) o.push(`${name(el)} outside the sheet`);
    }
    for (const el of stage.querySelectorAll('*')) {
      if (!vis(el) || el.closest('.dtr-mirror') || (el.closest('svg') && el.tagName !== 'svg')) continue;
      if (el.getBoundingClientRect().bottom > act.top + 0.5) o.push(`${name(el)} behind the action area`);
    }
    const m = stage.querySelector('#dtr-mirror');
    if (m && m.scrollHeight > m.clientHeight + 1) o.push('field text does not fit');
    return o;
  });
  ok(out.length === 0, `${tag}: ${out.join('; ')}`);
}

async function view(page) {
  return page.evaluate(() => {
    const s = document.querySelector('#dtr-sheet');
    return s ? s.dataset.view : null;
  });
}

async function waitView(page, v, tag) {
  try {
    await page.waitForFunction((want) => {
      const s = document.querySelector('#dtr-sheet');
      return s && s.dataset.view === want && s.dataset.fieldState !== 'checking';
    }, v, { timeout: 8000 });
    await page.waitForTimeout(120);
    ok(true, '');
  } catch {
    ok(false, `${tag}: expected view ${v}, got ${await view(page)}`);
  }
}

async function shot(page, vp, name) {
  const dir = path.join(SHOTS, vp.name);
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: path.join(dir, `${name}.png`) });
}

async function browserHolds(page) {
  return page.evaluate(() => {
    let st = '';
    for (const s of [localStorage, sessionStorage]) for (let i = 0; i < s.length; i++) st += s.key(i) + '=' + s.getItem(s.key(i)) + '\n';
    return document.documentElement.outerHTML + '\n' + st;
  });
}

async function post(page, url) {
  await page.evaluate((u) => fetch(u, { method: 'POST' }), url);
}

async function newPage(browser, vp) {
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    reducedMotion: 'reduce',
  });
  const page = await ctx.newPage();
  const log = [];
  page.on('response', async (res) => {
    const url = res.url();
    if (!url.includes('/api/')) return;
    let body = '';
    try {
      body = await res.text();
    } catch {
      body = '';
    }
    log.push({ url: url.replace(BASE, ''), method: res.request().method(), status: res.status(), body });
  });
  page.on('pageerror', (e) => failures.push(`${vp.name}: page error ${e.message}`));
  return { ctx, page, log };
}

async function openPage(page) {
  await page.goto(`${BASE}/__dev/login?next=/dual-translation`);
  await page.waitForSelector('#dtReproduction', { state: 'visible', timeout: 10000 });
}

async function submitText(page, text) {
  await page.fill('#dtReproduction', text);
  await page.click('#dtSubmit');
}

async function resultShown(page, tag) {
  try {
    await page.waitForSelector('#dtResult', { state: 'visible', timeout: 8000 });
    ok(true, '');
  } catch {
    ok(false, `${tag}: today's result view did not appear`);
    return;
  }
  const s = await page.evaluate(() => ({
    sheet: !!document.querySelector('#dtr-sheet'),
    errors: document.querySelector('#dtErrors').textContent.length,
    band: document.querySelector('#dtOverallBand').textContent.trim(),
  }));
  ok(!s.sheet, `${tag}: the sheet is still open over the result view`);
  ok(s.band === '3', `${tag}: result band is "${s.band}", expected 3`);
  return s;
}

async function mainPass(browser, vp) {
  const { ctx, page, log } = await newPage(browser, vp);
  await page.goto(`${BASE}/__dev/login?next=/dual-translation`);
  await post(page, `${BASE}/__dev/reset`);
  await openPage(page);
  await shot(page, vp, '00-exercise');
  await submitText(page, REPRO);
  await waitView(page, 'result', `${vp.name} pass`);
  const submit = log.find((r) => /\/submit$/.test(r.url));
  ok(submit && JSON.parse(submit.body).redacted === true, `${vp.name}: submit response is not redacted`);
  await layout(page, `${vp.name} result`);
  await shot(page, vp, '01-result');
  await page.click('#dtr-go');
  await waitView(page, 'fix', `${vp.name} start`);
  await layout(page, `${vp.name} fix`);
  await shot(page, vp, '02-fix');
  const hintNames = ['03-hint-where', '04-hint-kind', '05-hint-clue'];
  for (const n of hintNames) {
    await page.click('#dtr-hint');
    await page.waitForFunction(() => document.querySelector('#dtr-slot').textContent.length > 0, null, { timeout: 5000 });
    await page.waitForTimeout(100);
    await layout(page, `${vp.name} ${n}`);
    await shot(page, vp, n);
  }
  ok((await page.textContent('#dtr-mirror mark')) === 'sick', `${vp.name}: underline is not on "sick"`);
  ok((await page.getAttribute('#dtr-slot span[lang]', 'lang')) === 'zh', `${vp.name}: clue not marked lang=zh`);
  let held = await browserHolds(page);
  for (const s of [...SECRETS[0], ...SECRETS[2]]) ok(!held.includes(s), `${vp.name}: "${s}" in the page before its reveal`);
  await page.fill('#dtr-ta', "It's a cool way to learn by doing.");
  await page.click('#dtr-check');
  await page.waitForFunction(() => document.querySelector('#dtr-sheet').dataset.fieldState === 'checking', null, { timeout: 3000 }).catch(() => {});
  await shot(page, vp, '06-checking');
  await page.waitForFunction(() => /Still not quite/.test(document.querySelector('#dtr-slot').textContent), null, { timeout: 8000 });
  ok((await page.textContent('#dtr-mirror mark')) === 'cool', `${vp.name}: still-flagged underline not on "cool"`);
  await layout(page, `${vp.name} still`);
  await shot(page, vp, '07-still');
  await page.fill('#dtr-ta', "It's a great way to learn by doing!");
  await page.click('#dtr-check');
  await waitView(page, 'ok', `${vp.name} fixed`);
  ok((await page.textContent('.dtr-moment p')) === 'With 3 hints', `${vp.name}: success line`);
  await layout(page, `${vp.name} ok`);
  await shot(page, vp, '08-fixed');
  await page.click('#dtr-next');
  await waitView(page, 'fix', `${vp.name} step 2`);
  await page.click('#dtr-hint');
  await page.waitForFunction(() => document.querySelector('#dtr-mirror mark'), null, { timeout: 5000 });
  ok((await page.textContent('#dtr-hint')) === 'Show answer', `${vp.name}: short ladder button`);
  held = await browserHolds(page);
  const beforeReveal = log.map((r) => r.body).join('\n');
  for (const s of SECRETS[2]) {
    ok(!held.includes(s), `${vp.name}: "${s}" in the page before its reveal`);
    ok(!beforeReveal.includes(s), `${vp.name}: "${s}" in a response before its reveal`);
  }
  await shot(page, vp, '09-fix-2-where');
  await page.click('#dtr-hint');
  await waitView(page, 'reveal', `${vp.name} reveal`);
  ok((await page.textContent('#dtr-cmp-mine del')) === 'without it', `${vp.name}: You wrote mark`);
  ok((await page.textContent('#dtr-cmp-ans b')) === 'with it', `${vp.name}: Answer mark`);
  await layout(page, `${vp.name} reveal`);
  await shot(page, vp, '10-answer');
  await page.click('#dtr-next');
  await waitView(page, 'summary', `${vp.name} summary`);
  const tally = (await page.textContent('.dtr-tally')).replace(/\s+/g, ' ');
  ok(/Fixed yourself 1/.test(tally) && /Needed help 1/.test(tally) && /Saved to practice 2/.test(tally), `${vp.name}: summary "${tally}"`);
  await layout(page, `${vp.name} summary`);
  await shot(page, vp, '11-summary');
  await page.click('#dtr-done');
  await resultShown(page, `${vp.name} after pass`);
  const errs = await page.evaluate(() => document.querySelector('#dtErrors').textContent);
  ok(errs.includes('great') || errs.length > 20, `${vp.name}: full result has no error cards`);
  await shot(page, vp, '12-result-view');
  const st = await (await page.request.get(`${BASE}/__dev/state`)).json();
  const sess = Object.values(st.sessions)[0];
  ok(sess && sess.status === 'finished', `${vp.name}: session not finished (${sess && sess.status})`);
  ok(st.recheck_calls === 2, `${vp.name}: ${st.recheck_calls} re-check calls, expected 2`);
  ok(!(await page.evaluate(() => localStorage.getItem('dt_repair_open'))), `${vp.name}: resume stash left behind`);
  // the order of calls the page made
  const calls = log.filter((r) => r.url.includes('/repair/')).map((r) => `${r.method} ${r.url.replace(/^.*\/repair/, '')} ${r.status}`);
  fs.writeFileSync(path.join(SHOTS, vp.name, 'calls.txt'), calls.join('\n') + '\n');
  ok(calls.every((c) => / 200$/.test(c)), `${vp.name}: non-200 repair call: ${calls.filter((c) => !/ 200$/.test(c))}`);

  // daily practice next day: both sentences are due
  await post(page, `${BASE}/__dev/advance?hours=26`);
  await page.goto(`${BASE}/__dev/daily`);
  await waitView(page, 'fix', `${vp.name} daily`);
  ok((await page.getAttribute('#dtr-field', 'lang')) === 'en', `${vp.name}: daily field lang`);
  ok((await page.getAttribute('#dtr-prompt', 'lang')) === 'zh', `${vp.name}: daily prompt lang`);
  ok(!!(await page.$('.dtr-eyebrow')), `${vp.name}: daily from-date eyebrow`);
  await layout(page, `${vp.name} daily fix`);
  await shot(page, vp, '13-daily-fix');
  await page.fill('#dtr-ta', 'You can make many things with it.');
  await page.click('#dtr-check');
  await waitView(page, 'ok', `${vp.name} daily fixed`);
  ok((await page.textContent('.dtr-moment p')) === 'Without any more help', `${vp.name}: daily success line`);
  await page.click('#dtr-next');
  await waitView(page, 'fix', `${vp.name} daily 2`);
  await page.click('#dtr-hint');
  await page.waitForTimeout(300);
  await page.click('#dtr-hint');
  await page.waitForTimeout(300);
  await page.click('#dtr-hint');
  await waitView(page, 'reveal', `${vp.name} daily reveal`);
  await shot(page, vp, '14-daily-answer');
  await page.click('#dtr-next');
  await waitView(page, 'summary', `${vp.name} daily summary`);
  const dt = (await page.textContent('.dtr-tally')).replace(/\s+/g, ' ');
  ok(/Fixed yourself 1/.test(dt) && /Needed help 1/.test(dt) && /Back in practice later 1/.test(dt), `${vp.name}: daily summary "${dt}"`);
  await layout(page, `${vp.name} daily summary`);
  await shot(page, vp, '15-daily-summary');
  await page.click('#dtr-done');
  await page.waitForFunction(() => document.querySelector('#dev-daily-done').dataset.done, null, { timeout: 5000 });
  const done = JSON.parse(await page.getAttribute('#dev-daily-done', 'data-done'));
  ok(done.complete && done.complete.dt_repair === 2, `${vp.name}: daily block result ${JSON.stringify(done)}`);
  await ctx.close();
}

async function resumeAndClean(browser, vp) {
  const { ctx, page } = await newPage(browser, vp);
  await page.goto(`${BASE}/__dev/login?next=/dual-translation`);
  await post(page, `${BASE}/__dev/reset`);
  await openPage(page);
  await submitText(page, REPRO);
  await waitView(page, 'result', `${vp.name} resume`);
  await page.click('#dtr-go');
  await waitView(page, 'fix', `${vp.name} resume start`);
  await page.click('#dtr-hint');
  await page.waitForTimeout(300);
  await page.reload();
  await waitView(page, 'fix', `${vp.name} resumed after reload`);
  ok((await page.inputValue('#dtr-ta')).includes('sick'), `${vp.name}: resumed step is not the first open one`);
  await shot(page, vp, '20-resumed-after-reload');
  await page.click('#dtr-close');
  await resultShown(page, `${vp.name} closed early`);
  const st = await (await page.request.get(`${BASE}/__dev/state`)).json();
  const sess = Object.values(st.sessions)[0];
  ok(sess && sess.closed_early === true, `${vp.name}: close did not finish early`);

  // a clean submission: "No issues found", then today's result view
  await page.click('#dtTryAnother');
  await page.waitForSelector('#dtReproduction', { state: 'visible' });
  await submitText(page, GOLD);
  await waitView(page, 'clean', `${vp.name} clean`);
  await layout(page, `${vp.name} clean`);
  await shot(page, vp, '21-clean');
  await page.click('#dtr-done');
  await resultShown(page, `${vp.name} after clean`);
  await ctx.close();
}

async function fallbacks(browser, vp) {
  const cases = [
    ['flag off', `${BASE}/__dev/mode?flag=0`],
    ['grade not from the single-call grader', `${BASE}/__dev/mode?tier=tier2`],
    ['repair tables missing', `${BASE}/__dev/fail-tables?on=1`],
    ['bypassed (a score of 1)', `${BASE}/__dev/mode?band1=1`],
  ];
  for (const [label, url] of cases) {
    const { ctx, page, log } = await newPage(browser, vp);
    await page.goto(`${BASE}/__dev/login?next=/dual-translation`);
    await post(page, `${BASE}/__dev/reset`);
    await post(page, url);
    await openPage(page);
    await submitText(page, REPRO);
    await resultShown(page, `${vp.name} ${label}`);
    await page.waitForTimeout(300);
    ok(!(await page.$('#dtr-sheet')), `${vp.name} ${label}: a sheet opened`);
    const sub = JSON.parse(log.find((r) => /\/submit$/.test(r.url)).body);
    ok(!sub.redacted && sub.errors.length === 2, `${vp.name} ${label}: submit not the full contract`);
    ok(label.startsWith('bypassed') ? sub.repair && sub.repair.status === 'bypassed' : !('repair' in sub), `${vp.name} ${label}: repair key`);
    const extra = log.filter((r) => r.url.includes('/repair/'));
    ok(extra.length === 0, `${vp.name} ${label}: repair calls ${extra.map((r) => r.url)}`);
    if (label === 'repair tables missing') await shot(page, vp, '30-fallback-tables-missing');
    await ctx.close();
  }
}

(async () => {
  const browser = await chromium.launch();
  try {
    for (const vp of VIEWPORTS) {
      await mainPass(browser, vp);
      await resumeAndClean(browser, vp);
      await fallbacks(browser, vp);
    }
  } finally {
    await browser.close();
  }
  console.log(`${checks} checks, ${failures.length} failures`);
  failures.forEach((f) => console.log('  FAIL ' + f));
  process.exit(failures.length ? 1 : 0);
})();
