// node shots.js BASE OUTDIR — full-page screenshots of learner pages, desktop + phone
const { chromium, devices } = require('playwright'); const fs=require('fs'), path=require('path');
const S = __dirname, BASE = process.argv[2], OUT = process.argv[3]; fs.mkdirSync(OUT, { recursive: true });
const TOKEN = fs.readFileSync(path.join(S,'token.txt'),'utf8').trim();
const SLUG = 'ja-d1-a-roman-child-s-wooden-toy-hor-20260823223156';
const PAGES = { session: '/session', practice: '/session?mode=practice', tests: '/tests', preview: `/test/${SLUG}/preview`,
  test: `/test/${SLUG}?type=listening`, prestudy: `/test/${SLUG}/prestudy`, flashcards: '/flashcards', studyplan: '/study-plan',
  profile: '/profile', wordlist: '/word-list', calibration: '/calibration' };
const CDN = { 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css': 'bootstrap/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js': 'bootstrap/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css': '@fortawesome/fontawesome-free/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.min.css': 'bootstrap-icons/font/bootstrap-icons.min.css' };
async function setup(ctx) {
  await ctx.route(/cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/, (r) => {
    const u = r.request().url(); if (CDN[u]) return r.fulfill({ path: path.join(S,'cdn/node_modules',CDN[u]), headers:{'access-control-allow-origin':'*'} });
    let m = u.match(/font-awesome.*webfonts\/([^?]+)/); if (m) return r.fulfill({ path: path.join(S,'cdn/node_modules/@fortawesome/fontawesome-free/webfonts',m[1]), headers:{'access-control-allow-origin':'*'} });
    m = u.match(/bootstrap-icons.*fonts\/([^?]+)/); if (m) return r.fulfill({ path: path.join(S,'cdn/node_modules/bootstrap-icons/font/fonts',m[1]), headers:{'access-control-allow-origin':'*'} });
    return r.fulfill({ status: 200, contentType: 'text/css', body: '' }); });
  await ctx.addInitScript((t) => { localStorage.setItem('jwt_token', t); localStorage.setItem('selectedLanguageId','3'); }, TOKEN);
}
(async () => {
  const b = await chromium.launch(); const report = {};
  for (const [dev, opts] of [['desktop', { viewport: { width: 1280, height: 900 } }], ['phone', devices['iPhone 13']]]) {
    const ctx = await b.newContext(opts); await setup(ctx);
    for (const [name, url] of Object.entries(PAGES)) {
      const p = await ctx.newPage(); const errs = [];
      p.on('pageerror', e => errs.push('pageerror: ' + e.message));
      p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
      p.on('response', r => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url().replace(BASE, '')); });
      await p.goto(BASE + url, { waitUntil: 'networkidle', timeout: 120000 }).catch(e => errs.push('goto: ' + e.message));
      await p.waitForTimeout(800);
      await p.screenshot({ path: path.join(OUT, `${dev}_${name}.png`), fullPage: true });
      report[`${dev}_${name}`] = { landed: p.url().replace(BASE, ''), errs };
      await p.close();
    }
    await ctx.close();
  }
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 1)); await b.close();
  for (const [k, v] of Object.entries(report)) console.log(k, v.landed, v.errs.length ? JSON.stringify(v.errs).slice(0, 300) : '');
})();
