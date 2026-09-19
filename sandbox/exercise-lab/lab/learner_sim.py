"""
A synthetic learner population, for evaluating SERVING/selection algorithms.

WHY THIS EXISTS
----------------
docs/recon-serving.md §6 finding 10: as of 2026-09-17, of 14 real users,
exactly ONE has ever taken a test - every quality metric the live selection
harness (`scripts/measure_selection_quality.py`) can report describes that
single learner's history, in zh/ja only. No serving-algorithm change can be
validated against real behavioral data at any meaningful sample size. This
module exists to make "does this selector even work, in a controlled world
where we know the ground truth" answerable at all, by simulating a
population with a documented, swappable response model instead.

# FIDELITY GAP (the central one - read before trusting any curve this
# produces): every number `simulate()` returns is a property of the
# assumptions below, NOT of real learners. This is useful for testing
# whether a serving algorithm's *mechanism* behaves sensibly (does spacing
# help at all, does an ELO+vocabulary blend converge faster than ELO alone,
# does a selector get stuck) - it is NOT evidence about real magnitudes,
# real forgetting rates, or real guessing psychology. Treat every output as
# "does the mechanism work", never as "real users will learn N% faster."

Response model (this is the crux, and it deliberately reproduces the exact
mechanism docs/recon-serving.md §4 blames for capping ELO's reachable
spread at ~191 points):

    P(correct | ability, item_difficulty) =
        floor + (1 - floor) * sigmoid((ability - item_difficulty) / scale)

    floor = 1 / n_choices   <- the MC guessing floor.

Even a learner who knows NOTHING still clears `floor` of the time on a
multiple-choice item, so no amount of ELO K-factor tuning can push the
*observed* pass rate on a badly-mismatched item below that floor - the
logistic curve is squashed into [floor, 1.0] instead of [0.0, 1.0]. This is
a logistic-IRT-with-a-floor model (informally a 3-parameter item response
model), NOT a port of the literal live ELO/BKT formulas in
`sec_submission_rpcs_auth_gate.sql` - documented here as an assumption a
later agent can swap out (e.g. for a real 3PL IRT model, or per-item rather
than global floors), not as ground truth about production math.

Forgetting is a single global exponential half-life per learner (also a
documented, swappable simplification - real forgetting is per-item,
per-learner, and interacts with review spacing in ways this sandbox does
not attempt to model).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SenseKnowledge:
    """Per-learner, per-sense ground-truth knowledge state. Never exposed to
    a Selector directly - a realistic selector only sees what production
    would actually persist (e.g. an estimated p_known), not this."""

    sense_id: int
    true_p_known: float  # 0..1, ground truth
    last_seen_day: Optional[int] = None
    exposures: int = 0


@dataclass
class SimulatedLearner:
    learner_id: str
    true_ability: dict[str, float] = field(default_factory=dict)  # per skill/test_type, ELO-scale
    sense_knowledge: dict[int, SenseKnowledge] = field(default_factory=dict)
    forgetting_halflife_days: float = 14.0
    # FIDELITY GAP: one global halflife per learner; real forgetting is
    # per-item (easy/frequent words decay slower) and per-learner.
    guess_floor_choices: int = 4
    # Matches the dominant MC exercise shape across the ladder - see
    # docs/recon-generation.md §3a (most ladder levels are "MC" with
    # 3 wrong + 1 right, i.e. 4 choices).

    def p_known_now(self, sense_id: int, today: int) -> float:
        """BKT-flavoured recall probability for one sense at `today`,
        decaying toward a floor rather than to zero (a well-learned item
        degrades but doesn't fully vanish between reviews)."""
        sk = self.sense_knowledge.get(sense_id)
        if sk is None:
            return 0.05  # unseen: near-zero, same order of magnitude as
            # production's BKT default prior p_known=0.10 (see
            # docs/recon-data-surface.md §1, user_vocabulary_knowledge).
        if sk.last_seen_day is None:
            return sk.true_p_known
        days = max(0, today - sk.last_seen_day)
        decay = 0.5 ** (days / self.forgetting_halflife_days)
        floor = 0.15 * sk.true_p_known
        return floor + (sk.true_p_known - floor) * decay

    def response_prob(self, item_difficulty: float, skill: str, *, scale: float = 200.0) -> float:
        ability = self.true_ability.get(skill, 1200.0)
        floor = 1.0 / self.guess_floor_choices
        logit = (ability - item_difficulty) / scale
        sigmoid = 1.0 / (1.0 + math.exp(-logit))
        return floor + (1.0 - floor) * sigmoid

    def answer(self, item_difficulty: float, skill: str, rng: random.Random) -> bool:
        return rng.random() < self.response_prob(item_difficulty, skill)


def make_population(
    n: int,
    *,
    skills: list[str],
    seed: int = 0,
    ability_mean: float = 1200.0,
    ability_sd: float = 250.0,
) -> list[SimulatedLearner]:
    """`ability_mean`/`ability_sd` are chosen to sit near production's
    ELO cold-start default (1200) and clamp range (400-3000, see
    docs/recon-serving.md §4) - not derived from any real ability
    distribution, since (per the module docstring) none exists at any
    usable sample size."""
    rng = random.Random(seed)
    population: list[SimulatedLearner] = []
    for i in range(n):
        base = rng.gauss(ability_mean, ability_sd)
        # Per-skill ability correlated with the learner's overall level but
        # with independent noise, so e.g. reading and pitch_accent ability
        # aren't perfectly identical for one learner - mirroring (loosely)
        # the real "true ability spans 448 points across 8 test types for
        # one learner" finding in docs/recon-serving.md §4, without trying
        # to reproduce that exact number.
        abilities = {sk: base + rng.gauss(0, 80) for sk in skills}
        population.append(SimulatedLearner(learner_id=f"sim-{i:04d}", true_ability=abilities))
    return population


class Selector:
    """Interface a later agent implements to prototype a serving algorithm.
    Deliberately minimal - a real prototype will want more inputs, but
    everything it looks at must be derivable from what production actually
    persists (visible ELO, estimated p_known, etc), never from
    SimulatedLearner's private `true_*` fields. That boundary is the whole
    point: a selector that peeks at ground truth would trivially "win" and
    tell you nothing about a real algorithm."""

    name: str = "selector"

    def choose_difficulty(self, learner_visible_elo: float, skill: str, today: int) -> float:
        raise NotImplementedError


class NearestEloSelector(Selector):
    """Baseline selector: mirrors live `get_recommended_tests` at
    vocab_weight=0 (see docs/recon-serving.md §2) - serve the item whose
    difficulty equals the learner's current visible ELO."""

    name = "nearest_elo"

    def choose_difficulty(self, learner_visible_elo: float, skill: str, today: int) -> float:
        return learner_visible_elo


@dataclass
class DayResult:
    day: int
    learner_id: str
    skill: str
    item_difficulty: float
    correct: bool
    visible_elo_before: float
    visible_elo_after: float


def simulate(
    selector: Selector,
    learner: SimulatedLearner,
    n_days: int,
    *,
    skills: Optional[list[str]] = None,
    items_per_day: int = 1,
    k_factor: float = 32.0,
    seed: int = 0,
) -> list[DayResult]:
    """
    Runs one learner through n_days of daily items per skill. The Selector
    decides what difficulty gets served; the learner's response model
    (with its MC guessing floor) decides pass/fail; the ELO update here
    mirrors production's first-attempt rule (`expected = logistic(diff/400)`,
    see docs/recon-serving.md §4) so the resulting "visible ELO" trajectory
    is comparable to what production would actually show a selector.

    Returns the full per-day trajectory so a caller can build a learning
    curve (see `learning_curve()` below) or compute convergence/())stability
    metrics across selectors.
    """
    rng = random.Random(seed)
    skills = skills or list(learner.true_ability.keys())
    visible_elo = {sk: 1200.0 for sk in skills}  # cold start, matches production default
    history: list[DayResult] = []

    for day in range(n_days):
        for sk in skills:
            for _ in range(items_per_day):
                difficulty = selector.choose_difficulty(visible_elo[sk], sk, day)
                correct = learner.answer(difficulty, sk, rng)
                expected = 1.0 / (1.0 + 10 ** ((difficulty - visible_elo[sk]) / 400))
                before = visible_elo[sk]
                visible_elo[sk] = before + k_factor * ((1.0 if correct else 0.0) - expected)
                visible_elo[sk] = min(3000.0, max(400.0, visible_elo[sk]))
                history.append(
                    DayResult(
                        day=day,
                        learner_id=learner.learner_id,
                        skill=sk,
                        item_difficulty=difficulty,
                        correct=correct,
                        visible_elo_before=before,
                        visible_elo_after=visible_elo[sk],
                    )
                )
    return history


def learning_curve(history: list[DayResult], skill: str) -> list[tuple[int, float]]:
    """(day, visible_elo_after) pairs for one skill - plot this, or assert
    it trends toward the learner's true ability, as a sanity check that the
    simulator/selector loop is wired correctly."""
    return [(r.day, r.visible_elo_after) for r in history if r.skill == skill]
