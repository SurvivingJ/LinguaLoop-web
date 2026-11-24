"""Re-render ladder exercises for given senses with every judge on Claude (claude -p), replacing old rows.

    python3 rerender_claude.py SHARD_FILE DONE_FILE

SHARD_FILE: one sense id per line. DONE_FILE: appended "sid<TAB>status<TAB>n_rows" per sense; senses
already listed there are skipped (resume). Per sense: build_rows first (judges via Claude), then ONE
store.write_sense that inserts the new rows and deletes the sense's old ladder rows
(DeleteWhere(require_word_asset=True)) -- a failed build leaves the old rows in place.
"""
import collections
import os
import sys

sys.path.insert(0, '/home/user/LinguaLoop-web/scripts')
sys.path.insert(0, '/home/user/LinguaLoop-web')
os.chdir('/home/user/LinguaLoop-web')
os.environ.setdefault('EXERCISE_CONTENT_HTTP_TIMEOUT_S', '15')
from _common import admin_db, bootstrap  # noqa: E402

bootstrap()
import services.llm_service as ls  # noqa: E402

_orig = ls._resolve_provider
ls._resolve_provider = lambda provider=None: _orig('claude_cli')   # every model call -> claude -p
ls.LLM_DEFAULT_PROVIDER = 'claude_cli'
from services.exercise_content import store  # noqa: E402
from services.exercise_generation.judges.base import batch_mode, JudgeUnavailable  # noqa: E402
import re  # noqa: E402
LIMIT_RE = re.compile(r'usage limit|rate.?limit|overloaded|\b429\b|\b529\b|limit reached|out of extra usage|credit balance|billing', re.I)
consecutive_fail = 0
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer  # noqa: E402

shard, done_file = sys.argv[1], sys.argv[2]
done = set()
if os.path.exists(done_file):
    done = {line.split('\t')[0] for line in open(done_file) if line.strip()}
db = admin_db()
renderer = LadderExerciseRenderer(db)
for sid in [s.strip() for s in open(shard) if s.strip()]:
    if sid in done:
        continue
    try:
        with batch_mode():   # a judge that cannot reach Claude raises instead of passing everything
            rows = renderer.build_rows(int(sid), 3)
        if not rows:
            status, n = 'no_rows', 0
        else:
            store.write_sense(db, int(sid), 3, insert_rows=rows,
                              delete_where=store.DeleteWhere(require_word_asset=True))
            status, n = 'ok', len(rows)
        types = collections.Counter(r.get('exercise_type') for r in rows)
    except Exception as exc:  # noqa: BLE001 -- log and move on; rerun resumes
        status, n, types = f'error:{type(exc).__name__}:{str(exc)[:120]}', 0, {}
        if isinstance(exc, JudgeUnavailable) or LIMIT_RE.search(str(exc)):
            consecutive_fail += 1
        if consecutive_fail >= 3:
            print('STOP: Claude unavailable (usage limit?)', exc, flush=True)
            sys.exit(3)
    else:
        consecutive_fail = 0
    with open(done_file, 'a') as fh:
        fh.write(f"{sid}\t{status}\t{n}\t{dict(types)}\n")
    print(sid, status, n, flush=True)
