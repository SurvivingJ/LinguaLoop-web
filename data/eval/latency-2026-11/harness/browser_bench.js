// Usage: node browser_bench.js OUT.json N [baseUrl]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const S = __dirname, OUT = process.argv[2], N = +process.argv[3] || 8;
const BASE = process.argv[4] || 'http://127.0.0.1:5055';
const TOKEN = fs.readFileSync(path.join(S, 'token.txt'), 'utf8').trim();
const SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156';
const CDN = {
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css': ['bootstrap/dist/css/bootstrap.min.css', 'text/css'],
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js': ['bootstrap/dist/js/bootstrap.bundle.min.js', 'application/javascript'],
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css': ['@fortawesome/fontawesome-free/css/all.min.css', 'text/css'],
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.min.css': ['bootstrap-icons/font/bootstrap-icons.min.css', 'text/css'],
};
const PAGES = ['/session', '/tests', `/test/${SLUG}/preview`, `/test/${SLUG}`, `/test/${SLUG}/prestudy`, '/flashcards', '/study-plan'];
async function setup(ctx) {
  await ctx.route(/cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/, async (route) => {
    const u = route.request().url();
    if (CDN[u]) return route.fulfill({ path: path.join(S, 'cdn/node_modules', CDN[u][0]), contentType: CDN[u][1],
      headers: { 'access-control-allow-origin': '*', 'cache-control': 'public, max-age=31536000' } });
    if (/webfonts|fonts\//.test(u)) {           // FA / bootstrap-icons font files
      const m = u.match(/(webfonts|fonts)\/([^?]+)/);
      const p = u.includes('font-awesome') ? `@fortawesome/fontawesome-free/webfonts/${m[2]}` : `bootstrap-icons/font/fonts/${m[2]}`;
      if (fs.existsSync(path.join(S, 'cdn/node_modules', p))) return route.fulfill({ path: path.join(S, 'cdn/node_modules', p), headers: { 'access-control-allow-origin': '*' } });
    }
    return route.fulfill({ status: 200, contentType: 'text/css', body: '' }); // google fonts: stub (same before/after)
  });
  await ctx.addInitScript(([t]) => { localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3'); }, [TOKEN]);
}
async function measure(page, url) {
  const reqs = []; let bytes = 0;
  const onResp = async (r) => { try { const b = await r.body(); bytes += b.length; } catch (e) {} };
  page.on('requestfinished', (r) => reqs.push(r)); page.on('response', onResp);
  await page.goto(BASE + url, { waitUntil: 'load', timeout: 120000 });
  await page.waitForLoadState('networkidle', { timeout: 120000 }).catch(() => {});
  const m = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const api = performance.getEntriesByType('resource').filter((e) => e.name.includes('/api/'));
    return { dcl: nav.domContentLoadedEventEnd, load: nav.loadEventEnd,
      dataReady: api.length ? Math.max(...api.map((e) => e.responseEnd)) : nav.loadEventEnd,
      firstApiStart: api.length ? Math.min(...api.map((e) => e.startTime)) : null,
      apiCalls: api.map((e) => e.name.replace(location.origin, '').split('?')[0]),
      transfer: performance.getEntriesByType('resource').reduce((s, e) => s + (e.transferSize || 0), nav.transferSize || 0),
      path: location.pathname };
  });
  page.off('requestfinished', () => {}); page.removeListener('response', onResp);
  return { ...m, requests: reqs.length + 1, bodyBytes: bytes };
}
(async () => {
  const browser = await chromium.launch();
  const res = {};
  for (const url of PAGES) {
    res[url] = { cold: [], warm: [] };
    for (let i = 0; i < N; i++) {             // cold: fresh context each time
      const ctx = await browser.newContext(); await setup(ctx); const p = await ctx.newPage();
      res[url].cold.push(await measure(p, url)); await ctx.close();
    }
    const ctx = await browser.newContext(); await setup(ctx); const p = await ctx.newPage();
    await measure(p, url);                    // prime cache
    for (let i = 0; i < N; i++) { res[url].warm.push(await measure(p, url)); }
    await ctx.close();
    const c = res[url].cold, w = res[url].warm, med = (a) => a.slice().sort((x, y) => x - y)[Math.floor(a.length / 2)];
    console.log(url, 'landed', c[0].path, '| cold dataReady med', Math.round(med(c.map((x) => x.dataReady))),
      '| warm dataReady med', Math.round(med(w.map((x) => x.dataReady))), '| reqs', c[0].requests, '| api', c[0].apiCalls.length, '| transfer', c[0].transfer);
  }
  fs.writeFileSync(OUT, JSON.stringify(res)); await browser.close();
})();
