# Plan 1: Exercise Content Generation Pipeline — Developer Task List

## Overview

This document is the developer handoff for the LinguaLoop Exercise Content Generation Pipeline (V3). It covers all code to be written, every class and function signature, all SQL statements, and integration points with the existing codebase.

**The pipeline transforms three source types** — grammar patterns, vocabulary senses, and corpus collocations — into 16 exercise types stored in the `exercises` table. Content is sourced from `tests.transcript` first (reuse-first strategy); the LLM is called only as a fallback or for elements that cannot be deterministically assembled (distractors, translations, grading notes, error sentences).

**File layout (new directory `services/exercise_generation/`):**

```
services/exercise_generation/
├── orchestrator.py            # ExerciseGenerationOrchestrator
├── config.py                  # Constants, distribution tables, field maps
├── base_generator.py          # ExerciseGenerator ABC
├── transcript_miner.py        # TranscriptMiner + SentenceFilter
├── language_processor.py      # LanguageProcessor ABC + language subclasses
├── generators/
│   ├── cloze.py               # ClozeGenerator
│   ├── jumbled_sentence.py    # JumbledSentenceGenerator
│   ├── translation.py         # TlNlTranslationGenerator, NlTlTranslationGenerator
│   ├── flashcard.py           # FlashcardGenerator
│   ├── spot_incorrect.py      # SpotIncorrectGenerator
│   ├── semantic.py            # SemanticDiscrimGenerator, OddOneOutGenerator
│   ├── collocation.py         # CollocationGapFillGenerator, CollocationRepairGenerator, OddCollocationOutGenerator
│   ├── verb_noun_match.py     # VerbNounMatchGenerator
│   ├── context_spectrum.py    # ContextSpectrumGenerator
│   └── timed_speed_round.py  # TimedSpeedRoundGenerator
├── validators.py              # ExerciseValidator (deterministic, no LLM)
├── difficulty.py              # DifficultyCalibrator
└── run_exercise_generation.py # Cron entry point
```

**Key architectural decisions:**
- `ExerciseGenerator` is the abstract base class; each exercise type gets its own subclass.
- `LanguageProcessor` is a separate hierarchy for tokenisation and chunking — decoupled from exercise logic so a new language (e.g. Korean) only requires adding one subclass.
- `TranscriptMiner` is its own class, called by the orchestrator in Phase 1 before any generator runs.
- Validators are deterministic — no LLM calls in the validation layer.
- The no-shuffle rule: `options[0]` is always the correct answer in stored JSONB; `sentences[3]` is always the incorrect sentence for `spot_incorrect_sentence`. Frontend shuffles.
- All LLM calls follow the existing tenacity retry pattern (`@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))`).
- Database access uses the existing Supabase client pattern: `db.table('x').select(...).eq(...).execute()`.

---

## Phase 0: Schema & Configuration

### Task 0.1 — Database Schema: `dim_grammar_patterns`

**Description:** Create the grammar pattern registry table. This is a prerequisite for all grammar-sourced exercise generation.

**SQL (ready to run):**

```sql
-- Create grammar pattern registry
CREATE TABLE dim_grammar_patterns (
    id                   SERIAL PRIMARY KEY,
    pattern_code         TEXT NOT NULL UNIQUE,          -- e.g. 'en_present_perfect_cont'
    pattern_name         TEXT NOT NULL,                  -- internal English name
    description          TEXT NOT NULL,                  -- pedagogical description for prompts
    user_facing_description TEXT NOT NULL,              -- shown to users; English internally
    example_sentence     TEXT NOT NULL,                  -- canonical TL example
    example_sentence_en  TEXT,                           -- English gloss if TL ≠ English
    language_id          INTEGER NOT NULL REFERENCES dim_languages(id),
    cefr_level           TEXT NOT NULL CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
    category             TEXT NOT NULL CHECK (category IN (
                             'tense','aspect','voice','particles','word_order','modality',
                             'clause_structure','conjugation','honorifics','measure_words','complement'
                         )),
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_grammar_patterns_language ON dim_grammar_patterns(language_id);
CREATE INDEX idx_grammar_patterns_cefr     ON dim_grammar_patterns(cefr_level);
CREATE INDEX idx_grammar_patterns_active   ON dim_grammar_patterns(is_active) WHERE is_active = TRUE;
```

**Integration:** No existing table to modify. Seed data for initial patterns is in Appendix A of the V3 spec.

---

### Task 0.2 — Database Schema: `exercises` Table

**Description:** Create the central exercises table. All 16 exercise types share this table; the `exercise_type` discriminator column determines the JSONB structure of `content`.

**SQL (ready to run):**

```sql
CREATE TYPE exercise_source_type AS ENUM ('grammar', 'vocabulary', 'collocation');

CREATE TABLE exercises (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id             INTEGER NOT NULL REFERENCES dim_languages(id),
    exercise_type           TEXT NOT NULL,               -- one of 16 types
    source_type             exercise_source_type NOT NULL,
    grammar_pattern_id      INTEGER REFERENCES dim_grammar_patterns(id),
    word_sense_id           INTEGER REFERENCES dim_word_senses(id),
    corpus_collocation_id   INTEGER REFERENCES corpus_collocations(id),  -- Plan 5 FK
    content                 JSONB NOT NULL,              -- exercise payload
    tags                    JSONB NOT NULL DEFAULT '{}', -- e.g. {"grammar_pattern": "en_present_perfect_cont"}
    difficulty_static       NUMERIC(4,2),
    irt_difficulty          NUMERIC(5,3) NOT NULL DEFAULT 0.0,
    irt_discrimination      NUMERIC(5,3) NOT NULL DEFAULT 1.0,
    cefr_level              TEXT CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2')),
    attempt_count           INTEGER NOT NULL DEFAULT 0,
    correct_count           INTEGER NOT NULL DEFAULT 0,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    generation_batch_id     UUID,                        -- links rows from same orchestrator run
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Exactly one of these FKs must be set (enforced in application layer)
    CONSTRAINT chk_source_fk CHECK (
        (grammar_pattern_id IS NOT NULL)::INT +
        (word_sense_id IS NOT NULL)::INT +
        (corpus_collocation_id IS NOT NULL)::INT = 1
    )
);

CREATE INDEX idx_exercises_language     ON exercises(language_id);
CREATE INDEX idx_exercises_type         ON exercises(exercise_type);
CREATE INDEX idx_exercises_source       ON exercises(source_type);
CREATE INDEX idx_exercises_grammar      ON exercises(grammar_pattern_id) WHERE grammar_pattern_id IS NOT NULL;
CREATE INDEX idx_exercises_sense        ON exercises(word_sense_id) WHERE word_sense_id IS NOT NULL;
CREATE INDEX idx_exercises_collocation  ON exercises(corpus_collocation_id) WHERE corpus_collocation_id IS NOT NULL;
CREATE INDEX idx_exercises_cefr         ON exercises(cefr_level);
CREATE INDEX idx_exercises_active       ON exercises(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_exercises_tags_gin     ON exercises USING GIN (tags);
CREATE INDEX idx_exercises_content_gin  ON exercises USING GIN (content);
```

**Integration:**
- `corpus_collocation_id` references the `corpus_collocations` table populated by Plan 5. Add the FK column when Plan 5 schema is ready; constraint can be deferred.
- The existing `exercise_attempts` table should add FK: `ALTER TABLE exercise_attempts ADD COLUMN exercise_id UUID REFERENCES exercises(id);`

---

### Task 0.3 — Database Schema: `exercise_attempts` Updates

**Description:** Ensure `exercise_attempts` can track distractor tags and exercise FKs.

**SQL (ready to run):**

```sql
-- Add exercise_id FK if not present
ALTER TABLE exercise_attempts
    ADD COLUMN IF NOT EXISTS exercise_id UUID REFERENCES exercises(id);

-- user_response JSONB already exists; ensure it can hold distractor_tag:
-- {"selected_option": "...", "distractor_tag": "form_error", "response_time_ms": 2340, "is_correct": false}
-- No schema change needed — JSONB is flexible.

-- Index for distractor analytics query
CREATE INDEX IF NOT EXISTS idx_ea_exercise_id ON exercise_attempts(exercise_id);
CREATE INDEX IF NOT EXISTS idx_ea_user_response_gin ON exercise_attempts USING GIN (user_response);
```

---

### Task 0.4 — Database Schema: `dim_languages` Extension

**Description:** Add exercise model columns to `dim_languages` so the orchestrator can look up which LLM model to use per language.

**SQL (ready to run):**

```sql
ALTER TABLE dim_languages
    ADD COLUMN IF NOT EXISTS exercise_model          TEXT,   -- LLM model for exercise generation
    ADD COLUMN IF NOT EXISTS exercise_sentence_model TEXT;  -- LLM model for sentence generation fallback

-- Populate for existing languages
UPDATE dim_languages SET
    exercise_model          = 'google/gemini-flash-1.5',
    exercise_sentence_model = 'google/gemini-flash-1.5'
WHERE id IN (1, 2, 3);  -- Chinese, English, Japanese
```

**Integration:** Existing `prose_model` and `question_model` columns already present; this is an additive change.

---

### Task 0.5 — `config.py`: Constants & Distribution Tables

**Description:** Central configuration for the exercise generation service. No logic here — only constants and lookup tables consumed by other modules.

**File:** `services/exercise_generation/config.py`

**Contents to define:**

```python
# services/exercise_generation/config.py

from typing import FrozenSet

# --- Exercise type registry ---------------------------------------------------

ALL_EXERCISE_TYPES: list[str] = [
    'cloze_completion', 'jumbled_sentence', 'tl_nl_translation', 'nl_tl_translation',
    'collocation_gap_fill', 'text_flashcard', 'listening_flashcard',
    'semantic_discrimination', 'collocation_repair', 'spot_incorrect_sentence',
    'spot_incorrect_part', 'timed_speed_round', 'odd_one_out', 'context_spectrum',
    'odd_collocation_out', 'verb_noun_match',
]

# Exercise types that require an MCQ options array
MCQ_TYPES: FrozenSet[str] = frozenset({
    'cloze_completion', 'tl_nl_translation', 'collocation_gap_fill',
    'odd_one_out', 'odd_collocation_out',
})

# Expected option counts per MCQ type
EXPECTED_OPTION_COUNT: dict[str, int] = {
    'cloze_completion':     4,
    'tl_nl_translation':    3,
    'collocation_gap_fill': 4,
    'odd_one_out':          4,
    'odd_collocation_out':  4,
}

# --- Required JSONB fields per type ------------------------------------------

REQUIRED_FIELDS_BY_TYPE: dict[str, list[str]] = {
    'cloze_completion':        ['sentence_with_blank', 'correct_answer', 'options',
                                'explanation', 'distractor_tags'],
    'jumbled_sentence':        ['chunks', 'correct_ordering', 'original_sentence'],
    'tl_nl_translation':       ['tl_sentence', 'correct_nl', 'options'],
    'nl_tl_translation':       ['nl_sentence', 'primary_tl', 'grading_notes'],
    'text_flashcard':          ['front_sentence', 'highlight_word', 'back_sentence',
                                'word_of_interest', 'sense_id'],
    'listening_flashcard':     ['front_audio_url', 'back_sentence', 'word_of_interest', 'sense_id'],
    'semantic_discrimination': ['sentences', 'explanation'],
    'odd_one_out':             ['items', 'odd_index', 'shared_property', 'explanation'],
    'context_spectrum':        ['variants', 'exercise_context', 'correct_variant_index'],
    'collocation_gap_fill':    ['sentence', 'correct', 'options', 'collocation'],
    'collocation_repair':      ['sentence_with_error', 'error_word', 'correct_word'],
    'odd_collocation_out':     ['head_word', 'collocations', 'odd_index', 'explanation'],
    'verb_noun_match':         ['verbs', 'nouns', 'valid_pairs'],
    'spot_incorrect_sentence': ['sentences'],
    'spot_incorrect_part':     ['sentence', 'parts'],
}

# --- Distribution targets per grammar pattern --------------------------------
# Keys: exercise_type -> target count per source
GRAMMAR_DISTRIBUTION: dict[str, int] = {
    'cloze_completion':        150,
    'jumbled_sentence':        120,
    'tl_nl_translation':        80,
    'nl_tl_translation':        60,
    'collocation_gap_fill':     80,
    'text_flashcard':           80,
    'listening_flashcard':      80,
    'semantic_discrimination':  60,
    'collocation_repair':       50,
    'spot_incorrect_sentence':  40,
    'spot_incorrect_part':      30,
    'timed_speed_round':        50,
    'odd_one_out':              40,
    'context_spectrum':         30,
    'odd_collocation_out':      30,
    'verb_noun_match':          20,
}

VOCABULARY_DISTRIBUTION: dict[str, int] = {
    'text_flashcard':          3,
    'listening_flashcard':     3,
    'cloze_completion':        5,
    'tl_nl_translation':       3,
    'semantic_discrimination': 2,
}

COLLOCATION_DISTRIBUTION: dict[str, int] = {
    'collocation_gap_fill':  5,
    'collocation_repair':    3,
    'odd_collocation_out':   3,
    'text_flashcard':        2,
    'verb_noun_match':       1,   # 1 grid per collocation cluster
}

# --- Sentence pool thresholds ------------------------------------------------
MIN_TRANSCRIPT_SENTENCES: int = 80
DEFAULT_SENTENCE_TARGET:  int = 200
LLM_BATCH_SIZE:           int = 25

# --- CEFR → IRT difficulty seed ----------------------------------------------
CEFR_TO_IRT: dict[str, float] = {
    'A1': -2.0, 'A2': -1.0, 'B1': 0.0, 'B2': 0.5, 'C1': 1.0, 'C2': 2.0,
}

# --- Grammar pattern heuristics (for transcript mining) ---------------------
PATTERN_HEURISTICS: dict[str, str] = {
    'en_present_perfect_cont': r'\b(has|have)\s+been\s+\w+ing\b',
    'en_passive_voice_simple':  r'\b(is|was|are|were|been)\s+\w+ed\b',
    'en_reported_speech':       r'\b(said|told|asked|thought)\s+(that|if|whether)\b',
    'cn_ba_construction':       r'把',
    'cn_bei_passive':           r'被',
    'jp_te_form_progressive':   r'ている|ています',
    'jp_keigo_sonkeigo':        r'ていらっしゃ|いらっしゃ|ございます',
}

# --- Language IDs (mirrors dim_languages) ------------------------------------
LANG_CHINESE:  int = 1
LANG_ENGLISH:  int = 2
LANG_JAPANESE: int = 3
```

**Dependencies:** None. Must be implemented before any other module.

---

## Phase 1: Language Processing Layer

### Task 1.1 — `language_processor.py`: LanguageProcessor Hierarchy

**Description:** Provides language-specific tokenisation, sentence splitting, and syntactic chunking. This is the single point of extension for adding a new language — only a new subclass is needed. Exercise generators call this abstraction; they never import spaCy or jieba directly.

**File:** `services/exercise_generation/language_processor.py`

**Class hierarchy:**

```
LanguageProcessor (ABC)
├── EnglishProcessor    (language_id=2, spaCy en_core_web_sm)
├── ChineseProcessor    (language_id=1, jieba)
└── JapaneseProcessor   (language_id=3, spaCy ja_core_news_sm)
```

**Full signatures:**

```python
# services/exercise_generation/language_processor.py

import re
from abc import ABC, abstractmethod


class LanguageProcessor(ABC):
    """
    Abstract base for language-specific NLP operations.
    Instantiate via LanguageProcessor.for_language(language_id).
    All methods are stateless after __init__.
    """

    language_id: int  # set by subclass

    @abstractmethod
    def split_sentences(self, text: str) -> list[str]:
        """
        Split a paragraph or transcript into individual sentences.
        Returns cleaned, non-empty sentence strings.
        Args:
            text: raw transcript text, may contain newlines and punctuation
        Returns:
            List of sentence strings with leading/trailing whitespace stripped.
        """

    @abstractmethod
    def chunk_sentence(self, sentence: str) -> list[str]:
        """
        Split a sentence into 3–6 syntactic chunks suitable for a jumbled_sentence exercise.
        Args:
            sentence: a single, well-formed sentence in the target language
        Returns:
            List of chunk strings. Raises ValueError if < 3 chunks produced.
        """

    def matches_pattern(self, sentence: str, pattern_code: str) -> bool:
        """
        Return True if the sentence demonstrates the given grammar pattern.
        Default implementation uses PATTERN_HEURISTICS regex lookup from config.
        Override in subclass for complex patterns requiring full parse.
        Args:
            sentence:     target language sentence
            pattern_code: key from PATTERN_HEURISTICS or dim_grammar_patterns.pattern_code
        """
        from services.exercise_generation.config import PATTERN_HEURISTICS
        heuristic = PATTERN_HEURISTICS.get(pattern_code)
        if heuristic:
            return bool(re.search(heuristic, sentence))
        return False  # Unknown pattern — caller handles fallback

    def contains_collocation(self, sentence: str, collocation_text: str) -> bool:
        """
        Return True if collocation_text appears as a contiguous substring.
        For Chinese/Japanese, this is a simple string search (no word boundaries).
        For English, requires word boundary matching.
        Args:
            sentence:          target language sentence
            collocation_text:  the collocation phrase to search for
        """
        return collocation_text.lower() in sentence.lower()

    def merge_short_chunks(self, chunks: list[str], min_tokens: int = 2) -> list[str]:
        """
        Merge chunks shorter than min_tokens with their left neighbour.
        Used by chunk_sentence implementations to avoid single-word chunks.
        Args:
            chunks:     list of chunk strings
            min_tokens: minimum token count for a standalone chunk
        Returns:
            Merged list; always has len >= 1.
        """
        if not chunks:
            return chunks
        merged = [chunks[0]]
        for chunk in chunks[1:]:
            token_count = len(chunk.split()) if chunk.isascii() else len(chunk)
            if token_count < min_tokens:
                merged[-1] = merged[-1] + ' ' + chunk if chunk.isascii() else merged[-1] + chunk
            else:
                merged.append(chunk)
        return merged

    @staticmethod
    def for_language(language_id: int) -> 'LanguageProcessor':
        """
        Factory method. Returns the correct subclass for the given language_id.
        Args:
            language_id: integer FK matching dim_languages.id
        Raises:
            ValueError if language_id is not supported.
        """
        mapping = {1: ChineseProcessor, 2: EnglishProcessor, 3: JapaneseProcessor}
        cls = mapping.get(language_id)
        if cls is None:
            raise ValueError(f"No LanguageProcessor for language_id={language_id}")
        return cls()


class EnglishProcessor(LanguageProcessor):
    """
    English NLP using spaCy en_core_web_sm.
    Model is loaded once at class instantiation (module-level singleton pattern).
    """

    language_id = 2

    def __init__(self):
        import spacy
        # Load once; subsequent instantiations reuse the already-loaded model
        if not hasattr(EnglishProcessor, '_nlp'):
            EnglishProcessor._nlp = spacy.load('en_core_web_sm')
        self.nlp = EnglishProcessor._nlp

    def split_sentences(self, text: str) -> list[str]:
        """
        Use spaCy sentencizer to split text into sentences.
        Filters empty results. Strips whitespace.
        Args:
            text: raw transcript paragraph(s)
        Returns:
            List of clean sentence strings.
        """
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def chunk_sentence(self, sentence: str) -> list[str]:
        """
        Split English sentence into 3–6 syntactic chunks using spaCy noun_chunks
        plus inter-chunk verb/prep spans as separate chunks.
        Falls back to simple split at conjunctions if < 2 noun chunks are found.
        Args:
            sentence: single well-formed English sentence
        Returns:
            List of chunk strings (3–6 items).
        Raises:
            ValueError if fewer than 3 chunks are produced after merging.
        """
        doc = self.nlp(sentence)
        noun_chunks = list(doc.noun_chunks)

        if len(noun_chunks) < 2:
            chunks = self._simple_split(sentence)
        else:
            chunks = []
            prev_end = 0
            for nc in noun_chunks:
                between = doc[prev_end:nc.start]
                if between.text.strip():
                    chunks.append(between.text.strip())
                chunks.append(nc.text.strip())
                prev_end = nc.end
            tail = doc[prev_end:]
            if tail.text.strip():
                chunks.append(tail.text.strip())
            chunks = [c for c in chunks if c]

        chunks = self.merge_short_chunks(chunks, min_tokens=2)

        if len(chunks) < 3:
            raise ValueError(
                f"EnglishProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:60]}"
            )
        return chunks[:6]  # cap at 6

    def _simple_split(self, sentence: str) -> list[str]:
        """
        Fallback: split on common conjunctions and prepositions (after, before, because, when, while).
        Used when spaCy noun_chunks produces < 2 results.
        Args:
            sentence: raw English sentence
        Returns:
            List of phrase strings.
        """
        import re
        pattern = r'\b(after|before|because|when|while|and|but|although|since|if)\b'
        parts = re.split(pattern, sentence, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip() and not re.fullmatch(pattern, p.strip(), re.IGNORECASE)]

    def contains_collocation(self, sentence: str, collocation_text: str) -> bool:
        """
        English: enforce word-boundary matching for single-word collocations.
        For multi-word phrases, falls back to substring match.
        """
        words = collocation_text.split()
        if len(words) == 1:
            return bool(re.search(r'\b' + re.escape(collocation_text) + r'\b', sentence, re.IGNORECASE))
        return collocation_text.lower() in sentence.lower()


class ChineseProcessor(LanguageProcessor):
    """
    Mandarin Chinese NLP using jieba for tokenisation and chunking.
    No sentence-level model; splits on Chinese sentence-ending punctuation.
    """

    language_id = 1

    SENTENCE_END_PATTERN = re.compile(r'(?<=[。！？])')
    BOUNDARY_MARKERS = frozenset({'，', '。', '、', '了', '在', '和', '与', '但', '因为', '所以'})

    def split_sentences(self, text: str) -> list[str]:
        """
        Split Chinese text on 。！？ punctuation.
        Args:
            text: raw Chinese transcript text
        Returns:
            List of clean sentence strings (empty strings removed).
        """
        parts = self.SENTENCE_END_PATTERN.split(text)
        return [p.strip() for p in parts if p.strip()]

    def chunk_sentence(self, sentence: str) -> list[str]:
        """
        Chinese chunking via jieba.cut() + boundary marker rules.
        Groups tokens until a boundary marker is encountered or 4 tokens accumulated.
        Strips punctuation from chunk edges. Caps at 6 chunks.
        Args:
            sentence: single Chinese sentence (no trailing 。)
        Returns:
            List of chunk strings (3–6 items).
        Raises:
            ValueError if fewer than 3 chunks produced.
        """
        import jieba
        tokens = [t for t in jieba.cut(sentence, cut_all=False) if t.strip()]
        chunks = []
        current: list[str] = []

        for token in tokens:
            current.append(token)
            if token in self.BOUNDARY_MARKERS or len(current) >= 4:
                chunk_text = ''.join(current).strip('，。、')
                if chunk_text:
                    chunks.append(chunk_text)
                current = []

        if current:
            chunks.append(''.join(current).strip('，。、'))

        chunks = [c for c in chunks if len(c) >= 1]
        chunks = chunks[:6]

        if len(chunks) < 3:
            raise ValueError(
                f"ChineseProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:40]}"
            )
        return chunks


class JapaneseProcessor(LanguageProcessor):
    """
    Japanese NLP using spaCy ja_core_news_sm.
    Groups tokens into bunsetsu-like phrases on case/conjunction particles.
    """

    language_id = 3

    def __init__(self):
        import spacy
        if not hasattr(JapaneseProcessor, '_nlp'):
            JapaneseProcessor._nlp = spacy.load('ja_core_news_sm')
        self.nlp = JapaneseProcessor._nlp

    def split_sentences(self, text: str) -> list[str]:
        """
        Use spaCy sentencizer (Japanese model includes sentence boundaries).
        Args:
            text: raw Japanese transcript text
        Returns:
            List of clean sentence strings.
        """
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def chunk_sentence(self, sentence: str) -> list[str]:
        """
        Japanese chunking: group tokens into bunsetsu-like phrases.
        Boundary at case particles (は, が, を, に, で, へ, と, も) and conjunction marks.
        Args:
            sentence: single Japanese sentence
        Returns:
            List of chunk strings (3–6 items).
        Raises:
            ValueError if fewer than 3 chunks produced.
        """
        doc = self.nlp(sentence)
        chunks = []
        current: list[str] = []

        for token in doc:
            current.append(token.text)
            if token.pos_ == 'ADP' or token.dep_ in ('case', 'mark'):
                chunks.append(''.join(current))
                current = []

        if current:
            chunks.append(''.join(current))

        chunks = [c for c in chunks if c.strip()]
        chunks = chunks[:6]

        if len(chunks) < 3:
            raise ValueError(
                f"JapaneseProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:40]}"
            )
        return chunks
```

**Dependencies:** Task 0.5 (config). No exercise logic.

---

## Phase 2: Transcript Mining

### Task 2.1 — `transcript_miner.py`: TranscriptMiner + SentenceFilter

**Description:** Implements the "Reuse First" strategy. `TranscriptMiner` queries `tests.transcript` and extracts sentences matching the target source. `SentenceFilter` deduplicates and enforces quality constraints. `LLMSentenceGenerator` is the fallback, called only when fewer than 80 transcript sentences are found.

**File:** `services/exercise_generation/transcript_miner.py`

```python
# services/exercise_generation/transcript_miner.py

import re
import hashlib
from services.exercise_generation.config import (
    MIN_TRANSCRIPT_SENTENCES, DEFAULT_SENTENCE_TARGET,
    LLM_BATCH_SIZE, LANG_CHINESE,
)
from services.exercise_generation.language_processor import LanguageProcessor


class TranscriptMiner:
    """
    Extracts usable sentences from tests.transcript for a given source (grammar,
    vocabulary, or collocation). Uses the Reuse First strategy; does not call the LLM.
    """

    def __init__(self, db, language_processor: LanguageProcessor):
        """
        Args:
            db:                 Supabase client instance
            language_processor: LanguageProcessor subclass for the target language
        """
        self.db = db
        self.lp = language_processor

    def mine(
        self,
        source_type: str,
        source_id: int,
        language_id: int,
    ) -> list[dict]:
        """
        Entry point. Dispatches to the appropriate mining strategy based on source_type.
        Args:
            source_type: 'grammar', 'vocabulary', or 'collocation'
            source_id:   FK to dim_grammar_patterns.id, dim_word_senses.id, or corpus_collocations.id
            language_id: FK to dim_languages.id
        Returns:
            List of sentence dicts: {sentence, translation, topic, source, cefr_level, test_id}
            Deduplicated. May be empty.
        """
        if source_type == 'vocabulary':
            raw = self._mine_vocabulary(source_id, language_id)
        elif source_type == 'grammar':
            raw = self._mine_grammar(source_id, language_id)
        elif source_type == 'collocation':
            raw = self._mine_collocation(source_id, language_id)
        else:
            raise ValueError(f"Unknown source_type: {source_type}")

        return SentenceFilter.deduplicate(raw)

    def _mine_vocabulary(self, sense_id: int, language_id: int) -> list[dict]:
        """
        Vocabulary mining: use GIN-indexed vocab_sense_ids array to find tests containing
        the target sense, then use vocab_token_map to locate the exact token and extract
        its containing sentence.
        Args:
            sense_id:    dim_word_senses.id
            language_id: dim_languages.id
        Returns:
            Raw list of sentence dicts (may contain duplicates).
        """
        # Fast lookup via GIN index on vocab_sense_ids
        result = self.db.rpc('tests_containing_sense', {
            'p_sense_id': sense_id,
            'p_language_id': language_id,
        }).execute()

        sentences = []
        for test in (result.data or []):
            transcript = test.get('transcript', '')
            token_map  = test.get('vocab_token_map', [])  # [[display_text, sense_id], ...]
            cefr       = self._difficulty_to_cefr(test.get('difficulty', 2))

            # Find the display token for this sense
            target_tokens = [entry[0] for entry in token_map if entry[1] == sense_id]
            if not target_tokens:
                continue

            for token_text in target_tokens:
                extracted = self._extract_sentences_containing(
                    transcript, token_text, test['id'], cefr
                )
                sentences.extend(extracted)

        return sentences

    def _mine_grammar(self, pattern_id: int, language_id: int) -> list[dict]:
        """
        Grammar mining: load the pattern_code + heuristic regex, then scan all active
        transcripts for the target language. For patterns with no heuristic, calls
        LLM classification once offline (not repeated per exercise batch — handled
        by offline tagging job, not this method).
        Args:
            pattern_id:  dim_grammar_patterns.id
            language_id: dim_languages.id
        Returns:
            Raw list of sentence dicts.
        """
        pattern_row = self.db.table('dim_grammar_patterns') \
            .select('pattern_code, cefr_level') \
            .eq('id', pattern_id) \
            .single() \
            .execute().data

        pattern_code = pattern_row['pattern_code']

        tests = self.db.table('tests') \
            .select('id, transcript, difficulty') \
            .eq('language', language_id) \
            .eq('is_active', True) \
            .execute()

        sentences = []
        for test in (tests.data or []):
            transcript = test.get('transcript', '')
            cefr       = self._difficulty_to_cefr(test.get('difficulty', 2))
            raw_sents  = self.lp.split_sentences(transcript)

            for sent in raw_sents:
                if self.lp.matches_pattern(sent, pattern_code):
                    sentences.append(self._make_sentence_dict(sent, test['id'], cefr))

        return sentences

    def _mine_collocation(self, collocation_id: int, language_id: int) -> list[dict]:
        """
        Collocation mining: look up the collocation text from corpus_collocations,
        then substring-search all active transcripts.
        Args:
            collocation_id: corpus_collocations.id
            language_id:    dim_languages.id
        Returns:
            Raw list of sentence dicts.
        """
        col_row = self.db.table('corpus_collocations') \
            .select('collocation_text') \
            .eq('id', collocation_id) \
            .single() \
            .execute().data

        collocation_text = col_row['collocation_text']

        tests = self.db.table('tests') \
            .select('id, transcript, difficulty') \
            .eq('language', language_id) \
            .eq('is_active', True) \
            .execute()

        sentences = []
        for test in (tests.data or []):
            transcript = test.get('transcript', '')
            cefr       = self._difficulty_to_cefr(test.get('difficulty', 2))
            raw_sents  = self.lp.split_sentences(transcript)

            for sent in raw_sents:
                if self.lp.contains_collocation(sent, collocation_text):
                    sentences.append(self._make_sentence_dict(sent, test['id'], cefr))

        return sentences

    def _extract_sentences_containing(
        self,
        transcript: str,
        token_text: str,
        test_id: str,
        cefr: str,
    ) -> list[dict]:
        """
        Split transcript into sentences and return those containing token_text.
        Args:
            transcript: full test transcript
            token_text: the specific token string to find
            test_id:    UUID of the source test
            cefr:       CEFR level derived from test difficulty
        Returns:
            List of sentence dicts containing the token.
        """
        raw_sents = self.lp.split_sentences(transcript)
        return [
            self._make_sentence_dict(sent, test_id, cefr)
            for sent in raw_sents
            if self.lp.contains_collocation(sent, token_text)
        ]

    @staticmethod
    def _make_sentence_dict(sentence: str, test_id: str, cefr: str) -> dict:
        return {
            'sentence':    sentence,
            'translation': None,
            'topic':       'existing_content',
            'source':      'transcript',
            'cefr_level':  cefr,
            'test_id':     test_id,
        }

    @staticmethod
    def _difficulty_to_cefr(difficulty: float) -> str:
        """
        Map numeric test difficulty (1–5 scale) to CEFR level string.
        Args:
            difficulty: float difficulty score from tests table
        Returns:
            CEFR level string.
        """
        if difficulty < 1.5:  return 'A1'
        if difficulty < 2.5:  return 'A2'
        if difficulty < 3.5:  return 'B1'
        if difficulty < 4.0:  return 'B2'
        if difficulty < 4.5:  return 'C1'
        return 'C2'


class SentenceFilter:
    """
    Stateless utility class for deduplication and quality filtering of sentence pools.
    All methods are static.
    """

    @staticmethod
    def deduplicate(sentences: list[dict]) -> list[dict]:
        """
        Remove duplicate sentences by normalised lowercase text.
        Preserves first occurrence.
        Args:
            sentences: list of sentence dicts with 'sentence' key
        Returns:
            Deduplicated list.
        """
        seen: set[str] = set()
        result = []
        for s in sentences:
            key = s.get('sentence', '').lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(s)
        return result

    @staticmethod
    def filter_quality(sentences: list[dict], language_id: int) -> list[dict]:
        """
        Apply length and completeness filters. Length bounds are language-adjusted:
        word count for whitespace-delimited languages (English), character count for CJK.
        Args:
            sentences:   list of sentence dicts
            language_id: used to select word-count vs character-count mode
        Returns:
            Filtered list.
        """
        from services.exercise_generation.config import LANG_CHINESE, LANG_JAPANESE
        valid = []
        for s in sentences:
            text = s.get('sentence', '').strip()
            if not text:
                continue
            if language_id in (LANG_CHINESE,):
                length = len(text)
                lo, hi = 5, 80
            elif language_id == LANG_JAPANESE:
                length = len(text)
                lo, hi = 5, 100
            else:  # English and others
                length = len(text.split())
                lo, hi = 5, 80
            if lo <= length <= hi:
                valid.append(s)
        return valid


class LLMSentenceGenerator:
    """
    LLM fallback for sentence generation when transcript mining yields < MIN_TRANSCRIPT_SENTENCES.
    Generates sentences in batches of LLM_BATCH_SIZE using the prompt_templates table.
    """

    def __init__(self, db, llm_client, model: str):
        """
        Args:
            db:         Supabase client
            llm_client: existing call_llm callable from base_generator
            model:      LLM model string from dim_languages.exercise_sentence_model
        """
        self.db         = db
        self.llm_client = llm_client
        self.model      = model

    def generate(
        self,
        source_type: str,
        source_id: int,
        language_id: int,
        count: int,
    ) -> list[dict]:
        """
        Generate `count` sentences for the given source using the LLM.
        Reads the latest 'exercise_sentence_generation' prompt template.
        Calls LLM in batches of LLM_BATCH_SIZE.
        Applies SentenceFilter.filter_quality and SentenceFilter.deduplicate.
        Args:
            source_type: 'grammar', 'vocabulary', or 'collocation'
            source_id:   FK to the source table
            language_id: target language
            count:       number of sentences needed
        Returns:
            List of sentence dicts.
        """
        source_data = self._load_source_data(source_type, source_id)
        template    = self._load_prompt_template('exercise_sentence_generation')
        all_sentences: list[dict] = []

        for offset in range(0, count, LLM_BATCH_SIZE):
            batch_count = min(LLM_BATCH_SIZE, count - offset)
            prompt = template.format(count=batch_count, **source_data)
            result = self.llm_client(prompt, model=self.model, response_format='json')
            all_sentences.extend(result if isinstance(result, list) else [])

        filtered = SentenceFilter.filter_quality(all_sentences, language_id)
        return SentenceFilter.deduplicate(filtered)

    def _load_source_data(self, source_type: str, source_id: int) -> dict:
        """
        Load display data for the source entity to inject into prompt templates.
        Returns a dict with keys depending on source_type:
          grammar:     {pattern_code, description, example_sentence, cefr_level}
          vocabulary:  {word, definition, cefr_level}
          collocation: {collocation_text, pos_pattern}
        """
        if source_type == 'grammar':
            row = self.db.table('dim_grammar_patterns') \
                .select('pattern_code, description, example_sentence, cefr_level') \
                .eq('id', source_id).single().execute().data
            return row or {}
        elif source_type == 'vocabulary':
            row = self.db.table('dim_word_senses') \
                .select('word, definition, cefr_level') \
                .eq('id', source_id).single().execute().data
            return row or {}
        elif source_type == 'collocation':
            row = self.db.table('corpus_collocations') \
                .select('collocation_text, pos_pattern') \
                .eq('id', source_id).single().execute().data
            return row or {}
        return {}

    def _load_prompt_template(self, task_name: str) -> str:
        """
        Fetch the latest version of a named prompt template.
        Args:
            task_name: value of prompt_templates.task_name
        Returns:
            Template string ready for .format(**kwargs).
        Raises:
            RuntimeError if no template found.
        """
        result = self.db.table('prompt_templates') \
            .select('template_text') \
            .eq('task_name', task_name) \
            .order('version', desc=True) \
            .limit(1) \
            .execute()
        if not result.data:
            raise RuntimeError(f"No prompt template found for task_name='{task_name}'")
        return result.data[0]['template_text']


def get_sentence_pool(
    source_type: str,
    source_id: int,
    language_id: int,
    db,
    llm_client,
    model: str,
    target_count: int = DEFAULT_SENTENCE_TARGET,
) -> list[dict]:
    """
    Top-level function: build sentence pool using Reuse First strategy.
    Calls TranscriptMiner first; if fewer than MIN_TRANSCRIPT_SENTENCES are found,
    calls LLMSentenceGenerator for the remainder.
    Args:
        source_type:  'grammar', 'vocabulary', or 'collocation'
        source_id:    FK to the appropriate source table
        language_id:  FK to dim_languages.id
        db:           Supabase client
        llm_client:   callable for LLM calls
        model:        LLM model string
        target_count: total desired sentences (default 200)
    Returns:
        List of sentence dicts (length ≤ target_count).
    """
    lp      = LanguageProcessor.for_language(language_id)
    miner   = TranscriptMiner(db, lp)
    mined   = miner.mine(source_type, source_id, language_id)
    mined   = SentenceFilter.filter_quality(mined, language_id)

    if len(mined) >= MIN_TRANSCRIPT_SENTENCES:
        return mined[:target_count]

    needed    = target_count - len(mined)
    generator = LLMSentenceGenerator(db, llm_client, model)
    generated = generator.generate(source_type, source_id, language_id, needed)

    combined = SentenceFilter.deduplicate(mined + generated)
    return combined[:target_count]
```

**SQL required** (Supabase RPC for vocab mining — avoids N queries):

```sql
-- Function: tests_containing_sense
-- Returns tests where vocab_sense_ids contains the given sense.
-- Called by TranscriptMiner._mine_vocabulary via db.rpc().
CREATE OR REPLACE FUNCTION tests_containing_sense(
    p_sense_id    INTEGER,
    p_language_id INTEGER
)
RETURNS TABLE (
    id              UUID,
    transcript      TEXT,
    difficulty      NUMERIC,
    vocab_token_map JSONB
)
LANGUAGE sql STABLE
AS $$
    SELECT id, transcript, difficulty, vocab_token_map
    FROM tests
    WHERE vocab_sense_ids @> ARRAY[p_sense_id]
      AND language = p_language_id
      AND is_active = TRUE;
$$;
```

**Dependencies:** Task 0.5 (config), Task 1.1 (LanguageProcessor).

---

## Phase 3: Base Generator & Validation

### Task 3.1 — `base_generator.py`: ExerciseGenerator ABC

**Description:** Abstract base class for all 16 exercise type generators. Provides shared infrastructure: LLM calls with retry, prompt loading, batch insertion, and the `generate_batch` template method that all subclasses call.

**File:** `services/exercise_generation/base_generator.py`

```python
# services/exercise_generation/base_generator.py

import uuid
import logging
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ExerciseGenerator(ABC):
    """
    Abstract base class for all exercise generators.
    Subclasses implement generate_one() and exercise_type.
    The generate_batch() template method handles pool iteration, validation,
    and accumulation — subclasses do not override it.
    """

    exercise_type: str   # must be set by every concrete subclass
    source_type:   str   # 'grammar', 'vocabulary', or 'collocation' — set by subclass

    def __init__(self, db, language_id: int, model: str):
        """
        Args:
            db:          Supabase client
            language_id: target language FK
            model:       LLM model string from dim_languages.exercise_model
        """
        self.db          = db
        self.language_id = language_id
        self.model       = model

    @abstractmethod
    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate a single exercise item from a sentence dict.
        Returns a content JSONB dict on success, or None if this sentence is unsuitable.
        Args:
            sentence_dict: {sentence, translation, topic, source, cefr_level, test_id}
            source_id:     FK to the source entity (pattern_id, sense_id, collocation_id)
        Returns:
            Content dict ready for the exercises table, or None to skip.
        """

    def generate_batch(
        self,
        sentence_pool: list[dict],
        source_id: int,
        target_count: int,
        generation_batch_id: str,
    ) -> list[dict]:
        """
        Iterate the sentence pool, calling generate_one() for each sentence until
        target_count valid exercises are accumulated. Validates each result with
        ExerciseValidator before appending. Logs validation failures.
        Args:
            sentence_pool:       output of get_sentence_pool()
            source_id:           FK to source entity
            target_count:        how many exercises to produce
            generation_batch_id: UUID linking all exercises from this orchestrator run
        Returns:
            List of exercise row dicts ready for batch insert to exercises table.
        """
        from services.exercise_generation.validators import ExerciseValidator
        from services.exercise_generation.difficulty import DifficultyCalibrator

        validator  = ExerciseValidator()
        calibrator = DifficultyCalibrator()
        results    = []

        for sent in sentence_pool:
            if len(results) >= target_count:
                break
            try:
                content = self.generate_one(sent, source_id)
                if content is None:
                    continue
                is_valid, errors = validator.validate(content, self.exercise_type)
                if not is_valid:
                    logger.warning(
                        "Validation failed for %s: %s", self.exercise_type, errors
                    )
                    continue
                row = self._build_exercise_row(content, sent, source_id, generation_batch_id)
                row = calibrator.attach_difficulty(row, sent.get('cefr_level', 'B1'))
                results.append(row)
            except Exception as exc:
                logger.error("generate_one error for %s: %s", self.exercise_type, exc)

        return results

    def _build_exercise_row(
        self,
        content: dict,
        sentence_dict: dict,
        source_id: int,
        generation_batch_id: str,
    ) -> dict:
        """
        Assemble the full exercises table row dict from a content payload and metadata.
        Sets the correct source FK column based on self.source_type.
        Args:
            content:             JSONB content payload
            sentence_dict:       source sentence metadata dict
            source_id:           FK value
            generation_batch_id: batch UUID
        Returns:
            Dict matching exercises table columns.
        """
        row = {
            'id':                  str(uuid.uuid4()),
            'language_id':         self.language_id,
            'exercise_type':       self.exercise_type,
            'source_type':         self.source_type,
            'content':             content,
            'tags':                self._build_tags(source_id, sentence_dict),
            'cefr_level':          sentence_dict.get('cefr_level'),
            'is_active':           True,
            'generation_batch_id': generation_batch_id,
            'grammar_pattern_id':  None,
            'word_sense_id':       None,
            'corpus_collocation_id': None,
        }
        # Set the correct FK
        fk_map = {
            'grammar':     'grammar_pattern_id',
            'vocabulary':  'word_sense_id',
            'collocation': 'corpus_collocation_id',
        }
        row[fk_map[self.source_type]] = source_id
        return row

    def _build_tags(self, source_id: int, sentence_dict: dict) -> dict:
        """
        Build the tags JSONB dict for analytics. Subclasses may override to add
        type-specific tags.
        Args:
            source_id:     FK to source entity
            sentence_dict: source sentence metadata
        Returns:
            Tags dict.
        """
        return {
            'source_type':  self.source_type,
            'source_id':    source_id,
            'cefr_level':   sentence_dict.get('cefr_level'),
            'sentence_src': sentence_dict.get('source', 'unknown'),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def call_llm(self, prompt: str, response_format: str = 'json') -> dict | list:
        """
        Call the LLM via OpenRouter with retry on failure.
        Follows the existing pattern in services/test_generation/question_generator.py.
        Args:
            prompt:          complete prompt string
            response_format: 'json' or 'text'
        Returns:
            Parsed JSON dict/list, or raw text string.
        Raises:
            Exception after 3 failed attempts (tenacity handles retry).
        """
        from services.llm_client import call_llm as _call_llm  # existing utility
        return _call_llm(prompt, model=self.model, response_format=response_format)

    def load_prompt_template(self, task_name: str) -> str:
        """
        Fetch the latest version of a named prompt template from prompt_templates.
        Shared by all subclasses. Caches the result for the lifetime of this instance.
        Args:
            task_name: prompt_templates.task_name value
        Returns:
            Template string.
        """
        if not hasattr(self, '_template_cache'):
            self._template_cache: dict[str, str] = {}
        if task_name not in self._template_cache:
            result = self.db.table('prompt_templates') \
                .select('template_text') \
                .eq('task_name', task_name) \
                .order('version', desc=True) \
                .limit(1) \
                .execute()
            if not result.data:
                raise RuntimeError(f"No prompt template for task_name='{task_name}'")
            self._template_cache[task_name] = result.data[0]['template_text']
        return self._template_cache[task_name]

    def batch_insert(self, rows: list[dict]) -> int:
        """
        Insert a list of exercise rows into the exercises table in a single batch call.
        Args:
            rows: list of exercise row dicts (output of generate_batch)
        Returns:
            Count of inserted rows.
        """
        if not rows:
            return 0
        result = self.db.table('exercises').insert(rows).execute()
        return len(result.data or [])
```

**Integration:** Mirrors `services/test_generation/base_generator.py` pattern. The `call_llm` wrapper references the existing `services/llm_client.py` utility (same as used by `QuestionGenerator`).

**Dependencies:** Task 0.5 (config), Task 3.2 (validators), Task 4.1 (difficulty).

---

### Task 3.2 — `validators.py`: ExerciseValidator

**Description:** Deterministic validation of all exercise types. No LLM calls. Called by `ExerciseGenerator.generate_batch()` on every generated item before it is accepted.

**File:** `services/exercise_generation/validators.py`

```python
# services/exercise_generation/validators.py

from services.exercise_generation.config import (
    REQUIRED_FIELDS_BY_TYPE, MCQ_TYPES, EXPECTED_OPTION_COUNT,
)


class ExerciseValidator:
    """
    Runs deterministic structural validation on exercise content dicts.
    No LLM calls. Called after every generate_one() in the base generator.
    """

    def validate(self, content: dict, exercise_type: str) -> tuple[bool, list[str]]:
        """
        Validate a content dict for the given exercise type.
        Aggregates errors from all applicable checks.
        Returns (True, []) on success; (False, [error_strings]) on failure.
        Warnings (non-critical) are included in errors list with 'WARN:' prefix
        but do not cause is_valid=False.
        Args:
            content:       the exercise content JSONB dict
            exercise_type: one of ALL_EXERCISE_TYPES
        Returns:
            (is_valid, errors) tuple.
        """
        errors: list[str] = []

        self._check_required_fields(content, exercise_type, errors)

        if exercise_type in MCQ_TYPES:
            self._check_mcq(content, exercise_type, errors)

        dispatch = {
            'jumbled_sentence':        self._check_jumbled_sentence,
            'spot_incorrect_sentence': self._check_spot_incorrect_sentence,
            'spot_incorrect_part':     self._check_spot_incorrect_part,
            'text_flashcard':          self._check_text_flashcard,
            'listening_flashcard':     self._check_listening_flashcard,
            'cloze_completion':        self._check_cloze_completion,
            'semantic_discrimination': self._check_semantic_discrimination,
            'verb_noun_match':         self._check_verb_noun_match,
            'nl_tl_translation':       self._check_nl_tl_translation,
        }
        checker = dispatch.get(exercise_type)
        if checker:
            checker(content, errors)

        critical = [e for e in errors if not e.startswith('WARN:')]
        return (len(critical) == 0), errors

    # --- Field presence ---

    def _check_required_fields(
        self, content: dict, exercise_type: str, errors: list[str]
    ) -> None:
        for field in REQUIRED_FIELDS_BY_TYPE.get(exercise_type, []):
            if field not in content or content[field] is None:
                errors.append(f"Missing required field: {field}")

    # --- MCQ universal checks ---

    def _check_mcq(
        self, content: dict, exercise_type: str, errors: list[str]
    ) -> None:
        correct  = content.get('correct_answer') or content.get('correct_nl') or content.get('correct')
        options  = content.get('options', [])
        expected = EXPECTED_OPTION_COUNT.get(exercise_type, 4)

        if correct and options:
            if correct not in options:
                errors.append("Correct answer is not present in options")
            if options[0] != correct:
                errors.append("V3 rule violation: correct answer must be options[0]")

        if options:
            if len(options) != len(set(str(o).lower().strip() for o in options)):
                errors.append("Duplicate options detected")
            if len(options) != expected:
                errors.append(f"Expected {expected} options, got {len(options)}")

    # --- Type-specific checks ---

    def _check_jumbled_sentence(self, content: dict, errors: list[str]) -> None:
        chunks   = content.get('chunks', [])
        ordering = content.get('correct_ordering', [])
        if len(chunks) < 3:
            errors.append("jumbled_sentence requires at least 3 chunks")
        if len(chunks) > 7:
            errors.append("jumbled_sentence has too many chunks (max 7)")
        if sorted(ordering) != list(range(len(chunks))):
            errors.append("correct_ordering must reference all indices 0..n-1")

    def _check_spot_incorrect_sentence(self, content: dict, errors: list[str]) -> None:
        sentences = content.get('sentences', [])
        incorrect = [s for s in sentences if not s.get('is_correct', True)]
        correct   = [s for s in sentences if s.get('is_correct', True)]
        if len(incorrect) != 1:
            errors.append(f"spot_incorrect_sentence must have exactly 1 incorrect sentence, found {len(incorrect)}")
        if len(correct) < 3:
            errors.append(f"spot_incorrect_sentence must have at least 3 correct sentences, found {len(correct)}")
        if len(sentences) == 4 and sentences[3].get('is_correct', True):
            errors.append("V3 rule: incorrect sentence must be sentences[3]")

    def _check_spot_incorrect_part(self, content: dict, errors: list[str]) -> None:
        parts       = content.get('parts', [])
        error_parts = [p for p in parts if p.get('is_error')]
        if len(error_parts) != 1:
            errors.append(f"spot_incorrect_part must have exactly 1 error part, found {len(error_parts)}")
        for ep in error_parts:
            if not ep.get('correct_form'):
                errors.append("Error part must include correct_form")
            if not ep.get('explanation'):
                errors.append("Error part must include explanation")

    def _check_text_flashcard(self, content: dict, errors: list[str]) -> None:
        if not content.get('highlight_word') or content['highlight_word'] not in content.get('front_sentence', ''):
            errors.append("highlight_word must appear in front_sentence (wrapped in **)")
        if not content.get('sense_id'):
            errors.append("text_flashcard must have sense_id")

    def _check_listening_flashcard(self, content: dict, errors: list[str]) -> None:
        url = content.get('front_audio_url', '')
        if not url.startswith('http'):
            errors.append("listening_flashcard front_audio_url must be a valid URL")

    def _check_cloze_completion(self, content: dict, errors: list[str]) -> None:
        if '___' not in content.get('sentence_with_blank', ''):
            errors.append("cloze_completion sentence_with_blank must contain '___'")
        if not content.get('distractor_tags'):
            errors.append("WARN: cloze_completion missing distractor_tags (analytics impact)")

    def _check_semantic_discrimination(self, content: dict, errors: list[str]) -> None:
        sentences    = content.get('sentences', [])
        correct_cnt  = sum(1 for s in sentences if s.get('is_correct'))
        if correct_cnt != 1:
            errors.append(f"semantic_discrimination must have exactly 1 correct sentence, found {correct_cnt}")
        if len(sentences) < 4:
            errors.append("semantic_discrimination requires 4 sentences")

    def _check_verb_noun_match(self, content: dict, errors: list[str]) -> None:
        verbs  = content.get('verbs', [])
        nouns  = content.get('nouns', [])
        pairs  = content.get('valid_pairs', [])
        if len(verbs) < 2 or len(nouns) < 2:
            errors.append("verb_noun_match requires at least 2 verbs and 2 nouns")
        for pair in pairs:
            if not (isinstance(pair, list) and len(pair) == 2):
                errors.append("valid_pairs entries must be [verb_idx, noun_idx] lists")
                break
            v_idx, n_idx = pair
            if v_idx >= len(verbs) or n_idx >= len(nouns):
                errors.append(f"valid_pair {pair} references out-of-bounds index")
                break

    def _check_nl_tl_translation(self, content: dict, errors: list[str]) -> None:
        if not content.get('primary_tl'):
            errors.append("nl_tl_translation must have primary_tl")
        if not content.get('grading_notes'):
            errors.append("nl_tl_translation must have grading_notes")
```

**Dependencies:** Task 0.5 (config).

---

## Phase 4: Difficulty Calibration

### Task 4.1 — `difficulty.py`: DifficultyCalibrator

**Description:** Attaches static difficulty scores and IRT seed values to exercise rows. No LLM. Called by `ExerciseGenerator.generate_batch()` after validation.

**File:** `services/exercise_generation/difficulty.py`

```python
# services/exercise_generation/difficulty.py

from services.exercise_generation.config import CEFR_TO_IRT


class DifficultyCalibrator:
    """
    Computes and attaches static difficulty + IRT seed values to exercise row dicts.
    Formula: difficulty_static = 0.50 × cefr_numeric + 0.50 × sentence_length_score
    IRT seeds are initialised from CEFR level; updated dynamically after ≥ 30 attempts
    by a separate IRT update job (not in this module).
    """

    CEFR_NUMERIC: dict[str, float] = {
        'A1': 1.0, 'A2': 2.0, 'B1': 3.0, 'B2': 3.5, 'C1': 4.0, 'C2': 5.0,
    }

    def attach_difficulty(self, row: dict, cefr_level: str) -> dict:
        """
        Compute and attach difficulty_static, irt_difficulty, and irt_discrimination
        to an exercise row dict. Mutates and returns the row.
        Args:
            row:        exercise row dict (from _build_exercise_row)
            cefr_level: CEFR level string ('A1'–'C2')
        Returns:
            The same row dict with difficulty fields populated.
        """
        sentence = row.get('content', {}).get('original_sentence') \
                   or row.get('content', {}).get('sentence_with_blank') \
                   or row.get('content', {}).get('tl_sentence', '')

        cefr_score    = self.CEFR_NUMERIC.get(cefr_level, 3.0)
        length_score  = self._sentence_length_score(sentence, row.get('language_id', 2))
        static        = round(0.5 * cefr_score + 0.5 * length_score, 2)

        row['difficulty_static'] = static
        row['irt_difficulty']    = CEFR_TO_IRT.get(cefr_level, 0.0)
        row['irt_discrimination'] = 1.0  # default; updated by IRT job after 30+ attempts
        row['cefr_level']         = cefr_level
        return row

    def _sentence_length_score(self, sentence: str, language_id: int) -> float:
        """
        Map sentence length to a 1–5 scale for use in the difficulty formula.
        English: word count. Chinese/Japanese: character count.
        Args:
            sentence:    the primary sentence string from exercise content
            language_id: FK to dim_languages
        Returns:
            Float score in [1.0, 5.0].
        """
        from services.exercise_generation.config import LANG_CHINESE, LANG_JAPANESE
        if not sentence:
            return 2.5
        if language_id == LANG_CHINESE:
            length = len(sentence)
            breakpoints = [(10, 1.0), (20, 2.0), (35, 3.0), (50, 4.0)]
        elif language_id == LANG_JAPANESE:
            length = len(sentence)
            breakpoints = [(10, 1.0), (25, 2.0), (40, 3.0), (60, 4.0)]
        else:
            length = len(sentence.split())
            breakpoints = [(5, 1.0), (10, 2.0), (18, 3.0), (28, 4.0)]

        for threshold, score in breakpoints:
            if length <= threshold:
                return score
        return 5.0
```

**Dependencies:** Task 0.5 (config).

---

## Phase 5: Exercise Generators

### Task 5.1 — `generators/cloze.py`: ClozeGenerator

**Description:** Generates `cloze_completion` exercises. Sources sentence from pool, calls LLM once per sentence to produce distractors with type tags. Enforces `options[0]` = correct answer.

**File:** `services/exercise_generation/generators/cloze.py`

```python
# services/exercise_generation/generators/cloze.py

from services.exercise_generation.base_generator import ExerciseGenerator


class ClozeGenerator(ExerciseGenerator):
    """
    Generates cloze_completion exercises.
    Per sentence: identifies the target word/phrase, blanks it, calls LLM for
    3 tagged distractors (semantic, form_error, learner_error).
    LLM call: 1 per exercise item.
    """

    exercise_type = 'cloze_completion'
    source_type   = 'grammar'  # overridden per instantiation if needed

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate one cloze exercise from a sentence dict.
        Identifies target word from source metadata, blanks it, fetches distractors.
        Args:
            sentence_dict: {sentence, cefr_level, test_id, ...}
            source_id:     grammar_pattern_id, word_sense_id, or corpus_collocation_id
        Returns:
            Content dict or None if target word cannot be identified.
        """
        sentence    = sentence_dict['sentence']
        target_word = self._identify_target_word(sentence, source_id)
        if not target_word:
            return None

        blanked = sentence.replace(target_word, '___', 1)
        payload = self._generate_distractors(
            sentence, blanked, target_word, sentence_dict.get('cefr_level', 'B1')
        )
        if not payload:
            return None

        return {
            'sentence_with_blank': blanked,
            'original_sentence':   sentence,
            'correct_answer':      target_word,
            'options':             [target_word] + payload['distractors'],
            'distractor_tags':     payload['distractor_tags'],
            'explanation':         payload.get('explanation', ''),
            'source_test_id':      sentence_dict.get('test_id'),
        }

    def _identify_target_word(self, sentence: str, source_id: int) -> str | None:
        """
        For vocabulary source: look up the word text from dim_word_senses.
        For grammar source: use pattern metadata to identify the construction in the sentence.
        For collocation source: look up collocation_text from corpus_collocations.
        Returns the target string if found in sentence, else None.
        Args:
            sentence:  the source sentence
            source_id: FK to the source entity
        Returns:
            Target word/phrase string or None.
        """
        if self.source_type == 'vocabulary':
            row = self.db.table('dim_word_senses').select('word') \
                .eq('id', source_id).single().execute().data
            word = row.get('word', '') if row else ''
            return word if word and word.lower() in sentence.lower() else None

        elif self.source_type == 'collocation':
            row = self.db.table('corpus_collocations').select('collocation_text') \
                .eq('id', source_id).single().execute().data
            col = row.get('collocation_text', '') if row else ''
            return col if col and col.lower() in sentence.lower() else None

        elif self.source_type == 'grammar':
            # For grammar, target word is the pattern construction — identified by LLM
            # as part of distractor generation call; return a sentinel to proceed
            return '__grammar_target__'

        return None

    def _generate_distractors(
        self,
        original_sentence: str,
        blanked: str,
        correct_answer: str,
        cefr_level: str,
    ) -> dict | None:
        """
        Call LLM to generate 3 tagged distractors for the blank.
        Prompt instructs LLM to classify each distractor as: semantic, form_error, learner_error.
        Returns parsed payload or None on LLM failure.
        Args:
            original_sentence: full sentence without blank
            blanked:           sentence with ___ in place of target
            correct_answer:    the correct word/phrase
            cefr_level:        for learner_error calibration
        Returns:
            {'distractors': [...], 'distractor_tags': {...}, 'explanation': '...'} or None.
        """
        template = self.load_prompt_template('cloze_distractor_generation')
        prompt   = template.format(
            original_sentence=original_sentence,
            sentence_with_blank=blanked,
            correct_answer=correct_answer,
            cefr_level=cefr_level,
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            if len(distractors) < 3:
                return None
            return {
                'distractors':     distractors[:3],
                'distractor_tags': result.get('distractor_tags', {}),
                'explanation':     result.get('explanation', ''),
            }
        except Exception:
            return None
```

**Prompt template name:** `cloze_distractor_generation`
**Prompt should instruct LLM to return:**
```json
{
  "distractors": ["word1", "word2", "word3"],
  "distractor_tags": {"word1": "semantic", "word2": "form_error", "word3": "learner_error"},
  "explanation": "..."
}
```
**Note:** If source_type is `grammar` and `correct_answer` is `'__grammar_target__'`, the prompt must instruct the LLM to first identify the construction being tested. Add a grammar-aware variant to the prompt template.

**Dependencies:** Task 3.1 (ExerciseGenerator), Task 3.2 (validators).

---

### Task 5.2 — `generators/jumbled_sentence.py`: JumbledSentenceGenerator

**Description:** Generates `jumbled_sentence` exercises. Purely Python — no LLM calls. Delegates chunking to `LanguageProcessor.chunk_sentence()`.

**File:** `services/exercise_generation/generators/jumbled_sentence.py`

```python
# services/exercise_generation/generators/jumbled_sentence.py

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.language_processor import LanguageProcessor


class JumbledSentenceGenerator(ExerciseGenerator):
    """
    Generates jumbled_sentence exercises using Python NLP only — no LLM.
    Delegates to LanguageProcessor.chunk_sentence() for language-appropriate chunking.
    """

    exercise_type = 'jumbled_sentence'
    source_type   = 'grammar'  # can be overridden

    def __init__(self, db, language_id: int, model: str = '', source_type: str = 'grammar'):
        super().__init__(db, language_id, model)
        self.source_type    = source_type
        self.lang_processor = LanguageProcessor.for_language(language_id)

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Split a sentence into chunks. Returns content dict or None if < 3 chunks.
        No LLM call.
        Args:
            sentence_dict: {sentence, test_id, ...}
            source_id:     not used directly (sentence already sourced)
        Returns:
            Content dict with chunks and correct_ordering, or None.
        """
        sentence = sentence_dict['sentence']
        try:
            chunks = self.lang_processor.chunk_sentence(sentence)
        except ValueError:
            return None

        if len(chunks) < 3:
            return None

        return {
            'original_sentence': sentence,
            'chunks':            chunks,
            'correct_ordering':  list(range(len(chunks))),
            'source_test_id':    sentence_dict.get('test_id'),
        }
```

**Dependencies:** Task 1.1 (LanguageProcessor), Task 3.1 (ExerciseGenerator).

---

### Task 5.3 — `generators/translation.py`: TlNlTranslationGenerator + NlTlTranslationGenerator

**Description:** Two related generators. `TlNlTranslationGenerator` (MCQ) sources TL sentence from pool, calls LLM for 1 correct + 2 wrong NL translations. `NlTlTranslationGenerator` (production) sources TL sentence, calls LLM for grading criteria and acceptable variants.

**File:** `services/exercise_generation/generators/translation.py`

```python
# services/exercise_generation/generators/translation.py

from services.exercise_generation.base_generator import ExerciseGenerator


class TlNlTranslationGenerator(ExerciseGenerator):
    """
    Generates tl_nl_translation (MCQ) exercises.
    TL sentence sourced from pool → LLM generates 1 correct + 2 wrong NL translations.
    options[0] is always the correct translation (V3 rule).
    NL-specific content (options) is stored here as placeholder; Plan 6 overwrites
    via content_translations for each supported NL.
    """

    exercise_type = 'tl_nl_translation'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar',
                 nl_language_code: str = 'en'):
        super().__init__(db, language_id, model)
        self.source_type     = source_type
        self.nl_language_code = nl_language_code

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate one tl_nl_translation exercise.
        Args:
            sentence_dict: {sentence, cefr_level, test_id, ...}
            source_id:     grammar_pattern_id or word_sense_id
        Returns:
            Content dict with tl_sentence, correct_nl, options[0]=correct, or None.
        """
        tl_sentence = sentence_dict['sentence']
        template    = self.load_prompt_template('tl_nl_translation_generation')
        prompt      = template.format(
            tl_sentence=tl_sentence,
            nl_language=self.nl_language_code,
        )
        try:
            result      = self.call_llm(prompt, response_format='json')
            correct_nl  = result.get('correct_nl', '')
            wrong_nls   = result.get('wrong_options', [])
            if not correct_nl or len(wrong_nls) < 2:
                return None
            return {
                'tl_sentence':    tl_sentence,
                'tl_language':    self._get_language_code(),
                'nl_language':    self.nl_language_code,
                'correct_nl':     correct_nl,
                'options':        [correct_nl] + wrong_nls[:2],
                'source_test_id': sentence_dict.get('test_id'),
            }
        except Exception:
            return None

    def _get_language_code(self) -> str:
        """Fetch language ISO code from dim_languages for tagging."""
        row = self.db.table('dim_languages').select('code') \
            .eq('id', self.language_id).single().execute().data
        return row.get('code', 'unknown') if row else 'unknown'


class NlTlTranslationGenerator(ExerciseGenerator):
    """
    Generates nl_tl_translation (production) exercises.
    TL sentence from pool → LLM generates NL version, grading_notes, acceptable_variants.
    User types or constructs TL freely; graded by grading_notes criteria.
    """

    exercise_type = 'nl_tl_translation'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar',
                 nl_language_code: str = 'en'):
        super().__init__(db, language_id, model)
        self.source_type      = source_type
        self.nl_language_code = nl_language_code

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate one nl_tl_translation exercise.
        Args:
            sentence_dict: {sentence, cefr_level, test_id, ...}
            source_id:     grammar_pattern_id or word_sense_id
        Returns:
            Content dict with nl_sentence (placeholder), primary_tl, grading_notes, or None.
        """
        tl_sentence = sentence_dict['sentence']
        template    = self.load_prompt_template('nl_tl_translation_generation')
        prompt      = template.format(
            tl_sentence=tl_sentence,
            nl_language=self.nl_language_code,
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            if not result.get('nl_sentence') or not result.get('grading_notes'):
                return None
            return {
                'nl_sentence':         result['nl_sentence'],
                'nl_language':         self.nl_language_code,
                'tl_language':         self._get_language_code(),
                'primary_tl':          tl_sentence,
                'grading_notes':       result['grading_notes'],
                'acceptable_variants': result.get('acceptable_variants', []),
                'source_test_id':      sentence_dict.get('test_id'),
            }
        except Exception:
            return None

    def _get_language_code(self) -> str:
        row = self.db.table('dim_languages').select('code') \
            .eq('id', self.language_id).single().execute().data
        return row.get('code', 'unknown') if row else 'unknown'
```

**Prompt template names:** `tl_nl_translation_generation`, `nl_tl_translation_generation`

**Dependencies:** Task 3.1 (ExerciseGenerator).

---

### Task 5.4 — `generators/flashcard.py`: FlashcardGenerator

**Description:** Generates `text_flashcard` and `listening_flashcard` exercises. No LLM. Text flashcards assembled from `dim_word_senses` definitions. Audio flashcards call existing `AudioSynthesizer` for TTS, saving to Cloudflare R2.

**File:** `services/exercise_generation/generators/flashcard.py`

```python
# services/exercise_generation/generators/flashcard.py

from services.exercise_generation.base_generator import ExerciseGenerator


class FlashcardGenerator(ExerciseGenerator):
    """
    Generates text_flashcard and listening_flashcard exercises.
    No LLM calls. Definitions sourced from dim_word_senses.
    Audio flashcards call the existing AudioSynthesizer → Cloudflare R2.
    """

    exercise_type = 'text_flashcard'  # overridden per mode
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str = '',
                 mode: str = 'text', source_type: str = 'vocabulary',
                 audio_synthesizer=None):
        """
        Args:
            mode:              'text' or 'listening'
            source_type:       'vocabulary', 'grammar', or 'collocation'
            audio_synthesizer: AudioSynthesizer instance (required for 'listening' mode)
        """
        super().__init__(db, language_id, model)
        self.mode             = mode
        self.source_type      = source_type
        self.audio_synthesizer = audio_synthesizer
        self.exercise_type    = 'listening_flashcard' if mode == 'listening' else 'text_flashcard'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Assemble a flashcard from sentence + dim_word_senses definition.
        For listening mode: synthesise TTS audio and upload to R2.
        Args:
            sentence_dict: {sentence, test_id, ...}
            source_id:     word_sense_id (for vocabulary source) or grammar_pattern_id
        Returns:
            Content dict or None on failure.
        """
        sentence = sentence_dict['sentence']
        word, definition, sense_id = self._load_sense_data(source_id)
        if not word or word.lower() not in sentence.lower():
            return None

        if self.mode == 'text':
            return self._assemble_text_flashcard(sentence, word, definition, sense_id, sentence_dict)
        else:
            return self._assemble_listening_flashcard(sentence, word, definition, sense_id, sentence_dict)

    def _load_sense_data(self, source_id: int) -> tuple[str, str, int]:
        """
        Load word text and definition from dim_word_senses.
        For grammar sources: return placeholder data (grammar pattern name used as word).
        Args:
            source_id: dim_word_senses.id or dim_grammar_patterns.id depending on source_type
        Returns:
            (word, definition, sense_id) tuple. Returns ('', '', 0) on failure.
        """
        if self.source_type == 'vocabulary':
            row = self.db.table('dim_word_senses').select('word, definition, id') \
                .eq('id', source_id).single().execute().data
            if not row:
                return '', '', 0
            return row['word'], row['definition'], row['id']
        elif self.source_type == 'collocation':
            row = self.db.table('corpus_collocations').select('collocation_text, id') \
                .eq('id', source_id).single().execute().data
            if not row:
                return '', '', 0
            return row['collocation_text'], '', row['id']
        return '', '', 0

    def _assemble_text_flashcard(
        self,
        sentence: str,
        word: str,
        definition: str,
        sense_id: int,
        sentence_dict: dict,
    ) -> dict:
        """
        Build text flashcard content dict.
        Highlights word with markdown bold on front_sentence.
        back_translation is set to None — populated from content_translations at serve time (Plan 6).
        """
        front = sentence.replace(word, f'**{word}**', 1)
        return {
            'front_sentence':   front,
            'highlight_word':   word,
            'back_sentence':    sentence,
            'back_translation': None,
            'word_of_interest': word,
            'word_definition':  definition,
            'sense_id':         sense_id,
            'source_test_id':   sentence_dict.get('test_id'),
        }

    def _assemble_listening_flashcard(
        self,
        sentence: str,
        word: str,
        definition: str,
        sense_id: int,
        sentence_dict: dict,
    ) -> dict | None:
        """
        Build listening flashcard: synthesise audio for sentence, upload to R2.
        Calls self.audio_synthesizer (existing AudioSynthesizer).
        Args match _assemble_text_flashcard.
        Returns None if audio synthesis fails.
        """
        if not self.audio_synthesizer:
            return None
        try:
            audio_url = self.audio_synthesizer.synthesize_and_upload(
                text=sentence,
                language_id=self.language_id,
                purpose='exercise',
            )
        except Exception:
            return None

        return {
            'front_audio_url':  audio_url,
            'back_sentence':    sentence,
            'back_translation': None,
            'word_of_interest': word,
            'word_definition':  definition,
            'sense_id':         sense_id,
            'source_test_id':   sentence_dict.get('test_id'),
        }
```

**Integration:** `AudioSynthesizer` is the existing class in the codebase. Pass it in at construction time from the orchestrator — no direct import needed in this file.

**Dependencies:** Task 3.1 (ExerciseGenerator).

---

### Task 5.5 — `generators/spot_incorrect.py`: SpotIncorrectGenerator

**Description:** Generates both `spot_incorrect_sentence` and `spot_incorrect_part` from a **single LLM call**. Sources 3 correct sentences from pool, calls LLM once for the incorrect sentence + parts array, then produces 2 exercise rows.

**File:** `services/exercise_generation/generators/spot_incorrect.py`

```python
# services/exercise_generation/generators/spot_incorrect.py

import uuid
from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.validators import ExerciseValidator
from services.exercise_generation.difficulty import DifficultyCalibrator


class SpotIncorrectGenerator(ExerciseGenerator):
    """
    Generates spot_incorrect_sentence + spot_incorrect_part pairs.
    One LLM call produces content for both exercise types.
    Overrides generate_batch() because one call → two exercise rows.
    """

    exercise_type = 'spot_incorrect_sentence'  # primary type; second type appended in batch
    source_type   = 'grammar'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """Not used directly — generate_batch_pair() handles the paired logic."""
        raise NotImplementedError("Use generate_batch() for SpotIncorrectGenerator")

    def generate_batch(
        self,
        sentence_pool: list[dict],
        source_id: int,
        target_count: int,
        generation_batch_id: str,
    ) -> list[dict]:
        """
        Override: groups sentence_pool into triplets, calls LLM for each triplet,
        produces (spot_incorrect_sentence, spot_incorrect_part) pairs.
        target_count is the number of spot_incorrect_sentence items desired;
        an equal count of spot_incorrect_part items are also produced.
        Args:
            sentence_pool:       list of sentence dicts (need at least 3 × target_count sentences)
            source_id:           grammar_pattern_id
            target_count:        number of spot_incorrect_sentence items
            generation_batch_id: UUID for batch tracking
        Returns:
            List of exercise rows (2 × successful triplets — both types interleaved).
        """
        validator  = ExerciseValidator()
        calibrator = DifficultyCalibrator()
        results    = []

        # Group sentences into triplets
        triplets = [sentence_pool[i:i+3] for i in range(0, len(sentence_pool) - 2, 3)]

        for triplet in triplets:
            if len(results) >= target_count * 2:
                break
            if len(triplet) < 3:
                continue

            pair = self._generate_pair(triplet, source_id)
            if pair is None:
                continue

            sent_content, part_content = pair
            cefr = triplet[0].get('cefr_level', 'B1')

            for ex_type, content in [
                ('spot_incorrect_sentence', sent_content),
                ('spot_incorrect_part',     part_content),
            ]:
                is_valid, errors = validator.validate(content, ex_type)
                if not is_valid:
                    break
                row = self._build_exercise_row(content, triplet[0], source_id, generation_batch_id)
                row['exercise_type'] = ex_type
                row = calibrator.attach_difficulty(row, cefr)
                results.append(row)

        return results

    def _generate_pair(
        self, triplet: list[dict], source_id: int
    ) -> tuple[dict, dict] | None:
        """
        Call LLM with 3 correct sentences to generate 1 incorrect sentence + parts breakdown.
        Returns (sentence_content, part_content) or None on failure.
        Args:
            triplet:   list of 3 sentence dicts (all correct)
            source_id: grammar_pattern_id for context
        Returns:
            Tuple of (spot_incorrect_sentence content, spot_incorrect_part content) or None.
        """
        correct_texts = [s['sentence'] for s in triplet]
        template      = self.load_prompt_template('spot_incorrect_generation')
        prompt        = template.format(
            sentence_1=correct_texts[0],
            sentence_2=correct_texts[1],
            sentence_3=correct_texts[2],
        )
        try:
            result = self.call_llm(prompt, response_format='json')
        except Exception:
            return None

        incorrect_sentence = result.get('incorrect_sentence', '')
        error_description  = result.get('error_description', '')
        error_type         = result.get('error_type', '')
        parts              = result.get('parts', [])

        if not incorrect_sentence or not parts:
            return None

        sentence_content = {
            'sentences': [
                {'text': correct_texts[0], 'is_correct': True, 'source_test_id': triplet[0].get('test_id')},
                {'text': correct_texts[1], 'is_correct': True, 'source_test_id': triplet[1].get('test_id')},
                {'text': correct_texts[2], 'is_correct': True, 'source_test_id': triplet[2].get('test_id')},
                {'text': incorrect_sentence, 'is_correct': False,
                 'error_description': error_description, 'error_type': error_type},
            ]
        }

        part_content = {
            'sentence': incorrect_sentence,
            'parts':    parts,
        }

        return sentence_content, part_content
```

**Prompt template name:** `spot_incorrect_generation`
**Prompt returns:**
```json
{
  "incorrect_sentence": "...",
  "error_description": "...",
  "error_type": "subject_verb_agreement",
  "parts": [
    {"text": "He", "is_error": false},
    {"text": "have been", "is_error": true, "correct_form": "has been", "explanation": "..."},
    {"text": "working here", "is_error": false},
    {"text": "since 2020", "is_error": false}
  ]
}
```

**Dependencies:** Task 3.1 (ExerciseGenerator), Task 3.2 (validators), Task 4.1 (difficulty).

---

### Task 5.6 — `generators/semantic.py`: SemanticDiscrimGenerator + OddOneOutGenerator

**Description:** Two LLM-heavy generators for semantic and associative exercises.

**File:** `services/exercise_generation/generators/semantic.py`

```python
# services/exercise_generation/generators/semantic.py

from services.exercise_generation.base_generator import ExerciseGenerator


class SemanticDiscrimGenerator(ExerciseGenerator):
    """
    Generates semantic_discrimination exercises.
    LLM generates 4 sentences: 1 with correct usage of the target word/sense,
    3 with plausible-but-wrong usages (register mismatch, wrong collocation, etc).
    Correct sentence is always sentences[0] with is_correct=True; frontend shuffles.
    """

    exercise_type = 'semantic_discrimination'
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'vocabulary'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate 4 usage sentences for the target word/sense.
        Args:
            sentence_dict: provides context sentence and cefr_level
            source_id:     word_sense_id
        Returns:
            Content dict with 'sentences' array and 'explanation', or None.
        """
        sense_row = self.db.table('dim_word_senses') \
            .select('word, definition, cefr_level') \
            .eq('id', source_id).single().execute().data
        if not sense_row:
            return None

        template = self.load_prompt_template('semantic_discrimination_generation')
        prompt   = template.format(
            word=sense_row['word'],
            definition=sense_row['definition'],
            cefr_level=sense_row.get('cefr_level', 'B1'),
            example_sentence=sentence_dict.get('sentence', ''),
        )
        try:
            result     = self.call_llm(prompt, response_format='json')
            sentences  = result.get('sentences', [])
            explanation = result.get('explanation', '')
            if len(sentences) < 4:
                return None
            # Ensure correct sentence is first
            correct    = [s for s in sentences if s.get('is_correct')]
            incorrect  = [s for s in sentences if not s.get('is_correct')]
            if not correct:
                return None
            ordered    = correct[:1] + incorrect[:3]
            return {'sentences': ordered, 'explanation': explanation}
        except Exception:
            return None


class OddOneOutGenerator(ExerciseGenerator):
    """
    Generates odd_one_out exercises.
    LLM generates a group of 4 words/phrases where 3 share a semantic property and 1 does not.
    odd_index is always 3 in stored JSON (frontend shuffles all 4 before display).
    """

    exercise_type = 'odd_one_out'
    source_type   = 'vocabulary'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'vocabulary'):
        super().__init__(db, language_id, model)
        self.source_type = source_type

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate an odd-one-out group anchored to the target sense.
        The target sense's word is one of the 3 'correct' members of the group.
        Args:
            sentence_dict: context (may be unused for pure LLM generation)
            source_id:     word_sense_id
        Returns:
            Content dict with items, odd_index, shared_property, explanation, or None.
        """
        sense_row = self.db.table('dim_word_senses') \
            .select('word, definition') \
            .eq('id', source_id).single().execute().data
        if not sense_row:
            return None

        template = self.load_prompt_template('odd_one_out_generation')
        prompt   = template.format(
            word=sense_row['word'],
            definition=sense_row['definition'],
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            items  = result.get('items', [])
            if len(items) != 4:
                return None
            odd_item  = result.get('odd_item')
            odd_index = items.index(odd_item) if odd_item in items else None
            if odd_index is None:
                return None
            # Reorder so odd_item is at index 3
            group = [i for i in items if i != odd_item] + [odd_item]
            return {
                'items':           group,
                'odd_index':       3,
                'shared_property': result.get('shared_property', ''),
                'explanation':     result.get('explanation', ''),
            }
        except Exception:
            return None
```

**Prompt template names:** `semantic_discrimination_generation`, `odd_one_out_generation`

**Dependencies:** Task 3.1 (ExerciseGenerator).

---

### Task 5.7 — `generators/collocation.py`: CollocationGapFillGenerator + CollocationRepairGenerator + OddCollocationOutGenerator

**Description:** Three collocation-focused generators sourcing from `corpus_collocations`. All require LLM for distractor/repair/odd generation.

**File:** `services/exercise_generation/generators/collocation.py`

```python
# services/exercise_generation/generators/collocation.py

from services.exercise_generation.base_generator import ExerciseGenerator


class CollocationGapFillGenerator(ExerciseGenerator):
    """
    Generates collocation_gap_fill exercises.
    Sentence contains the collocation; the collocate word is blanked.
    LLM generates 3 distractors (semantically plausible but unnatural collocates).
    options[0] = correct collocate (V3 rule).
    """

    exercise_type = 'collocation_gap_fill'
    source_type   = 'collocation'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate one collocation gap-fill item.
        Args:
            sentence_dict: {sentence, test_id, ...} containing the target collocation
            source_id:     corpus_collocations.id
        Returns:
            Content dict or None.
        """
        col_row = self.db.table('corpus_collocations') \
            .select('collocation_text, head_word, collocate') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        collocate = col_row.get('collocate', '')
        sentence  = sentence_dict['sentence']

        if not collocate or collocate.lower() not in sentence.lower():
            return None

        blanked  = sentence.replace(collocate, '___', 1)
        template = self.load_prompt_template('collocation_gap_fill_generation')
        prompt   = template.format(
            head_word=col_row.get('head_word', ''),
            collocate=collocate,
            sentence=sentence,
        )
        try:
            result      = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            if len(distractors) < 3:
                return None
            return {
                'sentence':    blanked,
                'correct':     collocate,
                'options':     [collocate] + distractors[:3],
                'collocation': col_row.get('collocation_text', ''),
                'source_test_id': sentence_dict.get('test_id'),
            }
        except Exception:
            return None


class CollocationRepairGenerator(ExerciseGenerator):
    """
    Generates collocation_repair exercises.
    LLM replaces the correct collocate with an unnatural-but-plausible substitute.
    User identifies and corrects the substituted word.
    """

    exercise_type = 'collocation_repair'
    source_type   = 'collocation'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate one collocation repair item.
        Args:
            sentence_dict: {sentence, ...}
            source_id:     corpus_collocations.id
        Returns:
            Content dict with sentence_with_error, error_word, correct_word, or None.
        """
        col_row = self.db.table('corpus_collocations') \
            .select('collocation_text, head_word, collocate') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        template = self.load_prompt_template('collocation_repair_generation')
        prompt   = template.format(
            sentence=sentence_dict['sentence'],
            collocate=col_row.get('collocate', ''),
            head_word=col_row.get('head_word', ''),
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            if not result.get('error_word') or not result.get('correct_word'):
                return None
            return {
                'sentence_with_error': result['sentence_with_error'],
                'error_word':          result['error_word'],
                'correct_word':        result['correct_word'],
                'explanation':         result.get('explanation', ''),
                'source_test_id':      sentence_dict.get('test_id'),
            }
        except Exception:
            return None


class OddCollocationOutGenerator(ExerciseGenerator):
    """
    Generates odd_collocation_out exercises.
    LLM generates 4 collocations for a head word — 3 natural, 1 unnatural.
    odd_index is always 3 in stored JSON (frontend shuffles).
    Sourced from corpus_collocations; head_word drives LLM grouping.
    """

    exercise_type = 'odd_collocation_out'
    source_type   = 'collocation'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate one odd-collocation-out item anchored to a head word.
        Args:
            sentence_dict: context
            source_id:     corpus_collocations.id
        Returns:
            Content dict with head_word, collocations, odd_index, explanation, or None.
        """
        col_row = self.db.table('corpus_collocations') \
            .select('head_word, collocate') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        # Fetch 3 more natural collocates for the same head_word from corpus
        naturals = self._fetch_natural_collocates(col_row['head_word'], exclude_id=source_id)
        if len(naturals) < 2:
            return None  # Not enough corpus data

        template = self.load_prompt_template('odd_collocation_out_generation')
        prompt   = template.format(
            head_word=col_row['head_word'],
            natural_collocates=', '.join(naturals[:3]),
        )
        try:
            result      = self.call_llm(prompt, response_format='json')
            collocations = result.get('collocations', [])  # [nat1, nat2, nat3, odd]
            if len(collocations) != 4:
                return None
            return {
                'head_word':    col_row['head_word'],
                'collocations': collocations,
                'odd_index':    3,
                'explanation':  result.get('explanation', ''),
            }
        except Exception:
            return None

    def _fetch_natural_collocates(self, head_word: str, exclude_id: int) -> list[str]:
        """
        Fetch up to 3 additional natural collocates for head_word from corpus_collocations.
        Args:
            head_word:  the anchor word
            exclude_id: the source_id to exclude (already included elsewhere)
        Returns:
            List of collocate strings (may be empty).
        """
        result = self.db.table('corpus_collocations') \
            .select('collocate') \
            .eq('head_word', head_word) \
            .neq('id', exclude_id) \
            .gte('pmi_score', 3.0) \
            .limit(3) \
            .execute()
        return [r['collocate'] for r in (result.data or [])]
```

**Prompt template names:** `collocation_gap_fill_generation`, `collocation_repair_generation`, `odd_collocation_out_generation`

**Dependencies:** Task 3.1 (ExerciseGenerator).

---

### Task 5.8 — `generators/verb_noun_match.py`: VerbNounMatchGenerator

**Description:** Generates `verb_noun_match` grid exercises entirely from `corpus_collocations`. No LLM. Queries high-PMI VERB+NOUN pairs and assembles the grid.

**File:** `services/exercise_generation/generators/verb_noun_match.py`

```python
# services/exercise_generation/generators/verb_noun_match.py

from services.exercise_generation.base_generator import ExerciseGenerator


class VerbNounMatchGenerator(ExerciseGenerator):
    """
    Generates verb_noun_match grid exercises from corpus_collocations.
    No LLM. Queries VERB+NOUN pairs with PMI >= 3.0 for a corpus source.
    Grid: N verbs × M nouns; valid_pairs are [verb_idx, noun_idx] lists.
    Frontend shuffles verbs and nouns independently before rendering.
    """

    exercise_type = 'verb_noun_match'
    source_type   = 'collocation'

    MIN_GRID_VERBS: int = 2
    MIN_GRID_NOUNS: int = 2
    PMI_THRESHOLD:  float = 3.0

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Build a verb-noun match grid from corpus_collocations for the same corpus_source_id
        as the given collocation. Returns a content dict or None if insufficient data.
        Note: sentence_dict is unused — this generator is corpus-driven, not sentence-driven.
        Args:
            sentence_dict: ignored (required by interface)
            source_id:     corpus_collocations.id — used to look up corpus_source_id
        Returns:
            Content dict with verbs, nouns, valid_pairs, corpus_source_id, or None.
        """
        col_row = self.db.table('corpus_collocations') \
            .select('corpus_source_id, language_id') \
            .eq('id', source_id).single().execute().data
        if not col_row:
            return None

        pairs = self._fetch_verb_noun_pairs(
            col_row['corpus_source_id'], col_row['language_id']
        )
        if not pairs:
            return None

        verbs      = list(dict.fromkeys(p[0] for p in pairs))  # deduplicated, order-preserved
        nouns      = list(dict.fromkeys(p[1] for p in pairs))
        valid_pairs = [
            [verbs.index(v), nouns.index(n)] for v, n in pairs
            if v in verbs and n in nouns
        ]

        if len(verbs) < self.MIN_GRID_VERBS or len(nouns) < self.MIN_GRID_NOUNS:
            return None

        return {
            'verbs':            verbs,
            'nouns':            nouns,
            'valid_pairs':      valid_pairs,
            'corpus_source_id': col_row['corpus_source_id'],
        }

    def _fetch_verb_noun_pairs(
        self, corpus_source_id: int, language_id: int
    ) -> list[tuple[str, str]]:
        """
        Query corpus_collocations for high-PMI VERB+NOUN pairs.
        Returns list of (verb, noun) tuples, deduplicated, up to 20 pairs.
        Args:
            corpus_source_id: corpus_collocations.corpus_source_id
            language_id:      corpus_collocations.language_id
        Returns:
            List of (verb_phrase, noun_phrase) tuples.
        """
        result = self.db.rpc('get_verb_noun_pairs', {
            'p_corpus_source_id': corpus_source_id,
            'p_language_id':      language_id,
            'p_pmi_threshold':    self.PMI_THRESHOLD,
        }).execute()
        return [(r['verb_phrase'], r['noun_phrase']) for r in (result.data or [])]
```

**SQL required** (Supabase RPC — mirrors the raw query from spec section 1.12):

```sql
-- Function: get_verb_noun_pairs
-- Returns distinct (verb, noun) pairs from corpus_collocations for grid assembly.
CREATE OR REPLACE FUNCTION get_verb_noun_pairs(
    p_corpus_source_id INTEGER,
    p_language_id      INTEGER,
    p_pmi_threshold    NUMERIC DEFAULT 3.0
)
RETURNS TABLE (verb_phrase TEXT, noun_phrase TEXT, combined_pmi NUMERIC)
LANGUAGE sql STABLE
AS $$
    SELECT DISTINCT
        split_part(cc.collocation_text, ' ', 1)   AS verb_phrase,
        split_part(cc.collocation_text, ' ', 2)   AS noun_phrase,
        cc.pmi_score                               AS combined_pmi
    FROM corpus_collocations cc
    WHERE cc.pos_pattern       = 'VERB+NOUN'
      AND cc.corpus_source_id  = p_corpus_source_id
      AND cc.language_id       = p_language_id
      AND cc.pmi_score        >= p_pmi_threshold
    ORDER BY combined_pmi DESC
    LIMIT 20;
$$;
```

**Note:** The RPC splits `collocation_text` on the first space to extract verb and noun. For multi-word collocations, the split logic may need adjustment in a future iteration.

**Dependencies:** Task 3.1 (ExerciseGenerator).

---

### Task 5.9 — `generators/context_spectrum.py`: ContextSpectrumGenerator

**Description:** Generates `context_spectrum` exercises. LLM generates 3–4 register variants of the same meaning (informal → formal) for a grammar pattern or sentence. User picks the variant appropriate for the given context.

**File:** `services/exercise_generation/generators/context_spectrum.py`

```python
# services/exercise_generation/generators/context_spectrum.py

from services.exercise_generation.base_generator import ExerciseGenerator


class ContextSpectrumGenerator(ExerciseGenerator):
    """
    Generates context_spectrum exercises.
    LLM generates register variants (informal/neutral/formal/very formal) of a sentence.
    User selects the variant that fits the given exercise context.
    correct_variant_index is always 0 in stored JSON (frontend shuffles).
    """

    exercise_type = 'context_spectrum'
    source_type   = 'grammar'

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Generate register variants for the source sentence.
        Args:
            sentence_dict: {sentence, cefr_level, ...}
            source_id:     grammar_pattern_id
        Returns:
            Content dict with variants, exercise_context, correct_variant_index, or None.
        """
        sentence = sentence_dict['sentence']
        template = self.load_prompt_template('context_spectrum_generation')
        prompt   = template.format(
            sentence=sentence,
            cefr_level=sentence_dict.get('cefr_level', 'B1'),
        )
        try:
            result  = self.call_llm(prompt, response_format='json')
            variants = result.get('variants', [])
            if len(variants) < 3:
                return None
            context  = result.get('exercise_context', '')
            correct  = result.get('correct_variant', variants[0])
            # Ensure correct is variants[0]
            others   = [v for v in variants if v != correct]
            ordered  = [correct] + others[:3]
            return {
                'variants':              ordered,
                'exercise_context':      context,
                'correct_variant_index': 0,
                'source_test_id':        sentence_dict.get('test_id'),
            }
        except Exception:
            return None
```

**Prompt template name:** `context_spectrum_generation`

**Dependencies:** Task 3.1 (ExerciseGenerator).

---

### Task 5.10 — `generators/timed_speed_round.py`: TimedSpeedRoundGenerator

**Description:** Generates `timed_speed_round` wrappers. Does not create new exercise content — wraps existing exercises (cloze, flashcard, etc.) from the same source with timing metadata. No LLM.

**File:** `services/exercise_generation/generators/timed_speed_round.py`

```python
# services/exercise_generation/generators/timed_speed_round.py

from services.exercise_generation.base_generator import ExerciseGenerator


class TimedSpeedRoundGenerator(ExerciseGenerator):
    """
    Generates timed_speed_round exercise rows by sampling existing exercises
    for the same source_id and wrapping them in timing metadata.
    No LLM. No new sentence generation needed — source pool drives selection.
    """

    exercise_type = 'timed_speed_round'
    source_type   = 'grammar'

    WRAPPABLE_TYPES: list[str] = [
        'cloze_completion', 'text_flashcard', 'tl_nl_translation',
        'collocation_gap_fill',
    ]
    DEFAULT_ROUND_SIZE: int = 10
    DEFAULT_TIME_LIMIT_SECONDS: int = 60

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        """
        Sample WRAPPABLE_TYPES exercises from the exercises table for this source_id
        and assemble a speed round content dict referencing their IDs.
        Args:
            sentence_dict: not used (speed round is exercise-driven, not sentence-driven)
            source_id:     grammar_pattern_id, word_sense_id, or collocation_id
        Returns:
            Content dict with exercise_ids, round_size, time_limit_seconds, or None.
        """
        fk_col = {
            'grammar':     'grammar_pattern_id',
            'vocabulary':  'word_sense_id',
            'collocation': 'corpus_collocation_id',
        }.get(self.source_type)

        result = self.db.table('exercises') \
            .select('id') \
            .eq(fk_col, source_id) \
            .in_('exercise_type', self.WRAPPABLE_TYPES) \
            .eq('is_active', True) \
            .limit(self.DEFAULT_ROUND_SIZE) \
            .execute()

        exercise_ids = [r['id'] for r in (result.data or [])]
        if len(exercise_ids) < 5:
            return None

        return {
            'exercise_ids':        exercise_ids,
            'round_size':          len(exercise_ids),
            'time_limit_seconds':  self.DEFAULT_TIME_LIMIT_SECONDS,
            'source_type':         self.source_type,
            'source_id':           source_id,
        }
```

**Note:** `TimedSpeedRoundGenerator` should be run **after** Phase A generators have populated the `exercises` table for the given source, so it has exercises to wrap. The orchestrator handles ordering.

**Dependencies:** Task 3.1 (ExerciseGenerator), Phase A generators must be run first.

---

## Phase 6: Orchestrator

### Task 6.1 — `orchestrator.py`: ExerciseGenerationOrchestrator

**Description:** The top-level coordinator. Mirrors the pattern of `services/test_generation/orchestrator.py`. Accepts a source (type + ID), runs the five-phase pipeline, and persists results. Called from the cron entry point.

**File:** `services/exercise_generation/orchestrator.py`

```python
# services/exercise_generation/orchestrator.py

import uuid
import logging
from services.exercise_generation.config import (
    GRAMMAR_DISTRIBUTION, VOCABULARY_DISTRIBUTION, COLLOCATION_DISTRIBUTION,
)
from services.exercise_generation.transcript_miner import get_sentence_pool
from services.exercise_generation.generators.cloze             import ClozeGenerator
from services.exercise_generation.generators.jumbled_sentence  import JumbledSentenceGenerator
from services.exercise_generation.generators.translation       import TlNlTranslationGenerator, NlTlTranslationGenerator
from services.exercise_generation.generators.flashcard         import FlashcardGenerator
from services.exercise_generation.generators.spot_incorrect    import SpotIncorrectGenerator
from services.exercise_generation.generators.semantic          import SemanticDiscrimGenerator, OddOneOutGenerator
from services.exercise_generation.generators.collocation       import (
    CollocationGapFillGenerator, CollocationRepairGenerator, OddCollocationOutGenerator,
)
from services.exercise_generation.generators.verb_noun_match   import VerbNounMatchGenerator
from services.exercise_generation.generators.context_spectrum  import ContextSpectrumGenerator
from services.exercise_generation.generators.timed_speed_round import TimedSpeedRoundGenerator

logger = logging.getLogger(__name__)


class ExerciseGenerationOrchestrator:
    """
    Coordinates the full five-phase exercise generation pipeline for one source
    (grammar pattern, vocabulary sense, or collocation cluster).

    Phase 1 — Sentence Pool Assembly:  TranscriptMiner + LLMSentenceGenerator fallback
    Phase 2 — Exercise Assembly:        per-type generator classes
    Phase 3 — Deterministic Validation: ExerciseValidator (inside generate_batch)
    Phase 4 — Difficulty Calibration:   DifficultyCalibrator (inside generate_batch)
    Phase 5 — Persistence:              batch insert to exercises table

    Mirrors TestGenerationOrchestrator in services/test_generation/orchestrator.py.
    """

    def __init__(self, db, audio_synthesizer=None, nl_language_code: str = 'en'):
        """
        Args:
            db:                 Supabase client
            audio_synthesizer:  AudioSynthesizer instance for listening flashcards
            nl_language_code:   native language code for translation exercises (default 'en')
        """
        self.db                = db
        self.audio_synthesizer = audio_synthesizer
        self.nl_language_code  = nl_language_code

    def run(
        self,
        source_type: str,
        source_id: int,
        language_id: int,
        phases: list[str] | None = None,
    ) -> dict:
        """
        Execute the full pipeline for one source.
        Returns a summary dict with counts per exercise type.
        Args:
            source_type: 'grammar', 'vocabulary', or 'collocation'
            source_id:   FK to the appropriate source table
            language_id: FK to dim_languages.id
            phases:      optional list of phase names to restrict execution
                         ('A', 'B', 'C', 'D') — runs all if None
        Returns:
            {'batch_id': str, 'counts': {exercise_type: int}, 'total': int}
        """
        batch_id     = str(uuid.uuid4())
        model, sent_model = self._load_models(language_id)
        distribution = self._get_distribution(source_type)

        logger.info(
            "ExerciseGenerationOrchestrator.run: source=%s id=%s lang=%s batch=%s",
            source_type, source_id, language_id, batch_id,
        )

        # Phase 1: Sentence pool
        sentence_pool = get_sentence_pool(
            source_type, source_id, language_id,
            db=self.db, llm_client=self._call_llm_with_model(model),
            model=sent_model,
        )
        logger.info("Sentence pool size: %d", len(sentence_pool))

        # Phase 2–4: Generate, validate, calibrate per type
        counts: dict[str, int] = {}
        all_rows: list[dict]   = []

        generators = self._build_generators(source_type, language_id, model)

        for ex_type, gen in generators.items():
            if ex_type not in distribution:
                continue
            if not self._in_requested_phases(ex_type, phases):
                continue
            target = distribution[ex_type]
            rows   = gen.generate_batch(sentence_pool, source_id, target, batch_id)
            all_rows.extend(rows)
            counts[ex_type] = len(rows)
            logger.info("Generated %d × %s", len(rows), ex_type)

        # Phase 5: Persistence
        self._batch_insert(all_rows)

        total = sum(counts.values())
        logger.info("Batch %s complete: %d total exercises", batch_id, total)
        return {'batch_id': batch_id, 'counts': counts, 'total': total}

    def _load_models(self, language_id: int) -> tuple[str, str]:
        """
        Fetch exercise_model and exercise_sentence_model from dim_languages.
        Falls back to 'google/gemini-flash-1.5' if columns are null.
        Args:
            language_id: FK to dim_languages.id
        Returns:
            (exercise_model, exercise_sentence_model) tuple.
        """
        row = self.db.table('dim_languages') \
            .select('exercise_model, exercise_sentence_model') \
            .eq('id', language_id).single().execute().data
        default = 'google/gemini-flash-1.5'
        return (
            (row or {}).get('exercise_model') or default,
            (row or {}).get('exercise_sentence_model') or default,
        )

    def _get_distribution(self, source_type: str) -> dict[str, int]:
        """Return the count distribution dict for the given source_type."""
        return {
            'grammar':     GRAMMAR_DISTRIBUTION,
            'vocabulary':  VOCABULARY_DISTRIBUTION,
            'collocation': COLLOCATION_DISTRIBUTION,
        }[source_type]

    def _build_generators(
        self, source_type: str, language_id: int, model: str
    ) -> dict[str, object]:
        """
        Instantiate all applicable generator classes for the given source_type.
        Returns a dict of {exercise_type: generator_instance}.
        Only includes generators valid for this source_type.
        Args:
            source_type: 'grammar', 'vocabulary', or 'collocation'
            language_id: target language
            model:       LLM model string
        Returns:
            Dict of generator instances keyed by exercise_type string.
        """
        kw = dict(db=self.db, language_id=language_id, model=model)

        grammar_generators = {
            'cloze_completion':        ClozeGenerator(**kw, source_type='grammar'),
            'jumbled_sentence':        JumbledSentenceGenerator(**kw, source_type='grammar'),
            'tl_nl_translation':       TlNlTranslationGenerator(**kw, source_type='grammar',
                                           nl_language_code=self.nl_language_code),
            'nl_tl_translation':       NlTlTranslationGenerator(**kw, source_type='grammar',
                                           nl_language_code=self.nl_language_code),
            'text_flashcard':          FlashcardGenerator(**kw, mode='text', source_type='grammar'),
            'listening_flashcard':     FlashcardGenerator(**kw, mode='listening', source_type='grammar',
                                           audio_synthesizer=self.audio_synthesizer),
            'semantic_discrimination': SemanticDiscrimGenerator(**kw, source_type='grammar'),
            'spot_incorrect_sentence': SpotIncorrectGenerator(**kw),
            'odd_one_out':             OddOneOutGenerator(**kw, source_type='grammar'),
            'context_spectrum':        ContextSpectrumGenerator(**kw),
            'timed_speed_round':       TimedSpeedRoundGenerator(**kw, source_type='grammar'),
        }

        vocabulary_generators = {
            'text_flashcard':          FlashcardGenerator(**kw, mode='text', source_type='vocabulary'),
            'listening_flashcard':     FlashcardGenerator(**kw, mode='listening', source_type='vocabulary',
                                           audio_synthesizer=self.audio_synthesizer),
            'cloze_completion':        ClozeGenerator(**kw, source_type='vocabulary'),
            'tl_nl_translation':       TlNlTranslationGenerator(**kw, source_type='vocabulary',
                                           nl_language_code=self.nl_language_code),
            'semantic_discrimination': SemanticDiscrimGenerator(**kw, source_type='vocabulary'),
        }

        collocation_generators = {
            'collocation_gap_fill':  CollocationGapFillGenerator(**kw),
            'collocation_repair':    CollocationRepairGenerator(**kw),
            'odd_collocation_out':   OddCollocationOutGenerator(**kw),
            'text_flashcard':        FlashcardGenerator(**kw, mode='text', source_type='collocation'),
            'verb_noun_match':       VerbNounMatchGenerator(**kw),
        }

        return {
            'grammar':     grammar_generators,
            'vocabulary':  vocabulary_generators,
            'collocation': collocation_generators,
        }[source_type]

    def _batch_insert(self, rows: list[dict]) -> None:
        """
        Insert all exercise rows in a single Supabase batch call.
        Logs count on success; logs error without raising on failure.
        Args:
            rows: list of exercise row dicts
        """
        if not rows:
            return
        try:
            self.db.table('exercises').insert(rows).execute()
            logger.info("Inserted %d exercise rows", len(rows))
        except Exception as exc:
            logger.error("Batch insert failed: %s", exc)

    @staticmethod
    def _call_llm_with_model(model: str):
        """Return a partial callable with the model pre-bound for sentence generation."""
        from services.llm_client import call_llm
        def _call(prompt: str, response_format: str = 'json'):
            return call_llm(prompt, model=model, response_format=response_format)
        return _call

    @staticmethod
    def _in_requested_phases(ex_type: str, phases: list[str] | None) -> bool:
        """
        Return True if ex_type belongs to one of the requested implementation phases,
        or if phases is None (run all).
        Phase membership is defined by PHASE_MAP in config (add to config.py).
        """
        if phases is None:
            return True
        from services.exercise_generation.config import PHASE_MAP
        return any(ex_type in PHASE_MAP.get(p, []) for p in phases)
```

**Add to `config.py`** (Task 0.5 extension):

```python
# Phase membership — mirrors spec section 1.17
PHASE_MAP: dict[str, list[str]] = {
    'A': ['text_flashcard', 'listening_flashcard', 'cloze_completion'],
    'B': ['jumbled_sentence', 'spot_incorrect_sentence', 'spot_incorrect_part',
          'tl_nl_translation', 'nl_tl_translation'],
    'C': ['semantic_discrimination', 'collocation_gap_fill', 'collocation_repair',
          'odd_collocation_out', 'odd_one_out'],
    'D': ['verb_noun_match', 'context_spectrum', 'timed_speed_round'],
}
```

**Dependencies:** All Phase 2–5 tasks, Task 2.1 (TranscriptMiner), Task 0.5 (config).

---

### Task 6.2 — `run_exercise_generation.py`: Cron Entry Point

**Description:** Script executed by the cron job scheduler (Railway). Iterates all active grammar patterns, vocabulary senses, and collocations, calling the orchestrator for each. Mirrors `services/test_generation/run_test_generation.py`.

**File:** `services/exercise_generation/run_exercise_generation.py`

```python
# services/exercise_generation/run_exercise_generation.py

import logging
from services.supabase_client import get_supabase_client  # existing utility
from services.audio_synthesizer import AudioSynthesizer    # existing class
from services.exercise_generation.orchestrator import ExerciseGenerationOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_grammar_batch(
    language_id: int,
    phases: list[str] | None = None,
    pattern_ids: list[int] | None = None,
) -> dict:
    """
    Generate exercises for all active grammar patterns of a language,
    or a specific subset if pattern_ids is provided.
    Args:
        language_id:  FK to dim_languages.id
        phases:       optional phase filter list ['A', 'B', 'C', 'D']
        pattern_ids:  optional list of specific pattern IDs to process
    Returns:
        Aggregated summary dict: {pattern_id: run_result}
    """
    db             = get_supabase_client()
    synthesizer    = AudioSynthesizer()
    orchestrator   = ExerciseGenerationOrchestrator(db, audio_synthesizer=synthesizer)

    query = db.table('dim_grammar_patterns') \
        .select('id') \
        .eq('language_id', language_id) \
        .eq('is_active', True)
    if pattern_ids:
        query = query.in_('id', pattern_ids)
    patterns = query.execute()

    results = {}
    for row in (patterns.data or []):
        pid = row['id']
        try:
            result = orchestrator.run('grammar', pid, language_id, phases=phases)
            results[pid] = result
            logger.info("Pattern %d: %d exercises", pid, result['total'])
        except Exception as exc:
            logger.error("Pattern %d failed: %s", pid, exc)
            results[pid] = {'error': str(exc)}

    return results


def run_vocabulary_batch(
    language_id: int,
    sense_ids: list[int] | None = None,
) -> dict:
    """
    Generate exercises for all dim_word_senses rows of a language,
    or a specific subset if sense_ids is provided.
    Args:
        language_id: FK to dim_languages.id
        sense_ids:   optional list of specific sense IDs
    Returns:
        Aggregated summary dict: {sense_id: run_result}
    """
    db           = get_supabase_client()
    synthesizer  = AudioSynthesizer()
    orchestrator = ExerciseGenerationOrchestrator(db, audio_synthesizer=synthesizer)

    query = db.table('dim_word_senses') \
        .select('id') \
        .eq('language_id', language_id)
    if sense_ids:
        query = query.in_('id', sense_ids)
    senses = query.execute()

    results = {}
    for row in (senses.data or []):
        sid = row['id']
        try:
            result = orchestrator.run('vocabulary', sid, language_id)
            results[sid] = result
        except Exception as exc:
            logger.error("Sense %d failed: %s", sid, exc)
            results[sid] = {'error': str(exc)}

    return results


def run_collocation_batch(
    language_id: int,
    collocation_ids: list[int] | None = None,
) -> dict:
    """
    Generate exercises for corpus_collocations rows of a language.
    Requires Plan 5 corpus pipeline to have populated corpus_collocations.
    Args:
        language_id:      FK to dim_languages.id
        collocation_ids:  optional list of specific collocation IDs
    Returns:
        Aggregated summary dict: {collocation_id: run_result}
    """
    db           = get_supabase_client()
    synthesizer  = AudioSynthesizer()
    orchestrator = ExerciseGenerationOrchestrator(db, audio_synthesizer=synthesizer)

    query = db.table('corpus_collocations') \
        .select('id') \
        .eq('language_id', language_id) \
        .gte('pmi_score', 3.0)
    if collocation_ids:
        query = query.in_('id', collocation_ids)
    collocations = query.execute()

    results = {}
    for row in (collocations.data or []):
        cid = row['id']
        try:
            result = orchestrator.run('collocation', cid, language_id)
            results[cid] = result
        except Exception as exc:
            logger.error("Collocation %d failed: %s", cid, exc)
            results[cid] = {'error': str(exc)}

    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run exercise generation batch')
    parser.add_argument('--source',   choices=['grammar', 'vocabulary', 'collocation'], required=True)
    parser.add_argument('--language', type=int, required=True)
    parser.add_argument('--phases',   nargs='*', choices=['A', 'B', 'C', 'D'])
    parser.add_argument('--ids',      nargs='*', type=int)
    args = parser.parse_args()

    if args.source == 'grammar':
        run_grammar_batch(args.language, phases=args.phases, pattern_ids=args.ids)
    elif args.source == 'vocabulary':
        run_vocabulary_batch(args.language, sense_ids=args.ids)
    elif args.source == 'collocation':
        run_collocation_batch(args.language, collocation_ids=args.ids)
```

**Dependencies:** Task 6.1 (Orchestrator), all generator tasks.

---

## Phase 7: Analytics SQL

### Task 7.1 — Analytics Queries

**Description:** SQL views and queries for distractor analytics and exercise performance monitoring. Added to the database as views; consumed by the analytics dashboard (not in scope for this plan).

**SQL (ready to run):**

```sql
-- View: distractor error type breakdown per user per grammar pattern
CREATE OR REPLACE VIEW vw_distractor_error_analysis AS
SELECT
    ea.user_id,
    e.tags->>'grammar_pattern'          AS pattern_code,
    ea.user_response->>'distractor_tag' AS error_type,
    COUNT(*)                             AS error_count,
    MIN(ea.created_at)                   AS first_seen,
    MAX(ea.created_at)                   AS last_seen
FROM exercise_attempts ea
JOIN exercises e ON ea.exercise_id = e.id
WHERE ea.is_correct = FALSE
  AND ea.user_response->>'distractor_tag' IS NOT NULL
  AND e.exercise_type = 'cloze_completion'
GROUP BY 1, 2, 3;

-- View: exercise attempt rates by type and CEFR level
CREATE OR REPLACE VIEW vw_exercise_performance_by_type AS
SELECT
    e.exercise_type,
    e.cefr_level,
    e.language_id,
    COUNT(DISTINCT e.id)             AS exercise_count,
    COUNT(ea.id)                     AS total_attempts,
    SUM(ea.is_correct::INT)          AS correct_count,
    ROUND(
        SUM(ea.is_correct::INT)::NUMERIC / NULLIF(COUNT(ea.id), 0) * 100,
        1
    )                                AS accuracy_pct
FROM exercises e
LEFT JOIN exercise_attempts ea ON ea.exercise_id = e.id
WHERE e.is_active = TRUE
GROUP BY 1, 2, 3;

-- IRT update query (run by separate nightly job after ≥ 30 attempts per exercise)
-- Updates irt_difficulty using Maximum Likelihood Estimate approximation.
UPDATE exercises e
SET irt_difficulty = subq.new_b
FROM (
    SELECT
        ea.exercise_id,
        -- Simple MLE approximation: logit of observed error rate
        LN(
            NULLIF(SUM((NOT ea.is_correct)::INT), 0)::NUMERIC /
            NULLIF(SUM(ea.is_correct::INT), 0)
        ) AS new_b
    FROM exercise_attempts ea
    GROUP BY ea.exercise_id
    HAVING COUNT(*) >= 30
) subq
WHERE e.id = subq.exercise_id;

-- Query: exercises needing generation (no exercises yet for a given pattern + type)
SELECT
    gp.id          AS pattern_id,
    gp.pattern_code,
    gp.language_id,
    et.exercise_type,
    COUNT(e.id)    AS existing_count
FROM dim_grammar_patterns gp
CROSS JOIN (
    VALUES
        ('cloze_completion'), ('jumbled_sentence'), ('tl_nl_translation'),
        ('nl_tl_translation'), ('text_flashcard'), ('listening_flashcard'),
        ('semantic_discrimination'), ('spot_incorrect_sentence'), ('spot_incorrect_part'),
        ('timed_speed_round'), ('odd_one_out'), ('context_spectrum'),
        ('odd_collocation_out'), ('verb_noun_match'), ('collocation_gap_fill'),
        ('collocation_repair')
) AS et(exercise_type)
LEFT JOIN exercises e
    ON e.grammar_pattern_id = gp.id
   AND e.exercise_type      = et.exercise_type
WHERE gp.is_active = TRUE
GROUP BY 1, 2, 3, 4
HAVING COUNT(e.id) = 0
ORDER BY gp.language_id, gp.pattern_code, et.exercise_type;
```

---

## Phase 8: Prompt Templates

### Task 8.1 — Prompt Template Rows

**Description:** Insert all required prompt templates into the `prompt_templates` table. Each template is versioned; the orchestrator always fetches the latest version. Templates instruct the LLM to return JSON and follow the no-shuffle rule (do not shuffle options — put correct answer first).

**SQL (ready to run — insert once, update via new version rows):**

```sql
-- Template: exercise_sentence_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('exercise_sentence_generation', 1,
 'Generate {count} natural {cefr_level}-level sentences in the target language that demonstrate the following:
Pattern: {pattern_code}
Description: {description}
Example: {example_sentence}

Return a JSON array of objects: [{{"sentence": "...", "cefr_level": "{cefr_level}"}}]
Do not include translations. Sentences must be grammatically correct and contextually natural.');

-- Template: cloze_distractor_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('cloze_distractor_generation', 1,
 'Sentence: {original_sentence}
Blank: {sentence_with_blank}
Correct answer: {correct_answer}
Learner level: {cefr_level}

Generate exactly 3 distractors. For each, assign a tag:
- "semantic": plausible in a different context but wrong here
- "form_error": wrong grammatical form or tense
- "learner_error": the most common mistake at {cefr_level}

Return JSON:
{{"distractors": ["word1","word2","word3"], "distractor_tags": {{"word1":"semantic","word2":"form_error","word3":"learner_error"}}, "explanation": "Brief explanation of correct answer."}}

Put the correct answer first in the options — do NOT shuffle.');

-- Template: tl_nl_translation_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('tl_nl_translation_generation', 1,
 'Sentence (target language): {tl_sentence}
Native language: {nl_language}

Generate:
1. One accurate {nl_language} translation of the sentence.
2. Two plausible-but-wrong {nl_language} translations (same general topic, different tense/aspect/meaning).

Return JSON:
{{"correct_nl": "...", "wrong_options": ["...", "..."]}}

The correct translation goes first — do NOT shuffle.');

-- Template: nl_tl_translation_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('nl_tl_translation_generation', 1,
 'Target language sentence: {tl_sentence}
Translate to native language ({nl_language}) and provide grading criteria for a production exercise.

Return JSON:
{{"nl_sentence": "...", "grading_notes": "Key requirements: e.g. must use present perfect continuous, duration marker required.", "acceptable_variants": ["...", "..."]}}');

-- Template: spot_incorrect_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('spot_incorrect_generation', 1,
 'Here are three grammatically correct sentences:
1. {sentence_1}
2. {sentence_2}
3. {sentence_3}

Generate one grammatically INCORRECT sentence on the same topic, containing a realistic error a learner would make.
Also provide a parts breakdown identifying the exact error location.

Return JSON:
{{"incorrect_sentence": "...", "error_description": "...", "error_type": "e.g. subject_verb_agreement", "parts": [{{"text": "...", "is_error": false}}, {{"text": "...", "is_error": true, "correct_form": "...", "explanation": "..."}}]}}');

-- Template: semantic_discrimination_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('semantic_discrimination_generation', 1,
 'Word: {word}
Definition: {definition}
Level: {cefr_level}
Example context: {example_sentence}

Generate 4 sentences using "{word}":
- 1 correct, natural usage
- 3 plausible-but-wrong usages (wrong register, wrong collocation, wrong context)

Return JSON:
{{"sentences": [{{"text": "...", "is_correct": true}}, {{"text": "...", "is_correct": false}}, ...], "explanation": "..."}}

Put the correct sentence first.');

-- Template: odd_one_out_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('odd_one_out_generation', 1,
 'Anchor word: {word} (meaning: {definition})

Generate a group of 4 words/phrases:
- 3 that share a semantic property with "{word}" (e.g. all emotions, all cooking verbs, all formal register)
- 1 that does NOT share that property but is plausibly related

Return JSON:
{{"items": ["word1","word2","word3","odd_word"], "odd_item": "odd_word", "shared_property": "...", "explanation": "..."}}

Put the odd item last in items array.');

-- Template: collocation_gap_fill_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('collocation_gap_fill_generation', 1,
 'Head word: {head_word}
Correct collocate: {collocate}
Sentence: {sentence}

Generate 3 distractor collocates — semantically plausible but unnatural with "{head_word}".

Return JSON:
{{"distractors": ["...", "...", "..."]}}

Do NOT shuffle — distractors are always placed after the correct answer by the application.');

-- Template: collocation_repair_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('collocation_repair_generation', 1,
 'Original sentence: {sentence}
Natural collocate: {collocate} (with head word: {head_word})

Replace "{collocate}" with an unnatural-but-plausible substitute. The resulting sentence should sound "almost right" to a learner.

Return JSON:
{{"sentence_with_error": "...", "error_word": "substitute word", "correct_word": "{collocate}", "explanation": "Why the substitute is unnatural."}}');

-- Template: odd_collocation_out_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('odd_collocation_out_generation', 1,
 'Head word: {head_word}
Known natural collocates: {natural_collocates}

Generate a group of 4 collocations for "{head_word}":
- 3 natural (including some from the known list)
- 1 that is unnatural but sounds plausible to a learner

Return JSON:
{{"collocations": ["natural1 {head_word}", "natural2 {head_word}", "natural3 {head_word}", "odd {head_word}"], "explanation": "..."}}

Odd item must be last in the array.');

-- Template: context_spectrum_generation
INSERT INTO prompt_templates (task_name, version, template_text) VALUES
('context_spectrum_generation', 1,
 'Base sentence: {sentence}
Learner level: {cefr_level}

Generate 3–4 register variants of this sentence (informal → formal spectrum).
Then create a brief exercise context (e.g. "You are writing a business email") that makes one variant clearly correct.

Return JSON:
{{"variants": ["most appropriate variant", "variant2", "variant3"], "exercise_context": "...", "correct_variant": "most appropriate variant"}}

The correct variant must be first in the variants array.');
```

---

## Summary: Dependencies & Build Order

```
Phase 0  (Schema + Config)      → no dependencies
Phase 1  (LanguageProcessor)    → Phase 0
Phase 2  (TranscriptMiner)      → Phase 0, Phase 1
Phase 3  (Base + Validators)    → Phase 0
Phase 4  (Difficulty)           → Phase 0
Phase 5  (Generators)           → Phase 2, Phase 3, Phase 4
Phase 6  (Orchestrator + Cron)  → Phase 5
Phase 7  (Analytics SQL)        → Phase 0 (exercises table must exist)
Phase 8  (Prompt Templates)     → Phase 0 (prompt_templates table must exist)
```

**Recommended implementation order:**

| Sprint | Tasks |
|--------|-------|
| 1 | 0.1, 0.2, 0.3, 0.4, 0.5 (all schema + config) |
| 2 | 1.1, 2.1, 3.1, 3.2, 4.1 (infrastructure layer) |
| 3 | 5.1, 5.2, 5.4 + 8.1 (Phase A generators + prompts) |
| 4 | 5.3, 5.5 + 8.1 cont. (Phase B generators + prompts) |
| 5 | 5.6, 5.7 (Phase C generators) |
| 6 | 5.8, 5.9, 5.10 (Phase D generators) |
| 7 | 6.1, 6.2, 7.1 (Orchestrator, cron, analytics) |

---

## Existing Codebase — Required Changes

The following changes to existing files are needed. All other work is additive (new files only).

### `dim_languages` table
- Add `exercise_model` and `exercise_sentence_model` columns (Task 0.4 SQL).

### `exercise_attempts` table
- Add `exercise_id UUID REFERENCES exercises(id)` FK if not present (Task 0.3 SQL).

### `services/test_generation/run_test_generation.py`
- No changes needed. The exercise generation cron (`run_exercise_generation.py`) is a parallel entry point.

### `services/audio_synthesizer.py` (existing class)
- Confirm `synthesize_and_upload(text, language_id, purpose)` signature. If `purpose` argument is not present, add it with a default; `FlashcardGenerator` passes `purpose='exercise'` for R2 path organisation. No other changes needed.

### `prompt_templates` table
- Insert all rows from Task 8.1 (additive — no existing rows modified).
