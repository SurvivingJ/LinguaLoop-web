"""
Tests for LanguageProcessor.chunk_sentence — the constituent-aware chunker
used to render jumbled_sentence exercises.

Asserts:
- Chunks are 3 to 6 per sentence (or a fallback to whole sentence)
- Most chunks are multi-word (single-token chunks tolerated for content
  pronouns / single verbs / single adverbs where dep-parse leaves them)
- No chunk crosses a top-level constituent boundary (we sanity-check by
  ensuring the concatenation of chunks equals the original token stream)
"""

import pytest

from services.exercise_generation.language_processor import (
    LanguageProcessor,
    prepare_jumbled_content,
)


# ---------------------------------------------------------------------------
# English
# ---------------------------------------------------------------------------

ENGLISH_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "She made a wise decision yesterday.",
    "I went to the store because I needed bread.",
    "After the storm passed, we walked to the beach.",
    "He gave her a beautiful flower.",
    "The book is on the table.",
    "Although it was raining, they went hiking in the mountains.",
    "My brother and I are studying for the exam tomorrow.",
    "She opened the door slowly and stepped inside.",
    "The teacher asked the students to read the chapter.",
    "In the morning, I drink coffee and read the newspaper.",
    "The children were playing happily in the garden.",
    "She has been working on this project for months.",
    "If you study hard, you will pass the exam.",
    "The cat that I saw yesterday is sleeping on the couch.",
]


@pytest.fixture(scope="module")
def en():
    return LanguageProcessor.for_language(2)


@pytest.mark.parametrize("sentence", ENGLISH_SENTENCES)
def test_english_chunk_count_in_range(en, sentence):
    chunks = en.chunk_sentence(sentence)
    assert 3 <= len(chunks) <= 6, f"got {len(chunks)} for: {sentence}"


@pytest.mark.parametrize("sentence", ENGLISH_SENTENCES)
def test_english_chunks_cover_all_content_tokens(en, sentence):
    """Concatenating all chunks should yield every non-punct token in order."""
    chunks = en.chunk_sentence(sentence)
    chunk_words = [w for c in chunks for w in c.split()]
    original_tokens = en.tokenize(sentence)
    assert chunk_words == original_tokens, (
        f"chunk tokens {chunk_words} != original tokens {original_tokens}"
    )


@pytest.mark.parametrize("sentence", ENGLISH_SENTENCES)
def test_english_no_dangling_function_word_singletons(en, sentence):
    """No chunk should be a lone determiner/preposition/conjunction."""
    chunks = en.chunk_sentence(sentence)
    function_words = {
        "the", "a", "an",
        "of", "to", "in", "on", "at", "for", "with", "by", "from", "over",
        "and", "or", "but",
        "because", "although", "if", "when", "while", "since",
    }
    for c in chunks:
        words = c.split()
        if len(words) == 1 and words[0].lower() in function_words:
            pytest.fail(f"dangling function-word singleton '{c}' in {chunks!r}")


def test_english_multiword_majority(en):
    """Across the corpus, the majority of chunks should be multi-word."""
    total = 0
    multi = 0
    for s in ENGLISH_SENTENCES:
        for c in en.chunk_sentence(s):
            total += 1
            if len(c.split()) >= 2:
                multi += 1
    assert multi / total >= 0.55, f"only {multi}/{total} chunks are multi-word"


def test_english_short_sentence_raises(en):
    """Sentences too short to chunk meaningfully should raise ValueError."""
    with pytest.raises(ValueError):
        en.chunk_sentence("Birds fly.")


def test_english_pronoun_subject_merged_with_verb(en):
    """A single-token pronoun subject directly before the verb should merge."""
    chunks = en.chunk_sentence("She made a wise decision yesterday.")
    assert chunks[0] == "She made"


def test_english_multiword_subject_preserved(en):
    """Multi-word subject NP must stay distinct from the verb chunk."""
    chunks = en.chunk_sentence("The quick brown fox jumps over the lazy dog.")
    assert chunks[0] == "The quick brown fox"
    assert chunks[1] == "jumps"


# ---------------------------------------------------------------------------
# Chinese
# ---------------------------------------------------------------------------

CHINESE_SENTENCES = [
    "我把苹果吃了。",
    "他每天早上都去公园跑步。",
    "因为下雨，所以我们没出门。",
    "她正在写一封信给妈妈。",
    "我昨天看了一部很好看的电影。",
    "如果你有时间，请给我打电话。",
    "他和他的朋友一起去图书馆学习。",
    "老师让学生读这本书。",
    "小猫在沙发上睡觉。",
]


@pytest.fixture(scope="module")
def zh():
    return LanguageProcessor.for_language(1)


@pytest.mark.parametrize("sentence", CHINESE_SENTENCES)
def test_chinese_chunk_count_in_range(zh, sentence):
    chunks = zh.chunk_sentence(sentence)
    assert 3 <= len(chunks) <= 6, f"got {len(chunks)} for: {sentence}"


@pytest.mark.parametrize("sentence", CHINESE_SENTENCES)
def test_chinese_chunks_drop_punct_only(zh, sentence):
    """Concatenated chunks should equal the sentence with punctuation removed."""
    chunks = zh.chunk_sentence(sentence)
    joined = "".join(chunks)
    stripped = sentence
    for p in "，。、！？；：":
        stripped = stripped.replace(p, "")
    assert joined == stripped, f"{joined!r} != {stripped!r}"


def test_chinese_coverb_attaches_to_following_np(zh):
    """The coverb 把 should head its own chunk together with the following NP."""
    chunks = zh.chunk_sentence("我把苹果吃了。")
    assert any(c.startswith("把") and len(c) > 1 for c in chunks), chunks


# ---------------------------------------------------------------------------
# prepare_jumbled_content integration
# ---------------------------------------------------------------------------

def test_prepare_jumbled_content_english_multiword_chunks():
    """The serve-time entry point should now return multi-word chunks."""
    out = prepare_jumbled_content(
        {"original_sentence": "She made a wise decision yesterday."},
        language_id=2,
    )
    assert len(out["chunks"]) >= 3
    assert out["correct_ordering"] == list(range(len(out["chunks"])))
    # At least half the chunks should be multi-word.
    multi = sum(1 for c in out["chunks"] if len(c.split()) >= 2)
    assert multi >= len(out["chunks"]) // 2


def test_prepare_jumbled_content_short_sentence_fallback():
    """Sentences too short for chunk_sentence should fall back to word tokens."""
    out = prepare_jumbled_content(
        {"original_sentence": "Birds fly."},
        language_id=2,
    )
    # Falls back to tokenize -> ["Birds", "fly"]
    assert len(out["chunks"]) >= 1
    assert out["correct_ordering"] == list(range(len(out["chunks"])))
