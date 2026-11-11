"""gunicorn entry for local runs: stub NLP packages not installable here, then load
the app from APP_DIR (pristine worktree for 'before', the repo for 'after')."""
import os, sys
from unittest.mock import MagicMock
for m in ['spacy', 'pyopenjtalk']:
    try: __import__(m)
    except Exception: sys.modules[m] = MagicMock()
d = os.environ['APP_DIR']; sys.path.insert(0, d); os.chdir(d)
from app import create_app
app = create_app()
