"""
Deterministic generator tests (TASK-516, 528, 529, 532).

Golden fixtures rather than live data: every builder here is pure given its
``SenseContext``, so the interesting cases (a polyphone, a sparse homophone
set, a noun missing from the classifier dictionary) can be constructed exactly
instead of hoped for in a sample.

The distractor assertions are the point. "Produces four options" is nearly
worthless as a test — a generator padding with random words passes it. What
these check is that the options are *the right kind of wrong*: tone variants
for pinyin, voicing/length for kana, same-semantic-group for classifiers, real
corpus words for the sound→script direction.
"""

from __future__ import annotations

import pytest

from services.vocabulary_ladder import deterministic as det
from services.vocabulary_ladder.deterministic import dictionaries as dictmod
from services.vocabulary_ladder.deterministic import lexicon as lexmod
from services.vocabulary_ladder.deterministic.phonology import (
    format_pinyin, kana_distractors, parse_pinyin, pinyin_distractors,
    tone_pattern, tone_pattern_distractors,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_core(**overrides) -> dict:
    core = {
        'definition': 'a hot drink made from roasted beans',
        'pronunciation': 'kā fēi (ka1 fei1)',
        'semantic_class': 'concrete',
        'morphological_forms': [],
        'sentences': [
            {'text': '我每天早上喝咖啡。', 'target_word': '咖啡',
             'complexity_tier': 'A1'}
            for _ in range(10)
        ],
    }
    core.update(overrides)
    return core


def make_ctx(**overrides) -> det.SenseContext:
    core = overrides.pop('core', None) or make_core()
    kwargs = {
        'sense_id': 1,
        'language_id': 1,
        'lemma': '咖啡',
        'core': core,
        'semantic_class': 'concrete',
        'tier': 'A1',
        'pronunciation': core.get('pronunciation'),
        'definition': core.get('definition'),
        'db': None,
        'sentence_assignments': {1: 0, 4: 1, 9: 5},
    }
    kwargs.update(overrides)
    return det.SenseContext(**kwargs)


@pytest.fixture(autouse=True)
def clean_caches():
    """Every test owns its own lexicon/dictionary state."""
    lexmod.reset_cache()
    dictmod.reset_cache()
    yield
    lexmod.reset_cache()
    dictmod.reset_cache()


def install_lexicon(language_id: int, rows: list[tuple], components=None):
    """Seed the lexicon cache directly, bypassing the database."""
    lex = lexmod.Lexicon(language_id=language_id)
    for idx, (lemma, pron, definition, tier, freq) in enumerate(rows, start=100):
        entry = lexmod.LexEntry(
            sense_id=idx, lemma=lemma, definition=definition,
            pronunciation=pron, reading_key=lexmod.normalise_reading(pron),
            tier=tier, frequency=freq, semantic_class='concrete', sense_rank=1,
        )
        lex.entries.append(entry)
        if entry.reading_key:
            lex.by_reading.setdefault(entry.reading_key, []).append(entry)
            lex.lemma_readings.setdefault(lemma, set()).add(entry.reading_key)
        lex.by_lemma.setdefault(lemma, entry)
    lex.components = components or {}
    lexmod._cache[language_id] = lex
    return lex


def install_dictionary(kind: str, language_id: int, words, pairs):
    index = dictmod.MeasureIndex(kind=kind, language_id=language_id)
    for wid, form, reading, label, group_id, group_label, tier in words:
        index.words[wid] = dictmod.MeasureWord(
            id=wid, form=form, reading=reading, semantic_label=label,
            group_id=group_id, group_label=group_label, difficulty_tier=tier,
        )
        index.by_group.setdefault(group_id, []).append(wid)
    for lemma, wid in pairs:
        index.by_lemma.setdefault(lemma, []).append(wid)
    dictmod._cache[(kind, language_id)] = index
    return index


# ---------------------------------------------------------------------------
# phonology — the confusion sets
# ---------------------------------------------------------------------------

def test_pinyin_parses_both_notations():
    """The corpus stores marked and numbered forms in one string."""
    assert format_pinyin(parse_pinyin('kā fēi (ka1 fei1)')) == 'kā fēi'
    assert format_pinyin(parse_pinyin('nǐ hǎo')) == 'nǐ hǎo'
    assert parse_pinyin('') == []
    assert parse_pinyin('not pinyin at all!!') == []


@pytest.mark.parametrize('pron,expected_base', [
    ('xíng (xing2)', 'xing'),      # 行 — the classic polyphone
    ('chóng (chong2)', 'chong'),   # 重 — the other one
])
def test_pinyin_distractors_are_tone_variants_first(pron, expected_base):
    """Rule 1: tone is the Mandarin error, so it outranks segment swaps."""
    syllables = parse_pinyin(pron)
    distractors = pinyin_distractors(syllables, 3)
    assert len(distractors) == 3
    assert format_pinyin(syllables) not in distractors
    assert len(set(distractors)) == 3
    for candidate in distractors:
        parsed = parse_pinyin(candidate)
        assert parsed and parsed[0].base == expected_base


def test_polysyllable_distractors_vary_different_syllables():
    """Three tone variants of the final syllable would let the learner ignore
    the rest of the word."""
    syllables = parse_pinyin('zhòng yào (zhong4 yao4)')
    distractors = pinyin_distractors(syllables, 3)
    patterns = {tone_pattern(parse_pinyin(d)) for d in distractors}
    changed = {i for p in patterns for i in range(2) if p[i] != '4'}
    assert changed == {0, 1}, distractors


def test_tone_pattern_distractors_are_single_perturbations():
    syllables = parse_pinyin('kā fēi (ka1 fei1)')
    assert tone_pattern(syllables) == '11'
    out = tone_pattern_distractors(syllables, 3)
    assert '11' not in out
    for pattern in out:
        assert sum(1 for a, b in zip(pattern, '11') if a != b) == 1, pattern


@pytest.mark.parametrize('reading,expected', [
    ('がっこう', 'がっこ'),        # long vowel dropped, not doubled
    ('せんせい', 'せんせ'),
])
def test_kana_shortening_beats_lengthening(reading, expected):
    """A word that already has a long vowel gets the *shortened* foil; a naive
    right-to-left pass produced がっこうう instead."""
    assert expected in kana_distractors(reading, 3)


def test_kana_distractors_include_voicing_first():
    out = kana_distractors('ほん', 3)
    assert out[0] in ('ぼん', 'ぽん')
    assert 'ほん' not in out


def test_sokuon_only_before_voiceless_obstruents():
    """っ before a voiced consonant is unpronounceable, not confusable."""
    voiceless = 'かきくけこさしすせそたちつてとぱぴぷぺぽはひふへほ'
    for candidate in kana_distractors('たべる', 6):
        idx = candidate.find('っ')
        if idx >= 0 and idx + 1 < len(candidate):
            assert candidate[idx + 1] in voiceless


def test_kanji_input_yields_no_kana_distractors():
    """A reading column that was never backfilled must not become an exercise."""
    assert kana_distractors('学校') == []


# ---------------------------------------------------------------------------
# definition_match — the tier guard
# ---------------------------------------------------------------------------

def test_definition_match_prefers_words_of_similar_frequency():
    """The difficulty guard: common words beside common words.

    The pipeline's ``tier`` (a sentence label like T1/T3/T6) never equals a
    lexicon entry's tier, so the guard now keys on word frequency instead.
    """
    install_lexicon(1, [
        ('咖啡', 'kā fēi (ka1 fei1)', 'a hot drink made from roasted beans', 'A1', 5.0),
        ('茶', 'chá (cha2)', 'a drink made from leaves, hot', 'A1', 5.2),
        ('水', 'shuǐ (shui3)', 'clear liquid that you drink daily', 'A1', 4.8),
        ('牛奶', 'niú nǎi (niu2 nai3)', 'white drink that comes from cows', 'A1', 5.5),
        ('嗜热菌群', 'shì rè (shi4 re4)', 'thermophilic microbial community, rare', 'C2', 0.3),
    ])
    ctx = make_ctx(db=object(), tier='T3')   # tier is irrelevant to the match
    items, skips = det.generate(ctx, type_codes={'definition_match'})
    assert len(items) == 1, skips
    block = items[0].content['nl']['en']
    assert 'thermophilic microbial community, rare' not in block['options']
    assert block['correct_answer'] in block['options']


def test_definition_match_keeps_distractor_length_comparable_to_the_key():
    """An option three times longer than its neighbours gives the answer away."""
    long_def = 'a very long and elaborate definition ' * 4
    install_lexicon(1, [
        ('咖啡', 'kā fēi (ka1 fei1)', 'a hot drink made from roasted beans', 'A1', 5.0),
        ('茶', 'chá (cha2)', 'a drink made from leaves, hot', 'A1', 5.2),
        ('水', 'shuǐ (shui3)', 'clear liquid that you drink daily', 'A1', 4.8),
        ('牛奶', 'niú nǎi (niu2 nai3)', 'white drink that comes from cows', 'A1', 5.5),
        ('酒', 'jiǔ (jiu3)', long_def, 'A1', 5.1),
    ])
    items, skips = det.generate(make_ctx(db=object()), type_codes={'definition_match'})
    assert len(items) == 1, skips
    assert long_def not in items[0].content['nl']['en']['options']


def test_definition_match_loosens_in_stages_when_the_tight_pool_is_thin():
    """One item slightly off beats no item at all — but the tight picks come first."""
    install_lexicon(1, [
        ('咖啡', 'kā fēi (ka1 fei1)', 'a hot drink made from roasted beans', 'A1', 5.0),
        ('茶', 'chá (cha2)', 'a drink made from leaves, hot', 'A1', 5.2),     # near
        ('水', 'shuǐ (shui3)', 'clear liquid that you drink daily', 'A1', 2.0),   # far
        ('牛奶', 'niú nǎi (niu2 nai3)', 'white drink that comes from cows', 'A1', 1.0),  # far
    ])
    items, skips = det.generate(make_ctx(db=object()), type_codes={'definition_match'})
    assert len(items) == 1, skips
    assert len(items[0].content['nl']['en']['options']) == 4


def test_lexicon_definitions_near_orders_tight_before_loose():
    lex = install_lexicon(1, [
        ('far', 'a', 'x' * 30, 'A1', 1.0),
        ('near', 'b', 'y' * 30, 'A1', 5.1),
        ('mid', 'c', 'z' * 30, 'A1', 6.5),
    ])
    got = lex.definitions_near(5.0, 'k' * 30, set(), count=2)
    assert got[0] == 'y' * 30                      # inside the 1.0 band
    assert set(got) == {'y' * 30, 'z' * 30}        # then the 2.0 band, not the far one
    assert lex.frequency_of(None, 'near') == 5.1
    assert lex.frequency_of(None, 'missing') is None


def test_definition_match_skips_with_a_reason_when_pool_is_empty():
    install_lexicon(1, [])
    ctx = make_ctx(db=object())
    items, skips = det.generate(ctx, type_codes={'definition_match'})
    assert items == []
    assert any(s.type_code == 'definition_match' and s.reason for s in skips)


def test_definition_match_uses_the_nl_envelope():
    """Definitions are native-language text and must not sit at the top level."""
    from services.exercise_generation.schemas.envelope import validate_envelope
    install_lexicon(1, [
        ('茶', 'chá (cha2)', 'd1', 'A1', 5.0),
        ('水', 'shuǐ (shui3)', 'd2', 'A1', 6.0),
        ('牛奶', 'niú nǎi (niu2 nai3)', 'd3', 'A1', 4.5),
    ])
    ctx = make_ctx(db=object(), tier='A1')
    items, _ = det.generate(ctx, type_codes={'definition_match'})
    assert validate_envelope(items[0].content, 'definition_match') == []


def test_definition_match_word_is_the_headword_not_the_inflected_target():
    """ja verbs: the sentence target is a stem (描い); the word shown beside the
    definitions must be the dictionary form (描く)."""
    install_lexicon(1, [
        ('茶', 'chá (cha2)', 'd1', 'A1', 5.0),
        ('水', 'shuǐ (shui3)', 'd2', 'A1', 6.0),
        ('牛奶', 'niú nǎi (niu2 nai3)', 'd3', 'A1', 4.5),
    ])
    ctx = make_ctx(db=object(), tier='A1', headword='咖啡馆')
    items, _ = det.generate(ctx, type_codes={'definition_match'})
    assert items[0].content['word'] == '咖啡馆'

    ctx = make_ctx(db=object(), tier='A1')  # no headword: sentence target wins
    items, _ = det.generate(ctx, type_codes={'definition_match'})
    assert items[0].content['word'] == '咖啡'


def test_definition_match_shows_kana_for_rare_ja_spellings():
    from services.vocabulary_ladder.deterministic.definition_match import display_word
    assert display_word('為る', 3) == 'する'
    assert display_word('軈て', 3) == 'やがて'
    assert display_word('描く', 3) == '描く'      # ordinary kanji word: unchanged
    assert display_word('為る', 1) == '為る'      # only ja has the table

    install_lexicon(3, [
        ('水', 'みず', '飲み物として使う、透明な液体。', 'A1', 6.0),
        ('茶', 'ちゃ', '葉を煮出して作る、飲み物。', 'A1', 5.0),
        ('牛乳', 'ぎゅうにゅう', '牛から取れる、白い飲み物。', 'A1', 4.5),
    ])
    core = make_core(definition='ある動作をする。')
    ctx = make_ctx(db=object(), language_id=3, tier='A1', core=core,
                   definition=core['definition'], headword='為る')
    items, _ = det.generate(ctx, type_codes={'definition_match'})
    assert items[0].content['word'] == 'する'


def test_definition_match_never_mixes_definition_scripts():
    """A pool polluted with English glosses must not leak into a Japanese item."""
    from services.exercise_generation.schemas.envelope import validate_envelope
    install_lexicon(3, [
        ('水', 'みず', '飲み物として使う、透明な液体。', 'A1', 6.0),
        ('茶', 'ちゃ', '葉を煮出して作る、飲み物。', 'A1', 5.0),
        ('牛乳', 'ぎゅうにゅう', '牛から取れる、白い飲み物。', 'A1', 4.5),
        ('犬', 'いぬ', 'a dog', 'A1', 5.5),
        ('猫', 'ねこ', 'a cat', 'A1', 5.2),
    ])
    core = make_core(definition='豆から作る、温かい飲み物。')
    ctx = make_ctx(db=object(), language_id=3, tier='A1', core=core,
                   definition=core['definition'])
    items, skips = det.generate(ctx, type_codes={'definition_match'})
    assert len(items) == 1, skips
    block = items[0].content['nl']['en']
    assert 'a dog' not in block['options'] and 'a cat' not in block['options']
    assert validate_envelope(items[0].content, 'definition_match') == []


def test_definition_match_skips_rather_than_pad_with_foreign_definitions():
    install_lexicon(3, [
        ('水', 'みず', '飲み物として使う、透明な液体。', 'A1', 6.0),
        ('犬', 'いぬ', 'a dog', 'A1', 5.5),
        ('猫', 'ねこ', 'a cat', 'A1', 5.2),
        ('鳥', 'とり', 'a bird', 'A1', 5.0),
    ])
    core = make_core(definition='豆から作る、温かい飲み物。')
    ctx = make_ctx(db=object(), language_id=3, tier='A1', core=core,
                   definition=core['definition'])
    items, skips = det.generate(ctx, type_codes={'definition_match'})
    assert items == []
    assert any(s.type_code == 'definition_match' and s.reason for s in skips)


# ---------------------------------------------------------------------------
# readings — both directions (TASK-516 / TASK-529)
# ---------------------------------------------------------------------------

def test_reverse_direction_prefers_real_homophones():
    """张/章 share zhāng; 掌 (zhǎng) does not and must not be a homophone foil."""
    install_lexicon(1, [
        ('张', 'zhāng (zhang1)', 'to open', 'A1', 5.0),
        ('章', 'zhāng (zhang1)', 'a chapter', 'A2', 4.0),
        ('掌', 'zhǎng (zhang3)', 'palm', 'B1', 3.5),
        ('招', 'zhāo (zhao1)', 'to beckon', 'B1', 3.9),
    ])
    ctx = make_ctx(db=object(), lemma='张', sense_id=7,
                   core=make_core(pronunciation='zhāng (zhang1)'),
                   pronunciation='zhāng (zhang1)')
    items, skips = det.generate(ctx, type_codes={'pinyin_to_hanzi'})
    assert len(items) == 1, skips
    content = items[0].content
    assert content['correct_answer'] == '张'
    assert '章' in content['options']
    assert content['distractor_sources']['章'] == 'homophone'
    homophone_foils = [
        o for o, src in content['distractor_sources'].items()
        if src == 'homophone'
    ]
    assert '掌' not in homophone_foils


def test_reverse_direction_pads_from_components_when_homophones_are_sparse():
    install_lexicon(
        1,
        [
            ('张', 'zhāng (zhang1)', 'to open', 'A1', 5.0),
            ('掌', 'zhǎng (zhang3)', 'palm', 'B1', 3.5),
            ('长', 'cháng (chang2)', 'long', 'A1', 5.5),
            ('帐', 'zhàng (zhang4)', 'a curtain', 'B2', 3.2),
        ],
        components={
            '张': {'弓', '长'}, '掌': {'手', '尚'},
            '长': {'长'}, '帐': {'巾', '长'},
        },
    )
    ctx = make_ctx(db=object(), lemma='张', sense_id=7,
                   core=make_core(pronunciation='zhāng (zhang1)'),
                   pronunciation='zhāng (zhang1)')
    items, skips = det.generate(ctx, type_codes={'pinyin_to_hanzi'})
    assert len(items) == 1, skips
    sources = items[0].content['distractor_sources']
    assert 'component' in sources.values()
    assert '张' not in sources


def test_polyphone_items_carry_their_context_sentence():
    """'What is the reading of 行?' has no answer without a sentence."""
    install_lexicon(1, [
        ('行', 'xíng (xing2)', 'to walk', 'A2', 5.0),
        ('行', 'háng (hang2)', 'a row, a trade', 'B1', 4.5),
    ])
    core = make_core(
        pronunciation='xíng (xing2)',
        sentences=[{'text': '这条路很好行。', 'target_word': '行',
                    'complexity_tier': 'A2'}] * 10,
    )
    ctx = make_ctx(db=object(), lemma='行', core=core,
                   pronunciation='xíng (xing2)')
    items, _ = det.generate(ctx, type_codes={'hanzi_to_pinyin'})
    assert items[0].content['is_polyphonic'] is True
    assert items[0].content['context_sentence'] == '这条路很好行。'


def test_non_polyphone_items_have_no_context_sentence():
    install_lexicon(1, [('咖啡', 'kā fēi (ka1 fei1)', 'coffee', 'A1', 4.0)])
    ctx = make_ctx(db=object())
    items, _ = det.generate(ctx, type_codes={'hanzi_to_pinyin'})
    assert 'context_sentence' not in items[0].content


def test_kana_only_lemma_skips_the_reading_exercise():
    install_lexicon(3, [('ひと', 'ひと', 'person', 'A1', 6.0)])
    ctx = make_ctx(db=object(), language_id=3, lemma='ひと',
                   core=make_core(pronunciation='ひと'), pronunciation='ひと')
    items, skips = det.generate(ctx, type_codes={'kanji_to_reading'})
    assert items == []
    assert any('no kanji' in s.reason for s in skips)


# ---------------------------------------------------------------------------
# Coverage-gap fix #4: `SenseContext.headword` vs `.lemma` for the ja kanji
# reading pair. `.lemma` is a SENTENCE's target (the inflected surface form
# of whichever sentence happens to be first), which for a verb like 因る can
# legitimately be a kana-only inflection (よって) with no kanji at all —
# `has_kanji(ctx.lemma)` then false-negatives even though the dictionary
# headword plainly has kanji. `.headword` carries the dictionary form
# (mirrors exercise_renderer._headword's existing TASK-803 rationale for L1).
# ---------------------------------------------------------------------------

def test_kanji_to_reading_uses_headword_when_lemma_is_a_kana_only_inflection():
    """Regression for ja sense 35111 (因る): the first P1 sentence's target
    was a kana-only inflected form, so `ctx.lemma` alone has no kanji even
    though the word plainly does -- the exercise must not be skipped."""
    ctx = make_ctx(
        db=object(), language_id=3, lemma='よって', headword='因る',
        core=make_core(pronunciation='よる'), pronunciation='よる',
    )
    items, skips = det.generate(ctx, type_codes={'kanji_to_reading'})
    assert not any('no kanji' in s.reason for s in skips), skips
    if items:
        assert items[0].content['prompt'] == '因る'


def test_kanji_to_reading_falls_back_to_lemma_when_headword_is_absent():
    """Parity guard: omitting `headword` (every pre-existing caller/fixture)
    keeps the prior behaviour exactly -- a kana-only `.lemma` still skips."""
    ctx = make_ctx(
        db=object(), language_id=3, lemma='よって',
        core=make_core(pronunciation='よる'), pronunciation='よる',
    )
    assert ctx.headword is None
    items, skips = det.generate(ctx, type_codes={'kanji_to_reading'})
    assert items == []
    assert any('no kanji' in s.reason for s in skips)


def test_reading_to_kanji_also_uses_headword_for_the_has_kanji_gate():
    install_lexicon(3, [('因る', 'よる', 'to be due to', 'B1', 3.0)])
    ctx = make_ctx(
        db=object(), language_id=3, lemma='よって', headword='因る',
        core=make_core(pronunciation='よる'), pronunciation='よる',
    )
    items, skips = det.generate(ctx, type_codes={'reading_to_kanji'})
    assert not any('no kanji' in s.reason for s in skips), skips


# ---------------------------------------------------------------------------
# classifier_match / counter_match (TASK-528 / TASK-530)
# ---------------------------------------------------------------------------

CONTAINER_WORDS = [
    (1, '杯', 'bēi', 'cup-shaped containers', 10, 'containers', 1),
    (2, '瓶', 'píng', 'bottles', 10, 'containers', 1),
    (3, '包', 'bāo', 'packets', 10, 'containers', 2),
    (4, '盒', 'hé', 'boxes', 10, 'containers', 2),
    (5, '本', 'běn', 'bound volumes', 20, 'flat-bound', 1),
    (99, '个', 'gè', 'general', 30, 'general', 1),
]


def test_classifier_match_uses_semantic_group_distractors():
    install_dictionary('classifier', 1, CONTAINER_WORDS, [('咖啡', 1)])
    ctx = make_ctx(db=object())
    items, skips = det.generate(ctx, type_codes={'classifier_match'})
    assert len(items) == 1, skips
    content = items[0].content
    assert content['correct_answer'] == '杯'
    assert set(content['options']) <= {'杯', '瓶', '包', '盒'}
    assert len(content['options']) == 4


def test_classifier_match_never_offers_ge():
    """个 is the 'when in doubt' answer; offering it makes the item free."""
    install_dictionary('classifier', 1, CONTAINER_WORDS,
                       [('咖啡', 1), ('咖啡', 99)])
    ctx = make_ctx(db=object())
    items, _ = det.generate(ctx, type_codes={'classifier_match'})
    assert '个' not in items[0].content['options']
    assert '个' not in items[0].content['accepted_answers']


def test_classifier_match_keeps_every_acceptable_answer():
    install_dictionary('classifier', 1, CONTAINER_WORDS,
                       [('咖啡', 1), ('咖啡', 3)])
    ctx = make_ctx(db=object())
    items, _ = det.generate(ctx, type_codes={'classifier_match'})
    assert set(items[0].content['accepted_answers']) == {'杯', '包'}


def test_classifier_match_skips_nouns_absent_from_the_dictionary():
    install_dictionary('classifier', 1, CONTAINER_WORDS, [('书', 5)])
    ctx = make_ctx(db=object())
    items, skips = det.generate(ctx, type_codes={'classifier_match'})
    assert items == []
    assert any('not in the classifier dictionary' in s.reason for s in skips)


def test_counter_match_mirrors_classifier_behaviour():
    install_dictionary('counter', 3, [
        (1, '本', 'ほん', 'long thin objects', 10, 'long-thin', 1),
        (2, '枚', 'まい', 'flat objects', 20, 'flat', 1),
        (3, '匹', 'ひき', 'small animals', 30, 'animals', 1),
        (4, '台', 'だい', 'machines', 40, 'machines', 1),
        (5, '冊', 'さつ', 'bound volumes', 20, 'flat', 2),
    ], [('鉛筆', 1)])
    ctx = make_ctx(db=object(), language_id=3, lemma='鉛筆',
                   core=make_core(pronunciation='えんぴつ'),
                   pronunciation='えんぴつ')
    items, skips = det.generate(ctx, type_codes={'counter_match'})
    assert len(items) == 1, skips
    assert items[0].content['correct_answer'] == '本'
    assert len(items[0].content['options']) == 4


# ---------------------------------------------------------------------------
# cloze_typed (TASK-532)
# ---------------------------------------------------------------------------

def test_cloze_typed_blanks_the_target_and_stores_normalisation():
    ctx = make_ctx()
    items, skips = det.generate(ctx, type_codes={'cloze_typed'})
    assert len(items) == 1, skips
    content = items[0].content
    assert content['sentence_with_blank'] == '我每天早上喝___。'
    assert content['answer']['accepted'] == ['咖啡']
    assert content['normalization']['script'] == 't2s'
    assert content['input_mode'] == 'ime'


def test_cloze_typed_admits_variants_only_for_an_uninflected_slot():
    inflected = make_core(sentences=[
        {'text': 'Yesterday I ran home.', 'target_word': 'ran',
         'complexity_tier': 'A2'}] * 10)
    inflected['morphological_forms'] = [{'form': 'run'}, {'form': 'running'}]
    ctx = make_ctx(language_id=2, lemma='run', core=inflected,
                   pronunciation=None, semantic_class='action')
    items, _ = det.generate(ctx, type_codes={'cloze_typed'})
    assert items[0].content['answer']['accepted'] == ['ran']

    bare = make_core(sentences=[
        {'text': 'I run home every day.', 'target_word': 'run',
         'complexity_tier': 'A2'}] * 10)
    bare['morphological_forms'] = [{'form': 'ran'}, {'form': 'running'}]
    ctx = make_ctx(language_id=2, lemma='run', core=bare,
                   pronunciation=None, semantic_class='action')
    items, _ = det.generate(ctx, type_codes={'cloze_typed'})
    assert set(items[0].content['answer']['accepted']) == {'run', 'ran', 'running'}


# ---------------------------------------------------------------------------
# cloze_typed accepted-answer defects (TASK follow-up bug #2)
#
# Real failing items from data/eval/runs/phase1_ja/*.json.
# ---------------------------------------------------------------------------

def test_cloze_typed_drops_counter_and_derivation_labelled_forms():
    """Real eval-run bug, ja sense 35001: morphological_forms carried a
    measure-word counter ('台', labelled 助数詞) and a derived compound
    ('機械式', labelled 派生) alongside the noun itself. Neither is a
    grammatical substitute in a bare-noun slot ('機械が動いています' with
    '台' spliced in is nonsense), so both must be dropped."""
    core = make_core(sentences=[
        {'text': '機械が動いています。', 'target_word': '機械',
         'complexity_tier': 'B1'}] * 10)
    core['morphological_forms'] = [
        {'form': '台', 'label': '助数詞'},
        {'form': '機械式', 'label': '派生'},
    ]
    ctx = make_ctx(language_id=3, lemma='機械', core=core,
                    pronunciation=None, semantic_class='concrete')
    items, skips = det.generate(ctx, type_codes={'cloze_typed'})
    assert len(items) == 1, skips
    assert items[0].content['answer']['accepted'] == ['機械']


def test_cloze_typed_blocks_all_variants_when_sentence_continues_the_conjugation():
    """Real eval-run bug, ja sense 35017: the template bakes in the rest of
    the conjugation right after the blank ('___ています'), so every other
    活用 entry ('増えた', '増えて', '増えない', '増えています') is a
    DIFFERENT complete conjugation of the same verb, not a drop-in for this
    stem — splicing '増えています' in doubles the trailing 'ています'."""
    core = make_core(sentences=[
        {'text': '最近、ゴミの量が増えています。', 'target_word': '増え',
         'complexity_tier': 'B1'}] * 10)
    core['morphological_forms'] = [
        {'form': '増えた', 'label': '活用'},
        {'form': '増えて', 'label': '活用'},
        {'form': '増えない', 'label': '活用'},
        {'form': '増えています', 'label': '活用'},
    ]
    ctx = make_ctx(language_id=3, lemma='増え', core=core,
                    pronunciation=None, semantic_class='action')
    items, skips = det.generate(ctx, type_codes={'cloze_typed'})
    assert len(items) == 1, skips
    assert items[0].content['answer']['accepted'] == ['増え']


def test_cloze_typed_skips_when_target_has_no_clean_word_boundary_occurrence():
    """Same class of bug as the L3/L4 'workss' template glue (bug #3): if
    `target` is only a prefix of the word actually in the sentence, blanking
    it naively leaves a dangling suffix glued to the marker. cloze_typed must
    skip rather than ship 'Marcus ___s'."""
    core = make_core(sentences=[
        {'text': 'Marcus works today.', 'target_word': 'work',
         'complexity_tier': 'A2'}] * 10)
    ctx = make_ctx(language_id=2, lemma='work', core=core,
                    pronunciation=None, semantic_class='action')
    items, skips = det.generate(ctx, type_codes={'cloze_typed'})
    assert items == []
    reasons = [s.reason for s in skips if s.type_code == 'cloze_typed']
    assert any('clean word-boundary' in r for r in reasons), reasons


def test_cloze_typed_correct_answer_is_always_in_accepted():
    """Invariant the grading path (`grade()`) depends on: whatever ends up as
    `target_word` must be a member of `answer.accepted`, always."""
    ctx = make_ctx()
    items, skips = det.generate(ctx, type_codes={'cloze_typed'})
    assert len(items) == 1, skips
    content = items[0].content
    assert content['target_word'] in content['answer']['accepted']


# ---------------------------------------------------------------------------
# jumbled_sentence (TASK-516)
# ---------------------------------------------------------------------------

def test_jumbled_skips_a_sentence_it_cannot_chunk():
    core = make_core(sentences=[
        {'text': '好。', 'target_word': '好', 'complexity_tier': 'A1'}] * 10)
    ctx = make_ctx(core=core, lemma='好')
    items, skips = det.generate(ctx, type_codes={'jumbled_sentence'})
    assert items == []
    assert any(s.type_code == 'jumbled_sentence' for s in skips)


def test_jumbled_shuffle_never_equals_the_answer():
    ctx = make_ctx()
    items, _ = det.generate(ctx, type_codes={'jumbled_sentence'})
    if items:                       # depends on the ZH chunker being installed
        content = items[0].content
        assert content['shuffled_chunks'] != content['chunks']
        assert sorted(content['shuffled_chunks']) == sorted(content['chunks'])


# ---------------------------------------------------------------------------
# jumbled_sentence reconstruction invariant (TASK follow-up bug #1)
#
# Real failing items from data/eval/runs/phase1_en/16031.json (en sense
# 16031): the chunker produced chunks ('will waterlog', 'quickly', 'it')
# whose stored "correct" order concatenates to "will waterlog quickly it",
# not the source sentence's actual word order. Fixed by having `build()`
# verify the reconstruction itself and skip rather than trust the chunker.
# ---------------------------------------------------------------------------

from services.vocabulary_ladder.deterministic import jumbled as jumbled_mod  # noqa: E402


def test_jumbled_skips_when_chunks_do_not_reconstruct_the_source_sentence(monkeypatch):
    original = 'It will quickly waterlog the field.'
    broken_chunks = ['will waterlog', 'quickly', 'it']  # real eval-run bug

    monkeypatch.setattr(jumbled_mod, '_chunk', lambda text, lang: broken_chunks)

    core = make_core(sentences=[
        {'text': original, 'target_word': 'waterlog', 'complexity_tier': 'B1'},
    ] * 10)
    ctx = make_ctx(language_id=2, lemma='waterlog', core=core,
                    pronunciation=None, semantic_class='action',
                    sentence_assignments={9: 0})
    items, skips = det.generate(ctx, type_codes={'jumbled_sentence'})
    assert items == []
    reasons = [s.reason for s in skips if s.type_code == 'jumbled_sentence']
    assert any('reconstruct' in r for r in reasons), reasons


def test_jumbled_accepts_chunks_that_do_reconstruct_modulo_punctuation(monkeypatch):
    """The source sentence's trailing period is not part of any chunk (the
    chunker drops punctuation); the invariant check must not reject a
    perfectly good reconstruction over that."""
    original = 'It will quickly waterlog the field.'
    good_chunks = ['It', 'will quickly waterlog', 'the field']

    monkeypatch.setattr(jumbled_mod, '_chunk', lambda text, lang: good_chunks)

    core = make_core(sentences=[
        {'text': original, 'target_word': 'waterlog', 'complexity_tier': 'B1'},
    ] * 10)
    ctx = make_ctx(language_id=2, lemma='waterlog', core=core,
                    pronunciation=None, semantic_class='action',
                    sentence_assignments={9: 0})
    items, skips = det.generate(ctx, type_codes={'jumbled_sentence'})
    assert len(items) == 1, skips
    assert items[0].content['chunks'] == good_chunks


def test_jumbled_merge_never_fuses_the_target_word_into_a_neighbour():
    """Real eval-run bug (ja sense 34998): the shortest-adjacent-pair merge
    picked the one-character target '一' and fused it with the adjacent '二',
    producing a chunk ('一二') that reads as a different token entirely."""
    chunks = ['一', '二', '三四五', '六七八', '九十']
    merged = jumbled_mod._merge_to(chunks, limit=4, target='一')
    assert merged is not None
    assert '一' in merged
    assert all('一二' not in c for c in merged)


def test_jumbled_merge_returns_none_when_every_option_fuses_the_target():
    """If the target chunk has only one possible merge partner left, and
    using it is the only way to reach the chunk-count limit, bail rather
    than silently fuse the target."""
    merged = jumbled_mod._merge_to(['一', '二'], limit=1, target='一')
    assert merged is None


def test_jumbled_target_isolated_check_rejects_fused_chunk():
    assert jumbled_mod._target_is_isolated(['一二', '三'], '一', language_id=1) is False
    assert jumbled_mod._target_is_isolated(['一', '二', '三'], '一', language_id=1) is True


def test_jumbled_normalize_for_check_strips_punctuation_not_words():
    assert (
        jumbled_mod._normalize_for_check('It will quickly waterlog the field.')
        == jumbled_mod._normalize_for_check('It will quickly waterlog the field')
    )
    assert (
        jumbled_mod._normalize_for_check('会いましょう。')
        == jumbled_mod._normalize_for_check('会いましょう')
    )


# ---------------------------------------------------------------------------
# Framework contracts
# ---------------------------------------------------------------------------

def test_no_builder_calls_an_llm():
    """The whole value of this package is that it costs nothing to run."""
    import ast
    import pathlib
    package = pathlib.Path('services/vocabulary_ladder/deterministic')
    offenders = []
    for path in sorted(package.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [
                    getattr(node, 'module', '') or '',
                    *[a.name for a in node.names],
                ]
                if any('llm' in n.lower() or 'prompt_service' in n for n in names):
                    offenders.append(f'{path.name}: {names}')
    assert offenders == [], offenders


def test_every_deterministic_matrix_row_has_a_builder_or_is_serve_time():
    """A matrix row promising a deterministic type with nothing behind it
    silently produces no exercises for that family."""
    from services.vocabulary_ladder.config import CAPABILITY_MATRIX
    declared = {
        cap['type_code'] for cap in CAPABILITY_MATRIX
        if cap['generator'] == 'deterministic' and cap['is_enabled']
    }
    # Composed at serve time rather than rendered into rows.
    serve_time = {'text_flashcard', 'listening_flashcard', 'timed_speed_round'}
    assert declared - det.registered_types() - serve_time == set()


def test_a_raising_builder_costs_one_type_not_the_sense():
    def _boom(ctx, skips):
        raise RuntimeError('kaboom')

    det.registered_types()          # force the lazy import first
    det._REGISTRY['__test_explodes'] = _boom
    try:
        ctx = make_ctx()
        items, _ = det.generate(ctx, type_codes={'definition_match'} and None)
        assert any(i.type_code == 'hanzi_to_pinyin' for i in items)
    finally:
        det._REGISTRY.pop('__test_explodes', None)
