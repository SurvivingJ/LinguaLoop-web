"""Mint a fresh access token for the dedicated test account.

Uses Supabase's password grant (the app UI is OTP-only, but GoTrue still
accepts passwords), so automated runs get a real user session without
reading email.

Env: SUPABASE_URL, SUPABASE_KEY (anon), TEST_USER_EMAIL, TEST_USER_PASSWORD.

Usage:
    python scripts/mint_test_token.py            # prints the access token
    python scripts/mint_test_token.py --json     # prints the full session JSON
"""

import json
import os
import sys

import requests


def mint_session() -> dict:
    missing = [k for k in ('SUPABASE_URL', 'SUPABASE_KEY', 'TEST_USER_EMAIL', 'TEST_USER_PASSWORD')
               if not os.environ.get(k)]
    if missing:
        sys.exit(f"mint_test_token: missing env vars: {', '.join(missing)}")

    resp = requests.post(
        f"{os.environ['SUPABASE_URL'].rstrip('/')}/auth/v1/token?grant_type=password",
        headers={'apikey': os.environ['SUPABASE_KEY'], 'Content-Type': 'application/json'},
        json={'email': os.environ['TEST_USER_EMAIL'], 'password': os.environ['TEST_USER_PASSWORD']},
        timeout=15,
    )
    if resp.status_code != 200:
        sys.exit(f"mint_test_token: login failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


if __name__ == '__main__':
    session = mint_session()
    print(json.dumps(session) if '--json' in sys.argv else session['access_token'])
