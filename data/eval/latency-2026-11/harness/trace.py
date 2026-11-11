"""One request per endpoint; print each DB call with the app frames that issued it."""
import os, sys, time, traceback, logging
sys.path.insert(0, '/home/user/LinguaLoop-web'); os.chdir('/home/user/LinguaLoop-web')
os.environ['DISABLE_SCHEDULER'] = 'true'
import httpx
from unittest.mock import MagicMock
for m in ['spacy', 'pyopenjtalk']:
    try: __import__(m)
    except Exception: sys.modules[m] = MagicMock()
CALLS = []
_orig = httpx.Client.send
def send(self, req, *a, **k):
    p = req.url.path
    p = 'rpc:' + p.split('/rpc/')[1] if '/rpc/' in p else req.method + ' ' + p.split('/rest/v1/')[-1]
    fr = [f"{os.path.basename(f.filename)}:{f.lineno}:{f.name}" for f in traceback.extract_stack()
          if 'LinguaLoop-web' in f.filename and 'site-packages' not in f.filename][-4:]
    CALLS.append((p, ' < '.join(reversed(fr))))
    return _orig(self, req, *a, **k)
httpx.Client.send = send
logging.disable(logging.WARNING)
import middleware.auth as ma
USER, LANG = sys.argv[1], sys.argv[2]
ma._authenticate = lambda tok: ({'sub': USER, 'email': 'x', 'role': 'authenticated', 'aud': 'authenticated', 'user': None}, None)
from app import create_app
c = create_app().test_client()
for ep in sys.argv[3:]:
    CALLS.clear(); r = c.get(ep, headers={'Authorization': 'Bearer x'})
    print(f"\n== {ep} status={r.status_code} calls={len(CALLS)}")
    for p, fr in CALLS: print(f"  {p:38s} {fr}")
