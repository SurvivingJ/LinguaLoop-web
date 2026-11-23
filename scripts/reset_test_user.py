"""Wipe the test account's activity so each test run starts clean.

Deletes only rows where user_id = the test user's id, which is looked up from
TEST_USER_EMAIL and must match TEST_USER_ID if that is set. Account setup
(user_languages, user_tokens, token_transactions, user_study_plans,
trusted_devices) and logs are kept.

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TEST_USER_EMAIL, [TEST_USER_ID].

Usage:
    python scripts/reset_test_user.py             # dry run: show row counts only
    python scripts/reset_test_user.py --apply     # delete the rows

Nothing is deleted without --apply (--dry-run is accepted as an explicit alias).
"""

import os
import sys

import requests

try:
    from _common import base_parser
except ImportError:  # imported as scripts.<name>
    from scripts._common import base_parser

# Children before parents; anything blocked by a FK is retried on a later pass.
ACTIVITY_TABLES = [
    'question_attempt_results',
    'calibration_responses',
    'calibration_sessions',
    'user_calibration_state',
    'exercise_attempts',
    'user_exercise_history',
    'user_exercise_sessions',
    'test_attempts',
    'word_quiz_results',
    'dt_error_profile_entry',
    'dt_card',
    'dt_submission',
    'study_time_ledger',
    'daily_test_loads',
    'weekly_plan_states',
    'user_test_intros_seen',
    'user_flashcards',
    'user_vocabulary_knowledge',
    'user_word_ladder',
    'user_word_watchlist',
    'user_classifier_mastery',
    'user_skill_rating_adjustments',
    'user_skill_ratings',
]


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"reset_test_user: missing env var {name}")
    return value


def reset(dry_run: bool) -> None:
    base = _env('SUPABASE_URL').rstrip('/')
    key = _env('SUPABASE_SERVICE_ROLE_KEY')
    email = _env('TEST_USER_EMAIL')
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}

    # Refuse to run against anything that doesn't look like a test account.
    if 'test' not in email.split('@')[0].lower():
        sys.exit(f"reset_test_user: refusing to reset non-test email {email!r}")

    resp = requests.get(f'{base}/rest/v1/users', headers=headers,
                        params={'select': 'id', 'email': f'eq.{email}'}, timeout=15)
    resp.raise_for_status()
    rows = resp.json()
    if len(rows) != 1:
        sys.exit(f"reset_test_user: expected 1 user for {email}, found {len(rows)}")
    user_id = rows[0]['id']
    expected = os.environ.get('TEST_USER_ID')
    if expected and expected != user_id:
        sys.exit(f"reset_test_user: TEST_USER_ID {expected} != looked-up id {user_id}")

    params = {'user_id': f'eq.{user_id}'}
    pending = list(ACTIVITY_TABLES)
    for _ in range(3):
        failed = []
        for table in pending:
            if dry_run:
                r = requests.head(f'{base}/rest/v1/{table}', params=params, timeout=15,
                                  headers={**headers, 'Prefer': 'count=exact'})
                print(f'{table}: {r.headers.get("content-range", "?").split("/")[-1]} rows')
                continue
            r = requests.delete(f'{base}/rest/v1/{table}', params=params, timeout=30,
                                headers={**headers, 'Prefer': 'return=minimal,count=exact'})
            if r.status_code in (200, 204):
                print(f'{table}: deleted {r.headers.get("content-range", "?").split("/")[-1]}')
            else:
                failed.append((table, r.status_code, r.text[:200]))
        if not failed:
            break
        pending = [t for t, _, _ in failed]
    else:
        for table, status, body in failed:
            print(f'{table}: FAILED ({status}) {body}', file=sys.stderr)
        sys.exit(1)
    print(f'reset_test_user: done for {email} ({user_id})')


def main(argv=None) -> None:
    parser = base_parser(description="Wipe the test account's activity (dry run unless --apply).",
                         apply_help="delete the test user's activity rows",
                         dry_run_help='show row counts only (the default)')
    args = parser.parse_args(argv)
    reset(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
