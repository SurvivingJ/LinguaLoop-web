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

import logging

from services.exercise_generation.schemas import (
    JUDGE_RATING_KEY, JUDGE_REASON_KEY, read_index,
)
from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.test_generation.schemas import likert_to_verdict

from .base import (
    JudgeOutcome, accept_item, guard_fail_open, log_judge_verdict, safe_accept,
)

logger = logging.getLogger(__name__)

_PIPELINE = 'vocab_ladder'

_RELATION_TASK = 'judge_ladder_relation'
_RELATION_PT = 'ladder_relation_judge'

_FAMILY_TASK = 'judge_ladder_word_family'
_FAMILY_PT = 'ladder_word_family_judge'

# (prompt template name, language_id) -> cfg
_cfg_cache: dict[tuple[str, int], dict] = {}

# Rating used when the judge is unreachable, or an entry is missing. Keeps the
# candidate — a parse glitch must never manufacture a rejection (v3 contract).
_KEEP_RATING = 5.0


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
        return [], _empty_meta('unknown', 0)

    judged = _judge(
        db,
        pt_name=_RELATION_PT,
        task_name=_RELATION_TASK,
        language_id=language_id,
        candidates=foils,
        variables={
            'target': target,
            'definition': definition or '(no definition supplied)',
            'relation': relation,
            'correct_answer': correct_answer or '(none)',
        },
    )

    verdicts = judged['verdicts']
    kept = [f for f in foils if verdicts.get(f) != 'reject']
    rejected = [f for f in foils if verdicts.get(f) == 'reject']
    meta = {
        'rejected': len(rejected),
        'kept': len(kept),
        'rejected_items': rejected,
        'relation': relation,
        'model': judged['model'],
        'version': judged['version'],
    }
    return kept, meta


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
        return [], _empty_meta('unknown', 0)

    attested: list[str] = []
    to_judge: list[str] = []
    for candidate in candidates:
        known = dictionary_check(candidate) if dictionary_check else None
        if known is True:
            attested.append(candidate)
        else:
            to_judge.append(candidate)

    judged = _judge(
        db,
        pt_name=_FAMILY_PT,
        task_name=_FAMILY_TASK,
        language_id=language_id,
        candidates=to_judge,
        variables={
            'stem': stem,
            'correct_answer': correct_answer or '(none)',
        },
    ) if to_judge else {
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

    judged = _judge(
        db,
        pt_name=_FAMILY_PT,
        task_name=_FAMILY_TASK,
        language_id=language_id,
        candidates=[candidate],
        variables={'stem': stem, 'correct_answer': correct_answer or '(none)'},
    )
    if not judged['ok']:
        return safe_accept('word_family judge unavailable — safe-accept')

    outcome = JudgeOutcome(
        verdict=judged['verdicts'].get(candidate, 'flag'),
        confidence=judged['ratings'].get(candidate, _KEEP_RATING),
        reason=judged['reasons'].get(candidate, ''),
    )
    log_judge_verdict(
        task_name=_FAMILY_TASK, model=judged['model'],
        verdict=outcome.verdict, confidence=outcome.confidence,
        pipeline=_PIPELINE,
    )
    return outcome


# ---------------------------------------------------------------------------
# Shared internals
# ---------------------------------------------------------------------------

def _judge(
    db, *, pt_name: str, task_name: str, language_id: int,
    candidates: list[str], variables: dict,
) -> dict:
    """Run a numbered-candidate Likert prompt. Never raises outside batch mode."""
    try:
        cfg = _load_cfg(db, pt_name, language_id)
    except Exception as exc:
        logger.warning(
            '%s: template load failed for lang=%d, fail-open: %s',
            pt_name, language_id, exc,
        )
        return _failopen(pt_name, candidates, 'unknown', 0)

    numbered = '\n'.join(f'{i + 1}. {c}' for i, c in enumerate(candidates))
    prompt = cfg['template'].format(candidates_numbered=numbered, **variables)
    model, version = cfg['model'], cfg['version']

    try:
        result = call_llm(
            prompt,
            model=model,
            temperature=0.0,
            # Provider-enforced JSON: a judge that answers in prose fails open
            # and keeps every candidate, which is the expensive failure here.
            response_format='json_object',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=task_name,
            template_version=version,
        )
    except Exception as exc:
        logger.warning('%s: LLM call failed, fail-open: %s', pt_name, exc)
        return _failopen(pt_name, candidates, model, version)

    if not isinstance(result, dict):
        logger.warning(
            '%s: non-dict response (%s), fail-open', pt_name, type(result).__name__,
        )
        return _failopen(pt_name, candidates, model, version)

    verdicts: dict[str, str] = {}
    ratings: dict[str, float] = {}
    reasons: dict[str, str] = {}
    for idx, candidate in enumerate(candidates):
        # Top level stays keyed by 1-based candidate number; inside an entry
        # the numeric contract applies — 0=rating, 1=reason.
        entry = read_index(result, idx + 1)
        if not isinstance(entry, dict):
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        try:
            rating = float(read_index(entry, JUDGE_RATING_KEY))
        except (TypeError, ValueError):
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        verdicts[candidate] = likert_to_verdict(rating)
        ratings[candidate] = rating
        reasons[candidate] = str(read_index(entry, JUDGE_REASON_KEY) or '')[:200]

    return {
        'verdicts': verdicts, 'ratings': ratings, 'reasons': reasons,
        'model': model, 'version': version, 'ok': True,
    }


def _load_cfg(db, pt_name: str, language_id: int) -> dict:
    key = (pt_name, language_id)
    if key not in _cfg_cache:
        _cfg_cache[key] = get_template_config(db, pt_name, language_id)
    return _cfg_cache[key]


def _failopen(pt_name: str, candidates: list[str], model: str, version: int) -> dict:
    # In a generation batch this raises instead of returning — an unreachable
    # judge must abort the batch, not silently keep every candidate (TASK-510).
    guard_fail_open(pt_name, f'model={model!r} version={version}')
    return {
        'verdicts': {c: 'accept' for c in candidates},
        'ratings': {c: _KEEP_RATING for c in candidates},
        'reasons': {c: '' for c in candidates},
        'model': model, 'version': version, 'ok': False,
    }


def _empty_meta(model: str, version: int) -> dict:
    return {
        'rejected': 0, 'kept': 0, 'rejected_items': [],
        'model': model, 'version': version,
    }
