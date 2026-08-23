"""TASK-733 smoke: prove the rewritten prompts still run and that the emitted
difficulty actually tracks the requested tier.

Three families, each through its REAL code path rather than a hand-built API call:

* ``prose_generation``      -> services.test_generation.agents.prose_writer.ProseWriter
* ``exercise_sentence_generation`` -> services.exercise_generation.transcript_miner.LLMSentenceGenerator
* ``cloze_distractor_generation``  -> the live template + validators' tag contract

The exercise-sentence smoke matters most for ja: before this task that row's JSON
example was single-braced, so ``template.format(...)`` raised
``KeyError '"sentence"'`` at transcript_miner.py:226 — outside the try block, so
Japanese grammar sentence generation crashed outright rather than degrading.
``dim_grammar_patterns`` is empty in this project, so the source row is stubbed;
the line under test is the format call, not the lookup.

Usage::

    PYTHONIOENCODING=utf-8 PYTHONPATH=. python scripts/smoke_task733_prompts.py
    PYTHONIOENCODING=utf-8 PYTHONPATH=. python scripts/smoke_task733_prompts.py --family prose
"""

from __future__ import annotations

import argparse
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.prompt_service import get_template_config, get_template_text  # noqa: E402

LANG = {1: ('zh', 'Chinese'), 2: ('en', 'English'), 3: ('ja', 'Japanese')}
CJK = re.compile(r'[぀-ヿ一-鿿]')
CLOZE_TAGS = {'semantic', 'collocational', 'aspectual', 'register', 'valency'}


def complexity_of(text: str, language_id: int) -> dict:
    """Cheap, language-appropriate lexical-complexity probe.

    For en, mean word length and mean words-per-sentence. For zh/ja, mean
    characters-per-sentence plus the share of CJK characters — word tokenisation
    would need a segmenter and this is only a monotonicity check.
    """
    sentences = [s for s in re.split(r'[.!?。！？\n]+', text) if s.strip()]
    if language_id == 2:
        words = re.findall(r"[A-Za-z']+", text)
        return {
            'sentences': len(sentences),
            'mean_word_len': round(statistics.mean([len(w) for w in words]), 2) if words else 0,
            'mean_sent_len': round(len(words) / max(len(sentences), 1), 1),
            'long_words': sum(1 for w in words if len(w) >= 9),
        }
    chars = CJK.findall(text)
    return {
        'sentences': len(sentences),
        'cjk_chars': len(chars),
        'mean_sent_len': round(len(chars) / max(len(sentences), 1), 1),
    }


def smoke_prose(db) -> int:
    from services.test_generation.agents.prose_writer import ProseWriter

    print('\n=== prose_generation ===')
    problems = 0
    cases = [(2, 'T1', 1, 40, 70), (2, 'T6', 8, 90, 160),
             (1, 'T2', 3, 60, 120), (3, 'T5', 7, 90, 160)]
    seen = {}
    for lang_id, tier, difficulty, wmin, wmax in cases:
        code, name = LANG[lang_id]
        cfg = get_template_config(db, 'prose_generation', lang_id)
        writer = ProseWriter(model=cfg['model'])
        try:
            prose = writer.generate_prose(
                topic_concept='how bread is made',
                language_name=name, language_code=code, difficulty=difficulty,
                word_count_min=wmin, word_count_max=wmax,
                keywords=['bread', 'heat'] if lang_id == 2 else [],
                complexity_tier=tier, prompt_template=cfg['template'],
                model_override=cfg['model'], template_version=cfg['version'],
            )
        except Exception as exc:  # noqa: BLE001
            print(f'  {code} {tier}: FAILED {type(exc).__name__}: {exc}')
            problems += 1
            continue
        m = complexity_of(prose, lang_id)
        seen[(lang_id, tier)] = m
        print(f'  {code} {tier} (d{difficulty}): {m}')
        print(f'      {prose[:110].strip()}...')
        if not prose.strip():
            print(f'  {code} {tier}: EMPTY output'); problems += 1

    # Monotonicity: the tier must actually move the output, not just the label.
    lo, hi = seen.get((2, 'T1')), seen.get((2, 'T6'))
    if lo and hi:
        ok = hi['mean_word_len'] > lo['mean_word_len'] and hi['mean_sent_len'] > lo['mean_sent_len']
        print(f'\n  en T1 -> T6 tracks tier: {ok} '
              f'(word_len {lo["mean_word_len"]} -> {hi["mean_word_len"]}, '
              f'sent_len {lo["mean_sent_len"]} -> {hi["mean_sent_len"]})')
        if not ok:
            problems += 1
    return problems


def smoke_exercise_sentences(db) -> int:
    """Drive LLMSentenceGenerator.generate() with a stubbed source row.

    dim_grammar_patterns is empty in this project, so _load_source_data is
    patched; everything downstream — including the template.format() call that
    crashed for ja — is the real code path.
    """
    from services.exercise_generation.transcript_miner import LLMSentenceGenerator
    from services.llm_service import call_llm

    print('\n=== exercise_sentence_generation ===')
    problems = 0
    stub = {
        2: dict(pattern_code='USED_TO', description='Past habitual with "used to"',
                example_sentence='I used to walk to school.', complexity_tier='T2'),
        3: dict(pattern_code='TE_IRU', description='「〜ている」進行・状態',
                example_sentence='彼は本を読んでいる。', complexity_tier='T5'),
        1: dict(pattern_code='BA_SENTENCE', description='“把”字句',
                example_sentence='他把书放在桌子上。', complexity_tier='T3'),
    }
    for lang_id in (2, 3, 1):
        code, _ = LANG[lang_id]
        cfg = get_template_config(db, 'exercise_sentence_generation', lang_id)
        gen = LLMSentenceGenerator(db, call_llm, cfg['model'])
        gen._load_source_data = lambda _st, _sid, _d=stub[lang_id]: dict(_d)  # noqa: SLF001
        tier = stub[lang_id]['complexity_tier']
        try:
            out = gen.generate('grammar', 1, lang_id, 3)
        except Exception as exc:  # noqa: BLE001
            print(f'  {code} {tier}: FAILED {type(exc).__name__}: {exc}')
            problems += 1
            continue
        if not out:
            print(f'  {code} {tier}: no sentences returned'); problems += 1; continue
        keys = sorted({k for s in out for k in s})
        tiers = {s.get('complexity_tier') for s in out}
        print(f'  {code} {tier}: {len(out)} sentence(s), keys={keys}, emitted tier={tiers}')
        print(f'      {out[0].get("sentence", "")[:90]}')
        if any('cefr_level' in s for s in out):
            print(f'  {code}: cefr_level SURVIVES in output'); problems += 1
        if tiers != {tier}:
            print(f'  {code}: emitted tier {tiers} != requested {tier} (soft)')
    return problems


def smoke_cloze(db) -> int:
    from services.llm_service import call_llm

    print('\n=== cloze_distractor_generation ===')
    problems = 0
    cases = {
        1: dict(original_sentence='他把书放在桌子上。', sentence_with_blank='他把书___在桌子上。',
                correct_answer='放', complexity_tier='T3'),
        3: dict(original_sentence='彼は毎朝コーヒーを飲む。', sentence_with_blank='彼は毎朝コーヒーを___。',
                correct_answer='飲む', complexity_tier='T4'),
        2: dict(original_sentence='She quickly grasped the concept.',
                sentence_with_blank='She quickly ___ the concept.',
                correct_answer='grasped', complexity_tier='T5'),
    }
    for lang_id, args in cases.items():
        code, _ = LANG[lang_id]
        cfg = get_template_config(db, 'cloze_distractor_generation', lang_id)
        try:
            payload = call_llm(cfg['template'].format(**args), model=cfg['model'],
                               response_format='json', timeout=120,
                               pipeline='smoke', task_name='task733_smoke_cloze')
        except Exception as exc:  # noqa: BLE001
            print(f'  {code}: FAILED {type(exc).__name__}: {exc}'); problems += 1; continue
        tags = payload.get('distractor_tags', {}) if isinstance(payload, dict) else {}
        used = set(tags.values())
        print(f'  {code} {args["complexity_tier"]}: distractors='
              f'{payload.get("distractors")} tags={tags}')
        bad = used - CLOZE_TAGS
        if bad:
            print(f'  {code}: tags outside the five-dimension set: {bad}'); problems += 1
        if len(used) < 2:
            print(f'  {code}: only {len(used)} distinct dimension(s); prompt asks for >=2 (soft)')
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', choices=['prose', 'sentences', 'cloze', 'all'], default='all')
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    problems = 0
    if args.family in ('prose', 'all'):
        problems += smoke_prose(db)
    if args.family in ('sentences', 'all'):
        problems += smoke_exercise_sentences(db)
    if args.family in ('cloze', 'all'):
        problems += smoke_cloze(db)

    print(f'\n{"SMOKE OK" if not problems else f"{problems} SMOKE PROBLEM(S)"}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
