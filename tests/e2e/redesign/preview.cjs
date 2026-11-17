/* Phone-size preview harness for the 2026-11 mobile redesign.

   Opens a real page of the app (served by tests/e2e/redesign/serve.py, or any running
   instance) in Chromium at phone size, signed in with a fake token, with every /api/*
   request answered in the browser from fixture JSON. Reports whether the DOCUMENT scrolls,
   how far each stage overflows, whether the dock and its buttons are inside the viewport,
   horizontal overflow, and API calls that had no fixture. Optionally saves a screenshot.

   Run (start the server first):
     python tests/e2e/redesign/serve.py --port 5099 &
     node tests/e2e/redesign/preview.cjs --port 5099 --path /session --shot /tmp/session.png

   Options (all optional):
     --port N            server port (default 5099); or --base http://host:port
     --path /url         page to open (default /session); repeatable
     --size WxH          viewport (default 393x659 = iPhone 15 Safari, toolbars shown)
                         presets: --size iphone15 | iphone15-full (393x759) | se (375x553)
                         | desktop (1280x800)
     --theme ID          default | stillwater | midnight | sakura | forest | inkstone
     --mode M            system | light | dark   (default light)
     --lang ID           study language id: 1 zh, 2 en, 3 ja (default 1); 0 = none chosen
     --ui CODE           UI language: en | zh | ja | es
     --fixtures FILE     JSON fixture map (default: fixtures/default.json next to this file);
                         repeatable, later files win
     --task              force task mode on (LinguaShell.setTaskMode(true)) before measuring
     --click SELECTOR    click this before measuring; repeatable, in order
     --wait SELECTOR     wait for this selector before measuring
     --wait-ms N         extra settle time (default 400)
     --eval JS           run this JS in the page before measuring (after clicks)
     --shot FILE.png     save a screenshot (with --path repeated, -<n> is appended)
     --full              full-page screenshot instead of the viewport
     --fonts             let Google Fonts load (default: blocked, so runs are offline and
                         deterministic; text then renders in the fallback stacks)
     --json              print only the JSON report
     --strict            exit 1 if the document scrolls, the dock is off-screen or the page
                         overflows horizontally

   Fixture map: { "<METHOD> <path>": <response>, "<path>": <response>, "<prefix>*": <response> }
   A response is { "status": 200, "body": {...} } or just the JSON body. The query string
   is ignored unless the key contains "?". Unmatched calls get 200 {"success": true} and
   are listed in the report under "unmocked". */
'use strict';

const fs = require('fs');
const path = require('path');
const { chromium } = (() => {
  // Prefer the preinstalled Playwright (matches the preinstalled Chromium).
  for (const p of (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)) {
    try {
      return require(path.join(p, 'playwright'));
    } catch {
      /* try the next entry */
    }
  }
  return require('playwright');
})();

const SIZES = {
  iphone15: [393, 659],
  'iphone15-full': [393, 759],
  se: [375, 553],
  desktop: [1280, 800],
};
const LANGS = {
  1: { id: 1, code: 'zh', name: 'Chinese' },
  2: { id: 2, code: 'en', name: 'English' },
  3: { id: 3, code: 'ja', name: 'Japanese' },
};

function parseArgs(argv) {
  const o = { paths: [], fixtures: [], clicks: [], port: 5099, mode: 'light', lang: '1' };
  const many = { path: 'paths', fixtures: 'fixtures', click: 'clicks' };
  const flags = new Set(['task', 'full', 'fonts', 'json', 'strict']);
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const k = a.slice(2);
    if (flags.has(k)) {
      o[k] = true;
      continue;
    }
    const v = argv[++i];
    if (many[k]) o[many[k]].push(v);
    else o[k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = v;
  }
  if (!o.paths.length) o.paths.push('/session');
  if (!o.fixtures.length) o.fixtures.push(path.join(__dirname, 'fixtures', 'default.json'));
  return o;
}

function fakeToken() {
  const b64 = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64url');
  const exp = Math.floor(Date.now() / 1000) + 365 * 24 * 3600;
  return `${b64({ alg: 'none', typ: 'JWT' })}.${b64({ sub: 'test-user-id-123', exp })}.preview`;
}

function loadFixtures(files) {
  const map = {};
  for (const f of files) {
    if (!fs.existsSync(f)) {
      console.error(`[preview] fixture file not found: ${f}`);
      continue;
    }
    Object.assign(map, JSON.parse(fs.readFileSync(f, 'utf8')));
  }
  delete map._comment;
  return map;
}

function lookup(map, method, url) {
  const u = new URL(url);
  const withQuery = u.pathname + u.search;
  const keys = [
    `${method} ${withQuery}`,
    withQuery,
    `${method} ${u.pathname}`,
    u.pathname,
  ];
  for (const k of keys) if (k in map) return map[k];
  let best = null;
  for (const k of Object.keys(map)) {
    if (!k.endsWith('*')) continue;
    const [m, p] = k.includes(' ') ? k.split(' ') : [null, k];
    if (m && m !== method) continue;
    const prefix = p.slice(0, -1);
    if (u.pathname.startsWith(prefix) && (!best || prefix.length > best[0].length)) {
      best = [prefix, map[k]];
    }
  }
  return best ? best[1] : undefined;
}

async function measure(page) {
  return page.evaluate(() => {
    const se = document.scrollingElement || document.documentElement;
    const W = window.innerWidth;
    const H = window.innerHeight;
    const visible = (el) => {
      if (!el) return false;
      const c = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      return c.display !== 'none' && c.visibility !== 'hidden' && b.width > 0 && b.height > 0;
    };
    const desc = (el) =>
      el.tagName.toLowerCase() +
      (el.id ? '#' + el.id : '') +
      (el.className && typeof el.className === 'string'
        ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.')
        : '');
    const scrollers = [];
    document.querySelectorAll('.ld-stage, main#main-content').forEach((el) => {
      if (!visible(el)) return;
      scrollers.push({
        el: desc(el),
        clientHeight: el.clientHeight,
        scrollHeight: el.scrollHeight,
        overflowPx: Math.max(0, el.scrollHeight - el.clientHeight),
        overflowY: getComputedStyle(el).overflowY,
      });
    });
    const docks = [];
    document.querySelectorAll('.ld-dock').forEach((el) => {
      if (!visible(el)) return;
      const b = el.getBoundingClientRect();
      const buttons = [...el.querySelectorAll('button, a.btn, a.ld-btn')].filter(visible);
      docks.push({
        el: desc(el),
        top: Math.round(b.top),
        bottom: Math.round(b.bottom),
        inViewport: b.top >= -0.5 && b.bottom <= H + 0.5,
        buttonsOffscreen: buttons
          .filter((x) => x.getBoundingClientRect().bottom > H + 0.5)
          .map(desc),
      });
    });
    const wide = [];
    document.querySelectorAll('body *').forEach((el) => {
      if (wide.length > 8 || !visible(el)) return;
      const b = el.getBoundingClientRect();
      if (b.right > W + 1 && getComputedStyle(el).position !== 'fixed') wide.push(desc(el));
    });
    const smallTargets = [];
    document
      .querySelectorAll('button, a[href], [role="button"], input, select, textarea')
      .forEach((el) => {
        if (smallTargets.length > 12 || !visible(el)) return;
        const b = el.getBoundingClientRect();
        if (b.bottom < 0 || b.top > H) return;
        if (b.height < 44 && b.width < 44) smallTargets.push(`${desc(el)} ${Math.round(b.width)}x${Math.round(b.height)}`);
      });
    const body = document.body;
    return {
      url: location.pathname + location.search,
      viewport: `${W}x${H}`,
      theme: document.documentElement.getAttribute('data-theme') || 'default',
      mode: document.documentElement.getAttribute('data-mode') || 'system',
      scheme: document.documentElement.getAttribute('data-bs-theme'),
      shell: ['ld-task', 'ld-has-tabs', 'ld-bare'].filter((c) => body.classList.contains(c)),
      documentScrolls: se.scrollHeight > se.clientHeight + 1,
      documentScrollHeight: se.scrollHeight,
      documentOverflowPx: Math.max(0, se.scrollHeight - se.clientHeight),
      horizontalOverflow: se.scrollWidth > se.clientWidth + 1,
      wideElements: wide,
      stages: scrollers,
      docks,
      tabbarVisible: visible(document.getElementById('ldTabbar')),
      taskbarVisible: visible(document.getElementById('ldTaskbar')),
      smallTouchTargetsInView: smallTargets,
    };
  });
}

async function run() {
  const o = parseArgs(process.argv);
  const base = o.base || `http://127.0.0.1:${o.port}`;
  const [w, h] = SIZES[o.size] || (o.size ? o.size.split('x').map(Number) : SIZES.iphone15);
  const fixtures = loadFixtures(o.fixtures);
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: w, height: h },
    deviceScaleFactor: 2,
    isMobile: w < 768,
    hasTouch: w < 768,
    colorScheme: o.mode === 'dark' ? 'dark' : 'light',
    locale: o.ui ? { zh: 'zh-CN', ja: 'ja-JP', es: 'es-ES' }[o.ui] || 'en-US' : 'en-US',
  });
  const lang = LANGS[o.lang] || null;
  const storage = {
    jwt_token: fakeToken(),
    user_data: JSON.stringify({ id: 'test-user-id-123', email: 'preview@example.com' }),
    nativeLanguagePromptDone: '1',
  };
  if (lang) storage.selectedLanguageId = String(lang.id);
  if (o.theme) storage['linguadojo-theme'] = o.theme;
  if (o.mode && o.mode !== 'system') storage['linguadojo-theme-mode'] = o.mode;
  if (o.ui) storage['linguadojo-ui-lang'] = o.ui;
  await context.addInitScript((items) => {
    try {
      if (sessionStorage.getItem('__preview_seeded')) return;
      sessionStorage.setItem('__preview_seeded', '1');
      for (const [k, v] of Object.entries(items)) localStorage.setItem(k, v);
    } catch {
      /* storage unavailable */
    }
  }, storage);

  const unmocked = [];
  const external = [];
  await context.route('**/*', (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const local = url.origin === new URL(base).origin;
    if (!local) {
      if (o.fonts && /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) return route.continue();
      external.push(url.hostname);
      return route.abort();
    }
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const hit = lookup(fixtures, req.method(), req.url());
    if (hit === undefined) {
      unmocked.push(`${req.method()} ${url.pathname}${url.search}`);
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' });
    }
    const isEnvelope = hit && typeof hit === 'object' && 'body' in hit && Object.keys(hit).every((k) => ['status', 'body', 'delay'].includes(k));
    const status = isEnvelope ? hit.status || 200 : 200;
    const body = isEnvelope ? hit.body : hit;
    const send = () =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    return isEnvelope && hit.delay ? new Promise((r) => setTimeout(r, hit.delay)).then(send) : send();
  });

  const reports = [];
  let failed = false;
  for (let n = 0; n < o.paths.length; n++) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(String(e.message || e).split('\n')[0]));
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push('console: ' + m.text().split('\n')[0]);
    });
    unmocked.length = 0;
    await page.goto(base + o.paths[n], { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('load').catch(() => {});
    if (o.wait) await page.waitForSelector(o.wait, { timeout: 8000 }).catch(() => errors.push(`wait: ${o.wait} not found`));
    await page.waitForTimeout(Number(o.waitMs || 400));
    if (o.task) await page.evaluate(() => window.LinguaShell && window.LinguaShell.setTaskMode(true));
    for (const sel of o.clicks) {
      await page.click(sel, { timeout: 5000 }).catch((e) => errors.push(`click ${sel}: ${e.message.split('\n')[0]}`));
      await page.waitForTimeout(250);
    }
    if (o.eval) await page.evaluate(o.eval).catch((e) => errors.push('eval: ' + e.message.split('\n')[0]));
    await page.waitForTimeout(150);
    const report = await measure(page);
    report.unmocked = [...new Set(unmocked)];
    report.blockedHosts = [...new Set(external)];
    report.errors = errors;
    if (o.shot) {
      const file = o.paths.length > 1 ? o.shot.replace(/(\.png)?$/, `-${n + 1}.png`) : o.shot;
      await page.screenshot({ path: file, fullPage: !!o.full });
      report.screenshot = file;
    }
    reports.push(report);
    if (report.documentScrolls || report.horizontalOverflow || report.docks.some((d) => !d.inViewport || d.buttonsOffscreen.length)) {
      failed = true;
    }
    await page.close();
  }
  await browser.close();

  if (o.json) {
    console.log(JSON.stringify(reports, null, 2));
  } else {
    for (const r of reports) {
      console.log(`\n== ${r.url} @ ${r.viewport}  theme=${r.theme} mode=${r.mode} scheme=${r.scheme} shell=${r.shell.join(',')}`);
      console.log(`document scrolls: ${r.documentScrolls ? `YES (+${r.documentOverflowPx}px)` : 'no'}   horizontal overflow: ${r.horizontalOverflow ? 'YES ' + r.wideElements.join(', ') : 'no'}`);
      for (const s of r.stages) console.log(`stage ${s.el}: overflow ${s.overflowPx}px (overflow-y ${s.overflowY})`);
      for (const d of r.docks) console.log(`dock ${d.el}: ${d.inViewport ? 'in viewport' : 'OFF-SCREEN'} (${d.top}-${d.bottom})${d.buttonsOffscreen.length ? ' buttons off-screen: ' + d.buttonsOffscreen.join(', ') : ''}`);
      console.log(`tab bar: ${r.tabbarVisible ? 'visible' : 'hidden'}   task header: ${r.taskbarVisible ? 'visible' : 'hidden'}`);
      if (r.smallTouchTargetsInView.length) console.log(`touch targets < 44px: ${r.smallTouchTargetsInView.join('; ')}`);
      if (r.unmocked.length) console.log(`unmocked API calls (answered {"success":true}): ${r.unmocked.join(', ')}`);
      if (r.errors.length) console.log(`page errors: ${r.errors.join(' | ')}`);
      if (r.screenshot) console.log(`screenshot: ${r.screenshot}`);
    }
  }
  if (o.strict && failed) process.exit(1);
}

run().catch((e) => {
  console.error(e);
  process.exit(2);
});
