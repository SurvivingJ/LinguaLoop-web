"""Shared helpers for the four-stage sense-linking workflow.

Stages (see .claude/skills/test-sense-linking/SKILL.md):
    1. scripts/export_tests_missing_senses.py  — worklist CSV
    2. scripts/sense_candidates.py             — DB candidate lookup
    3. (the skill: an LLM decides select-or-create per term)
    4. scripts/upload_test_senses.py           — write senses + link the test

Everything the stages share lives here for one reason: the token-map builder.
That routine already exists twice in this repo — backfill_vocab.py grew its own
copy and drifted from backfill_token_maps.py until it unpacked a 4-tuple into
three names and raised on every test it touched. A third copy would be a third
chance at the same bug, so stages 2 and 4 import this one.

None of this module talks to an LLM. Tokenisation is pure NLP (jieba / spaCy /
fugashi) and the processors are imported directly rather than through
VocabularyExtractionPipeline, which would drag in the phrase-detector's OpenAI
client for no benefit.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.vocabulary.processors import (
    ChineseProcessor,
    EnglishProcessor,
    JapaneseProcessor,
)

logger = logging.getLogger(__name__)

PAGE = 1000

_PROCESSOR_CLASSES = {
    'zh': ChineseProcessor,
    'en': EnglishProcessor,
    'ja': JapaneseProcessor,
}

_processor_cache: dict = {}

LANGUAGE_ID_TO_CODE = {k: v['code'] for k, v in Config.LANGUAGES.items()}


def get_processor(language_code: str):
    """Lazily build and cache the NLP processor for a language.

    Construction is expensive (spaCy model load, MeCab dictionary), so a script
    that handles several tests in one run must not rebuild it per test.
    """
    if language_code not in _processor_cache:
        cls = _PROCESSOR_CLASSES.get(language_code)
        if cls is None:
            raise ValueError(f"No processor for language '{language_code}'")
        _processor_cache[language_code] = cls()
    return _processor_cache[language_code]


def language_code_for(language_id: int) -> str:
    code = LANGUAGE_ID_TO_CODE.get(language_id)
    if not code:
        raise ValueError(f"Unknown language_id {language_id}")
    return code


_COLUMNS = ('id, slug, language_id, difficulty, is_active, transcript, '
            'vocab_sense_ids, vocab_token_map')


def _looks_like_uuid(ref: str) -> bool:
    parts = ref.split('-')
    return len(parts) == 5 and len(ref) == 36


def fetch_test(db, ref: str) -> dict:
    """Load one test by uuid or by slug, or raise if it doesn't exist.

    tests.id is a uuid, which is unreadable in a filename and unreadable in a
    log line, so every entry point here accepts the slug too and resolves it the
    same way.
    """
    ref = str(ref).strip()
    column = 'id' if _looks_like_uuid(ref) else 'slug'
    rows = (db.table('tests').select(_COLUMNS).eq(column, ref).limit(1).execute().data or [])
    if not rows and column == 'id':
        rows = (db.table('tests').select(_COLUMNS).eq('slug', ref).limit(1).execute().data or [])
    if not rows:
        raise ValueError(f"No test matching {ref!r} (tried {column}, then slug)")
    return rows[0]


class VocabIndex:
    """In-memory dim_vocabulary index for one language, with tiered lookup.

    An LLM extracting terms from a transcript writes the surface form it saw
    ("machines", "食べた", "机械的"). dim_vocabulary stores the tokenizer's lemma.
    Matching only on the exact string would miss rows that plainly exist and send
    stage 4 off to create duplicate vocabulary — so lookup falls back through
    casefolding, the traditional-Chinese mirror, and finally the tokenizer's own
    lemma for the term.

    `resolve()` reports which tier matched. That label is the signal stage 3 needs
    to distrust a match: an `exact` hit is the tokenizer agreeing with the LLM, a
    `tokenized` hit is this index guessing.
    """

    def __init__(self, db, language_id: int, language_code: str):
        self.language_id = language_id
        self.language_code = language_code
        self.by_lemma: dict[str, int] = {}
        self.by_casefold: dict[str, int] = {}
        self.by_traditional: dict[str, int] = {}
        self._load(db)

    def _load(self, db) -> None:
        offset = 0
        while True:
            resp = db.table('dim_vocabulary') \
                .select('id, lemma, lemma_traditional') \
                .eq('language_id', self.language_id) \
                .range(offset, offset + PAGE - 1) \
                .execute()
            rows = resp.data or []
            for row in rows:
                lemma = row['lemma']
                self.by_lemma.setdefault(lemma, row['id'])
                self.by_casefold.setdefault(lemma.casefold(), row['id'])
                trad = row.get('lemma_traditional')
                if trad:
                    self.by_traditional.setdefault(trad, row['id'])
            if len(rows) < PAGE:
                break
            offset += PAGE
        logger.info("Indexed %d %s vocabulary rows", len(self.by_lemma), self.language_code)

    def tokenized_lemma(self, term: str) -> str | None:
        """The tokenizer's lemma for `term`, when it reduces to one content token.

        A multi-token term ("ice cream", "食べ + た") returns None rather than a
        guess: picking one of its tokens would silently link the test to the
        wrong word.
        """
        try:
            tokens = get_processor(self.language_code).tokenize_full(term)
        except Exception as exc:
            logger.debug("tokenize failed for %r: %s", term, exc)
            return None
        content = [lemma for _display, lemma, is_content, _reading in tokens
                   if is_content and lemma]
        if len(content) == 1:
            return content[0]
        return None

    def resolve(self, term: str) -> tuple[int | None, str | None, str]:
        """Return (vocab_id, canonical_lemma, match_tier).

        match_tier is one of: exact, traditional, casefold, tokenized,
        tokenized_casefold, none.
        """
        term = (term or '').strip()
        if not term:
            return None, None, 'none'

        if term in self.by_lemma:
            return self.by_lemma[term], term, 'exact'
        if term in self.by_traditional:
            vid = self.by_traditional[term]
            return vid, term, 'traditional'
        folded = term.casefold()
        if folded in self.by_casefold:
            vid = self.by_casefold[folded]
            return vid, folded, 'casefold'

        lemma = self.tokenized_lemma(term)
        if lemma:
            if lemma in self.by_lemma:
                return self.by_lemma[lemma], lemma, 'tokenized'
            lf = lemma.casefold()
            if lf in self.by_casefold:
                return self.by_casefold[lf], lemma, 'tokenized_casefold'
            # Known lemma form, no row yet — hand stage 4 the normalised spelling
            # so a create writes the tokenizer's lemma, not the LLM's surface form.
            return None, lemma, 'none'

        return None, term, 'none'


def fetch_standard_senses(db, vocab_ids: list[int], language_id: int) -> dict[int, list[dict]]:
    """Batch-fetch standard-level senses for many vocab_ids, grouped and rank-ordered.

    Mirrors SenseGenerator._get_existing_senses' filters exactly (standard level,
    matching definition_language_id, ordered by sense_rank) so the candidate list
    stage 3 chooses from is the same list the inline generator would have seen.
    """
    out: dict[int, list[dict]] = {vid: [] for vid in vocab_ids}
    for i in range(0, len(vocab_ids), 500):
        chunk = vocab_ids[i:i + 500]
        resp = db.table('dim_word_senses') \
            .select('id, vocab_id, definition, sense_rank, example_sentence, source') \
            .in_('vocab_id', chunk) \
            .eq('definition_language_id', language_id) \
            .eq('definition_level', 'standard') \
            .order('sense_rank') \
            .execute()
        for row in (resp.data or []):
            out.setdefault(row['vocab_id'], []).append(row)
    return out


def build_token_map(language_code: str, transcript: str,
                    lemma_to_sense: dict[str, int]) -> tuple[list, list[str]]:
    """Build tests.vocab_token_map: [[display_text, sense_id_or_0], ...].

    Concatenating every display_text reproduces the transcript exactly — the
    renderer relies on that, so punctuation and whitespace tokens are kept with
    sense_id 0.

    Returns (token_map, unmatched_lemmas). `unmatched_lemmas` is every distinct
    content lemma that got a 0, which is the coverage signal a caller should log
    rather than discover later as unclickable words in the UI.

    NOTE the 4-tuple. tokenize_full returns (display, lemma, is_content, reading)
    for all three processors; unpacking three names here is the bug that took
    backfill_vocab.py:296 out of service.
    """
    processor = get_processor(language_code)
    tokens = processor.tokenize_full(transcript)

    token_map = []
    unmatched: set[str] = set()
    for display_text, lemma, is_content, _reading in tokens:
        sense_id = 0
        if is_content and lemma:
            sense_id = lemma_to_sense.get(lemma) or lemma_to_sense.get(lemma.casefold()) or 0
            if not sense_id:
                unmatched.add(lemma)
        token_map.append([display_text, sense_id])

    return token_map, sorted(unmatched)


def lemma_sense_lookup(db, sense_ids: list[int]) -> dict[str, int]:
    """Reverse a sense_id list into {lemma: sense_id} for token-map building.

    Used to seed the token map from the senses a run has just linked, before the
    fallback below fills in everything else the dictionary already knows.
    """
    if not sense_ids:
        return {}

    sense_to_vocab: dict[int, int] = {}
    for i in range(0, len(sense_ids), 500):
        chunk = sense_ids[i:i + 500]
        resp = db.table('dim_word_senses').select('id, vocab_id').in_('id', chunk).execute()
        for row in (resp.data or []):
            sense_to_vocab[row['id']] = row['vocab_id']

    vocab_ids = list(set(sense_to_vocab.values()))
    vocab_to_lemma: dict[int, str] = {}
    for i in range(0, len(vocab_ids), 500):
        chunk = vocab_ids[i:i + 500]
        resp = db.table('dim_vocabulary').select('id, lemma').in_('id', chunk).execute()
        for row in (resp.data or []):
            vocab_to_lemma[row['id']] = row['lemma']

    lookup: dict[str, int] = {}
    for sense_id, vocab_id in sense_to_vocab.items():
        lemma = vocab_to_lemma.get(vocab_id)
        if lemma and lemma not in lookup:
            lookup[lemma] = sense_id
            lookup.setdefault(lemma.casefold(), sense_id)
    return lookup


def build_token_map_with_fallback(db, language_code: str, language_id: int,
                                  transcript: str, lemma_to_sense: dict[str, int],
                                  resolve_vocab_id) -> tuple[list, list[str]]:
    """Token map from known links, extended with each remaining word's best sense.

    Two passes. The first links the senses the caller already knows about. Every
    content lemma that came back unmatched is then resolved to a vocab_id via
    `resolve_vocab_id(lemma)` and given its lowest-ranked standard sense, and the
    map is rebuilt. Words the dictionary already covers should not render as
    plain text just because this particular run didn't extract them.

    `resolve_vocab_id` is a callback because callers hold different indexes — a
    VocabIndex here, a preloaded ``(lemma, language_id)`` cache in
    backfill_vocab.py — and neither should have to adopt the other's.

    Only standard-level senses in this language are eligible (fetch_standard_senses
    enforces both). An earlier hand-rolled version of this fallback filtered on
    neither, so it could link a `simple` row's id and show a child-register gloss
    where the standard definition belonged.
    """
    lemma_to_sense = dict(lemma_to_sense)

    token_map, unmatched = build_token_map(language_code, transcript, lemma_to_sense)
    if not unmatched:
        return token_map, unmatched

    lemma_by_vocab: dict[int, str] = {}
    for lemma in unmatched:
        vocab_id = resolve_vocab_id(lemma)
        if vocab_id:
            lemma_by_vocab.setdefault(vocab_id, lemma)
    if not lemma_by_vocab:
        return token_map, unmatched

    for vocab_id, senses in fetch_standard_senses(
        db, list(lemma_by_vocab), language_id
    ).items():
        if senses:
            lemma_to_sense.setdefault(lemma_by_vocab[vocab_id], senses[0]['id'])

    return build_token_map(language_code, transcript, lemma_to_sense)
