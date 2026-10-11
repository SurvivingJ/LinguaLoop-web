"""TASK-845 — deterministic resolver for the word_choice `explanation_variant`.

Taxonomy v6 (ADR-031 Decision A, renamed 2026-10-04) gives every `word_choice`
error one of ``prompts.VARIANT_ENUM``:

    wrong_sense    — the learner used the reference's OWN lemma, in a different
                     dictionary sense (narrow: same lemma only);
    false_synonym  — a different word that the learner's L1 glosses the same way
                     as the correct word, but with a different meaning/usage
                     (知道 vs 认识, both "know");
    wrong_word     — everything else.

Precedence: same lemma → wrong_sense; shared L1 gloss → false_synonym; else the
model's call (the residual). The first two are decided here from the sense
dictionary, never fuzzily:

  * Lemma resolution — exact ``dim_vocabulary.lemma`` match in the L2 first;
    else ``services.dictation.tokenizer`` tokens, accepted only when exactly one
    distinct content token resolves. Unresolvable on either side → both
    deterministic steps are skipped.
  * Same lemma — the two sides' vocab_id sets intersect.
  * Gloss match — ``dim_word_senses`` rows with ``definition_language_id`` = the
    learner's L1 (glosses share (vocab_id, sense_rank, level) with the native
    rows, so the language filter is what selects them), split into terms and
    normalised; a non-empty EXACT intersection → false_synonym. When either word
    has no gloss in that L1 (always so for an en L2 today — en words carry no
    zh/ja glosses) the lookup is unavailable and the model's call stands.

Residual (``_residual``):
  * model ``wrong_word`` → kept (basis ``model``);
  * model ``wrong_sense`` → kept unless both lemmas resolved to DIFFERENT words —
    then it is provably not the same lemma → ``wrong_word`` (basis ``default``);
  * model ``false_synonym`` → kept (basis ``model``) only when the gloss lookup
    could not run (no glosses, or a lemma unresolvable); refuted by a lookup that
    ran and found no shared term → ``wrong_word`` (basis ``default``);
  * missing → ``wrong_word`` (basis ``default``).

Batched: at most two DB round trips per submission (one dim_vocabulary, one
dim_word_senses). Any DB exception is logged and degrades to basis ``default``;
grading always continues. Read-only.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from services.dictation import tokenizer
from services.dual_translation import prompts

logger = logging.getLogger(__name__)

WORD_CHOICE = "word_choice"
WRONG_WORD, WRONG_SENSE, FALSE_SYNONYM = prompts.VARIANT_ENUM
BASES: tuple[str, ...] = ("same_lemma", "shared_gloss", "model", "default")

# Gloss-term separators. The spec list (; , 、 ， ／ /) plus the full-width
# semicolon "；" — the zh/ja gloss format (cross-language-glosses skill) separates
# equivalents with it ("紧张；不安"), so without it no zh/ja gloss would split.
_GLOSS_SPLIT_RE = re.compile(r"[;；,，、／/]")
# Parentheticals, ASCII and full-width (one nesting level is all glosses use).
_PAREN_RE = re.compile(r"\([^()]*\)|（[^（）]*）")
# The `standard` gloss level may end in a clarifier after an em dash
# ("spirit; mind; feeling — no single English equivalent; covers …"). It is
# prose, not an equivalent; left in, two lossy words would "share" a gloss term
# like "no single english equivalent". Everything from the dash on is dropped.
_CLARIFIER_RE = re.compile(r"\s*(?:——|—|–|--).*$", re.S)
_LEADING_WORDS: tuple[str, ...] = ("to ", "a ", "an ", "the ")
_EDGE_PUNCT = " \t\r\n.。!！?？:：\"'“”‘’「」『』"
# en function words that are not "content tokens" for lemma resolution
# (same list the gloss normaliser strips: "to know" / "the key").
_EN_STOP_TOKENS = frozenset({"a", "an", "the", "to"})


# ---------------------------------------------------------------------------
# Gloss normalisation
# ---------------------------------------------------------------------------

def normalise_gloss_term(term: str) -> str:
    """Lowercase, strip parentheticals and leading "to "/"a "/"an "/"the ",
    collapse whitespace, trim edge punctuation. '' for an empty term."""
    t = _PAREN_RE.sub(" ", term or "").lower()
    t = " ".join(t.split()).strip(_EDGE_PUNCT)
    changed = True
    while changed:
        changed = False
        for prefix in _LEADING_WORDS:
            if t.startswith(prefix):
                t = t[len(prefix):].strip(_EDGE_PUNCT)
                changed = True
    return t


def gloss_terms(definition: str) -> set[str]:
    """The normalised equivalents in one gloss definition (clarifier dropped)."""
    text = _PAREN_RE.sub(" ", definition or "")
    text = _CLARIFIER_RE.sub("", text)
    terms = {normalise_gloss_term(part) for part in _GLOSS_SPLIT_RE.split(text)}
    terms.discard("")
    return terms


# ---------------------------------------------------------------------------
# Lemma candidates / resolution
# ---------------------------------------------------------------------------

def _exact_candidates(form: str) -> list[str]:
    stripped = (form or "").strip()
    out: list[str] = []
    for c in (stripped, stripped.lower()):
        if c and c not in out:
            out.append(c)
    return out


def _token_candidates(form: str, l2_code: str) -> list[str]:
    tokens = tokenizer.tokenize(tokenizer.normalize(form or ""), l2_code)
    if (l2_code or "").lower() == "en":
        tokens = [t for t in tokens if t not in _EN_STOP_TOKENS]
    out: list[str] = []
    for t in tokens:
        if t not in out:
            out.append(t)
    return out


def _resolve_ids(form: str, l2_code: str, lemma_ids: dict[str, set[int]]) -> Optional[frozenset]:
    """vocab_ids for `form`: the first exact-lemma hit, else the single resolving
    content token; None when unresolvable (no hit, or >1 token resolves)."""
    for c in _exact_candidates(form):
        if c in lemma_ids:
            return frozenset(lemma_ids[c])
    resolved = [t for t in _token_candidates(form, l2_code) if t in lemma_ids]
    if len(resolved) == 1:
        return frozenset(lemma_ids[resolved[0]])
    return None


# ---------------------------------------------------------------------------
# DB reads (≤2 round trips per batch)
# ---------------------------------------------------------------------------

def _fetch_lemma_ids(db, l2_language_id: int, candidates: list[str]) -> dict[str, set[int]]:
    resp = (
        db.table("dim_vocabulary")
        .select("id, lemma")
        .eq("language_id", l2_language_id)
        .in_("lemma", candidates)
        .execute()
    )
    out: dict[str, set[int]] = {}
    for row in resp.data or []:
        lemma, vid = row.get("lemma"), row.get("id")
        if lemma is not None and vid is not None:
            out.setdefault(lemma, set()).add(vid)
    return out


def _fetch_gloss_terms(db, l1_language_id: int, vocab_ids: list[int]) -> dict[int, set[str]]:
    resp = (
        db.table("dim_word_senses")
        .select("vocab_id, definition")
        .eq("definition_language_id", l1_language_id)
        .in_("vocab_id", vocab_ids)
        .execute()
    )
    out: dict[int, set[str]] = {}
    for row in resp.data or []:
        vid = row.get("vocab_id")
        if vid is None:
            continue
        out.setdefault(vid, set()).update(gloss_terms(row.get("definition") or ""))
    return out


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def _residual(model_variant: Optional[str], *, lemmas_differ: bool, lookup_ran: bool) -> tuple[str, str]:
    """The model's call, where the dictionary did not decide (module docstring)."""
    if model_variant == WRONG_WORD:
        return WRONG_WORD, "model"
    if model_variant == WRONG_SENSE:
        return (WRONG_WORD, "default") if lemmas_differ else (WRONG_SENSE, "model")
    if model_variant == FALSE_SYNONYM:
        return (WRONG_WORD, "default") if lookup_ran else (FALSE_SYNONYM, "model")
    return WRONG_WORD, "default"


def _empty_counts() -> dict[str, int]:
    return {b: 0 for b in BASES}


def resolve_variants(
    db, errors: list[dict], *, l2_code: str, l2_language_id: Optional[int],
    l1_language_id: Optional[int],
) -> dict[str, int]:
    """Set `explanation_variant` on every error in `errors`, in place, and return
    the per-basis counts over the word_choice errors ({basis: n}, all four keys).

    Non-word_choice errors get None. A word_choice error's incoming
    `explanation_variant` is taken as the model's call (an already-decoded slug)."""
    counts = _empty_counts()
    targets: list[dict] = []
    for err in errors:
        if err.get("subtype") == WORD_CHOICE:
            targets.append(err)
        else:
            err["explanation_variant"] = None
    if not targets:
        return counts

    def _model(err) -> Optional[str]:
        v = err.get("explanation_variant")
        return v if v in prompts.VARIANT_ENUM else None

    def _set(err, variant: str, basis: str) -> None:
        err["explanation_variant"] = variant
        counts[basis] += 1

    def _all_default(reason: str, exc: Exception) -> dict[str, int]:
        logger.warning(
            "dual_translation.word_choice_variant: %s failed (%s) — %d word_choice "
            "error(s) fall back to basis 'default'", reason, exc, len(targets),
        )
        for e in targets:
            _set(e, WRONG_WORD, "default")
        return counts

    # ── Round trip 1: resolve every form's lemma in one query ──────────────
    candidates: list[str] = []
    for err in targets:
        for form in (err.get("learner_form"), err.get("corrected_form")):
            for c in _exact_candidates(form) + _token_candidates(form, l2_code):
                if c not in candidates:
                    candidates.append(c)

    lemma_ids: dict[str, set[int]] = {}
    if candidates and l2_language_id is not None:
        try:
            lemma_ids = _fetch_lemma_ids(db, l2_language_id, candidates)
        except Exception as exc:  # noqa: BLE001 — never fail a grade over this
            return _all_default("dim_vocabulary lookup", exc)

    pending: list[tuple[dict, frozenset, frozenset]] = []
    for err in targets:
        learner_ids = _resolve_ids(err.get("learner_form"), l2_code, lemma_ids)
        corrected_ids = _resolve_ids(err.get("corrected_form"), l2_code, lemma_ids)
        if learner_ids and corrected_ids:
            if learner_ids & corrected_ids:
                _set(err, WRONG_SENSE, "same_lemma")
            else:
                pending.append((err, learner_ids, corrected_ids))
        else:
            _set(err, *_residual(_model(err), lemmas_differ=False, lookup_ran=False))

    if not pending:
        return counts

    # ── Round trip 2: L1 glosses for every still-undecided pair ────────────
    terms_by_id: dict[int, set[str]] = {}
    if l1_language_id is not None:
        ids = sorted({vid for _, a, b in pending for vid in (*a, *b)})
        try:
            terms_by_id = _fetch_gloss_terms(db, l1_language_id, ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "dual_translation.word_choice_variant: dim_word_senses lookup failed (%s) — "
                "%d word_choice error(s) fall back to basis 'default'", exc, len(pending),
            )
            for err, _, _ in pending:
                _set(err, WRONG_WORD, "default")
            return counts

    for err, learner_ids, corrected_ids in pending:
        learner_terms = set().union(*(terms_by_id.get(v, set()) for v in learner_ids))
        corrected_terms = set().union(*(terms_by_id.get(v, set()) for v in corrected_ids))
        lookup_ran = bool(learner_terms) and bool(corrected_terms)
        if lookup_ran and learner_terms & corrected_terms:
            _set(err, FALSE_SYNONYM, "shared_gloss")
        else:
            _set(err, *_residual(_model(err), lemmas_differ=True, lookup_ran=lookup_ran))
    return counts


def resolve_variant(
    db, *, learner_form: str, corrected_form: str, l2_code: str,
    l1_language_id: Optional[int], model_variant: Optional[str],
    l2_language_id: Optional[int] = None,
) -> tuple[str, str]:
    """Single-error form of :func:`resolve_variants` → ``(variant, basis)``.

    `l2_language_id` is resolved from `l2_code` via DimensionService when not
    given (a failed lookup leaves the lemma steps skipped, never raises)."""
    if l2_language_id is None:
        try:
            from services.dimension_service import DimensionService
            l2_language_id = DimensionService.get_language_id(l2_code, db)
        except Exception as exc:  # noqa: BLE001
            logger.warning("dual_translation.word_choice_variant: no language id for %r (%s)", l2_code, exc)
            l2_language_id = None
    err = {
        "subtype": WORD_CHOICE,
        "learner_form": learner_form,
        "corrected_form": corrected_form,
        "explanation_variant": model_variant,
    }
    counts = resolve_variants(
        db, [err], l2_code=l2_code, l2_language_id=l2_language_id, l1_language_id=l1_language_id,
    )
    basis = next(b for b, n in counts.items() if n)
    return err["explanation_variant"], basis
