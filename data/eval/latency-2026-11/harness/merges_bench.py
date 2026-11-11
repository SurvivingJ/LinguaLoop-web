"""HTTP latency harness: real Flask app (create_app) against the live DB.
Auth is stubbed locally (no token minted). Every outbound HTTP call is timed.
Usage: bench.py USER LANG N OUT.json [SLUG]"""
import os, sys, time, json, logging
APP = os.environ.get('APP_DIR', '/home/user/LinguaLoop-web'); sys.path.insert(0, APP); os.chdir(APP)
import httpx
from unittest.mock import MagicMock
for m in ['azure','azure.cognitiveservices','azure.cognitiveservices.speech','spacy','pyopenjtalk','fugashi','MeCab','unidic_lite','ipadic']:
    sys.modules.setdefault(m, MagicMock())
CALLS = []
_orig = httpx.Client.send
def send(self, req, *a, **k):
    t = time.perf_counter()
    try: return _orig(self, req, *a, **k)
    finally:
        p = req.url.path
        if '/rpc/' in p: p = 'rpc:' + p.split('/rpc/')[1]
        elif '/rest/v1/' in p: p = req.method + ' ' + p.split('/rest/v1/')[1]
        CALLS.append((p, (time.perf_counter()-t)*1000))
httpx.Client.send = send
logging.disable(logging.WARNING)
import middleware.auth as ma
USER, LANG, N, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
SLUG = sys.argv[5] if len(sys.argv) > 5 else None
ma._authenticate = lambda tok: ({'sub': USER, 'email': 'bench@local', 'role': 'authenticated', 'aud': 'authenticated', 'user': None}, None)
from app import create_app
app = create_app(); c = app.test_client()
H = {'Authorization': 'Bearer x'}
EPS = [f'/api/study-session?language_id={LANG}', f'/api/practice/session?language_id={LANG}&minutes=10', f'/api/study-plan?language_id={LANG}']
if SLUG: EPS += [f'/api/tests/{SLUG}', f'/api/tests/test/{SLUG}']
res = {}
for ep in EPS:
    c.get(ep, headers=H)  # warm-up, discarded
    samples = []
    for i in range(N):
        CALLS.clear(); t = time.perf_counter(); r = c.get(ep, headers=H); wall = (time.perf_counter()-t)*1000
        samples.append(dict(wall=wall, db=sum(d for _, d in CALLS), calls=len(CALLS), status=r.status_code,
                            paths=[p for p, _ in CALLS], bytes=len(r.data)))
    res[ep] = samples
    w = sorted(s['wall'] for s in samples)
    print(f"{ep}: status={samples[-1]['status']} calls={samples[-1]['calls']} median={w[len(w)//2]:.0f}ms bytes={samples[-1]['bytes']}", flush=True)
json.dump(res, open(OUT, 'w'))
