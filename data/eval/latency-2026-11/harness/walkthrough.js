// Functional walkthrough with the test account. node walkthrough.js BASE OUTDIR
const { chromium, devices } = require('playwright'); const fs = require('fs'), path = require('path');
const { execFileSync } = require('child_process');
const S = __dirname, BASE = process.argv[2], OUT = process.argv[3]; fs.mkdirSync(OUT, { recursive: true });
const SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156';
const PY = path.join(S, 'venv/bin/python');
const mint = () => JSON.parse(execFileSync(PY, [path.join(S, 'mint.py'), '--json']).toString());
const CDN = { 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css': 'bootstrap/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js': 'bootstrap/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css': '@fortawesome/fontawesome-free/css/all.min.css' };
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const fakeJwt = (exp) => `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64({ sub: 'x', exp })}.invalidsig`;
const results = [];
const RAWKEY = /\b(?:test|tests|session|common|nav|prestudy|study_plan|flashcards|profile|preview|practice|error|login|calibration|word_list)\.[a-z_]+(?:\.[a-z_]+)*\b/g;
const check = (name, ok, detail) => { results.push({ name, ok: !!ok, detail }); console.log(ok ? 'PASS' : 'FAIL', name, detail ? JSON.stringify(detail).slice(0, 300) : ''); };

async function context(browser, { token, refresh, opts = {}, uiLang } = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...opts });
  await ctx.route(/cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/, (r) => {
    const u = r.request().url(); if (CDN[u]) return r.fulfill({ path: path.join(S, 'cdn/node_modules', CDN[u]), headers: { 'access-control-allow-origin': '*' } });
    const m = u.match(/webfonts\/([^?]+)/); if (m) return r.fulfill({ path: path.join(S, 'cdn/node_modules/@fortawesome/fontawesome-free/webfonts', m[1]), headers: { 'access-control-allow-origin': '*' } });
    return r.fulfill({ status: 200, contentType: 'text/css', body: '' }); });
  await ctx.addInitScript(([t, l]) => { if (!sessionStorage.getItem('__init')) { sessionStorage.setItem('__init', '1');
    localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3'); if (l) localStorage.setItem('linguadojo-ui-lang', l); } }, [token, uiLang || null]);
  if (refresh) await ctx.addCookies([{ name: 'lingualoop_refresh', value: refresh, url: BASE + '/api/auth/', httpOnly: true }]);
  return ctx;
}
function track(page) {
  const t = { reqs: [], errors: [], statuses: [] };
  page.on('request', (r) => t.reqs.push(r.url().replace(BASE, '')));
  page.on('response', (r) => { if (r.url().startsWith(BASE + '/api/')) t.statuses.push([r.url().replace(BASE, '').split('?')[0], r.status()]); });
  page.on('pageerror', (e) => t.errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/ERR_TUNNEL|audio\.linguadojo/.test(m.text())) t.errors.push(m.text()); });
  return t;
}

(async () => {
  const browser = await chromium.launch();
  let sess = mint();

  // 1. Expired token in storage: the head script renews ONCE; page calls wait and never 401.
  { const ctx = await context(browser, { token: fakeJwt(1000), refresh: sess.refresh_token }); const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + '/tests', { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
    const refreshes = t.reqs.filter((u) => u.startsWith('/api/auth/refresh-token')).length;
    const s401 = t.statuses.filter(([, s]) => s === 401);
    check('expired token: one renewal, no 401s, tests listed', refreshes === 1 && !s401.length && (await p.locator('.test-card, [onclick*="goToTestPreview"]').count()) > 0,
      { refreshes, s401, url: p.url().replace(BASE, ''), errors: t.errors });
    await p.screenshot({ path: path.join(OUT, '01_expired_token_tests.png') }); await ctx.close(); }

  // 2. Token rejected by the server (bad signature, future exp): parallel 401s share ONE renewal.
  sess = mint();
  { const ctx = await context(browser, { token: fakeJwt(Math.floor(Date.now() / 1000) + 3600), refresh: sess.refresh_token }); const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + '/tests', { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
    const refreshes = t.reqs.filter((u) => u.startsWith('/api/auth/refresh-token')).length;
    const n401 = t.statuses.filter(([, s]) => s === 401).length; const ok200 = t.statuses.filter(([u, s]) => s === 200 && u.startsWith('/api/tests')).length;
    check('rejected token: 401s share one renewal, then data loads', refreshes === 1 && ok200 >= 3, { refreshes, n401, ok200, url: p.url().replace(BASE, ''), errors: t.errors });
    await ctx.close(); }

  // Fresh, valid session for the rest.
  sess = mint();
  const ctx = await context(browser, { token: sess.access_token, refresh: sess.refresh_token });

  // 3. Daily session: start, first player mounts (lazily), only needed player modules load.
  { const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + '/session', { waitUntil: 'networkidle' });
    const players0 = t.reqs.filter((u) => u.includes('/session/players/'));
    await p.click('#sessionStartBtn'); await p.waitForTimeout(1500); await p.waitForLoadState('networkidle');
    const spinner = await p.locator('#sessionStage [data-player-loading]').count();
    const stageText = (await p.locator('#sessionStage').innerText()).trim();
    check('session: start mounts first player', !spinner && stageText.length > 20 && !t.errors.length,
      { preloadedPlayers: players0.map((u) => u.split('/').pop().split('?')[0]), stageText: stageText.slice(0, 120), errors: t.errors });
    await p.screenshot({ path: path.join(OUT, '03_session_first_item.png'), fullPage: true }); await p.close(); }

  // 4. Practice mode: start, an exercise renders; answer it (first choice) and see feedback.
  { const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + '/session?mode=practice', { waitUntil: 'networkidle' });
    const startVisible = await p.locator('#sessionStartBtn').isVisible().catch(() => false);
    if (startVisible) { await p.click('#sessionStartBtn');
      for (let i = 0; i < 40; i++) { await p.waitForTimeout(500); if ((await p.locator('#sessionStage').innerText()).trim().length > 40) break; } }
    await p.screenshot({ path: path.join(OUT, '04_practice_item.png'), fullPage: true });
    const stage = (await p.locator('#sessionStage').innerText().catch(() => '')).trim();
    let answered = false;
    const input = p.locator('#sessionStage input[type=text], #sessionStage input:not([type])').first();
    if (await input.count()) { await input.fill('x'); await p.locator('#sessionStage button', { hasText: 'Check' }).first().click().catch(() => {}); }
    else { const choice = p.locator('#sessionStage button:not([disabled])').filter({ hasNotText: /skip|later|done|keep|end|know/i }).first();
           if (await choice.count()) await choice.click().catch(() => {}); }
    await p.waitForTimeout(1500); answered = /not quite|correct|right|wrong|next/i.test(await p.locator('#sessionStage').innerText());
    await p.screenshot({ path: path.join(OUT, '04b_practice_after_answer.png'), fullPage: true });
    const attemptPosts = t.statuses.filter(([u]) => /attempt|intro\/complete/.test(u));
    check('practice: exercise renders and an answer is accepted', stage.length > 10 && !t.errors.length && attemptPosts.every(([, s]) => s < 400),
      { startVisible, answered, attemptPosts, stage: stage.slice(0, 120), errors: t.errors });
    await p.close(); }

  // 5. Preview -> Start -> test page reuses the preview payload (one /api/tests/test fetch total).
  { const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + `/test/${SLUG}/preview?type=reading`, { waitUntil: 'networkidle' });
    await p.screenshot({ path: path.join(OUT, '05_preview.png'), fullPage: true });
    await Promise.all([p.waitForNavigation({ waitUntil: 'networkidle' }), p.click('#startTestBtn')]);
    await p.waitForTimeout(1000);
    const fetches = t.reqs.filter((u) => u.startsWith(`/api/tests/test/${SLUG}`)).length;
    const qCount = await p.locator('input[type=radio], .choice-btn, .answer-option, [data-choice]').count();
    check('preview -> test: test payload fetched once, questions render', fetches === 1 && qCount > 0 && !t.errors.length,
      { fetches, qCount, url: p.url().replace(BASE, ''), errors: t.errors });
    await p.screenshot({ path: path.join(OUT, '05b_test_page.png'), fullPage: true });
    // Reload: no hand-off left, so it fetches again (and still renders).
    const before = t.reqs.filter((u) => u.startsWith(`/api/tests/test/${SLUG}`)).length;
    await p.reload({ waitUntil: 'networkidle' }); await p.waitForTimeout(800);
    const after = t.reqs.filter((u) => u.startsWith(`/api/tests/test/${SLUG}`)).length;
    check('test page reload fetches fresh data', after === before + 1 && (await p.locator('input[type=radio], .choice-btn, .answer-option, [data-choice]').count()) > 0, { before, after });
    await p.close(); }

  // 6. UI language: switch to Japanese, nav translates; both i18n files load on a fresh page.
  { const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + '/tests', { waitUntil: 'networkidle' });
    const navEn = await p.locator('nav').first().innerText();
    await p.evaluate(() => window.LinguaI18n.setLanguage('ja')); await p.waitForTimeout(800);
    const navJa = await p.locator('nav').first().innerText();
    await p.reload({ waitUntil: 'networkidle' });
    const navJa2 = await p.locator('nav').first().innerText();
    const i18n = t.reqs.filter((u) => u.startsWith('/static/i18n/'));
    check('i18n: switching to ja translates, survives reload, versioned files', navEn !== navJa && navJa2 === navJa && i18n.every((u) => /\?v=/.test(u)),
      { navEn: navEn.replace(/\s+/g, ' ').slice(0, 80), navJa: navJa.replace(/\s+/g, ' ').slice(0, 80), i18n, errors: t.errors });
    await p.screenshot({ path: path.join(OUT, '06_tests_ja.png') });
    await p.evaluate(() => window.LinguaI18n.setLanguage('en')); await p.close(); }

  // 7. Remaining pages load without errors.
  for (const [n, u] of Object.entries({ tests: '/tests', preview: `/test/${SLUG}/preview?type=reading`, test: `/test/${SLUG}?type=reading`, session: '/session', studyplan: '/study-plan', prestudy: `/test/${SLUG}/prestudy?type=reading`, flashcards: '/flashcards', profile: '/profile', wordlist: '/word-list' })) {
    const p = await ctx.newPage(); const t = track(p);
    await p.goto(BASE + u, { waitUntil: 'networkidle' }); await p.waitForTimeout(800);
    const bad = t.statuses.filter(([, s]) => s >= 400);
    const rawKeys = ((await p.locator('body').innerText()).match(RAWKEY) || []);
    check(`${n}: loads without errors or raw i18n keys`, !bad.length && !t.errors.length && !rawKeys.length, { bad, rawKeys, errors: t.errors, landed: p.url().replace(BASE, '') });
    await p.close();
  }
  await ctx.close();
  fs.writeFileSync(path.join(OUT, 'walkthrough.json'), JSON.stringify(results, null, 1));
  await browser.close();
  console.log(`${results.filter((r) => r.ok).length}/${results.length} passed`);
})();
