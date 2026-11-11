// node filmstrip.js URLPATH OUTDIR -- one cold throttled load per server, frames + shifts
const NOPROXY_ENV = Object.fromEntries(Object.entries(process.env).filter(([k]) => !/^(https?|all|no)_proxy$/i.test(k)));
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const { execFileSync } = require('child_process');
const S = __dirname, URLP = process.argv[2], OUT = process.argv[3]; fs.mkdirSync(OUT, { recursive: true });
const HOSTS = ['cdn.jsdelivr.net', 'cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com'];
const NET = { offline: false, latency: 150, downloadThroughput: 1.6 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 };
(async () => {
  const b = await chromium.launch({ env: NOPROXY_ENV, args: ['--no-proxy-server', '--proxy-server=direct://', '--proxy-bypass-list=*', '--ignore-certificate-errors', '--host-resolver-rules=' + HOSTS.map((h) => `MAP ${h} 127.0.0.1`).join(', ')] });
  for (const [label, base] of [['before', 'http://127.0.0.1:5055'], ['after', 'http://127.0.0.1:5056']]) {
    const token = execFileSync(path.join(S, 'venv/bin/python'), [path.join(S, 'mint.py')]).toString().trim();
    const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1280, height: 720 } });
    await ctx.addInitScript((t) => {
      localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3'); window.__shifts = [];
      new PerformanceObserver((l) => { for (const e of l.getEntries()) if (e.value > 0.003) window.__shifts.push({ t: Math.round(e.startTime), v: +e.value.toFixed(3),
        src: (e.sources || []).slice(0, 3).map((s) => { const n = s.node; const id = !n ? '?' : n.id ? '#' + n.id : (typeof n.className === 'string' && n.className ? '.' + n.className.split(' ')[0] : n.nodeName);
          return `${id} y${Math.round(s.previousRect.y)}->${Math.round(s.currentRect.y)} h${Math.round(s.previousRect.height)}->${Math.round(s.currentRect.height)}`; }) }); })
        .observe({ type: 'layout-shift', buffered: true });
    }, token);
    const p = await ctx.newPage(); const cdp = await ctx.newCDPSession(p); await cdp.send('Network.enable'); await cdp.send('Network.emulateNetworkConditions', NET);
    const t0 = Date.now(); const ev = [];
    p.on('requestfinished', (r) => { const u = r.url(); if (/woff2|googleapis|\/api\/|i18n\/|vendor\/.*css|styles\.css/.test(u)) ev.push(`${Date.now() - t0}ms ${u.replace(base, '').replace(/\?.*$/, '').replace(/^https:\/\/([^/]+)/, '$1').slice(0, 60)}`); });
    const nav = p.goto(base + URLP, { waitUntil: 'networkidle', timeout: 120000 });
    let i = 0; const frames = [];
    const timer = setInterval(async () => { const t = Date.now() - t0; try { await p.screenshot({ path: path.join(OUT, `${label}_${String(i++).padStart(2, '0')}_${t}ms.png`) }); frames.push(t); } catch (e) {} }, 400);
    await nav; await p.waitForTimeout(800); clearInterval(timer);
    const r = await p.evaluate(() => ({ fcp: Math.round((performance.getEntriesByType('paint').find((x) => x.name === 'first-contentful-paint') || {}).startTime || 0), shifts: window.__shifts }));
    console.log(`\n== ${label} FCP ${r.fcp} CLS(>0.003 entries) ${r.shifts.reduce((s, x) => s + x.v, 0).toFixed(3)}`);
    r.shifts.forEach((s) => console.log('  shift', s.t, s.v, s.src.join(' | ')));
    console.log('  ' + ev.join('\n  '));
    await ctx.close();
  }
  await b.close();
})();
