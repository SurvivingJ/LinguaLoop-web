"""QuestionValidator changes for the test quality checks (TASK-914, 916, 921)."""

import pytest

from services.test_generation.agents.question_validator import (
    QuestionValidator,
    check_quoted_phrase_in_passage,
)

ORGAN = 'お医者さんが、病気の人の体に、他の人の体の一部を入れる医療の手順があります。'


@pytest.fixture(autouse=True)
def _calibrated(monkeypatch):
    monkeypatch.delenv('TEST_QC_MODES', raising=False)


def vq(question, choices, answer, type_code='vocabulary_context'):
    return {'question': question, 'choices': choices, 'answer': answer, 'type_code': type_code}


def test_bracket_target_present_passes():
    assert check_quoted_phrase_in_passage('文中の（他の人）の意味として最も適切なものは？', ORGAN,
                                          include_brackets=True) is None


def test_bracket_target_missing_rejected():
    err = check_quoted_phrase_in_passage('文中の（存在しない語）の意味は？', ORGAN, include_brackets=True)
    assert err and '存在しない語' in err


def test_brackets_ignored_without_flag():
    assert check_quoted_phrase_in_passage('文中の（存在しない語）の意味は？', ORGAN) is None


def test_long_cjk_span_skipped():
    long_span = '「' + 'あ' * 13 + '」はどういう意味？'
    assert check_quoted_phrase_in_passage(long_span, ORGAN) is None


def test_validator_vocab_bracket_rejects():
    v = QuestionValidator()
    ok, err = v.validate_question(
        vq('文中の（存在しない語）の意味は？', ['あ', 'い', 'う', 'え'], 'あ'), ORGAN)
    assert not ok and '存在しない語' in err


def test_non_vocab_brackets_unchecked():
    v = QuestionValidator()
    ok, _ = v.validate_question(
        vq('お医者さんは（だれ）に体の一部を入れますか？', ['病気の人', '子ども', '先生', '犬'], '病気の人',
           'literal_detail'), ORGAN)
    assert ok


def test_legacy_signature_still_works():
    v = QuestionValidator()
    ok, _ = v.validate_question(
        vq('What does "help" mean here?', ['aid', 'harm', 'leave', 'sing'], 'aid', 'literal_detail'),
        'They help at home.', ['Where do they help?'])
    assert ok


def test_calibrated_mode_rejects_script_above_level():
    # CHECK_MODES['script_above_level'] == 'reject' since calibration 2026-11-09
    v = QuestionValidator()
    item = vq('ロボットはどこでてつだいをしますか？', ['学校', 'おうち', '店', 'こうえん'], 'おうち', 'literal_detail')
    ok, err = v.validate_question(item, 'あたらしいロボットは、おうちでてつだいをします。', language_code='ja', tier=1)
    assert not ok and err.startswith('qc:script_above_level')


def test_flags_attached_in_flag_mode(monkeypatch):
    monkeypatch.setenv('TEST_QC_MODES', 'flag')
    v = QuestionValidator()
    item = vq('ロボットはどこでてつだいをしますか？', ['学校', 'おうち', '店', 'こうえん'], 'おうち', 'literal_detail')
    ok, _ = v.validate_question(item, 'あたらしいロボットは、おうちでてつだいをします。', language_code='ja', tier=1)
    assert ok and {f['code'] for f in item['_quality_flags']} == {'script_above_level'}


def test_reject_mode_fails_validation(monkeypatch):
    monkeypatch.setenv('TEST_QC_MODES', 'reject')
    v = QuestionValidator()
    item = vq('ロボットはどこでてつだいをしますか？', ['学校', 'おうち', '店', 'こうえん'], 'おうち', 'literal_detail')
    ok, err = v.validate_question(item, 'あたらしいロボットは、おうちでてつだいをします。', language_code='ja', tier=1)
    assert not ok and err.startswith('qc:script_above_level')


def test_pairwise_duplicate_in_reject_mode(monkeypatch):
    monkeypatch.setenv('TEST_QC_MODES', 'reject')
    v = QuestionValidator()
    prev = [vq('なにをつみましたか？', ['き', 'いし', 'つち', 'かみ'], 'いし', 'literal_detail')]
    cand = vq('かべはなにでできていますか？', ['き', 'いし', 'つち', 'かみ'], 'いし', 'literal_detail')
    ok, err = v.validate_question(cand, 'いしをつんでかべをつくりました。', language_code='ja', tier=1,
                                  previous=prev)
    assert not ok and 'duplicate_answer' in err


def test_fix_question_strips_labels():
    v = QuestionValidator()
    fixed = v.fix_question({'question': 'Q?', 'choices': ['A. red', 'B. blue', 'C. green', 'D. pink'],
                            'answer': 'B. blue'})
    assert fixed['choices'] == ['red', 'blue', 'green', 'pink'] and fixed['answer'] == 'blue'
    fixed = v.fix_question({'question': 'Q?', 'choices': ['A. red', 'B. blue', 'C. green', 'D. pink'],
                            'answer': 'C'})
    assert fixed['answer'] == 'green'


def test_apply_test_quality_checks_drops_second_duplicate(monkeypatch):
    from services.test_generation.orchestrator import apply_test_quality_checks
    monkeypatch.setenv('TEST_QC_MODES', 'reject')
    qs = [vq('なにをつみましたか？', ['き', 'いし', 'つち', 'かみ'], 'いしをつんだ', 'literal_detail'),
          vq('どこですか？', ['うみ', 'やま', 'まち', 'むら'], 'やま', 'literal_detail'),
          vq('かべはなにでできていますか？', ['き', 'いし', 'つち', 'かみ'], 'いしをつんだ', 'literal_detail')]
    out = apply_test_quality_checks(qs, 'いしをつんでかべをつくりました。', 'かべ', 'ja', 1)
    assert [q['question'] for q in out] == ['なにをつみましたか？', 'どこですか？']


def test_apply_test_quality_checks_flags_in_flag_mode(monkeypatch):
    from services.test_generation.orchestrator import apply_test_quality_checks
    monkeypatch.setenv('TEST_QC_MODES', 'flag')
    qs = [vq('a？', ['き', 'いし', 'つち', 'かみ'], 'いしをつんだ', 'literal_detail'),
          vq('b？', ['き', 'いし', 'つち', 'かみ'], 'いしをつんだ', 'literal_detail')]
    out = apply_test_quality_checks(qs, 'いしをつんだ。', None, 'ja', 1)
    assert len(out) == 2
    assert {f['code'] for f in out[1]['_quality_flags']} == {'duplicate_answer'}
    assert 'missing_title' in {f['code'] for f in out[0]['_quality_flags']}


def test_review_queue_rows_include_quality_flags():
    from types import SimpleNamespace
    from services.test_generation.orchestrator import _write_review_queue_rows
    inserted = []

    class T:
        def insert(self, rows):
            inserted.extend(rows); return self

        def execute(self):
            return None

    db = SimpleNamespace(table=lambda name: T())
    q = {'_quality_flags': [{'code': 'duplicate_answer', 'severity': 'flag'}]}
    _write_review_queue_rows(db, [q, {}], [SimpleNamespace(id='a'), SimpleNamespace(id='b')])
    assert len(inserted) == 1 and inserted[0]['flag_reasons'] == ['qc:duplicate_answer']
    assert inserted[0]['judge_scores']['quality_checks'][0]['code'] == 'duplicate_answer'
