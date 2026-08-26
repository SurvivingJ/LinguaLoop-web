"""Unit tests for Dual Translation remediation card generation (TASK-613)
and its DB/FSRS wiring (TASK-614).

Pure-logic tests (build_*, interleave_by_subtype) — no DB, no OpenRouter —
mirroring the "mock every boundary" convention of the other dual-translation
suites. The ``generate_cards_for_queued_entries`` tests below use a minimal
fake query-builder, matching the ``_FakeDB`` pattern in
test_dual_translation_routes.py.
"""

from services.dual_translation import cards


def err(*, span_reference, corrected_form, learner_form="", subtype="article"):
    """Build one dt_error_instance-shaped record (only the fields cards.py
    actually reads)."""
    return {
        "span_reference": span_reference,
        "corrected_form": corrected_form,
        "learner_form": learner_form,
        "subtype": subtype,
    }


# ---------------------------------------------------------------------------
# The headline acceptance criterion: answer target is corrected_form, never
# learner_form — for BOTH card types.
# ---------------------------------------------------------------------------

def test_cloze_answer_is_corrected_form_never_learner_form():
    gold_l2 = "The cat sat on mat. It was sleepy."
    span = [15, 18]  # "mat" -> should be "the mat"
    assert gold_l2[span[0]:span[1]] == "mat"
    error = err(span_reference=span, corrected_form="the mat", learner_form="mat")

    card = cards.build_cloze_card(error, gold_l2)

    assert card["answer"] == "the mat"
    assert card["answer"] != error["learner_form"]
    assert "learner_form" not in card
    assert error["learner_form"] not in card.values()


def test_isolate_retranslate_answer_is_corrected_form_never_learner_form():
    gold_l2 = "The cat sat on the mat. It was sleepy."
    l1_text = "猫は座布団の上に座っていた。眠そうだった。"
    span = [4, 7]  # "cat"
    error = err(span_reference=span, corrected_form="the cat", learner_form="cat")

    card = cards.build_isolate_retranslate_card(error, gold_l2, l1_text)

    assert card["answer"] == "the cat"
    assert card["answer"] != error["learner_form"]
    assert "learner_form" not in card
    assert error["learner_form"] not in card.values()


def test_build_cards_returns_both_types_never_carrying_learner_form():
    gold_l2 = "The cat sat on the mat. It was sleepy."
    l1_text = "The cat context."
    error = err(span_reference=[4, 7], corrected_form="the cat", learner_form="cat")

    built = cards.build_cards(error, gold_l2, l1_text)
    by_type = {c["card_type"]: c for c in built}

    assert set(by_type) == {cards.CARD_TYPE_CLOZE, cards.CARD_TYPE_ISOLATE_RETRANSLATE}
    for card in built:
        assert card["subtype"] == "article"
        payload = card["prompt_payload"]
        assert payload["answer"] == "the cat"
        assert "learner_form" not in payload


# ---------------------------------------------------------------------------
# One atomic target per cloze card
# ---------------------------------------------------------------------------

def test_cloze_card_blanks_exactly_one_atom():
    gold_l2 = "The cat sat on the mat. It was sleepy."
    error = err(span_reference=[4, 7], corrected_form="the cat", learner_form="cat")

    card = cards.build_cloze_card(error, gold_l2)

    assert card["prompt"].count(cards.CLOZE_BLANK) == 1
    assert "cat" not in card["prompt"].replace(cards.CLOZE_BLANK, "")


def test_cloze_card_handles_zero_width_omission_span():
    """An omission error (learner left something out): span is zero-width at
    the insertion point, corrected_form is the word that should be inserted."""
    gold_l2 = "I go school every day."
    span = [4, 4]  # insertion point right before "school"
    error = err(span_reference=span, corrected_form="to", learner_form="")

    card = cards.build_cloze_card(error, gold_l2)

    assert card["answer"] == "to"
    assert card["prompt"].count(cards.CLOZE_BLANK) == 1
    assert "school" in card["prompt"]  # surrounding sentence preserved


# ---------------------------------------------------------------------------
# Sentence isolation — cards scope to the containing sentence, not the whole
# (2-4 sentence) passage.
# ---------------------------------------------------------------------------

def test_cloze_card_scopes_to_containing_sentence_only():
    gold_l2 = "Once upon a time there was a fox. The fox sat on the mat. It was sleepy."
    # error is in sentence 2 ("The fox sat on the mat.")
    start = gold_l2.index("the mat")
    span = [start, start + len("the mat")]
    error = err(span_reference=span, corrected_form="a mat", learner_form="the mat")

    card = cards.build_cloze_card(error, gold_l2)

    assert "fox" in card["prompt"]  # sentence 2's own subject retained
    assert "Once upon a time" not in card["prompt"]  # sentence 1 excluded
    assert "It was sleepy" not in card["prompt"]  # sentence 3 excluded


def test_isolate_retranslate_card_scopes_to_containing_sentence_only():
    gold_l2 = "Once upon a time there was a fox. The fox sat on the mat. It was sleepy."
    start = gold_l2.index("the mat")
    span = [start, start + len("the mat")]
    error = err(span_reference=span, corrected_form="a mat", learner_form="the mat")

    # l1_text has 1 sentence against gold_l2's 3 -- counts don't match, so
    # l1_context can't be narrowed and falls back to the whole thing (the
    # pre-existing, always-safe behaviour).
    card = cards.build_isolate_retranslate_card(error, gold_l2, l1_text="从前有一只狐狸。")

    assert card["target_sentence"] == "The fox sat on the mat."
    assert card["l1_context"] == "从前有一只狐狸。"


def test_isolate_retranslate_narrows_l1_context_to_matching_sentence():
    """Regression for the reported bug: a card instructed "Translate this
    into the language you are studying" but showed the whole 2-4 sentence
    passage as the reference while only ONE sentence was ever graded
    (target_sentence/answer). When l1_text's sentence count matches gold_l2's,
    l1_context must narrow to the one L1 sentence corresponding to
    target_sentence, not the whole passage.
    """
    gold_l2 = "Once upon a time there was a fox. The fox sat on the mat. It was sleepy."
    l1_text = "从前有一只狐狸。狐狸坐在垫子上。它很困。"
    start = gold_l2.index("the mat")
    span = [start, start + len("the mat")]
    error = err(span_reference=span, corrected_form="a mat", learner_form="the mat")

    card = cards.build_isolate_retranslate_card(error, gold_l2, l1_text)

    assert card["target_sentence"] == "The fox sat on the mat."
    assert card["l1_context"] == "狐狸坐在垫子上。"
    assert card["l1_context"] != l1_text


def test_cloze_card_includes_l1_context_for_the_containing_sentence():
    """Regression for the reported bug: a "word choice" cloze card correctly
    blanked the L2 element but gave no English reference, so the learner had
    no way to know which word was meant. The cloze payload must carry
    l1_context (scoped to the one corresponding L1 sentence), same as
    isolate_retranslate already does."""
    gold_l2 = "Once upon a time there was a fox. The fox sat on the mat. It was sleepy."
    l1_text = "从前有一只狐狸。狐狸坐在垫子上。它很困。"
    start = gold_l2.index("the mat")
    span = [start, start + len("the mat")]
    error = err(
        span_reference=span, corrected_form="a mat", learner_form="the mat",
        subtype="word_choice",
    )

    card = cards.build_cloze_card(error, gold_l2, l1_text)

    assert card["l1_context"] == "狐狸坐在垫子上。"


def test_cloze_card_l1_context_defaults_to_empty_string_when_omitted():
    """Callers that only have gold_l2 (no l1_text) still work -- l1_context
    degrades to "" rather than raising or carrying the whole gold_l2 text."""
    gold_l2 = "The cat sat on the mat. It was sleepy."
    error = err(span_reference=[4, 7], corrected_form="the cat", learner_form="cat")

    card = cards.build_cloze_card(error, gold_l2)

    assert card["l1_context"] == ""


def test_cjk_sentence_terminators_are_recognised():
    gold_l2 = "从前有一只狐狸。狐狸坐在垫子上。它很困。"
    start = gold_l2.index("垫子")
    span = [start, start + len("垫子")]
    error = err(span_reference=span, corrected_form="椅子", learner_form="垫子", subtype="classifier")

    card = cards.build_cloze_card(error, gold_l2)

    assert "从前" not in card["prompt"]
    assert "它很困" not in card["prompt"]
    assert card["prompt"].count(cards.CLOZE_BLANK) == 1


# ---------------------------------------------------------------------------
# interleave_by_subtype (TASK-614) — the due queue must not block-group one
# subtype (acceptance criterion, [[features/dual-translation-remediation.tech]]
# §Testing Strategy).
# ---------------------------------------------------------------------------

def test_interleave_round_robins_across_subtypes():
    due = [
        {"card_id": 1, "subtype": "article"},
        {"card_id": 2, "subtype": "article"},
        {"card_id": 3, "subtype": "article"},
        {"card_id": 4, "subtype": "classifier"},
        {"card_id": 5, "subtype": "classifier"},
    ]

    result = cards.interleave_by_subtype(due)

    # No two consecutive cards share a subtype until one bucket is drained.
    subtypes = [c["subtype"] for c in result]
    assert subtypes == ["article", "classifier", "article", "classifier", "article"]


def test_interleave_preserves_within_subtype_order():
    due = [
        {"card_id": 1, "subtype": "article"},
        {"card_id": 2, "subtype": "classifier"},
        {"card_id": 3, "subtype": "article"},
    ]

    result = cards.interleave_by_subtype(due)

    article_ids = [c["card_id"] for c in result if c["subtype"] == "article"]
    assert article_ids == [1, 3]


def test_interleave_empty_input():
    assert cards.interleave_by_subtype([]) == []


def test_interleave_single_subtype_returns_unchanged_order():
    due = [{"card_id": 1, "subtype": "article"}, {"card_id": 2, "subtype": "article"}]
    assert cards.interleave_by_subtype(due) == due


# ---------------------------------------------------------------------------
# generate_cards_for_queued_entries (TASK-614 DB wiring)
# ---------------------------------------------------------------------------

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Minimal chainable stand-in for supabase-py's query builder — mirrors
    test_dual_translation_routes.py's ``_FakeQuery``. Filter/projection
    methods are no-ops that return self; insert/update record their payload
    on the owning _FakeDB; execute() returns the canned data for this table."""

    def __init__(self, data, recorder, table_name):
        self._data = data
        self._recorder = recorder
        self._table_name = table_name

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def or_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def insert(self, payload):
        self._recorder.append((self._table_name, 'insert', payload))
        return self

    def update(self, payload):
        self._recorder.append((self._table_name, 'update', payload))
        return self

    def execute(self):
        return _FakeResult(self._data)


class _FakeDB:
    def __init__(self, tables: dict):
        self._tables = tables
        self.calls = []

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []), self.calls, name)


def _base_tables(**overrides):
    tables = {
        'dt_error_profile_entry': [{'id': 100, 'subtype': 'article'}],
        'dt_card': [],
        'dt_submission': [{'id': 5, 'passage_id': 9, 'l1_language_id': 2}],
        'dt_error_instance': [{
            'id': 900, 'submission_id': 5, 'span_reference': [4, 7],
            'corrected_form': 'the cat', 'learner_form': 'cat', 'subtype': 'article',
        }],
        'dt_passage': [{'l2_text': 'The cat sat on the mat.'}],
        'dt_passage_reference': [{'l1_text': 'Le chat context.'}],
    }
    tables.update(overrides)
    return tables


class TestGenerateCardsForQueuedEntries:

    def test_no_queued_entries_returns_zero_and_writes_nothing(self):
        db = _FakeDB({'dt_error_profile_entry': []})

        assert cards.generate_cards_for_queued_entries(db, 'u1') == 0
        assert db.calls == []

    def test_skips_entries_that_already_have_a_card(self):
        db = _FakeDB(_base_tables(dt_card=[{'profile_entry_id': 100}]))

        assert cards.generate_cards_for_queued_entries(db, 'u1') == 0
        assert not any(name == 'dt_card' and method == 'insert' for name, method, _ in db.calls)

    def test_carded_entry_inserts_both_card_types_and_flips_to_drilling(self):
        db = _FakeDB(_base_tables())

        carded = cards.generate_cards_for_queued_entries(db, 'u1')

        assert carded == 1
        card_insert = next(p for n, m, p in db.calls if n == 'dt_card' and m == 'insert')
        assert len(card_insert) == 2
        card_types = {row['card_type'] for row in card_insert}
        assert card_types == {cards.CARD_TYPE_CLOZE, cards.CARD_TYPE_ISOLATE_RETRANSLATE}
        for row in card_insert:
            assert row['user_id'] == 'u1'
            assert row['profile_entry_id'] == 100
            assert row['origin_error_id'] == 900
            assert row['state'] == 'new'
            assert 'learner_form' not in row['prompt_payload']

        status_update = next(
            p for n, m, p in db.calls if n == 'dt_error_profile_entry' and m == 'update'
        )
        assert status_update == {'remediation_status': 'drilling'}

    def test_skips_entry_when_no_matching_error_instance(self):
        db = _FakeDB(_base_tables(dt_error_instance=[]))

        assert cards.generate_cards_for_queued_entries(db, 'u1') == 0
        assert not any(name == 'dt_card' for name, _, _ in db.calls)

    def test_skips_entry_when_source_passage_unresolvable(self):
        db = _FakeDB(_base_tables(dt_passage=[]))

        assert cards.generate_cards_for_queued_entries(db, 'u1') == 0
        assert not any(name == 'dt_card' for name, _, _ in db.calls)


# ---------------------------------------------------------------------------
# select_error_exercises_for_practice (TASK-618 Practice Engine injection)
# ---------------------------------------------------------------------------

def _due_card(card_id, subtype='article', due_date='2026-07-01', profile_entry_id=100):
    """One due dt_card-shaped row (only the fields the selector reads). Carries
    profile_entry_id so the internal generate_cards pass sees it as already
    carded and stays a no-op."""
    return {
        'id': card_id,
        'card_type': 'cloze',
        'subtype': subtype,
        'prompt_payload': {'prompt': f'p{card_id}', 'answer': f'a{card_id}'},
        'state': 'review',
        'due_date': due_date,
        'profile_entry_id': profile_entry_id,
    }


class TestSelectErrorExercisesForPractice:

    def test_no_injection_into_empty_normal_session(self):
        # Even with due cards, a session with no normal items gets none — error
        # cards interleave INTO real practice, they don't stand in for it.
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': [_due_card(1)]})
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=None, normal_item_count=0
        )
        assert out == []

    def test_max_cards_zero_disables_injection(self):
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': [_due_card(1), _due_card(2)]})
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=None, normal_item_count=20, max_cards=0
        )
        assert out == []

    def test_absolute_max_caps_the_count(self):
        due = [_due_card(i, subtype=f's{i % 3}') for i in range(1, 11)]
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': due})
        # normal_item_count large so the fraction cap is generous; MAX=2 binds.
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=None, normal_item_count=50, max_cards=2, fraction=0.5
        )
        assert len(out) == 2

    def test_fraction_cap_binds_when_smaller_than_max(self):
        due = [_due_card(i, subtype=f's{i % 2}') for i in range(1, 11)]
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': due})
        # ceil(4 * 0.25) = 1 < max_cards=5, so the fraction cap wins.
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=None, normal_item_count=4, max_cards=5, fraction=0.25
        )
        assert len(out) == 1

    def test_items_are_non_sense_linked_and_marked(self):
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': [_due_card(7)]})
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=None, normal_item_count=10, max_cards=3
        )
        assert len(out) == 1
        item = out[0]
        assert item['word_sense_id'] is None          # NOT sense-linked
        assert item['is_error_exercise'] is True
        assert item['type'] == 'error_card'
        assert item['exercise_type'] == cards.ERROR_EXERCISE_TYPE
        assert item['card_id'] == 7
        assert item['id'] == 'dt-error-7'
        assert 'prompt_payload' in item

    def test_interleaves_by_subtype_not_block_grouped(self):
        # 3 of subtype A then 3 of subtype B — must not come back block-grouped.
        due = (
            [_due_card(i, subtype='A') for i in range(1, 4)]
            + [_due_card(i, subtype='B') for i in range(4, 7)]
        )
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': due})
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=None, normal_item_count=50, max_cards=6, fraction=1.0
        )
        subtypes = [it['subtype'] for it in out]
        assert len(out) == 6
        # No three-in-a-row of the same subtype (round-robin guarantee).
        assert not any(
            subtypes[i] == subtypes[i + 1] == subtypes[i + 2]
            for i in range(len(subtypes) - 2)
        )

    def test_language_scope_no_matching_entries_yields_nothing(self):
        # A due card exists, but no profile entry in the requested L2 → the
        # language scope filters it out (a JA session gets no ZH card).
        db = _FakeDB({'dt_error_profile_entry': [], 'dt_card': [_due_card(1)]})
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=3, normal_item_count=10
        )
        assert out == []

    def test_language_scope_matching_entries_yields_cards(self):
        db = _FakeDB({
            'dt_error_profile_entry': [{'id': 100, 'l2_language_id': 3}],
            'dt_card': [_due_card(1, profile_entry_id=100)],
        })
        out = cards.select_error_exercises_for_practice(
            db, 'u1', language_id=3, normal_item_count=10, max_cards=3
        )
        assert len(out) == 1
        assert out[0]['card_id'] == 1
