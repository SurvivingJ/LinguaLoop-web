"""Unit tests for the dual-translation passage builder (TASK-603).

Everything is mocked: segmentation/windowing/dedupe are pure functions, and the
only network-touching function (`generate_l1_reference`) takes its router
resolver and model caller as injectable arguments, so no live DB or OpenRouter
call happens here (same convention as test_dual_translation_routes.py /
test_dual_translation_grader_cascade.py). Live verification against a real
seeded corpus is done by scripts/build_dt_passages.py, not here.
"""

import pytest

from services.dual_translation import passage_builder as pb


# ---------------------------------------------------------------------------
# segment_sentences
# ---------------------------------------------------------------------------

class TestSegmentSentences:

    def test_empty_and_none(self):
        assert pb.segment_sentences(None, 'en') == []
        assert pb.segment_sentences('   ', 'en') == []

    def test_cjk_boundaries_zh(self):
        text = '我喜欢猫。你呢？我也是！'
        assert pb.segment_sentences(text, 'zh') == ['我喜欢猫。', '你呢？', '我也是！']

    def test_cjk_keeps_terminatorless_tail(self):
        text = '第一句。第二句还没结束'
        assert pb.segment_sentences(text, 'zh') == ['第一句。', '第二句还没结束']

    def test_latin_boundaries(self):
        text = 'The cat sat. Where did it go? It ran away!'
        assert pb.segment_sentences(text, 'en') == [
            'The cat sat.', 'Where did it go?', 'It ran away!',
        ]

    def test_latin_collapses_newlines(self):
        text = 'Line one.\n  Line two.\n\nLine three.'
        assert pb.segment_sentences(text, 'en') == ['Line one.', 'Line two.', 'Line three.']

    def test_ja_uses_cjk_path(self):
        text = '猫が好きです。犬も好きです。'
        assert pb.segment_sentences(text, 'ja') == ['猫が好きです。', '犬も好きです。']


# ---------------------------------------------------------------------------
# window_sentences
# ---------------------------------------------------------------------------

class TestWindowSentences:

    def test_too_short_yields_nothing(self):
        assert pb.window_sentences([]) == []
        assert pb.window_sentences(['only one']) == []

    def test_min_to_max_is_single_window(self):
        two = ['a', 'b']
        four = ['a', 'b', 'c', 'd']
        assert pb.window_sentences(two) == [['a', 'b']]
        assert pb.window_sentences(four) == [['a', 'b', 'c', 'd']]

    def test_five_rebalances_short_tail_to_3_2(self):
        # naive chunking -> [4, 1]; tail < 2 -> rebalance to 3 + 2
        result = pb.window_sentences(['a', 'b', 'c', 'd', 'e'])
        assert result == [['a', 'b', 'c'], ['d', 'e']]
        assert all(2 <= len(w) <= 4 for w in result)

    def test_six_is_two_full_windows(self):
        result = pb.window_sentences(['1', '2', '3', '4', '5', '6'])
        assert result == [['1', '2', '3', '4'], ['5', '6']]

    def test_nine_rebalances_final_short_tail(self):
        # [4,4,1] -> last <2 -> [4, 3, 2]; no window dropped, none > 4
        result = pb.window_sentences(['1', '2', '3', '4', '5', '6', '7', '8', '9'])
        assert result == [['1', '2', '3', '4'], ['5', '6', '7'], ['8', '9']]
        assert sum(len(w) for w in result) == 9
        assert all(2 <= len(w) <= 4 for w in result)

    def test_seven_keeps_valid_tail(self):
        # [4,3] -> tail already >= 2, no rebalance
        result = pb.window_sentences(['1', '2', '3', '4', '5', '6', '7'])
        assert result == [['1', '2', '3', '4'], ['5', '6', '7']]


# ---------------------------------------------------------------------------
# difficulty_to_age_tier
# ---------------------------------------------------------------------------

class TestDifficultyToAgeTier:

    @pytest.mark.parametrize('difficulty,expected', [
        (1, 1), (2, 1), (3, 2), (4, 3), (5, 3), (6, 4), (7, 5), (8, 6), (9, 6),
    ])
    def test_mapping(self, difficulty, expected):
        assert pb.difficulty_to_age_tier(difficulty) == expected

    def test_none_falls_back_to_t3(self):
        assert pb.difficulty_to_age_tier(None) == 3

    def test_result_always_in_check_range(self):
        for d in range(1, 10):
            assert 1 <= pb.difficulty_to_age_tier(d) <= 6


# ---------------------------------------------------------------------------
# build_passages_for_test
# ---------------------------------------------------------------------------

class TestBuildPassagesForTest:

    def test_blank_transcript_yields_nothing(self):
        test = {'id': 't1', 'transcript': '   ', 'difficulty': 4, 'language_id': 2}
        assert pb.build_passages_for_test(test, 'en') == []

    def test_too_short_transcript_yields_nothing(self):
        test = {'id': 't1', 'transcript': 'Only one sentence.', 'difficulty': 4, 'language_id': 2}
        assert pb.build_passages_for_test(test, 'en') == []

    def test_inherits_derived_age_tier_and_metadata(self):
        test = {
            'id': 'abc-123', 'difficulty': 8, 'language_id': 1,
            'transcript': '第一句。第二句。第三句。',
        }
        rows = pb.build_passages_for_test(test, 'zh')
        assert len(rows) == 1
        row = rows[0]
        assert row['l2_language_id'] == 1
        assert row['source_kind'] == 'test_transcript'
        assert row['source_ref_id'] == 'abc-123'  # str(uuid)
        assert row['age_tier'] == 6  # difficulty 8 -> T6
        assert row['register'] is None
        assert row['status'] == 'active'
        # CJK join: no separator
        assert row['l2_text'] == '第一句。第二句。第三句。'

    def test_english_join_uses_space(self):
        test = {
            'id': 't9', 'difficulty': 4, 'language_id': 2,
            'transcript': 'One thing. Two thing. Three thing.',
        }
        rows = pb.build_passages_for_test(test, 'en')
        assert rows[0]['l2_text'] == 'One thing. Two thing. Three thing.'

    def test_multiple_windows_from_long_transcript(self):
        sentences = ''.join(f'句{i}。' for i in range(6))  # 6 sentences
        test = {'id': 't', 'difficulty': 4, 'language_id': 1, 'transcript': sentences}
        rows = pb.build_passages_for_test(test, 'zh')
        assert len(rows) == 2  # [4, 2]


# ---------------------------------------------------------------------------
# normalize_for_dedupe / dedupe_key / select_new_passages
# ---------------------------------------------------------------------------

class TestNormalizeAndDedupe:

    def test_nfkc_folds_fullwidth(self):
        # full-width digits/letters fold to half-width
        assert pb.normalize_for_dedupe('ＡＢＣ１２３', 'en') == 'abc123'

    def test_whitespace_collapsed_and_stripped(self):
        assert pb.normalize_for_dedupe('  a   b\tc ', 'en') == 'a b c'

    def test_ja_kata_folds_to_hira(self):
        assert pb.normalize_for_dedupe('カタカナ', 'ja') == pb.normalize_for_dedupe('かたかな', 'ja')

    def test_dedupe_key_shape(self):
        key = pb.dedupe_key('uuid-1', 'Hello World.', 'en')
        assert key == ('uuid-1', 'hello world.')

    def test_select_new_filters_existing(self):
        candidates = [
            {'source_ref_id': 't1', 'l2_text': 'Sentence one. Sentence two.'},
            {'source_ref_id': 't1', 'l2_text': 'Brand new span here. Yes.'},
        ]
        existing = {pb.dedupe_key('t1', 'Sentence one. Sentence two.', 'en')}
        fresh = pb.select_new_passages(candidates, existing, 'en')
        assert len(fresh) == 1
        assert fresh[0]['l2_text'] == 'Brand new span here. Yes.'

    def test_select_new_collapses_intra_batch_duplicates(self):
        candidates = [
            {'source_ref_id': 't1', 'l2_text': 'Same span. Repeated.'},
            {'source_ref_id': 't1', 'l2_text': 'same   span.  repeated.'},  # normalizes equal
        ]
        fresh = pb.select_new_passages(candidates, set(), 'en')
        assert len(fresh) == 1


# ---------------------------------------------------------------------------
# reference_l1_ids
# ---------------------------------------------------------------------------

class TestReferenceL1Ids:

    def test_excludes_own_l2(self):
        assert pb.reference_l1_ids(2) == [1, 3]   # L2=en -> zh, ja
        assert pb.reference_l1_ids(1) == [2, 3]   # L2=zh -> en, ja
        assert pb.reference_l1_ids(3) == [1, 2]   # L2=ja -> zh, en

    def test_respects_custom_supported_set(self):
        assert pb.reference_l1_ids(1, supported_ids=(1, 2)) == [2]


# ---------------------------------------------------------------------------
# generate_l1_reference (router + LLM boundary injected)
# ---------------------------------------------------------------------------

class _Route:
    def __init__(self, slug, reason=None):
        self.slug = slug
        self.reason = reason


class TestGenerateL1Reference:

    def test_returns_row_with_slug_provenance(self):
        calls = {}

        def fake_resolve(db, tier, language_id):
            calls['resolve'] = (tier, language_id)
            return _Route('google/gemini-flash-1.5')

        def fake_call(slug, prompt, *, temperature):
            calls['call'] = (slug, prompt, temperature)
            return ('Hola mundo.', 11, 4, 0.2)

        ref = pb.generate_l1_reference(
            db=object(),
            l2_text='你好世界。再见。',
            l2_language_id=1,
            l1_language_id=2,
            l1_code='en',
            resolve=fake_resolve,
            call=fake_call,
        )

        assert ref == {
            'l1_language_id': 2,
            'l1_text': 'Hola mundo.',
            'generator_slug': 'google/gemini-flash-1.5',
        }
        # resolves the grading tier for the passage's L2, not the L1
        assert calls['resolve'] == ('tier1', 1)
        # prompt names the target L1 and contains the source text
        assert 'English' in calls['call'][1]
        assert '你好世界。再见。' in calls['call'][1]

    def test_none_when_router_has_no_slug(self):
        def fake_resolve(db, tier, language_id):
            return _Route(None, reason='no usable tier; fail open to Tier 0 marks')

        def boom_call(*a, **k):  # pragma: no cover - must not be reached
            raise AssertionError("must not call the model when no slug is available")

        ref = pb.generate_l1_reference(
            db=object(), l2_text='x', l2_language_id=1, l1_language_id=2, l1_code='en',
            resolve=fake_resolve, call=boom_call,
        )
        assert ref is None

    def test_none_when_model_returns_empty(self):
        ref = pb.generate_l1_reference(
            db=object(), l2_text='x', l2_language_id=1, l1_language_id=2, l1_code='en',
            resolve=lambda db, tier, lid: _Route('some/slug'),
            call=lambda slug, prompt, *, temperature: ('   ', 1, 0, 0.1),
        )
        assert ref is None
