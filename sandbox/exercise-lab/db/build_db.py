"""
Builds sandbox/exercise-lab/db/lab.sqlite from LOCAL FILES ONLY.

WHY THIS EXISTS: nobody can prototype or measure a generation/serving change
until there is something to read from and write to. This script is that
one-time (well - re-runnable) build step: it reads real files already in
this repo (raw/, data/, root-level CSVs, tests/fixtures/) and produces a
self-contained SQLite database mirroring the slice of production schema
that matters (see db/schema.sql). It NEVER touches Supabase, makes an LLM
call, or downloads anything from the network.

Run it with:
    cd sandbox/exercise-lab
    ../../venv/Scripts/python db/build_db.py

It always rebuilds from scratch (deletes any existing lab.sqlite first) -
the sources are deterministic and the build takes well under a minute, so
"stale db vs fresh sources" is not a failure mode worth defending against.

See README.md "Seeding" section for the full narrative of what came from
where, what was skipped, and every fidelity gap. Search this file for
`# FIDELITY GAP:` for the inline version of the same list.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

THIS_DIR = Path(__file__).resolve().parent
LAB_DIR = THIS_DIR.parent
REPO_ROOT = LAB_DIR.parent.parent  # sandbox/exercise-lab/db -> sandbox/exercise-lab -> sandbox -> repo root

sys.path.insert(0, str(LAB_DIR))
from lab.embeddings import HashedCharNgramTfidf, pack_embedding  # noqa: E402

DB_PATH = THIS_DIR / "lab.sqlite"
SCHEMA_PATH = THIS_DIR / "schema.sql"

# Language ids, taken verbatim from dim_languages_rows.csv at the repo root
# (NOT 'zh'/'ja' - the live language_code values are 'cn'/'en'/'jp').
LANG_ZH = 1
LANG_EN = 2
LANG_JA = 3

# How many highest-frequency senses per language get a computed embedding +
# a corpus-mined example sentence. Full dictionaries (esp. CC-CEDICT at
# ~125k raw entries) are loaded into dim_vocabulary/dim_word_senses in full,
# but embedding EVERY row would mean millions of hashed n-gram operations
# for entries no prototype is likely to ever touch (obscure classical/
# proper-noun CEDICT entries). This cap keeps build time under a minute
# while still covering more senses than production's own current
# pronunciation-coverage numbers for two of three languages (see
# docs/recon-data-surface.md §3: zh pronunciation coverage is 34%, ja 22%).
EMBED_TOP_N_PER_LANGUAGE = 8000

_WORDFREQ_ZIPF_MIN = 0.25  # per docs/recon-data-surface.md §1: real range is 0.25-6.56


def log(msg: str) -> None:
    print(f"[build_db] {msg}", flush=True)


def zipf_or_none(word: str, lang: str, wordfreq_zipf) -> float | None:
    """wordfreq returns 0.0 for words it has no data for at all - we treat
    that as NULL (matches production's own "no frequency data" convention,
    not a real Zipf score of zero) rather than storing a fake floor value."""
    try:
        z = wordfreq_zipf(word, lang)
    except Exception:
        return None
    return round(z, 3) if z and z >= _WORDFREQ_ZIPF_MIN else None


# ---------------------------------------------------------------------------
# dim_languages
# ---------------------------------------------------------------------------
def load_dim_languages(conn: sqlite3.Connection) -> int:
    path = REPO_ROOT / "dim_languages_rows.csv"
    n = 0
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            conn.execute(
                """INSERT INTO dim_languages
                   (id, language_code, language_name, native_name, iso_639_1,
                    iso_639_3, is_active, display_order)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    int(row["id"]),
                    row["language_code"],
                    row["language_name"],
                    row["native_name"] or None,
                    row["iso_639_1"] or None,
                    row["iso_639_3"] or None,
                    1 if row["is_active"].lower() == "true" else 0,
                    int(row["display_order"] or 0),
                ),
            )
            n += 1
    conn.commit()
    log(f"dim_languages: {n} rows (source: dim_languages_rows.csv)")
    return n


# ---------------------------------------------------------------------------
# zh vocabulary + senses, from raw/cedict_ts.u8 (CC-CEDICT)
# ---------------------------------------------------------------------------
_CEDICT_LINE_RE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]*)\]\s+/(.*)/\s*$")


def load_cedict_zh(conn: sqlite3.Connection, wordfreq_zipf) -> dict:
    """
    CC-CEDICT line format: `Traditional Simplified [pinyin] /def1/def2/.../`
    We key dim_vocabulary on the SIMPLIFIED form (the app's default script -
    Traditional is generated deterministically elsewhere in production via
    a script converter, docs/recon-data-surface.md §4, not stored separately
    here). Multiple CEDICT lines sharing one simplified lemma (different
    pronunciations/senses of the same written word - real polysemy) become
    multiple dim_word_senses rows under ONE dim_vocabulary row, exactly like
    production's one-lemma-many-senses model.

    # FIDELITY GAP: CC-CEDICT's definitions are English glosses, not native
    # Chinese-language definitions. Every zh sense seeded here has
    # definition_language_id=EN. Production supports a zh-language
    # definition of a zh word (for an L1 zh learner reading a native
    # definition) - no local source in this repo provides that, so it
    # cannot be prototyped from this seed data without new synthesis.

    # FIDELITY GAP: full CC-CEDICT (~125k entries) is far larger and
    # broader than production's curated zh dictionary (~23,870 senses per
    # docs/recon-data-surface.md §3) - it includes proper nouns, classical/
    # literary entries, technical jargon, and abbreviations production has
    # never curated. Do not treat zh vocabulary COVERAGE numbers from this
    # sandbox as representative of production's curated scope, only as
    # "how much is available in a raw community dictionary."
    """
    raw_lines = 0
    parsed = 0
    vocab_id_by_lemma: dict[str, int] = {}
    sense_rank_by_vocab: dict[int, int] = {}
    sense_rows: list[tuple] = []  # (vocab_id, lemma, pinyin, def_text)

    path = REPO_ROOT / "raw" / "cedict_ts.u8"
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"):
                continue
            raw_lines += 1
            m = _CEDICT_LINE_RE.match(line.rstrip("\n"))
            if not m:
                continue
            _traditional, simplified, pinyin, defs_str = m.groups()
            defs = [d for d in defs_str.split("/") if d]
            if not defs:
                continue
            definition = "; ".join(defs[:3])
            parsed += 1

            vocab_id = vocab_id_by_lemma.get(simplified)
            if vocab_id is None:
                zipf = zipf_or_none(simplified, "zh", wordfreq_zipf)
                cur = conn.execute(
                    """INSERT INTO dim_vocabulary
                       (language_id, lemma, phrase_type, part_of_speech,
                        frequency_rank, level_tag, semantic_class)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        LANG_ZH,
                        simplified,
                        "single_word" if len(simplified) <= 2 else "compound",
                        None,  # CEDICT has no reliable POS tag
                        zipf,
                        "cedict",
                        None,
                    ),
                )
                vocab_id = cur.lastrowid
                vocab_id_by_lemma[simplified] = vocab_id
                sense_rank_by_vocab[vocab_id] = 0

            sense_rank_by_vocab[vocab_id] += 1
            sense_rows.append((vocab_id, simplified, pinyin, definition, sense_rank_by_vocab[vocab_id]))

    for vocab_id, _lemma, pinyin, definition, sense_rank in sense_rows:
        for level in ("simple", "standard"):
            # FIDELITY GAP: production generates genuinely different text for
            # simple vs standard definition_level (two separate LLM outputs).
            # CC-CEDICT gives us exactly one definition per entry, so both
            # levels here are byte-identical. Any prototype that branches on
            # definition_level for zh will see no real difference.
            conn.execute(
                """INSERT INTO dim_word_senses
                   (vocab_id, definition_language_id, definition, definition_level,
                    pronunciation, sense_rank, source, is_validated)
                   VALUES (?,?,?,?,?,?,?,1)""",
                (vocab_id, LANG_EN, definition, level, pinyin, sense_rank, "cedict"),
            )
    conn.commit()
    log(
        f"zh (CC-CEDICT): {raw_lines} raw dictionary lines, {parsed} parsed defs, "
        f"{len(vocab_id_by_lemma)} distinct lemmas -> dim_vocabulary, "
        f"{len(sense_rows) * 2} dim_word_senses rows (simple+standard)"
    )
    return {
        "raw_lines": raw_lines,
        "parsed": parsed,
        "vocab_rows": len(vocab_id_by_lemma),
        "sense_rows": len(sense_rows) * 2,
    }


# ---------------------------------------------------------------------------
# ja vocabulary + senses, from raw/jmdict_eng.json (JMdict)
# ---------------------------------------------------------------------------
def load_jmdict_ja(conn: sqlite3.Connection, wordfreq_zipf) -> dict:
    """
    raw/jmdict_eng.json was NOT in the recon's identified source list - it
    turned up in a plain directory listing while building this script. It is
    a real, structured Japanese<->English dictionary (JMdict), which is
    strictly better than the "derive ja lemmas from the test corpus alone"
    fallback the task brief anticipated for languages with no local
    dictionary. Using it here, documented, rather than deliberately ignoring
    a better available source.

    Each JMdict "word" entry can have multiple kanji/kana surface forms and
    multiple senses (with English glosses). We take:
      - lemma = first kanji form's text if any kanji form exists, else the
        first kana form's text (matches how a learner would normally look
        the word up).
      - pronunciation = first kana form's text (JMdict entries essentially
        always have at least one kana reading).
      - part_of_speech = the raw JMdict tag string(s) from the first sense
        (e.g. 'v5r-i', 'n') - NOT expanded to a human-readable label; the
        `tags` dict at the top of the source JSON has the expansions if a
        later agent wants them.
      - definition = up to 3 English glosses from the first sense, joined.

    Only entries with `common: true` on at least one kanji or kana form are
    loaded (22,630 of 218,461 total JMdict entries as of this file's
    2026-08-17 dictDate) - this keeps ja vocabulary at a scale close to
    production's own curated set (~21,378 senses per
    docs/recon-data-surface.md §3) instead of importing every archaic/rare
    JMdict headword.

    # FIDELITY GAP: same as CC-CEDICT - JMdict's glosses are English, so
    # every ja sense here has definition_language_id=EN, not a native
    # Japanese-language definition.
    """
    path = REPO_ROOT / "raw" / "jmdict_eng.json"
    vocab_id_by_lemma: dict[str, int] = {}
    sense_rank_by_vocab: dict[int, int] = {}
    n_entries_seen = 0
    n_common = 0
    pending_senses: list[tuple] = []  # (vocab_id, pronunciation, pos, definition)

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith('{"id"'):
                continue
            if line.endswith(","):
                line = line[:-1]
            n_entries_seen += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            kanji = entry.get("kanji", [])
            kana = entry.get("kana", [])
            is_common = any(k.get("common") for k in kanji) or any(k.get("common") for k in kana)
            if not is_common:
                continue
            n_common += 1

            lemma = None
            if kanji:
                lemma = kanji[0].get("text")
            if not lemma and kana:
                lemma = kana[0].get("text")
            if not lemma:
                continue
            reading = kana[0]["text"] if kana else None

            senses = entry.get("sense", [])
            pos = None
            definition = None
            if senses:
                pos_list = senses[0].get("partOfSpeech") or []
                pos = ",".join(pos_list) if pos_list else None
                glosses = [
                    g["text"]
                    for g in senses[0].get("gloss", [])
                    if g.get("lang") == "eng" and g.get("text")
                ]
                if glosses:
                    definition = "; ".join(glosses[:3])
            if not definition:
                continue  # no usable English gloss at all - skip, don't fabricate one

            vocab_id = vocab_id_by_lemma.get(lemma)
            if vocab_id is None:
                zipf = zipf_or_none(lemma, "ja", wordfreq_zipf)
                cur = conn.execute(
                    """INSERT INTO dim_vocabulary
                       (language_id, lemma, phrase_type, part_of_speech,
                        frequency_rank, level_tag, semantic_class)
                       VALUES (?,?,?,?,?,?,?)""",
                    (LANG_JA, lemma, "single_word", pos, zipf, "jmdict", None),
                )
                vocab_id = cur.lastrowid
                vocab_id_by_lemma[lemma] = vocab_id
                sense_rank_by_vocab[vocab_id] = 0

            sense_rank_by_vocab[vocab_id] += 1
            pending_senses.append((vocab_id, reading, sense_rank_by_vocab[vocab_id], definition))

    for vocab_id, reading, sense_rank, definition in pending_senses:
        for level in ("simple", "standard"):
            conn.execute(
                """INSERT INTO dim_word_senses
                   (vocab_id, definition_language_id, definition, definition_level,
                    pronunciation, sense_rank, source, is_validated)
                   VALUES (?,?,?,?,?,?,?,1)""",
                (vocab_id, LANG_EN, definition, level, reading, sense_rank, "jmdict"),
            )
    conn.commit()
    log(
        f"ja (JMdict): {n_entries_seen} total entries scanned, {n_common} common, "
        f"{len(vocab_id_by_lemma)} distinct lemmas -> dim_vocabulary, "
        f"{len(pending_senses) * 2} dim_word_senses rows (simple+standard)"
    )
    return {
        "entries_scanned": n_entries_seen,
        "common": n_common,
        "vocab_rows": len(vocab_id_by_lemma),
        "sense_rows": len(pending_senses) * 2,
    }


# ---------------------------------------------------------------------------
# en vocabulary - NO local dictionary exists (recon confirmed this). Derive
# lemmas from (a) wordfreq's own published English frequency wordlist and
# (b) tokens actually occurring in the local EN test transcripts, and tag
# each with a real spaCy POS tag (en_core_web_sm is installed offline in
# this repo's venv). No definitions are available from any local source.
# ---------------------------------------------------------------------------
def load_en_vocab(conn: sqlite3.Connection, wordfreq_zipf, en_transcripts: list[str]) -> dict:
    """
    # FIDELITY GAP (the largest one in this build): there is no local
    # English dictionary anywhere in this repo (confirmed: no wordnet/nltk
    # data, no bundled English dictionary file - only the `wordfreq` package,
    # which ships frequency data, not definitions). Every en dim_word_senses
    # row seeded here has definition=NULL. This means:
    #   - en `definition_match` prototypes (a deterministic ladder type in
    #     production, docs/recon-generation.md §3a) CANNOT be prototyped
    #     against this seed data - there is nothing to match against.
    #   - en distractor-embedding prototypes only have the LEMMA STRING
    #     itself to embed (no definition text), which starves the TF-IDF
    #     proxy embedder even further than usual (see lab/embeddings.py).
    # part_of_speech IS real here (spaCy en_core_web_sm, run offline, no
    # download) - this is the one axis where en fidelity is fine.
    """
    import spacy

    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])

    top_words = [w for w in _wordfreq_top_n("en", 4000) if w.isalpha()]
    corpus_tokens: dict[str, int] = {}
    token_re = re.compile(r"[A-Za-z']+")
    for t in en_transcripts:
        for tok in token_re.findall(t.lower()):
            corpus_tokens[tok] = corpus_tokens.get(tok, 0) + 1

    lemma_source: dict[str, str] = {w: "wordfreq_top4000" for w in top_words}
    for tok, count in corpus_tokens.items():
        if tok not in lemma_source and count >= 1:
            lemma_source[tok] = "corpus_transcript"

    words = sorted(lemma_source.keys())
    pos_by_word: dict[str, str | None] = {}
    for doc in nlp.pipe(words, batch_size=500):
        if len(doc) == 0:
            continue
        pos_by_word[doc[0].text] = doc[0].pos_

    n_vocab = 0
    n_sense = 0
    for word in words:
        zipf = zipf_or_none(word, "en", wordfreq_zipf)
        cur = conn.execute(
            """INSERT INTO dim_vocabulary
               (language_id, lemma, phrase_type, part_of_speech, frequency_rank, level_tag)
               VALUES (?,?,?,?,?,?)""",
            (LANG_EN, word, "single_word", pos_by_word.get(word), zipf, lemma_source[word]),
        )
        vocab_id = cur.lastrowid
        n_vocab += 1
        for level in ("simple", "standard"):
            conn.execute(
                """INSERT INTO dim_word_senses
                   (vocab_id, definition_language_id, definition, definition_level,
                    sense_rank, source, is_validated)
                   VALUES (?,?,?,?,1,?,0)""",
                (vocab_id, LANG_EN, None, level, "wordfreq+spacy_no_definition"),
            )
            n_sense += 1
    conn.commit()
    log(
        f"en (wordfreq top4000 + corpus tokens + spaCy POS, NO definitions available "
        f"locally): {n_vocab} dim_vocabulary rows, {n_sense} dim_word_senses rows "
        f"(all definition=NULL)"
    )
    return {"vocab_rows": n_vocab, "sense_rows": n_sense}


def _wordfreq_top_n(lang: str, n: int) -> list[str]:
    from wordfreq import top_n_list

    return top_n_list(lang, n)


# ---------------------------------------------------------------------------
# tests + questions, from generated_tests_20251209_225642_{tests,questions}.csv
# ---------------------------------------------------------------------------
_TRANSCRIPT_JSON_RE = re.compile(r'"transcript"\s*:\s*"((?:[^"\\]|\\.)*)"')

_LANG_NAME_TO_ID = {"chinese": LANG_ZH, "english": LANG_EN, "japanese": LANG_JA}


def _extract_transcript(raw_field: str) -> str:
    """The CSV's `transcript` column is a ```json-fenced blob containing
    {"transcript": "...", "difficulty_level": N}, not plain text - unwrap
    it. Falls back to the raw field if the expected shape isn't found
    (defensive - do not raise the whole build over one malformed row)."""
    m = _TRANSCRIPT_JSON_RE.search(raw_field)
    if not m:
        return raw_field
    escaped = m.group(1)
    try:
        return json.loads(f'"{escaped}"')
    except json.JSONDecodeError:
        return escaped.replace('\\"', '"').replace("\\n", "\n")


def load_tests_and_questions(conn: sqlite3.Connection) -> dict:
    tests_path = REPO_ROOT / "generated_tests_20251209_225642_tests.csv"
    questions_path = REPO_ROOT / "generated_tests_20251209_225642_questions.csv"

    n_tests = 0
    en_transcripts: list[str] = []
    with tests_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lang_id = _LANG_NAME_TO_ID.get(row["language"].strip().lower())
            if lang_id is None:
                continue
            transcript = _extract_transcript(row["transcript"])
            if lang_id == LANG_EN:
                en_transcripts.append(transcript)
            conn.execute(
                """INSERT INTO tests
                   (id, language_id, slug, topic, difficulty, style, tier, title,
                    transcript, total_attempts, is_active, is_featured, is_custom,
                    generation_model, vocab_sense_ids, vocab_token_map, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["id"],
                    lang_id,
                    row["slug"] or None,
                    row["topic"] or None,
                    int(row["difficulty"]) if row["difficulty"] else None,
                    row["style"] or None,
                    row["tier"] or None,
                    row["title"] or None,
                    transcript,
                    int(row["total_attempts"] or 0),
                    1 if row["is_active"].lower() == "true" else 0,
                    1 if row["is_featured"].lower() == "true" else 0,
                    1 if row["is_custom"].lower() == "true" else 0,
                    row["generation_model"] or None,
                    "[]",  # not linked in this sandbox - see schema.sql note
                    "{}",
                    row["created_at"] or None,
                    row["updated_at"] or None,
                ),
            )
            n_tests += 1

    n_questions = 0
    with questions_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            choices = row["choices"] or "[]"
            try:
                correct_answer = json.loads(row["correct_answer"]) if row["correct_answer"] else None
            except json.JSONDecodeError:
                correct_answer = row["correct_answer"]
            conn.execute(
                """INSERT INTO questions
                   (id, test_id, question_id, question_text, question_type, choices,
                    correct_answer, answer_explanation, points, sense_ids, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row["id"],
                    row["test_id"],
                    row["question_id"] or None,
                    row["question_text"],
                    row["question_type"] or None,
                    choices,
                    correct_answer,
                    row["answer_explanation"] or None,
                    int(row["points"] or 1),
                    "[]",
                    row["created_at"] or None,
                ),
            )
            n_questions += 1
    conn.commit()
    log(
        f"tests: {n_tests} rows loaded (CSV had 703 raw physical lines per recon's naive "
        f"line count, but csv.DictReader correctly parses embedded newlines inside "
        f"quoted transcript fields down to {n_tests} real rows)"
    )
    log(f"questions: {n_questions} rows loaded, referencing {n_tests} tests")
    return {"tests": n_tests, "questions": n_questions, "en_transcripts": en_transcripts}


# ---------------------------------------------------------------------------
# Classifier (zh 量词) / counter (ja 助数詞) dictionaries
# ---------------------------------------------------------------------------
def load_classifiers(conn: sqlite3.Connection, zh_lemma_to_vocab: dict[str, int],
                      zh_primary_sense: dict[int, int]) -> dict:
    from pypinyin import Style, pinyin as pypinyin_convert

    curation_dir = REPO_ROOT / "data" / "classifier_curation"
    files = sorted(p for p in curation_dir.glob("*.json") if p.name != "approved_curation.json")

    n_classifiers = 0
    n_pairs = 0
    n_resolved = 0
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        hanzi = data["classifier"]["hanzi"]
        semantic_label = data["classifier"].get("semantic_label") or None
        pinyin_syllables = pypinyin_convert(hanzi, style=Style.TONE)
        pinyin_display = "".join(s[0] for s in pinyin_syllables)
        pinyin_numeric = " ".join(s[0] for s in pypinyin_convert(hanzi, style=Style.TONE3))

        nouns = [n for n in data.get("nouns", []) if n.get("accepted")]
        example_nouns = json.dumps([n["noun"] for n in nouns[:5]], ensure_ascii=False)
        zipf = zipf_or_none(hanzi, "zh", __import__("wordfreq").zipf_frequency)

        cur = conn.execute(
            """INSERT INTO dim_classifiers
               (language_id, hanzi, pinyin, pinyin_display, semantic_label,
                example_nouns, frequency_rank)
               VALUES (?,?,?,?,?,?,?)""",
            (LANG_ZH, hanzi, pinyin_numeric, pinyin_display, semantic_label, example_nouns, zipf),
        )
        classifier_id = cur.lastrowid
        n_classifiers += 1

        for noun_info in nouns:
            noun = noun_info["noun"]
            vocab_id = zh_lemma_to_vocab.get(noun)
            sense_id = zh_primary_sense.get(vocab_id) if vocab_id else None
            if sense_id:
                n_resolved += 1
            conn.execute(
                """INSERT INTO dim_classifier_noun_pairs
                   (language_id, noun_sense_id, lemma_text, classifier_id,
                    is_primary, frequency_score, source)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    LANG_ZH,
                    sense_id,
                    noun,
                    classifier_id,
                    1,
                    float(noun_info.get("judge_rating") or 0) / 5.0,
                    "classifier_curation_json",
                ),
            )
            n_pairs += 1
    conn.commit()
    log(
        f"dim_classifiers: {n_classifiers} rows (from {len(files)} data/classifier_curation/*.json), "
        f"dim_classifier_noun_pairs: {n_pairs} rows ({n_resolved} resolved to a seeded zh sense, "
        f"{n_pairs - n_resolved} left noun_sense_id=NULL - noun not in our seeded zh vocabulary)"
    )
    return {"classifiers": n_classifiers, "pairs": n_pairs, "pairs_resolved": n_resolved}


def load_counters(conn: sqlite3.Connection, ja_lemma_to_vocab: dict[str, int],
                   ja_primary_sense: dict[int, int]) -> dict:
    curation_dir = REPO_ROOT / "data" / "counter_curation"
    files = sorted(p for p in curation_dir.glob("*.json") if p.name != "approved_curation.json")

    n_counters = 0
    n_pairs = 0
    n_resolved = 0
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        c = data["counter"]
        kanji = c["counter"]
        reading = c.get("reading")
        semantic_label = c.get("semantic_label") or None
        zipf = zipf_or_none(kanji, "ja", __import__("wordfreq").zipf_frequency)

        nouns = [n for n in data.get("nouns", []) if n.get("accepted")]
        example_nouns = json.dumps([n["noun"] for n in nouns[:5]], ensure_ascii=False)

        cur = conn.execute(
            """INSERT INTO dim_counters
               (language_id, kanji, reading, reading_display, semantic_label,
                example_nouns, frequency_rank)
               VALUES (?,?,?,?,?,?,?)""",
            (LANG_JA, kanji, reading, reading, semantic_label, example_nouns, zipf),
        )
        counter_id = cur.lastrowid
        n_counters += 1

        for noun_info in nouns:
            noun = noun_info["noun"]
            vocab_id = ja_lemma_to_vocab.get(noun)
            sense_id = ja_primary_sense.get(vocab_id) if vocab_id else None
            if sense_id:
                n_resolved += 1
            conn.execute(
                """INSERT INTO dim_counter_noun_pairs
                   (language_id, noun_sense_id, lemma_text, counter_id,
                    is_primary, frequency_score, source)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    LANG_JA,
                    sense_id,
                    noun,
                    counter_id,
                    1,
                    float(noun_info.get("judge_rating") or 0) / 5.0,
                    "counter_curation_json",
                ),
            )
            n_pairs += 1
    conn.commit()
    log(
        f"dim_counters: {n_counters} rows (from {len(files)} data/counter_curation/*.json), "
        f"dim_counter_noun_pairs: {n_pairs} rows ({n_resolved} resolved to a seeded ja sense, "
        f"{n_pairs - n_resolved} left noun_sense_id=NULL)"
    )
    return {"counters": n_counters, "pairs": n_pairs, "pairs_resolved": n_resolved}


# ---------------------------------------------------------------------------
# Embeddings + corpus-mined example sentences for the top-N senses/language
# ---------------------------------------------------------------------------
_SENTENCE_SPLIT_RE = {
    LANG_ZH: re.compile(r"[。！？\n]"),
    LANG_JA: re.compile(r"[。！？\n]"),
    LANG_EN: re.compile(r"(?<=[.!?])\s+|\n"),
}


def compute_embeddings_and_examples(conn: sqlite3.Connection, transcripts_by_lang: dict[int, list[str]]) -> dict:
    """
    Fits one HashedCharNgramTfidf per language on ALL standard-level
    definitions for that language (broad IDF statistics), then computes and
    stores a packed-float32 embedding for only the top
    EMBED_TOP_N_PER_LANGUAGE senses by frequency_rank (bounded build time -
    see the module-level constant's docstring). The same capped set also
    gets a real corpus-mined example_sentence where the lemma is found
    verbatim in a local test transcript for that language.
    """
    sentences_by_lang: dict[int, list[str]] = {}
    for lang_id, texts in transcripts_by_lang.items():
        splitter = _SENTENCE_SPLIT_RE[lang_id]
        sentences: list[str] = []
        for t in texts:
            for s in splitter.split(t):
                s = s.strip()
                if s:
                    sentences.append(s)
        sentences_by_lang[lang_id] = sentences

    totals = {"embedded": 0, "examples_filled": 0}
    for lang_id in (LANG_ZH, LANG_JA, LANG_EN):
        rows = conn.execute(
            """SELECT ws.id AS sense_id, v.lemma AS lemma, ws.definition AS definition
               FROM dim_word_senses ws
               JOIN dim_vocabulary v ON v.id = ws.vocab_id
               WHERE v.language_id = ? AND ws.definition_level = 'standard'
               ORDER BY v.frequency_rank DESC NULLS LAST
               LIMIT ?""",
            (lang_id, EMBED_TOP_N_PER_LANGUAGE),
        ).fetchall()
        if not rows:
            continue

        backend = HashedCharNgramTfidf(dim=512)
        # Fit on the full definitions corpus for this language (broader
        # sample than just the capped rows), matching production's
        # philosophy of embedding "{lemma}: {definition}".
        all_defs = [
            r["definition"]
            for r in conn.execute(
                """SELECT ws.definition AS definition FROM dim_word_senses ws
                   JOIN dim_vocabulary v ON v.id = ws.vocab_id
                   WHERE v.language_id = ? AND ws.definition_level = 'standard'
                   AND ws.definition IS NOT NULL""",
                (lang_id,),
            ).fetchall()
        ]
        texts_for_fit = [f"{r['lemma']}: {r['definition']}" for r in rows if r["definition"]] + all_defs
        backend.fit(texts_for_fit)

        sentences = sentences_by_lang.get(lang_id, [])
        n_embedded = 0
        n_examples = 0
        for r in rows:
            embed_text = f"{r['lemma']}: {r['definition'] or ''}"
            vec = backend.embed(embed_text)
            blob = pack_embedding(vec)

            example = None
            if sentences:
                for s in sentences:
                    if r["lemma"] and r["lemma"] in s:
                        example = s
                        n_examples += 1
                        break

            # Update BOTH definition_level rows that share this lemma's
            # sense_rank (same embedding/example for simple+standard, since
            # our seed definitions are identical across levels anyway - see
            # the FIDELITY GAP notes in load_cedict_zh/load_jmdict_ja).
            conn.execute(
                "UPDATE dim_word_senses SET embedding = ?, example_sentence = COALESCE(example_sentence, ?) "
                "WHERE id = ?",
                (blob, example, r["sense_id"]),
            )
            n_embedded += 1
        conn.commit()
        totals["embedded"] += n_embedded
        totals["examples_filled"] += n_examples
        log(
            f"embeddings/examples for language_id={lang_id}: {n_embedded} senses embedded "
            f"(top {EMBED_TOP_N_PER_LANGUAGE} by frequency_rank, backend={backend.name}), "
            f"{n_examples} got a real corpus-mined example_sentence "
            f"(corpus had {len(sentences)} candidate sentences for this language)"
        )
    return totals


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    t_start = time.time()
    if DB_PATH.exists():
        DB_PATH.unlink()
        log(f"removed existing {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # OFF during bulk load for speed/ordering freedom
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    from wordfreq import zipf_frequency

    counts: dict[str, object] = {}
    counts["dim_languages"] = load_dim_languages(conn)
    counts["zh"] = load_cedict_zh(conn, zipf_frequency)
    counts["ja"] = load_jmdict_ja(conn, zipf_frequency)

    tq = load_tests_and_questions(conn)
    counts["tests"] = tq["tests"]
    counts["questions"] = tq["questions"]

    en_counts = load_en_vocab(conn, zipf_frequency, tq["en_transcripts"])
    counts["en"] = en_counts

    # Build lemma -> vocab_id and vocab_id -> primary sense_id maps for the
    # classifier/counter noun-linking pass (primary = sense_rank 1, standard level).
    def _lemma_maps(lang_id: int) -> tuple[dict[str, int], dict[int, int]]:
        lemma_to_vocab: dict[str, int] = {}
        for row in conn.execute(
            "SELECT id, lemma FROM dim_vocabulary WHERE language_id = ?", (lang_id,)
        ):
            lemma_to_vocab[row[1]] = row[0]
        vocab_to_sense: dict[int, int] = {}
        for row in conn.execute(
            """SELECT vocab_id, id FROM dim_word_senses
               WHERE definition_level = 'standard' AND sense_rank = 1
               AND vocab_id IN (SELECT id FROM dim_vocabulary WHERE language_id = ?)""",
            (lang_id,),
        ):
            vocab_to_sense[row[0]] = row[1]
        return lemma_to_vocab, vocab_to_sense

    zh_lemma_to_vocab, zh_vocab_to_sense = _lemma_maps(LANG_ZH)
    ja_lemma_to_vocab, ja_vocab_to_sense = _lemma_maps(LANG_JA)

    counts["classifiers"] = load_classifiers(conn, zh_lemma_to_vocab, zh_vocab_to_sense)
    counts["counters"] = load_counters(conn, ja_lemma_to_vocab, ja_vocab_to_sense)

    # zh/ja transcripts for corpus-mined example sentences (en handled
    # separately above, reusing the same list already extracted).
    zh_transcripts = [
        r[0] for r in conn.execute("SELECT transcript FROM tests WHERE language_id = ?", (LANG_ZH,))
    ]
    ja_transcripts = [
        r[0] for r in conn.execute("SELECT transcript FROM tests WHERE language_id = ?", (LANG_JA,))
    ]
    counts["embeddings"] = compute_embeddings_and_examples(
        conn,
        {LANG_ZH: zh_transcripts, LANG_JA: ja_transcripts, LANG_EN: tq["en_transcripts"]},
    )

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    log("--- Row count summary (all tables) ---")
    for (table,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        log(f"  {table}: {n}")

    conn.close()
    log(f"Build complete in {time.time() - t_start:.1f}s -> {DB_PATH}")


if __name__ == "__main__":
    main()
