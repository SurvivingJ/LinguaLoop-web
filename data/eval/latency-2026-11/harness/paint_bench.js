// First-paint benchmark. Real third-party origins are replaced by the local mock
// CDN (mockcdn/server.js on 127.0.0.1:443, 450 ms connection setup), mapped by
// host-resolver rules -- no request interception, so the HTTP cache works.
// Phone network via CDP (Lighthouse "Slow 4G"). node paint_bench.js OUT.json N BASE
const NOPROXY_ENV = Object.fromEntries(Object.entries(process.env).filter(([k]) => !/^(https?|all|no)_proxy$/i.test(k)));
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const S = __dirname, OUT = process.argv[2], N = +process.argv[3] || 10, BASE = process.argv[4];
const { execFileSync } = require('child_process');
let TOKEN = '';
const mint = () => { TOKEN = execFileSync(path.join(S, 'venv/bin/python'), [path.join(S, 'mint.py')]).toString().trim(); };
const SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156';
const PAGES = ['/login', '/session', '/tests', `/test/${SLUG}/preview`, `/test/${SLUG}`, `/test/${SLUG}/prestudy`, '/flashcards', '/study-plan'];
const NET = { offline: false, latency: 150, downloadThroughput: 1.6 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 };
const HOSTS = ['cdn.jsdelivr.net', 'cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com'];
const ARGS = ['--no-proxy-server', '--proxy-server=direct://', '--proxy-bypass-list=*', '--ignore-certificate-errors',
  '--host-resolver-rules=' + HOSTS.map((h) => `MAP ${h} 127.0.0.1`).join(', ')];
const INIT = (t) => {
  localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3');
  window.__lcp = 0; window.__cls = 0;
  new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
};
async function newPage(browser) {
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
  await ctx.addInitScript(INIT, TOKEN);
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable'); await cdp.send('Network.emulateNetworkConditions', NET);
  return { ctx, page };
}
async function measure(page, url) {
  await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 180000 });
  await page.waitForTimeout(300);
  return page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const res = performance.getEntriesByType('resource');
    const paint = Object.fromEntries(performance.getEntriesByType('paint').map((p) => [p.name, p.startTime]));
    const api = res.filter((e) => e.name.includes('/api/'));
    const third = res.filter((e) => !e.name.startsWith(location.origin));
    const blocking = res.filter((e) => e.renderBlockingStatus === 'blocking');
    return { fcp: paint['first-contentful-paint'] || null, lcp: window.__lcp, cls: window.__cls,
      dcl: nav.domContentLoadedEventEnd, load: nav.loadEventEnd,
      dataReady: api.length ? Math.max(...api.map((e) => e.responseEnd)) : nav.loadEventEnd,
      requests: res.length + 1, thirdParty: third.length,
      renderBlocking: blocking.map((e) => e.name.replace(location.origin, '').split('?')[0]),
      bytes: res.reduce((s, e) => s + (e.transferSize || 0), nav.transferSize || 0),
      landed: location.pathname, apiCount: api.length };
  });
}
(async () => {
  const browser = await chromium.launch({ env: NOPROXY_ENV, args: ARGS });
  const res = {};
  for (const url of PAGES) {
    mint();  // fresh session per page: a run outlasts one token
    res[url] = { cold: [], warm: [] };
    for (let i = 0; i < N; i++) { const { ctx, page } = await newPage(browser); res[url].cold.push(await measure(page, url)); await ctx.close(); }
    const { ctx, page } = await newPage(browser); await measure(page, url);
    for (let i = 0; i < N; i++) res[url].warm.push(await measure(page, url));
    await ctx.close();
    const med = (a, k) => a.map((x) => x[k]).sort((x, y) => x - y)[Math.floor(a.length / 2)];
    const c = res[url].cold, w = res[url].warm;
    console.log(url.replace(SLUG, '<slug>'), '| cold FCP', Math.round(med(c, 'fcp')), 'LCP', Math.round(med(c, 'lcp')), 'CLS', med(c, 'cls').toFixed(3),
      'KB', Math.round(med(c, 'bytes') / 1024), 'landed', c[0].landed, 'api', c[0].apiCount, 'blocking', c[0].renderBlocking.length, 'thirdParty', c[0].thirdParty,
      '| warm FCP', Math.round(med(w, 'fcp')), 'LCP', Math.round(med(w, 'lcp')));
  }
  fs.writeFileSync(OUT, JSON.stringify(res)); await browser.close();
})();
