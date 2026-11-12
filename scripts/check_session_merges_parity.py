"""Read-only parity check for the daily-session read merges (ADR-043 option B).

For real learners, compares each bundle RPC against the per-table reads it
replaces:
  * prestudy.plan_for_tests        via prestudy_plan_inputs   vs per-table reads
  * PracticeSessionService._new_word_state via new_word_state_inputs vs two RPCs

Run after applying migrations/latency_2026_11_session_merges.sql:
    python scripts/check_session_merges_parity.py [--users N]

Reads only (service-role client); prints one line per (user, language) and exits
non-zero on any difference.
"""

from __future__ import annotations

import argparse
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client  # noqa: E402

from services import optional_rpc, prestudy  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--users', type=int, default=20)
    args = ap.parse_args()
    db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

    from services.practice_session_service import PracticeSessionService
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = db

    plans = db.table('user_study_plans').select('user_id, language_id').limit(args.users).execute().data or []
    bad = 0
    for p in plans:
        u, lang = p['user_id'], p['language_id']
        loads = db.table('daily_test_loads').select('test_ids').eq('user_id', u).eq('language_id', lang) \
            .order('load_date', desc=True).limit(1).execute().data or []
        tests = [{'id': t['test_id'], 'test_type': t.get('test_type')}
                 for t in ((loads[0]['test_ids'] if loads else []) or []) if isinstance(t, dict)]

        optional_rpc.reset()
        bundled_plans = prestudy.plan_for_tests(db, u, lang, tests)
        bundled_state = svc._new_word_state(u, lang)
        with patch.object(optional_rpc, 'call_bundle', lambda *a, **k: None):
            table_plans = prestudy.plan_for_tests(db, u, lang, tests)
            table_state = svc._new_word_state(u, lang)

        ok = bundled_plans == table_plans and bundled_state == table_state
        bad += not ok
        print(f"{'OK  ' if ok else 'DIFF'} user={u} lang={lang} tests={len(tests)} "
              f"plans={len(table_plans)} state={'yes' if table_state else 'none'}")
        if not ok:
            if bundled_plans != table_plans:
                print('   plans  bundle:', bundled_plans, '\n          tables:', table_plans)
            if bundled_state != table_state:
                print('   state  bundle:', bundled_state, '\n          tables:', table_state)
    print(f"{len(plans) - bad}/{len(plans)} identical")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
