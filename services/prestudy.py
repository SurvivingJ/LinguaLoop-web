"""Test prestudy: the data a learner needs to study a test before taking it.

Spec: wiki/features/test-prestudy.md (modes 1 and 2, readiness check).

``build_prestudy_payload`` returns one object in the shape the prestudy page
(static/js/prestudy/prestudy.js) reads:

    {
      test:       {id, slug, title, language_id, transcript, audio_url,
                   difficulty, target_age_tier, vocab_sense_ids,
                   vocab_token_map, furigana_payload, pinyin_payload},
      questions:  [{sense_ids}],                 # question-linked senses only
      senses:     {sense_id: {lemma, pos, freq, reading,
                              glosses: {lang_id: {def, ex}}}},
      knowledge:  {sense_id: {p, status, n}},    # the learner's BKT rows
      exercises:  {sense_id: [{id, type, group, level, c}]},
      gloss_language_id, ability_zipf
    }

The scored questions' text, choices and answers are never included: prestudy
must not leak the test. Only each question's linked senses are sent, so the
page can rank the words the questions turn on first.

Functions here read the database but never write; evidence is written by the
route through VocabularyKnowledgeService.update_from_word_tests_batch.
"""

from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

# Ladder exercise types the prestudy prime can render, the content fields each
# renderer needs, and which practice round (use / judge) it belongs to.
EXERCISE_FIELDS = {
    'cloze_completion': ['sentence_with_blank', 'options', 'correct_answer', 'explanation', 'original_sentence'],
    'cloze_typed': ['sentence_with_blank', 'answer', 'original_sentence', 'target_word'],
    'semantic_discrimination': ['sentences', 'explanation', 'target_word'],
    'spot_incorrect_sentence': ['sentences'],
    'tl_nl_translation': ['tl_sentence', 'options', 'correct_nl'],
    'jumbled_sentence': ['chunks', 'correct_ordering', 'original_sentence'],
    'definition_match': ['word', 'options', 'correct_definition', 'pronunciation'],
    'particle_selection': ['sentence_with_blank', 'options', 'correct_answer', 'original_sentence', 'nl'],
    'morphology_slot': ['sentence_with_blank', 'options', 'correct_answer', 'explanation', 'original_sentence', 'form_label'],
    'synonym_antonym_match': ['word', 'options', 'correct_answer', 'relation', 'nl'],
}
EXERCISE_GROUP = {
    'cloze_completion': 'use', 'cloze_typed': 'use', 'particle_selection': 'use',
    'morphology_slot': 'use', 'definition_match': 'use',
    'semantic_discrimination': 'judge', 'spot_incorrect_sentence': 'judge',
    'tl_nl_translation': 'judge', 'jumbled_sentence': 'judge', 'synonym_antonym_match': 'judge',
}
MAX_EXERCISES_PER_TYPE = 2
DEFAULT_ABILITY_ZIPF = 5.0


def trim_exercise(row: dict, rng: random.Random | None = None) -> Optional[dict]:
    """Keep only what a prestudy renderer needs from an ``exercises`` row."""
    t = row.get('exercise_type')
    fields = EXERCISE_FIELDS.get(t)
    content = row.get('content') or {}
    if not fields or not isinstance(content, dict):
        return None
    c = {k: content.get(k) for k in fields if k in content}
    if isinstance(c.get('nl'), dict):
        c['nl'] = {'en': c['nl'].get('en')}
    if t == 'cloze_typed':
        c['answer'] = {'accepted': ((content.get('answer') or {}).get('accepted') or [])}
    return {'id': row.get('id'), 'type': t, 'group': EXERCISE_GROUP[t],
            'level': row.get('ladder_level'), 'c': c}


def group_exercises(rows: list[dict], seed: int = 0) -> dict[str, list[dict]]:
    """At most MAX_EXERCISES_PER_TYPE trimmed exercises per sense and type."""
    rng = random.Random(seed)
    by_sense: dict[int, dict[str, list[dict]]] = {}
    for r in rows:
        item = trim_exercise(r)
        if item is None:
            continue
        by_sense.setdefault(r['word_sense_id'], {}).setdefault(item['type'], []).append(item)
    out: dict[str, list[dict]] = {}
    for sid, types in by_sense.items():
        picked: list[dict] = []
        for items in types.values():
            rng.shuffle(items)
            picked.extend(items[:MAX_EXERCISES_PER_TYPE])
        out[str(sid)] = picked
    return out


def _chunks(seq: list, n: int = 200):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _load_senses(db, sense_ids: list[int], gloss_language_id: Optional[int]) -> dict[str, dict]:
    """Lemma, POS, frequency, reading and glosses (native + preferred) per sense."""
    rows: list[dict] = []
    for part in _chunks(sense_ids):
        rows += db.table('dim_word_senses').select(
            'id, vocab_id, sense_rank, definition, definition_language_id, example_sentence, pronunciation, '
            'dim_vocabulary(lemma, part_of_speech, frequency_rank, reading, language_id)'
        ).in_('id', part).execute().data or []
    senses: dict[str, dict] = {}
    wanted: dict[tuple, int] = {}
    for r in rows:
        v = r.get('dim_vocabulary') or {}
        sid = str(r['id'])
        senses[sid] = {
            'lemma': v.get('lemma') or '',
            'pos': v.get('part_of_speech'),
            'freq': v.get('frequency_rank'),
            'reading': v.get('reading') or r.get('pronunciation'),
            'glosses': {str(r.get('definition_language_id')): {'def': r.get('definition'), 'ex': r.get('example_sentence')}},
        }
        if gloss_language_id and gloss_language_id != r.get('definition_language_id'):
            wanted[(r['vocab_id'], r.get('sense_rank'))] = r['id']
    if wanted:
        vocab_ids = sorted({k[0] for k in wanted})
        for part in _chunks(vocab_ids):
            for g in db.table('dim_word_senses').select(
                'vocab_id, sense_rank, definition, example_sentence, definition_language_id'
            ).in_('vocab_id', part).eq('definition_language_id', gloss_language_id).execute().data or []:
                sid = wanted.get((g['vocab_id'], g.get('sense_rank')))
                if sid is not None and g.get('definition'):
                    senses[str(sid)]['glosses'][str(gloss_language_id)] = {'def': g['definition'], 'ex': g.get('example_sentence')}
    return senses


def _load_knowledge(db, user_id: str, sense_ids: list[int]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for part in _chunks(sense_ids):
        for k in db.table('user_vocabulary_knowledge').select(
            'sense_id, p_known, status, evidence_count'
        ).eq('user_id', user_id).in_('sense_id', part).execute().data or []:
            out[str(k['sense_id'])] = {'p': float(k['p_known']), 'status': k.get('status'), 'n': k.get('evidence_count') or 0}
    return out


def _load_exercises(db, sense_ids: list[int]) -> dict[str, list[dict]]:
    rows: list[dict] = []
    for part in _chunks(sense_ids):
        rows += db.table('exercises').select(
            'id, word_sense_id, exercise_type, content, ladder_level'
        ).eq('is_active', True).in_('word_sense_id', part).in_('exercise_type', list(EXERCISE_FIELDS)).execute().data or []
    return group_exercises(rows)


def _ability_zipf(db, user_id: str, language_id: int) -> float:
    try:
        r = db.table('user_calibration_state').select('ability_zipf').eq('user_id', user_id) \
            .eq('language_id', language_id).limit(1).execute().data
        if r and r[0].get('ability_zipf') is not None:
            return float(r[0]['ability_zipf'])
    except Exception as e:  # optional signal; the prior falls back to the default
        logger.info("ability_zipf lookup skipped for %s: %s", user_id, e)
    return DEFAULT_ABILITY_ZIPF


def build_prestudy_payload(db, test: dict, user_id: str, gloss_language_id: Optional[int]) -> dict:
    """Everything the prestudy page needs for one test (see module docstring).

    ``test`` is a ``tests`` row with at least id, slug, title, language_id,
    transcript, audio_url, difficulty, target_age_tier, vocab_sense_ids,
    vocab_token_map, furigana_payload, pinyin_payload.
    """
    sense_ids = sorted({int(s) for s in (test.get('vocab_sense_ids') or []) if s})
    questions = db.table('questions').select('sense_ids').eq('test_id', test['id']).execute().data or []
    q_sense_ids = sorted({int(s) for q in questions for s in (q.get('sense_ids') or []) if s})
    all_ids = sorted(set(sense_ids) | set(q_sense_ids))
    senses = _load_senses(db, all_ids, gloss_language_id) if all_ids else {}
    return {
        'test': {k: test.get(k) for k in (
            'id', 'slug', 'title', 'language_id', 'transcript', 'audio_url', 'difficulty',
            'target_age_tier', 'vocab_sense_ids', 'vocab_token_map', 'furigana_payload', 'pinyin_payload')},
        'questions': [{'sense_ids': q.get('sense_ids') or []} for q in questions],
        'senses': senses,
        'knowledge': _load_knowledge(db, user_id, all_ids) if all_ids else {},
        'exercises': _load_exercises(db, sense_ids) if sense_ids else {},
        'gloss_language_id': gloss_language_id or int(test.get('language_id') or 0),
        'ability_zipf': _ability_zipf(db, user_id, int(test.get('language_id') or 0)),
    }


def evidence_rows(answers: list[dict], allowed_sense_ids: set[int]) -> list[dict]:
    """Collapse the prime's answers into one word-test evidence row per sense.

    Each answer is {sense_id, correct, idk}. "I don't know" counts as wrong,
    the same as calibration's explicit skip. A sense is recorded correct only
    when its correct answers outnumber its wrong ones: the batch RPC merges
    duplicate rows with bool_or, so sending every answer would let one late
    correct answer erase four misses. Senses not in the test are dropped, so
    the endpoint cannot write evidence for arbitrary words.
    """
    tally: dict[int, list[int]] = {}
    for a in answers or []:
        try:
            sid = int(a.get('sense_id'))
        except (TypeError, ValueError):
            continue
        if sid not in allowed_sense_ids:
            continue
        ok = bool(a.get('correct')) and not a.get('idk')
        t = tally.setdefault(sid, [0, 0])
        t[0 if ok else 1] += 1
    return [{'sense_id': sid, 'is_correct': c > w} for sid, (c, w) in sorted(tally.items())]
