/* Screenshots (deviceScaleFactor 2, 390x844) of each step of the real sheet, named like the
   design mockup's steps/*.png, for a side-by-side look.
   Run: NODE_PATH=/opt/node-tools/node_modules node tests/e2e/dt-repair/shots.cjs [outDir]
   Default outDir: wiki/design/dt-feedback/option-2-guided-self-repair/built */
const path = require('path');
const fs = require('fs');
const { chromium } = (() => {
  for (const p of (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)) {
    try { return require(path.join(p, 'playwright')); } catch { /* next */ }
  }
  return require('playwright');
})();

const ROOT = path.join(__dirname, '..', '..', '..');
const OUT = process.argv[2] || path.join(ROOT, 'wiki/design/dt-feedback/option-2-guided-self-repair/built');
const URL = 'file://' + path.join(__dirname, 'harness.html');
const BUNDLES = {};
for (const l of ['en', 'zh', 'ja']) BUNDLES[l] = JSON.parse(fs.readFileSync(path.join(ROOT, 'static/i18n', l + '.json'), 'utf8'));

(async () => {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const mk = async (opts = {}) => {
    const ctx = await browser.newContext({ viewport: { width: opts.w || 390, height: opts.h || 844 }, colorScheme: opts.scheme || 'light', hasTouch: opts.w === 1280 ? false : true, isMobile: opts.w === 1280 ? false : true, deviceScaleFactor: 2 });
    await ctx.addInitScript((b) => { window.__I18N = b; }, BUNDLES);
    return { ctx, page: await ctx.newPage() };
  };
  let n = 0;
  const snap = async (page, label, dir = OUT) => { await page.waitForTimeout(80); await page.screenshot({ path: path.join(dir, `${String(++n).padStart(2, '0')}-${label}.png`) }); };
  const view = (page, v) => page.waitForSelector(`#dtr-sheet[data-view="${v}"]`);
  const edit = (page, a, b) => page.evaluate(([x, y]) => { const ta = document.querySelector('#dtr-ta'); ta.value = x === null ? ta.value + y : ta.value.replace(x, y); ta.dispatchEvent(new Event('input', { bubbles: true })); }, [a, b]);
  const settle = (page) => page.waitForFunction(() => { const s = document.querySelector('#dtr-sheet'); return !s || s.dataset.fieldState !== 'checking'; });

  // the en flow (steps/): hints on sentence 1, first try on sentence 2
  { const { ctx, page } = await mk();
    await page.goto(`${URL}?fast&scenario=en_errors&lat=250`);
    await snap(page, 'start');
    await page.click('#submit'); await view(page, 'result'); await snap(page, 'result');
    await page.click('#dtr-go'); await view(page, 'fix'); await snap(page, 'fix-1');
    await page.click('#dtr-hint'); await page.waitForTimeout(400); await snap(page, 'fix-1-hint-where');
    await page.click('#dtr-hint'); await page.waitForTimeout(400); await snap(page, 'fix-1-hint-kind');
    await page.click('#dtr-hint'); await page.waitForTimeout(400); await snap(page, 'fix-1-hint-clue');
    await edit(page, null, ' really');
    await page.click("#dtr-check"); await page.waitForTimeout(100); await snap(page, "fix-1-checking"); await settle(page);
    await snap(page, 'fix-1-still-not-quite');
    await page.click('#dtr-hint'); await view(page, 'reveal'); await snap(page, 'fix-1-answer');
    await page.click('#dtr-next'); await view(page, 'fix'); await snap(page, 'fix-2');
    await edit(page, 'without it', 'with it'); await page.click('#dtr-check'); await view(page, 'ok'); await snap(page, 'fix-2-fixed');
    await page.click('#dtr-next'); await view(page, 'summary'); await snap(page, 'summary');
    await page.click('#dtr-done'); await page.waitForSelector('#dtr-sheet', { state: 'detached' });
    await page.selectOption('#scen', 'en_unsure'); await page.click('#submit'); await page.click('#dtr-go'); await view(page, 'fix'); await snap(page, 'unsure');
    await page.click('#dtr-close'); await page.waitForSelector('#dtr-sheet', { state: 'detached' });
    await page.selectOption('#scen', 'en_clean'); await page.click('#submit'); await view(page, 'clean'); await snap(page, 'clean');
    await page.click('#dtr-done'); await page.waitForSelector('#dtr-sheet', { state: 'detached' });
    await page.click('#daily'); await view(page, 'fix'); await snap(page, 'daily');
    await ctx.close(); }

  // the answer screen with a no-issue-found and a dispute, plus a point (omission) marker
  { const dir = path.join(OUT, 'extra'); fs.mkdirSync(dir); n = 0;
    const { ctx, page } = await mk();
    await page.goto(`${URL}?fast&scenario=en_mixed`);
    await page.click('#submit'); await page.click('#dtr-go'); await view(page, 'fix');
    await edit(page, 'sick', 'great'); await page.click('#dtr-check'); await view(page, 'ok');
    await page.click('#dtr-next'); await view(page, 'reveal'); await snap(page, 'direct-answer', dir);
    await page.click('#dtr-next'); await view(page, 'fix'); await page.click('#dtr-hint'); await page.waitForTimeout(150); await snap(page, 'point-marker', dir);
    await ctx.close(); }
  { const dir = path.join(OUT, 'zh-dark'); fs.mkdirSync(dir); n = 0;
    const { ctx, page } = await mk({ scheme: 'dark' });
    await page.goto(`${URL}?fast&scenario=zh_errors&theme=midnight&ui=zh`);
    await page.click('#submit'); await view(page, 'result'); await snap(page, 'result', dir);
    await page.click('#dtr-go'); await view(page, 'fix'); await snap(page, 'fix', dir);
    for (let i = 0; i < 3; i++) { await page.click('#dtr-hint'); await page.waitForTimeout(300); }
    await page.waitForTimeout(150); await snap(page, 'clue', dir);
    await page.click('#dtr-hint'); await view(page, 'reveal'); await snap(page, 'answer', dir);
    await ctx.close(); }
  { const dir = path.join(OUT, 'desktop'); fs.mkdirSync(dir); n = 0;
    const { ctx, page } = await mk({ w: 1280, h: 800 });
    await page.goto(`${URL}?fast&scenario=en_errors`);
    await page.click('#submit'); await view(page, 'result'); await snap(page, 'result', dir);
    await page.click('#dtr-go'); await view(page, 'fix'); await page.click('#dtr-hint'); await page.waitForTimeout(300); await snap(page, 'fix-hint', dir);
    for (let i = 0; i < 3; i++) { await page.click('#dtr-hint'); await page.waitForTimeout(300); } await view(page, 'reveal'); await snap(page, 'answer', dir);
    await ctx.close(); }
  { const dir = path.join(OUT, 'keyboard'); fs.mkdirSync(dir); n = 0;
    const { ctx, page } = await mk({ h: 500 });
    await page.goto(`${URL}?fast&scenario=stress_ja`);
    await page.click('#submit'); await page.click('#dtr-go'); await view(page, 'fix'); await page.click('#dtr-hint'); await page.focus('#dtr-ta'); await snap(page, 'keyboard-ja', dir);
    await ctx.close(); }
  await browser.close();
  console.log('screenshots written to ' + OUT);
})();
