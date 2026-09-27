#!/usr/bin/env python
"""Score a set of transcripts with jev under several instruction variants, so a
tier calibration can be judged against a blind gold set (ADR-029).

  python scripts/calibrate_tier_jev.py --lang ja --variants base,grammar

Reads ``data/eval/jev_recalibration_2026-09-27/<lang>_transcripts.json``
({test_id: transcript}); writes ``<lang>_scores_<variant>.json``
({test_id: {score, confidence, probabilities}}). Read-only against the DB and
logged to llm_calls as pipeline='diag', task 'jev_tier_calibration' so it never
mixes with production tier assignment. Variants live in VARIANTS below.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, '.env'))

from services import jev_client, tier_classifier  # noqa: E402
from services.supabase_factory import SupabaseFactory  # noqa: E402

OUT = os.path.join(REPO, 'data', 'eval', 'jev_recalibration_2026-09-27')

# Extra guidance appended to the language's own instruction sentence. 'base' is
# the production prompt.
VARIANTS = {
    'ja': {
        'base': '',
        'grammar': (
            '判断の主な手がかりは、文の構造（従属節の複雑さ、慣用句、修辞技法、語り口）と'
            '語彙の抽象度です。専門用語や外来語が並んでいるだけで、標準的な大人向けの平易な'
            '説明文を高い年齢層に置かないでください。'
        ),
    },
}


def score_all(lang: str, variant: str, transcripts: dict) -> dict:
    extra = VARIANTS[lang][variant]

    def one(item):
        test_id, text = item
        state, questions = tier_classifier.build_passage_request(lang, text)
        if extra:
            q = questions['tier']
            q['instructions'] = q['instructions'] + extra
        r = jev_client.call_jev(
            state, questions, pipeline='diag',
            task_name='jev_tier_calibration', language_code=lang,
        )
        a = r.answers['tier']
        return test_id, {
            'score': a['score'], 'confidence': a.get('confidence'),
            'probabilities': a.get('probabilities'), 'cost_usd': r.cost_usd,
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(pool.map(one, transcripts.items()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', required=True)
    ap.add_argument('--variants', required=True)
    args = ap.parse_args()
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    with open(os.path.join(OUT, f'{args.lang}_transcripts.json'), encoding='utf-8') as fh:
        transcripts = json.load(fh)
    for variant in args.variants.split(','):
        scores = score_all(args.lang, variant, transcripts)
        path = os.path.join(OUT, f'{args.lang}_scores_{variant}.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(scores, fh, indent=1)
        cost = sum(v['cost_usd'] or 0 for v in scores.values())
        print(f'{variant}: {len(scores)} scored, ${cost:.5f} -> {path}')


if __name__ == '__main__':
    main()
