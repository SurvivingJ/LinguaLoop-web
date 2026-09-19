"""
Makes `import lab.xxx` and `import build_db` work regardless of how pytest
was invoked (PYTHONPATH set or not) - see the project memory note that
pytest silently collects zero tests on a hidden import error rather than
failing loudly. Inserting this sandbox's own directories directly is more
robust than relying on the caller's PYTHONPATH.
"""
import sys
from pathlib import Path

EXLAB_DIR = Path(__file__).resolve().parent.parent  # sandbox/exercise-lab
sys.path.insert(0, str(EXLAB_DIR))
sys.path.insert(0, str(EXLAB_DIR / "db"))
