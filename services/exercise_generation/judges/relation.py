"""Relation judges: synonym/antonym foils and word-family derivations (TASK-522).

Two judges, one module, because they answer the same shape of question about
two different relations — "is this candidate genuinely NOT in the stated
relation to the target?" — and share the numbering / Likert / fail-open
plumbing that every ladder judge uses.

synonym_antonym_match
---------------------
The failure that matters is **polysemy**. A foil is asked to be "not a synonym
of the target", and the model checks that against the *lemma*, not against the
sense being taught. For *bank* (financial institution) it happily offers
*shore* as a foil — correct for the lemma, and a second right answer for
anybody who reads "bank" as riverbank. So the prompt is anchored on the sense
definition, and the judge is asked whether the candidate stands in the stated
relation **to that definition**.

The rating measures how clearly the candidate is a genuine NON-instance of the
relation, mirroring the collocation judge's polarity:

    5 = clearly not a synonym/antonym of this sense → ideal foil
    1 = a full synonym/antonym of this sense → an also-correct answer

Verdicts come from ``schemas.likert_to_verdict`` (5/4 accept, 3 flag, 2/1
reject), per the project's v3 Likert convention. ``judges/particle`` calls the
same function on the same raw rating with no per-judge threshold, so the
polarity is shared by construction rather than by coincidence — a regression
test pins that, because a silent divergence would invert one judge's decisions
without failing anything.

Each entry in the response is numerically keyed (0=rating, 1=reason) per
TASK-537; the top level stays keyed by 1-based candidate number, which is the
numbering the prompt itself handed the model.

word_family
-----------
Here the distractors are *invented* derivations — "decisionment" — and the
failure is the model accidentally inventing a real word, or offering a real
word of the wrong family. The judge is asked whether each candidate is a
non-word: 5 = confidently not an English word, 1 = a real, current word.
A dictionary probe runs alongside it and can veto without a model call.

Fail-open on both, and fail-closed inside ``batch_mode()`` — the standard
contract from ``judges/base``.
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner
# Re-exported: tests pin that this judge and judges/particle score with the
# same mapper (the runner applies it to both).
from services.test_generation.schemas import likert_to_verdict  # noqa: F401

from .base import (
    JudgeOutcome, JudgeSpec, accept_item, candidate_outcome, empty_meta,
    llm_call_kwargs, log_verdict, numbered, run_candidate_judge, safe_accept,
    split_rejected,
    log_judge_verdict,  # noqa: F401 — resolved by the runner
)

_RELATION_TASK = 'judge_ladder_relation'
_RELATION_PT = 'ladder_relation_judge'

_FAMILY_TASK = 'judge_ladder_word_family'
_FAMILY_PT = 'ladder_word_family_judge'

# (prompt template name, language_id) -> cfg
_cfg_cache: dict[tuple[str, int], dict] = {}


def _ask(spec, prompt, cfg, language_id):
    return call_llm(
        prompt,
        # RE-DERIVED 2026-10-03 (ADR-028 cost work): TASK-812's 13000 was
        # sized against a relation p99 inflated by reasoning tokens
        # (qwen reasoning is now OFF). With reasoning off,
        # data/eval/runs/phase2_bundle_*/ + phase2_fix_*/ +
        # phase2_smoke_ja_v3/ + phase2_smoke_zh_r/ *.json llm_calls for
        # the two task_names sharing this call site pooled together:
        # n=100, p99=120, max=120 (judge_ladder_word_family/en, n=19,
        # governs; judge_ladder_relation tops out at 111 across en/ja/zh,
        # n=28/24/29). cap = max(ceil(p99*2), ceil(max*1.25)) = 240,
        # rounded up to 250. At gemini-3.5-flash-lite's $2.50/M
        # completion price (en's model, the governing case) this cuts
        # the worst-case reservation from ~$0.033/request to
        # ~$0.001/request.
        max_tokens=250,
        **llm_call_kwargs(spec, cfg, language_id),
    )


def _spec(pt_name: str, task_name: str) -> JudgeSpec:
    return JudgeSpec(
        name=pt_name, module=__name__, task_name=task_name, pt_name=pt_name,
        ask=_ask,
        # Provider-enforced JSON: a judge that answers in prose fails open
        # and keeps every candidate, which is the expensive failure here.
        response_format='json_object',
        numeric_entries=True, keyed_cache=True,
    )


_RELATION_SPEC = _spec(_RELATION_PT, _RELATION_TASK)
_FAMILY_SPEC = _spec(_FAMILY_PT, _FAMILY_TASK)


# ---------------------------------------------------------------------------
# synonym / antonym
# ---------------------------------------------------------------------------

def filter_relation_foils(
    db,
    target: str,
    definition: str,
    relation: str,
    correct_answer: str,
    foils: list[str],
    language_id: int,
) -> tuple[list[str], dict]:
    """Drop foils that are themselves in ``relation`` to the *sense*.

    Returns ``(kept, judge_meta)``. ``judge_meta`` is the generalized sidecar
    lifted into ``exercises.tags.relation_judge``.

    A foil is dropped only on a ``reject`` verdict (rating 1-2, i.e. it really
    is a synonym/antonym of this sense). Uncertainty keeps it: the band check
    in ``sense_neighbours`` is the other half of this decision, and two
    independent "maybe"s should not compound into a drop.
    """
    if not foils:
        return [], empty_meta()

    judged = _judge(_RELATION_SPEC, db, language_id, foils, {
        'target': target,
        'definition': definition or '(no definition supplied)',
        'relation': relation,
        'correct_answer': correct_answer or '(none)',
    })
    return split_rejected(foils, judged, relation=relation)


# ---------------------------------------------------------------------------
# word family
# ---------------------------------------------------------------------------

def filter_invented_derivations(
    db,
    stem: str,
    correct_answer: str,
    candidates: list[str],
    language_id: int,
    dictionary_check=None,
) -> tuple[list[str], dict]:
    """Keep only distractors that are genuinely NOT words.

    ``dictionary_check`` is an optional ``callable(word) -> bool | None``
    returning True when the word is attested. A True result drops the
    candidate without spending a model call; None means "no opinion" and
    defers to the judge. Separating the two lets a cheap, certain signal
    override an expensive, fuzzy one.
    """
    if not candidates:
        return [], empty_meta()

    attested: list[str] = []
    to_judge: list[str] = []
    for candidate in candidates:
        known = dictionary_check(candidate) if dictionary_check else None
        if known is True:
            attested.append(candidate)
        else:
            to_judge.append(candidate)

    judged = _judge(_FAMILY_SPEC, db, language_id, to_judge, {
        'stem': stem,
        'correct_answer': correct_answer or '(none)',
    }) if to_judge else {
        'verdicts': {}, 'ratings': {}, 'reasons': {},
        'model': 'unknown', 'version': 0, 'ok': True,
    }

    verdicts = judged['verdicts']
    rejected = attested + [c for c in to_judge if verdicts.get(c) == 'reject']
    kept = [c for c in candidates if c not in rejected]
    meta = {
        'rejected': len(rejected),
        'kept': len(kept),
        'rejected_items': rejected,
        'dictionary_rejected': attested,
        'model': judged['model'],
        'version': judged['version'],
    }
    return kept, meta


def judge_derivation(
    db, stem: str, correct_answer: str, candidate: str, language_id: int,
) -> JudgeOutcome:
    """Single-candidate verdict, for the planted-defect test and admin tools."""
    if not candidate:
        return accept_item('no candidate to judge')

    judged = _judge(_FAMILY_SPEC, db, language_id, [candidate], {
        'stem': stem, 'correct_answer': correct_answer or '(none)',
    })
    if not judged['ok']:
        return safe_accept('word_family judge unavailable — safe-accept')

    outcome = candidate_outcome(judged, candidate)
    log_verdict(_FAMILY_SPEC, judged['model'], outcome.verdict, outcome.confidence)
    return outcome


def _judge(
    spec: JudgeSpec, db, language_id: int, candidates: list[str], variables: dict,
) -> dict:
    """Run a numbered-candidate Likert prompt. Never raises outside batch mode."""
    return run_candidate_judge(
        spec, db, language_id, candidates,
        lambda template: template.format(
            candidates_numbered=numbered(candidates), **variables,
        ),
    )
