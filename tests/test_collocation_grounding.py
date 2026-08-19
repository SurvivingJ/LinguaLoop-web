"""TASK-523 — corpus grounding for the collocate P1 asserts (finding G6).

No network, no Supabase: the bundled list is written to a tmp_path and the
``corpus_collocations`` lookup is driven by a stub client.

The distinction the tests keep coming back to is ``llm_asserted`` vs
``no_source``. Collapsing the two would make Japanese — which has no frequency
source at all — report as 0% validated, which reads as a quality problem
rather than as an unmeasured language.
"""

import pytest

from services.vocabulary_ladder import collocation_grounding as cg
from services.vocabulary_ladder.collocation_grounding import (
    GROUNDING_ASSERTED, GROUNDING_CORPUS, GROUNDING_NO_SOURCE,
    SOURCE_CORPUS, SOURCE_LIST,
    BundledCollocationList, CollocationGrounder, ground_core_asset,
)

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _StubTable:
    """Minimal postgrest chain that returns fixed rows (or raises)."""

    def __init__(self, rows, raises=False):
        self._rows = rows
        self._raises = raises

    def select(self, *_a, **_k):
        return self

    eq = or_ = gte = order = limit = select

    def execute(self):
        if self._raises:
            raise RuntimeError('connection reset')
        return _Resp(self._rows)


class _StubDB:
    def __init__(self, rows=None, raises=False):
        self.rows = rows or []
        self.raises = raises

    def table(self, name):
        assert name in ('corpus_collocations', 'word_assets'), name
        return _StubTable(self.rows, self.raises)


@pytest.fixture(autouse=True)
def _clear_cache():
    cg.clear_list_cache()
    yield
    cg.clear_list_cache()


@pytest.fixture
def list_dir(tmp_path):
    """A data dir holding a small English collocation list."""
    path = tmp_path / 'en_collocations.tsv'
    path.write_text(
        '# comment line, ignored\n'
        'head\tcollocate\tfrequency\trelation\n'
        'make\tdecision\t48213\tverb_object\n'
        'strong\tcoffee\t9042\tadjective_noun\n'
        'faint\tcoffee\t2\tadjective_noun\n'          # below MIN_LIST_FREQUENCY
        'malformed row with no tabs\n'
        'brew\tcoffee\tnot-a-number\tverb_object\n',  # unparseable count
        encoding='utf-8',
    )
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Bundled list loading
# ---------------------------------------------------------------------------

def test_list_indexes_pairs_unordered(list_dir):
    loaded = cg.bundled_list(LANG_EN, list_dir)
    assert loaded.frequency('make', 'decision') == 48213
    # P1 never says which side is the head, so both orders are one fact.
    assert loaded.frequency('decision', 'make') == 48213
    assert loaded.frequency('DECISION', 'Make') == 48213


def test_list_skips_comments_headers_and_unparseable_rows(list_dir):
    loaded = cg.bundled_list(LANG_EN, list_dir)
    assert loaded.frequency('brew', 'coffee') is None
    assert loaded.frequency('head', 'collocate') is None
    assert len(loaded.pairs) == 3


def test_missing_list_is_a_supported_state_not_an_error(tmp_path):
    loaded = BundledCollocationList(path=str(tmp_path / 'absent.tsv')).load()
    assert loaded.pairs == {}
    assert loaded.loaded is True


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def test_bundled_list_hit_validates(list_dir):
    grounder = CollocationGrounder(db=None, data_dir=list_dir)
    result = grounder.validate('make', 'decision', LANG_EN)

    assert result.status == GROUNDING_CORPUS
    assert result.source == SOURCE_LIST
    assert result.validated
    assert result.score == 48213.0


def test_rare_list_pair_does_not_count_as_evidence(list_dir):
    """A long-tail count is a corpus artefact, not something to teach."""
    grounder = CollocationGrounder(db=None, data_dir=list_dir)
    assert grounder.validate('faint', 'coffee', LANG_EN).status == GROUNDING_ASSERTED


def test_corpus_pmi_hit_validates_when_the_list_misses(list_dir):
    db = _StubDB(rows=[{'pmi_score': 7.4, 'head_word': 'brew', 'collocate': 'coffee'}])
    grounder = CollocationGrounder(db=db, data_dir=list_dir)

    result = grounder.validate('brew', 'coffee', LANG_EN)

    assert result.status == GROUNDING_CORPUS
    assert result.source == SOURCE_CORPUS
    assert result.score == 7.4


def test_unattested_pair_is_flagged_not_deleted(list_dir):
    """The motivating defect: 'personalize' + 'advertising'."""
    db = _StubDB(rows=[])
    grounder = CollocationGrounder(db=db, data_dir=list_dir)

    result = grounder.validate('personalize', 'advertising', LANG_EN)

    assert result.status == GROUNDING_ASSERTED
    assert result.checkable, 'English is measurable; this pair simply is not attested'
    assert SOURCE_LIST in result.reason and SOURCE_CORPUS in result.reason


def test_japanese_is_unmeasured_rather_than_unattested():
    result = CollocationGrounder(db=_StubDB()).validate('約束', '守る', LANG_JA)

    assert result.status == GROUNDING_NO_SOURCE
    assert not result.checkable
    assert not result.validated


def test_chinese_uses_the_corpus_only():
    db = _StubDB(rows=[{'pmi_score': 6.1}])
    result = CollocationGrounder(db=db).validate('茶', '沏', LANG_ZH)

    assert result.status == GROUNDING_CORPUS
    assert result.source == SOURCE_CORPUS


def test_null_sentinel_collocate_is_no_source_not_asserted():
    """P1 writes the literal string "null" when it has no collocate."""
    result = CollocationGrounder(db=_StubDB()).validate('coffee', 'null', LANG_EN)
    assert result.status == GROUNDING_NO_SOURCE


def test_unconfigured_language_is_not_claimed_to_be_unattested():
    result = CollocationGrounder(db=_StubDB()).validate('a', 'b', 99)
    assert result.status == GROUNDING_NO_SOURCE
    assert 'language_id=99' in result.reason


def test_db_failure_degrades_to_asserted_rather_than_raising(list_dir):
    """Grounding is an annotation pass; it must never sink a generation."""
    db = _StubDB(raises=True)
    result = CollocationGrounder(db=db, data_dir=list_dir).validate(
        'personalize', 'advertising', LANG_EN,
    )
    assert result.status == GROUNDING_ASSERTED


# ---------------------------------------------------------------------------
# Tag shape + asset plumbing
# ---------------------------------------------------------------------------

def test_tag_carries_status_source_and_score(list_dir):
    tag = CollocationGrounder(db=None, data_dir=list_dir).validate(
        'strong', 'coffee', LANG_EN,
    ).to_tag()

    assert tag['status'] == GROUNDING_CORPUS
    assert tag['source'] == SOURCE_LIST
    assert tag['score'] == 9042.0
    assert tag['reason']


def test_no_source_tag_omits_source_and_score():
    tag = CollocationGrounder(db=_StubDB()).validate('約束', '守る', LANG_JA).to_tag()
    assert set(tag) == {'status', 'reason'}


def test_ground_core_asset_pins_the_tag_in_place():
    core = {
        'primary_collocate': 'decision',
        'sentences': [{'text': 'They make a decision.', 'target_word': 'make'}],
    }

    grounding = ground_core_asset(core, LANG_ZH, _StubDB(rows=[{'pmi_score': 8.0}]))

    assert grounding.validated
    assert core['collocate_grounding']['status'] == GROUNDING_CORPUS


def test_ground_core_asset_handles_an_asset_with_no_sentences():
    core = {'primary_collocate': 'decision', 'sentences': []}
    grounding = ground_core_asset(core, LANG_EN, _StubDB())

    assert grounding.status == GROUNDING_NO_SOURCE
    assert core['collocate_grounding']['status'] == GROUNDING_NO_SOURCE


# ---------------------------------------------------------------------------
# L5 gate reads the tag rather than re-querying
# ---------------------------------------------------------------------------

def _pipeline():
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    pipeline = VocabAssetPipeline.__new__(VocabAssetPipeline)
    pipeline.db = _StubDB(rows=[])       # would report "unattested" if queried
    return pipeline


def test_l5_gate_trusts_a_validated_tag_without_re_querying():
    core = {
        'primary_collocate': 'decision',
        'collocate_grounding': {'status': GROUNDING_CORPUS, 'reason': 'x'},
        'sentences': [{'text': 'They make a decision.', 'target_word': 'make'}],
    }
    assert _pipeline()._collocation_is_fixed(core, LANG_EN) is True


def test_l5_gate_drops_an_asserted_collocate():
    core = {
        'primary_collocate': 'advertising',
        'collocate_grounding': {'status': GROUNDING_ASSERTED, 'reason': 'x'},
        'sentences': [{'text': 'We personalize advertising.', 'target_word': 'personalize'}],
    }
    assert _pipeline()._collocation_is_fixed(core, LANG_EN) is False


def test_l5_gate_drops_when_the_language_cannot_be_checked():
    """'We cannot check' is not a licence to ship a collocation item."""
    core = {
        'primary_collocate': '守る',
        'collocate_grounding': {'status': GROUNDING_NO_SOURCE, 'reason': 'x'},
        'sentences': [{'text': '約束を守る。', 'target_word': '約束'}],
    }
    assert _pipeline()._collocation_is_fixed(core, LANG_JA) is False


def test_l5_gate_grades_a_legacy_untagged_asset_on_the_spot():
    """Assets predate grounding; the gate must not treat that as validated."""
    core = {
        'primary_collocate': 'advertising',
        'sentences': [{'text': 'We personalize advertising.', 'target_word': 'personalize'}],
    }
    assert _pipeline()._collocation_is_fixed(core, LANG_EN) is False
