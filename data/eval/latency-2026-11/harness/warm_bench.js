// Warm-cache loads WITHOUT request interception (interception disables Chromium's
// HTTP cache). CDN hosts are mapped to a closed port so they fail instantly,
// identically before and after. node warm_bench.js OUT.json N BASE
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const S = __dirname, OUT = process.argv[2], N = +process.argv[3] || 10, BASE = process.argv[4];
const TOKEN = fs.readFileSync(path.join(S, 'token.txt'), 'utf8').trim();
const SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156';
const PAGES = ['/session', '/tests', `/test/${SLUG}/preview`, `/test/${SLUG}`, `/test/${SLUG}/prestudy`, '/flashcards', '/study-plan'];
(async () => {
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP cdn.jsdelivr.net 127.0.0.1:9, MAP cdnjs.cloudflare.com 127.0.0.1:9, MAP fonts.googleapis.com 127.0.0.1:9, MAP fonts.gstatic.com 127.0.0.1:9'] });
  const res = {};
  for (const url of PAGES) {
    const ctx = await browser.newContext();
    await ctx.addInitScript((t) => { localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3'); }, TOKEN);
    const page = await ctx.newPage();
    let hits = 0; page.on('response', (r) => { if (r.url().startsWith(BASE)) hits++; });
    await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 120000 });   // prime
    res[url] = [];
    for (let i = 0; i < N; i++) {
      hits = 0;
      await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 120000 });
      const m = await page.evaluate((base) => {
        const nav = performance.getEntriesByType('navigation')[0];
        const all = performance.getEntriesByType('resource').filter((e) => e.name.startsWith(base));
        const api = all.filter((e) => e.name.includes('/api/'));
        const stat = all.filter((e) => e.name.includes('/static/'));
        return { dataReady: api.length ? Math.max(...api.map((e) => e.responseEnd)) : nav.loadEventEnd,
          load: nav.loadEventEnd, staticCount: stat.length,
          staticFromCache: stat.filter((e) => e.transferSize === 0).length,
          staticBytes: stat.reduce((s, e) => s + e.transferSize, 0),
          totalBytes: all.reduce((s, e) => s + e.transferSize, 0) + nav.transferSize };
      }, BASE);
      res[url].push({ ...m, serverHits: hits });
    }
    const r = res[url], med = (k) => r.map((x) => x[k]).sort((a, b) => a - b)[Math.floor(r.length / 2)];
    console.log(url.replace(SLUG, '<slug>'), 'dataReady', Math.round(med('dataReady')), 'static', med('staticCount'), 'fromCache', med('staticFromCache'),
      'staticKB', (med('staticBytes') / 1024).toFixed(1), 'serverHits', med('serverHits'));
    await ctx.close();
  }
  fs.writeFileSync(OUT, JSON.stringify(res)); await browser.close();
})();
