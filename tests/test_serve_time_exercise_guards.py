"""Guards for two serve-time exercise defects.

* jumbled_sentence rows that cannot be prepared (no chunks and no
  ``original_sentence``, or fewer than three chunks) must be dropped from a
  session instead of reaching the renderer, which throws on them.
* definition_match options must all be in the key definition's language.
"""

from services.exercise_generation.language_processor import (
    jumbled_is_servable,
    prepare_jumbled_content,
)
from services.vocabulary_ladder.deterministic.definition_match import script_family


def test_prepare_jumbled_content_without_sentence_raises_clear_error():
    try:
        prepare_jumbled_content({}, language_id=2)
    except ValueError as exc:
        assert 'original_sentence' in str(exc)
    else:
        raise AssertionError('expected ValueError')


def test_jumbled_is_servable():
    ok = {'chunks': ['a', 'b', 'c'], 'correct_ordering': [0, 1, 2]}
    assert jumbled_is_servable(ok)
    assert not jumbled_is_servable({'chunks': ['a', 'b'], 'correct_ordering': [0, 1]})
    assert not jumbled_is_servable({'chunks': ['a', 'b', ' '], 'correct_ordering': [0, 1, 2]})
    assert not jumbled_is_servable({'chunks': ['a', 'b', 'c']})
    assert not jumbled_is_servable({'original_sentence': 'x'})
    assert not jumbled_is_servable(None)


def test_prepare_jumbled_items_drops_unservable_rows():
    from services.practice_session_service import PracticeSessionService

    good = {
        'exercise_type': 'jumbled_sentence', 'exercise_id': 'good',
        'content': {'chunks': ['a', 'b', 'c']},
    }
    no_text = {'exercise_type': 'jumbled_sentence', 'exercise_id': 'empty', 'content': {}}
    other = {'exercise_type': 'cloze_completion', 'exercise_id': 'other', 'content': {}}
    items = [good, no_text, other]

    PracticeSessionService._prepare_jumbled_items(items, language_id=2)

    assert [i['exercise_id'] for i in items] == ['good', 'other']
    assert good['content']['correct_ordering'] == [0, 1, 2]


def test_script_family_separates_japanese_from_english():
    assert script_family('食べ物を口に入れて飲み込む') == 'cjk'
    assert script_family('to put food in the mouth and swallow') == 'latin'
    assert script_family('日本語の定義 (JLPT N5)') == 'cjk'
