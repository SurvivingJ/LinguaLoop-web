// Local stand-in for the third-party origins (jsdelivr, cdnjs, Google Fonts).
// HTTPS (self-signed), HTTP/1.1 like separate CDN hosts, with an artificial
// connection-setup delay per new TCP connection (DNS + TCP + TLS on a phone
// network) because Chrome's DevTools throttling only delays requests, not
// handshakes. Files: npm packages for jsdelivr/cdnjs; Google Fonts CSS and
// woff2 fetched once through the sandbox proxy (curl) and cached on disk.
const https = require('https'), fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const D = __dirname, NM = path.join(D, '..', 'cdn', 'node_modules');
const CONNECT_DELAY = +(process.env.CONNECT_DELAY_MS || 450);
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';
const MAP = {
  'cdn.jsdelivr.net/npm/bootstrap@5.3.2/': 'bootstrap/',
  'cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/': 'bootstrap-icons/',
  'cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/': '@fortawesome/fontawesome-free/',
};
const TYPES = { '.css': 'text/css', '.js': 'application/javascript', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf' };
function fetchCached(url, ext) {
  const f = path.join(D, 'cache', Buffer.from(url).toString('base64url').slice(0, 200) + ext);
  if (!fs.existsSync(f)) execFileSync('curl', ['-s', '-f', '-A', UA, '-o', f, url]);
  return f;
}
const server = https.createServer({ key: fs.readFileSync(path.join(D, 'key.pem')), cert: fs.readFileSync(path.join(D, 'cert.pem')) }, (req, res) => {
  // First request on a new connection pays the connection-setup cost.
  if (!req.socket.__seen) { req.socket.__seen = true; return setTimeout(() => handle(req, res), CONNECT_DELAY); }
  handle(req, res);
});
function handle(req, res) {
  const host = req.headers.host.split(':')[0]; const full = host + req.url;
  try {
    let file, type;
    for (const [pre, dir] of Object.entries(MAP)) if (full.startsWith(pre)) { file = path.join(NM, dir, full.slice(pre.length).split('?')[0]); type = TYPES[path.extname(file)]; }
    if (!file && host === 'fonts.googleapis.com') { file = fetchCached('https://' + full, '.css'); type = 'text/css; charset=utf-8'; }
    if (!file && host === 'fonts.gstatic.com') { file = fetchCached('https://' + full, '.woff2'); type = 'font/woff2'; }
    if (!file || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
    const body = fs.readFileSync(file);
    const zlib = require('zlib'); const gz = /\b(br|gzip)\b/.test(req.headers['accept-encoding'] || '') && /css|javascript/.test(type);
    res.writeHead(200, { 'content-type': type, 'access-control-allow-origin': '*', 'cache-control': 'public, max-age=31536000',
      'timing-allow-origin': '*', ...(gz ? { 'content-encoding': 'gzip' } : {}) });
    res.end(gz ? zlib.gzipSync(body) : body);
  } catch (e) { res.writeHead(502); res.end(String(e)); }
}
server.listen(443, '127.0.0.1', () => console.log('mock cdn on 443, connect delay', CONNECT_DELAY));
