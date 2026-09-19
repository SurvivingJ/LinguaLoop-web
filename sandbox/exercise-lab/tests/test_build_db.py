"""
Proves the lab database actually builds and has the shape the rest of this
sandbox depends on. Reuses an already-built db/lab.sqlite if present (the
build takes ~30s from local files - not worth re-paying on every test run);
deletes-and-rebuilds only if it's missing.
"""
import sqlite3

import build_db

REQUIRED_TABLES = {
    "dim_languages",
    "dim_vocabulary",
    "dim_word_senses",
    "word_assets",
    "exercises",
    "tests",
    "questions",
    "user_skill_ratings",
    "user_vocabulary_knowledge",
    "exercise_attempts",
    "test_attempts",
    "question_attempt_results",
    "dim_classifiers",
    "dim_classifier_noun_pairs",
    "dim_counters",
    "dim_counter_noun_pairs",
}

# Tables this sandbox deliberately seeds with ZERO rows: no LLM call is ever
# allowed to populate word_assets/exercises, and no synthetic attempts are
# baked into the static seed (learner_sim.py generates those in-memory,
# on demand, not as part of build_db.py).
EXPECTED_EMPTY_TABLES = {
    "word_assets",
    "exercises",
    "user_skill_ratings",
    "user_vocabulary_knowledge",
    "exercise_attempts",
    "test_attempts",
    "question_attempt_results",
}


def _ensure_built() -> None:
    if not build_db.DB_PATH.exists():
        build_db.main()


def _connect() -> sqlite3.Connection:
    _ensure_built()
    conn = sqlite3.connect(str(build_db.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def test_all_required_tables_exist():
    conn = _connect()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = REQUIRED_TABLES - tables
    assert not missing, f"missing tables: {missing}"


def test_row_counts_match_the_documented_seed():
    conn = _connect()

    def count(table: str) -> int:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    assert count("dim_languages") == 3
    # zh (CC-CEDICT) + ja (JMdict common) + en (wordfreq+corpus) lemmas
    assert count("dim_vocabulary") > 140_000
    assert count("dim_word_senses") > 250_000
    assert count("tests") == 153
    assert count("questions") == 765
    assert count("dim_classifiers") == 43
    assert count("dim_counters") == 43

    for table in EXPECTED_EMPTY_TABLES:
        assert count(table) == 0, f"{table} should be seeded empty, found {count(table)} rows"


def test_frequency_rank_is_a_zipf_score_not_a_rank():
    """的 ('de', the single most common zh grammatical particle) must have a
    HIGH frequency_rank close to the documented max (6.56), not a low value -
    this is the exact inversion bug the recon flags as a real, previously-hit
    defect (migrations/calibration_semantic_distractors.sql:39-52)."""
    conn = _connect()
    row = conn.execute(
        "SELECT frequency_rank FROM dim_vocabulary WHERE lemma = ? AND language_id = 1", ("的",)
    ).fetchone()
    assert row is not None
    assert row["frequency_rank"] > 5.0


def test_dim_word_senses_has_two_rows_per_sense_rank():
    conn = _connect()
    row = conn.execute(
        """SELECT vocab_id, sense_rank, COUNT(*) as n
           FROM dim_word_senses GROUP BY vocab_id, sense_rank
           HAVING vocab_id = (SELECT id FROM dim_vocabulary WHERE lemma='你' AND language_id=1)
           LIMIT 1"""
    ).fetchone()
    assert row is not None
    assert row["n"] == 2  # simple + standard


def test_en_senses_have_no_definition_documented_gap():
    """The largest fidelity gap in this build: no local English dictionary
    exists, so every en sense's definition is NULL by construction."""
    conn = _connect()
    total = conn.execute(
        """SELECT COUNT(*) FROM dim_word_senses ws
           JOIN dim_vocabulary v ON v.id = ws.vocab_id WHERE v.language_id = 2"""
    ).fetchone()[0]
    with_def = conn.execute(
        """SELECT COUNT(*) FROM dim_word_senses ws
           JOIN dim_vocabulary v ON v.id = ws.vocab_id
           WHERE v.language_id = 2 AND ws.definition IS NOT NULL"""
    ).fetchone()[0]
    assert total > 0
    assert with_def == 0


def test_embedding_blob_round_trips_to_the_right_shape():
    from lab.embeddings import unpack_embedding

    conn = _connect()
    row = conn.execute(
        "SELECT embedding FROM dim_word_senses WHERE embedding IS NOT NULL LIMIT 1"
    ).fetchone()
    assert row is not None
    vec = unpack_embedding(row["embedding"])
    assert vec.shape == (512,)
    assert vec.dtype.name == "float32"


def test_classifier_noun_pairs_link_back_to_seeded_zh_senses():
    conn = _connect()
    resolved = conn.execute(
        "SELECT COUNT(*) FROM dim_classifier_noun_pairs WHERE noun_sense_id IS NOT NULL"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM dim_classifier_noun_pairs").fetchone()[0]
    assert total > 0
    assert resolved > 0  # at least some nouns resolve against the CEDICT-derived vocabulary
