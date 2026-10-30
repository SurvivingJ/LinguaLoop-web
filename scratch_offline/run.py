import os, runpy, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'scripts')]
os.environ.setdefault('SUPABASE_URL', 'http://offline'); os.environ.setdefault('SUPABASE_KEY', 'x')
import offline_db  # noqa
script = sys.argv[1]; sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
