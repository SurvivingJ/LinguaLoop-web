const NOPROXY_ENV = Object.fromEntries(Object.entries(process.env).filter(([k]) => !/^(https?|all|no)_proxy$/i.test(k)));
const { chromium } = require('playwright'); const path = require('path'); const { execFileSync } = require('child_process');
const S = __dirname; const HOSTS = ['cdn.jsdelivr.net', 'cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com'];
(async () => {
  const token = execFileSync(path.join(S, 'venv/bin/python'), [path.join(S, 'mint.py')]).toString().trim();
  const b = await chromium.launch({ env: NOPROXY_ENV, args: ['--no-proxy-server', '--proxy-server=direct://', '--proxy-bypass-list=*', '--ignore-certificate-errors', '--host-resolver-rules=' + HOSTS.map((h) => `MAP ${h} 127.0.0.1`).join(', ')] });
  for (const base of ['http://127.0.0.1:5055', 'http://127.0.0.1:5056']) {
    const ctx = await b.newContext({ ignoreHTTPSErrors: true }); await ctx.addInitScript((t) => { localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId', '3'); }, token);
    const p = await ctx.newPage(); await p.goto(base + process.argv[2], { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
    const r = await p.evaluate(() => performance.getEntriesByType('resource').map((e) => [Math.round(e.transferSize / 1024), e.name.replace(location.origin, '').split('?')[0].slice(0, 80)]).filter((x) => x[0] > 3).sort((x, y) => y[0] - x[0]));
    console.log('\n==', base.endsWith('5055') ? 'before' : 'after', 'total KB', r.reduce((s, x) => s + x[0], 0)); r.forEach((x) => console.log('  ', x[0], x[1]));
    await ctx.close();
  }
  await b.close();
})();
