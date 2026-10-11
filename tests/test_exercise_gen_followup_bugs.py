"""Regression tests for the three pipeline-independent follow-up bugs from
wiki/evaluations/exercise-gen-phase1-2026-09.md §14 ("Follow-up bugs
(deterministic-generator defects, pipeline-independent)") and
wiki/evaluations/exercise-gen-phase2-2026-10.md §8:

  1. jumbled_sentence (L9) chunk reconstruction broken or missing chunks
     -- covered in tests/test_deterministic_generators.py (jumbled.py).
  2. cloze_typed accepted-answer list / correct_answer mismatches
     -- builder-level cases covered in tests/test_deterministic_generators.py
        (cloze_typed.py); the shared blanking fix it also depends on is
        exercised here via `_render_cloze`.
  3. Template concatenation bugs producing glued non-words ('workss',
     'smallchild') -- the shared root cause for every per-level renderer
     that cuts a blank with `text.replace(target, '___', 1)`.

Everything here is pure data transformation (`LadderExerciseRenderer` is
explicitly "no LLM calls" per its own module docstring); judge calls are only
reached after the new skip-path checks, so a sentinel `db=object()` never
actually needs to answer anything in these tests.
"""

from __future__ import annotations

from services.vocabulary_ladder.config import blank_target
from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer


def _core(sentences: list[dict]) -> dict:
    return {'definition': 'x', 'sentences': sentences}


# ---------------------------------------------------------------------------
# blank_target (shared helper, services/vocabulary_ladder/config.py)
# ---------------------------------------------------------------------------

def test_blank_target_rejects_a_prefix_only_match():
    """Real eval-run bug, reference sense 13929 (L3): template 'Marcus ___s'
    + answer 'works' rendered as 'workss'. Root cause: target='work' is only
    a prefix of the sentence's actual word 'works', so a naive
    `str.replace` blanks the prefix and leaves the 's' glued to the marker.
    The fix must refuse to blank a non-boundary match at all."""
    assert blank_target('Marcus works today.', 'work', language_id=2) is None


def test_blank_target_does_not_eat_a_word_boundary_space():
    """Real eval-run bug, candidate sense 14033 (L3): '___child'/'___wooden'
    instead of '___ child'/'___ wooden'. Root cause: an incidental trailing
    space on the stored target ('small ') gets consumed by the replace along
    with the word, eating the space that separated it from the next word."""
    assert blank_target('a small child', 'small ', language_id=2) == 'a ___ child'


def test_blank_target_blanks_a_clean_match_normally():
    assert blank_target('Marcus works today.', 'works', language_id=2) == 'Marcus ___ today.'
    assert blank_target('我每天早上喝咖啡。', '咖啡', language_id=1) == '我每天早上喝___。'


def test_blank_target_none_when_absent():
    assert blank_target('no match here', 'xyz', language_id=2) is None
    assert blank_target('', 'work', language_id=2) is None
    assert blank_target('text', '', language_id=2) is None


# ---------------------------------------------------------------------------
# _render_cloze (L3) -- same template-glue class of bug, applied in the
# renderer that reads the LLM-generated cloze_completion asset.
# ---------------------------------------------------------------------------

def test_render_cloze_skips_rather_than_glue_a_suffix_onto_the_blank():
    renderer = LadderExerciseRenderer(db=object())
    core = _core([
        {'text': 'Marcus works today.', 'target_word': 'work'},
    ])
    p2 = {'level_3': {
        'sentence_index': 0,
        'correct_answer': 'works',
        'options': [
            {'text': 'works', 'is_correct': True},
            {'text': 'plays', 'is_correct': False},
            {'text': 'sings', 'is_correct': False},
            {'text': 'eats', 'is_correct': False},
        ],
    }}
    result = renderer._render_cloze(core, p2, {}, sense_id=1, language_id=2, sa={})
    assert result is None


def test_render_cloze_blanks_cleanly_when_target_matches_exactly(monkeypatch):
    renderer = LadderExerciseRenderer(db=object())
    core = _core([
        {'text': 'Marcus works today.', 'target_word': 'works'},
    ])
    p2 = {'level_3': {
        'sentence_index': 0,
        'correct_answer': 'works',
        'options': [
            {'text': 'works', 'is_correct': True},
            {'text': 'plays', 'is_correct': False},
            {'text': 'sings', 'is_correct': False},
            {'text': 'eats', 'is_correct': False},
        ],
    }}
    # Bundle mode off and no real judge DB: patch the distractor judge to a
    # pure pass-through so this stays an offline, no-LLM test.
    import services.exercise_generation.cloze_judge as cloze_judge_mod
    monkeypatch.setattr(
        cloze_judge_mod, 'filter_distractors',
        lambda db, sentence_with_blank, correct_answer, distractors, language_id:
            (distractors, {'rejected': 0, 'kept': len(distractors)}),
    )
    renderer._bundle_judge_result = None
    result = renderer._render_cloze(core, p2, {}, sense_id=1, language_id=2, sa={})
    assert result is not None
    assert result['sentence_with_blank'] == 'Marcus ___ today.'


# ---------------------------------------------------------------------------
# _render_morphology_slot (L4) -- the '複雑'/'複雑すぎ' class of defect: the
# blank is cut at the sentence's own target, but the model's "correct_form"
# names a different span, so the right-answer option doesn't fit the blank
# it is offered for.
# ---------------------------------------------------------------------------

def test_render_morphology_slot_skips_when_correct_form_disagrees_with_target():
    """Named eval-run example: template '___て' (blanked from '複雑すぎ') +
    correct_form '複雑' renders as '複雑て' instead of '複雑すぎて'."""
    renderer = LadderExerciseRenderer(db=object())
    core = _core([
        {'text': 'そこに、発酵の複雑すぎな役割が凝縮されているのである。',
         'target_word': '複雑すぎ'},
    ])
    p3 = {'level_4': {
        'sentence_index': 0,
        'correct_form': '複雑',
        'base_form': '複雑',
        'form_label': 'plain',
        'options': [
            {'text': '複雑', 'is_correct': True},
            {'text': 'A', 'is_correct': False},
            {'text': 'B', 'is_correct': False},
            {'text': 'C', 'is_correct': False},
        ],
    }}
    result = renderer._render_morphology_slot(core, {}, p3, sense_id=1, language_id=3, sa={})
    assert result is None


def test_render_morphology_slot_renders_when_correct_form_matches_target():
    renderer = LadderExerciseRenderer(db=object())
    core = _core([
        {'text': 'Her decision was final.', 'target_word': 'decision'},
    ])
    p3 = {'level_4': {
        'sentence_index': 0,
        'correct_form': 'decision',
        'base_form': 'decide',
        'form_label': 'noun',
        'options': [
            {'text': 'decision', 'is_correct': True},
            {'text': 'decidement', 'is_correct': False},
            {'text': 'decisionment', 'is_correct': False},
            {'text': 'decisive', 'is_correct': False},
        ],
    }}
    result = renderer._render_morphology_slot(core, {}, p3, sense_id=1, language_id=2, sa={})
    assert result is not None
    assert result['sentence_with_blank'] == 'Her ___ was final.'
    assert result['correct_answer'] == 'decision'


# ---------------------------------------------------------------------------
# _render_collocation_gap (L5) -- same blanking helper, same class of bug.
# ---------------------------------------------------------------------------

def test_render_collocation_gap_skips_on_a_prefix_only_collocate_match():
    renderer = LadderExerciseRenderer(db=object())
    core = _core([
        {'text': 'He works hard every day.', 'target_word': 'work'},
    ])
    p2 = {'level_5': {
        'sentence_index': 0,
        'correct_collocate': 'work',  # sentence actually has 'works'
        'options': [
            {'text': 'work', 'is_correct': True},
            {'text': 'play', 'is_correct': False},
        ],
    }}
    result = renderer._render_collocation_gap(core, p2, {}, sense_id=1, language_id=2, sa={})
    assert result is None
