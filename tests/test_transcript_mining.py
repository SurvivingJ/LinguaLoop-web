"""TASK-513 — transcript mining as a P1 sentence source.

What this replaces: ``_fetch_corpus_sentences`` used to pull 50 arbitrary
transcripts plus 30 conversations and substring-match the bare lemma. It could
not distinguish one sense of a word from another, and its fixed window meant a
common word could be all over the corpus and still be missed.

Mining now goes through the index built for the question —
``tests.vocab_sense_ids`` via the ``tests_containing_sense`` RPC, with
``tests.vocab_token_map`` supplying the surface forms that realise the sense.

Covered here:
  - the RPC is the entry point, and its failure degrades to "generate all"
  - sense discrimination: another sense's tokens are not mined
  - CJK matching goes through the tokeniser, never ``\\b``
  - markup stripping, dedup, and the TASK-524 tier screen
  - provenance: ``sentence_source`` per sentence, echoed into exercise tags

No LLM, no Supabase: the db handle is a stub and the RPC returns fixtures.
"""

from services.vocabulary_ladder import exercise_renderer as rendermod
from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3

SENSE = 42
OTHER_SENSE = 99


# ---------------------------------------------------------------------------
# Stub Supabase surface
# ---------------------------------------------------------------------------

class _RpcResult:
    def __init__(self, data):
        self.data = data


class _RpcBuilder:
    """Mirrors postgrest-py: ``db.rpc(name, params).execute()``."""

    def __init__(self, rows, error):
        self._rows = rows
        self._error = error

    def execute(self):
        if self._error:
            raise self._error
        return _RpcResult(self._rows)


class _StubDb:
    """Just enough of the Supabase client for the mining path."""

    def __init__(self, rows, rpc_error=None):
        self.rows = rows
        self.rpc_error = rpc_error
        self.rpc_calls: list[tuple[str, dict]] = []

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        return _RpcBuilder(self.rows, self.rpc_error)


def _pipeline(rows, rpc_error=None, lemma='run'):
    p = VocabAssetPipeline.__new__(VocabAssetPipeline)
    p.db = _StubDb(rows, rpc_error)
    p._lemma_for_sense = lambda sense_id: lemma
    return p


def _test_row(transcript, token_map, test_id='t-1', difficulty=2):
    return {
        'id': test_id,
        'transcript': transcript,
        'vocab_token_map': token_map,
        'difficulty': difficulty,
    }


# ---------------------------------------------------------------------------
# vocab_token_map parsing
# ---------------------------------------------------------------------------

def test_token_map_pair_shape():
    tokens = VocabAssetPipeline._sense_surface_tokens(
        [['ran', SENSE], ['running', SENSE], ['walked', OTHER_SENSE]], SENSE,
    )
    assert tokens == ['ran', 'running']


def test_token_map_object_shape():
    tokens = VocabAssetPipeline._sense_surface_tokens(
        [{'token': 'ran', 'sense_id': SENSE},
         {'text': 'runs', 'sense_id': SENSE},
         {'token': 'walked', 'sense_id': OTHER_SENSE}], SENSE,
    )
    assert tokens == ['ran', 'runs']


def test_token_map_deduplicates_and_survives_junk():
    tokens = VocabAssetPipeline._sense_surface_tokens(
        [['ran', SENSE], ['ran', SENSE], None, 'garbage', ['x'], {}], SENSE,
    )
    assert tokens == ['ran']


def test_token_map_empty_inputs():
    assert VocabAssetPipeline._sense_surface_tokens(None, SENSE) == []
    assert VocabAssetPipeline._sense_surface_tokens([], SENSE) == []


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------

def test_mining_uses_the_sense_index_rpc():
    p = _pipeline([])
    p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert p.db.rpc_calls == [
        ('tests_containing_sense',
         {'p_sense_id': SENSE, 'p_language_id': LANG_EN}),
    ]


def test_mining_extracts_the_sentences_holding_the_sense_token():
    transcript = (
        'The meeting was long. She had to run to the station every day. '
        'Everyone went home.'
    )
    p = _pipeline([_test_row(transcript, [['run', SENSE]])])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert len(mined) == 1
    assert 'run to the station' in mined[0]['text']
    assert mined[0]['target_word'] == 'run'
    assert mined[0]['sentence_source'] == 'mined'
    assert mined[0]['source'] == 'transcript'
    assert mined[0]['test_id'] == 't-1'


def test_mining_ignores_another_senses_tokens():
    """The whole point of going through vocab_token_map."""
    transcript = 'She had to run to the station. They walked home slowly.'
    p = _pipeline([_test_row(
        transcript, [['run', SENSE], ['walked', OTHER_SENSE]],
    )])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert len(mined) == 1
    assert 'walked' not in mined[0]['text']


def test_mining_falls_back_to_the_lemma_when_the_token_map_is_silent():
    """The sense is indexed on the test but no surface form was recorded."""
    transcript = 'She had to run to the station every single day.'
    p = _pipeline([_test_row(transcript, [])])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert len(mined) == 1
    assert mined[0]['target_word'] == 'run'


def test_mining_strips_markdown_bold_leaking_from_the_corpus():
    transcript = 'She had to **run** to the station every single day.'
    p = _pipeline([_test_row(transcript, [['run', SENSE]])])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert mined
    assert '**' not in mined[0]['text']
    assert 'run' in mined[0]['text']


def test_mining_deduplicates_across_transcripts():
    sentence = 'She had to run to the station every single day.'
    p = _pipeline([
        _test_row(sentence, [['run', SENSE]], test_id='t-1'),
        _test_row(sentence, [['run', SENSE]], test_id='t-2'),
    ])

    assert len(p._fetch_corpus_sentences(SENSE, LANG_EN)) == 1


def test_mining_drops_sentences_the_tier_gate_rejects():
    """No point seeding P1 with a sentence TASK-524 will reject downstream."""
    good = 'She had to run to the station every single day.'
    off_tier = ('The peripatetic quaestor adjured the recalcitrant '
                'amanuensis to run posthaste.')
    p = _pipeline([_test_row(f'{good} {off_tier}', [['run', SENSE]])])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    texts = [m['text'] for m in mined]
    assert any('station' in t for t in texts)
    assert not any('quaestor' in t for t in texts)


def test_mining_caps_at_the_configured_sentence_budget():
    from config import Config

    sentences = ' '.join(
        f'She had to run to the station on day number {i}.' for i in range(40)
    )
    p = _pipeline([_test_row(sentences, [['run', SENSE]])])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert len(mined) <= Config.VOCAB_SENTENCES_PER_WORD


def test_mining_skips_very_short_fragments():
    p = _pipeline([_test_row('Run. She had to run to the station daily.',
                             [['run', SENSE]])])

    mined = p._fetch_corpus_sentences(SENSE, LANG_EN)

    assert all(len(m['text']) >= 10 for m in mined)


def test_mining_maps_test_difficulty_onto_a_complexity_tier():
    p = _pipeline([_test_row(
        'She had to run to the station every single day.',
        [['run', SENSE]], difficulty=5,
    )])

    assert p._fetch_corpus_sentences(SENSE, LANG_EN)[0]['complexity_tier'] == 'T6'


# ---------------------------------------------------------------------------
# CJK — tokenizer matching, never `\b` (AC)
# ---------------------------------------------------------------------------

def test_chinese_mining_matches_through_the_tokenizer():
    transcript = '今天天气很好。我每天早上都喝咖啡。然后我去上班。'
    p = _pipeline([_test_row(transcript, [['咖啡', SENSE]])], lemma='咖啡')

    mined = p._fetch_corpus_sentences(SENSE, LANG_ZH)

    assert len(mined) == 1
    assert '咖啡' in mined[0]['text']


def test_chinese_mining_rejects_an_in_token_substring():
    """``\\b`` cannot express this; the tokenizer can.

    咖啡 occurs only inside 咖啡馆 ("cafe"), a different word. A substring
    search would mine the sentence; whole-word matching must not.
    """
    transcript = '他昨天去了一家很有名的咖啡馆见朋友。'
    p = _pipeline([_test_row(transcript, [['咖啡', SENSE]])], lemma='咖啡')

    mined = p._fetch_corpus_sentences(SENSE, LANG_ZH)

    assert mined == []


def test_chinese_mining_recovers_a_verb_object_merge():
    """jieba merges 喝+咖啡 into one token; the sentence still attests 咖啡.

    Suffix position (merged phrase) is mined; prefix position (咖啡馆, a
    distinct lexeme) is not — see ``_mentions_token``.
    """
    from services.exercise_generation.language_processor import LanguageProcessor

    processor = LanguageProcessor.for_language(LANG_ZH)
    sentence = '我每天早上都喝咖啡。'
    assert '喝咖啡' in processor.tokenize(sentence), 'fixture assumption changed'

    assert VocabAssetPipeline._mentions_token(processor, sentence, '咖啡') is True
    assert VocabAssetPipeline._mentions_token(
        processor, '他去了那家咖啡馆。', '咖啡') is False


def test_the_merge_fallback_does_not_apply_to_english():
    """A substring fallback in EN would match 'run' inside 'running'."""
    from services.exercise_generation.language_processor import LanguageProcessor

    processor = LanguageProcessor.for_language(LANG_EN)

    assert VocabAssetPipeline._mentions_token(
        processor, 'She was running late today.', 'run') is False
    assert VocabAssetPipeline._mentions_token(
        processor, 'She had to run today.', 'run') is True


def test_mentions_token_handles_empty_input():
    from services.exercise_generation.language_processor import LanguageProcessor

    processor = LanguageProcessor.for_language(LANG_EN)
    assert VocabAssetPipeline._mentions_token(processor, '', 'run') is False
    assert VocabAssetPipeline._mentions_token(processor, 'text', '') is False


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------

def test_rpc_failure_degrades_to_generating_everything():
    p = _pipeline([], rpc_error=RuntimeError('connection reset'))

    assert p._fetch_corpus_sentences(SENSE, LANG_EN) == []


def test_no_matching_transcripts_returns_empty():
    assert _pipeline([])._fetch_corpus_sentences(SENSE, LANG_EN) == []


def test_unresolvable_lemma_returns_empty():
    p = _pipeline([_test_row('anything at all here', [])], lemma='')

    assert p._fetch_corpus_sentences(SENSE, LANG_EN) == []
    assert p.db.rpc_calls == [], 'no RPC spend without a lemma'


def test_blank_transcripts_are_skipped():
    p = _pipeline([_test_row('', [['run', SENSE]]),
                   _test_row(None, [['run', SENSE]], test_id='t-2')])

    assert p._fetch_corpus_sentences(SENSE, LANG_EN) == []


# ---------------------------------------------------------------------------
# Provenance — P1 tagging
# ---------------------------------------------------------------------------

def _tag(content, corpus):
    CoreAssetGenerator._tag_sentence_sources(content, corpus)
    return [s.get('sentence_source') for s in content['sentences']]


def test_seeded_sentences_come_back_labelled_mined():
    corpus = [{'text': 'She had to run to the station.'}]
    content = {'sentences': [
        {'text': 'She had to run to the station.'},
        {'text': 'He will run the marathon next spring.'},
    ]}

    assert _tag(content, corpus) == ['mined', 'generated']


def test_labelling_is_insensitive_to_whitespace_and_case():
    corpus = [{'text': 'She had to run to the station.'}]
    content = {'sentences': [{'text': '  she had  to run to the STATION.  '}]}

    assert _tag(content, corpus) == ['mined']


def test_a_rewritten_sentence_is_not_claimed_as_mined():
    """Conservative by design: a false 'mined' claims attestation it lacks."""
    corpus = [{'text': 'She had to run to the station.'}]
    content = {'sentences': [{'text': 'She had to run to the train station.'}]}

    assert _tag(content, corpus) == ['generated']


def test_labelling_with_no_seed_marks_everything_generated():
    content = {'sentences': [{'text': 'a'}, {'text': 'b'}]}
    assert _tag(content, []) == ['generated', 'generated']


def test_labelling_survives_malformed_content():
    for bad in ({}, {'sentences': None}, {'sentences': 'nope'},
                {'sentences': [None, 'x']}):
        CoreAssetGenerator._tag_sentence_sources(bad, [{'text': 'a'}])


# ---------------------------------------------------------------------------
# Provenance — echoed into exercise tags
# ---------------------------------------------------------------------------

def test_provenance_summarises_the_asset():
    prov = rendermod.LadderExerciseRenderer._sentence_provenance({'sentences': [
        {'text': 'a', 'sentence_source': 'mined'},
        {'text': 'b', 'sentence_source': 'generated'},
        {'text': 'c', 'sentence_source': 'generated'},
    ]})

    assert prov['sentence_sources'] == ['mined', 'generated', 'generated']
    assert prov['mined_count'] == 1
    assert prov['generated_count'] == 2


def test_provenance_is_absent_for_pre_task_513_assets():
    assert rendermod.LadderExerciseRenderer._sentence_provenance(
        {'sentences': [{'text': 'a'}]}) is None
    assert rendermod.LadderExerciseRenderer._sentence_provenance({}) is None


def test_rendered_rows_carry_the_provenance_block(monkeypatch):
    core = {
        'semantic_class': 'action',
        'definition': 'to move at speed',
        'pronunciation': 'rʌn',
        'morphological_forms': [{'form': 'ran', 'label': 'past'}],
        'sentences': [
            {'text': f'She had to run to stop {i}.', 'target_word': 'run',
             'complexity_tier': 'T2',
             'sentence_source': 'mined' if i == 0 else 'generated'}
            for i in range(10)
        ],
    }
    r = rendermod.LadderExerciseRenderer(db=object())
    monkeypatch.setattr(r, '_load_assets', lambda sid: {'prompt1_core': core})
    monkeypatch.setattr(r, '_load_asset_ids', lambda sid: {'prompt1_core': 'a-1'})
    monkeypatch.setattr(r, '_render_hant_mirror', lambda c, l: None)

    rows = r.build_rows(sense_id=1, language_id=LANG_EN)

    assert rows
    for row in rows:
        assert row['tags']['provenance']['mined_count'] == 1
