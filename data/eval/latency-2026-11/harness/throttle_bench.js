// Mobile-throttled page loads (Lighthouse "Slow 4G": 150 ms RTT, 1.6 Mbps down,
// 750 Kbps up) via CDP, cold (fresh context) and warm (same context), no request
// interception so the HTTP cache works. CDN hosts mapped to a closed port in both runs.
// node throttle_bench.js OUT.json N BASE
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const S = __dirname, OUT = process.argv[2], N = +process.argv[3] || 10, BASE = process.argv[4];
const TOKEN = fs.readFileSync(path.join(S, 'token.txt'), 'utf8').trim();
const SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156';
const PAGES = ['/session', '/tests', `/test/${SLUG}/preview`, `/test/${SLUG}`, `/test/${SLUG}/prestudy`, '/flashcards', '/study-plan'];
const NET = { offline: false, latency: 150, downloadThroughput: 1.6 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 };
async function newPage(browser) {
  const ctx = await browser.newContext();
  await ctx.addInitScript((t) => { localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3'); }, TOKEN);
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable'); await cdp.send('Network.emulateNetworkConditions', NET);
  return { ctx, page };
}
async function measure(page, url) {
  await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 180000 });
  return page.evaluate((base) => {
    const nav = performance.getEntriesByType('navigation')[0];
    const all = performance.getEntriesByType('resource').filter((e) => e.name.startsWith(base));
    const api = all.filter((e) => e.name.includes('/api/'));
    return { dataReady: api.length ? Math.max(...api.map((e) => e.responseEnd)) : nav.loadEventEnd,
      firstApiStart: api.length ? Math.min(...api.map((e) => e.startTime)) : null,
      dcl: nav.domContentLoadedEventEnd, load: nav.loadEventEnd,
      bytes: all.reduce((s, e) => s + e.transferSize, 0) + nav.transferSize, requests: all.length + 1 };
  }, BASE);
}
(async () => {
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP cdn.jsdelivr.net 127.0.0.1:9, MAP cdnjs.cloudflare.com 127.0.0.1:9, MAP fonts.googleapis.com 127.0.0.1:9, MAP fonts.gstatic.com 127.0.0.1:9'] });
  const res = {};
  for (const url of PAGES) {
    res[url] = { cold: [], warm: [] };
    for (let i = 0; i < N; i++) { const { ctx, page } = await newPage(browser); res[url].cold.push(await measure(page, url)); await ctx.close(); }
    const { ctx, page } = await newPage(browser); await measure(page, url);
    for (let i = 0; i < N; i++) res[url].warm.push(await measure(page, url));
    await ctx.close();
    const med = (a, k) => a.map((x) => x[k]).sort((x, y) => x - y)[Math.floor(a.length / 2)];
    console.log(url.replace(SLUG, '<slug>'), '| cold dataReady', Math.round(med(res[url].cold, 'dataReady')), 'firstApi', Math.round(med(res[url].cold, 'firstApiStart')),
      'KB', (med(res[url].cold, 'bytes') / 1024).toFixed(0), '| warm dataReady', Math.round(med(res[url].warm, 'dataReady')), 'KB', (med(res[url].warm, 'bytes') / 1024).toFixed(0));
  }
  fs.writeFileSync(OUT, JSON.stringify(res)); await browser.close();
})();
