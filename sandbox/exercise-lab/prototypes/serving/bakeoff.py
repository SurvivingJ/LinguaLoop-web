"""
EXPERIMENT 2 (selector bake-off) + EXPERIMENT 3 (the simulator trap), one
engine so the same five selectors race under four genuinely different
response/learning models. See docs/results-serving.md for the writeup;
this file is the instrument, not the report.

Common interface (Experiment 2's requirement): every Selector.choose(...)
sees only candidate metadata a real selector could see in production
(seeded/content difficulty, covered senses, and the learner's VISIBLE elo +
this sandbox's per-sense p_known estimate, standing in for
`user_vocabulary_knowledge.p_known` - never the ground-truth "true_*"
fields a real selector could not observe). Selector E (random-in-tier) is
the control; per the task instructions, if it is not clearly beaten by the
others, that is the headline, not a footnote.

Four response/learning models (Experiment 3):
  bkt      - discrete BKT mastery, FAMILY_BKT_RATES from
             services/vocabulary_ladder/config.py (learn=0.15, slip=0.12
             for the 'standard' family - the only rates this sandbox reuses
             verbatim from production code).
  fsrs     - continuous retrievability R=exp(-days/stability), stability
             grows on review; no discrete "mastery" state at all.
  pure_irt - NO learning-rate heterogeneity: per-sense knowledge is fixed
             forever. This is the adversarial-for-learning model: if a
             selector's apparent "win" on retention survives here, that
             win was noise, because nothing in this model can be learned.
  misspec  - deliberately wrong assumptions: BKT learn/slip swapped
             (mastery decays faster than it builds) AND forgetting
             half-life is ANTI-correlated with ability (stronger learners
             forget faster) - the opposite of every other model's
             assumption and of what any selector here is built to expect.

Per the module's own warning (and docs/redteam-serving.md SS8): a selector
that only wins under the model whose assumptions it was designed around is
not evidence about real learners. Only conclusions that hold across all
four models are reported as findings in results-serving.md.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass, field

FAMILY_BKT = {"learn": 0.15, "slip": 0.12}  # services/vocabulary_ladder/config.py:186-190, 'standard'
MISSPEC_BKT = {"learn": 0.12, "slip": 0.15}  # deliberately swapped

N_SENSES = 60
N_ITEMS = 45
N_LEARNERS = 24
N_DAYS = 30
HOLDOUT_START_DAY = 23  # final 7 days: holdout senses never served
N_HOLDOUT = 10
MASTERY_THRESHOLD = 0.8
TEST_TIME_SEC = 60.0
NEVER_RE_SERVE = True  # mirrors get_recommended_tests' hard filter (see exp4)


# ---------------------------------------------------------------------------
# World: senses + item catalog (shared across all learners/selectors/models
# in one run, built once per seed so every arm sees an identical world)
# ---------------------------------------------------------------------------

@dataclass
class Sense:
    id: int
    zipf: float          # 3.0 (rare) .. 6.0 (common) - higher = more common
    difficulty_true: float  # ELO-equivalent, derived from zipf


@dataclass
class Item:
    id: int
    senses: list[int]
    item_type: int             # 0/1/2 - the "prose-complexity family" bucket
    difficulty_true: float     # correct, content-derived (mean of covered senses)
    difficulty_seeded: float   # noisy, TYPE-blind (defect #2 in recon-serving.md SS6)


def build_world(seed: int) -> tuple[list[Sense], list[Item]]:
    rng = random.Random(seed)
    senses = []
    for i in range(N_SENSES):
        zipf = 3.0 + 3.0 * i / (N_SENSES - 1)
        difficulty_true = 1200.0 - (zipf - 4.5) * 150.0  # common (high zipf) -> easier
        senses.append(Sense(i, zipf, difficulty_true))

    items = []
    for i in range(N_ITEMS):
        covered = rng.sample(range(N_SENSES), 3)
        d_true = statistics.mean(senses[s].difficulty_true for s in covered)
        item_type = i % 3
        type_bias = {0: -180.0, 1: 0.0, 2: 180.0}[item_type]  # a shared, wrong offset per type
        d_seeded = 0.3 * d_true + 0.7 * (1200.0 + type_bias + rng.gauss(0, 40))
        items.append(Item(i, covered, item_type, d_true, d_seeded))
    return senses, items


# ---------------------------------------------------------------------------
# Learner
# ---------------------------------------------------------------------------

@dataclass
class SimLearner:
    id: str
    ability: float
    p_known: list[float] = field(default_factory=lambda: [0.05] * N_SENSES)
    last_seen: list[int | None] = field(default_factory=lambda: [None] * N_SENSES)
    stability: list[float] = field(default_factory=lambda: [1.0] * N_SENSES)  # fsrs only
    halflife: float = 14.0
    visible_elo: float = 1200.0
    served_item_ids: set[int] = field(default_factory=set)


def make_learners(n: int, seed: int) -> list[SimLearner]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        ability = rng.gauss(1200.0, 250.0)
        out.append(SimLearner(f"L{i:03d}", ability))
    return out


def p_known_now(learner: SimLearner, sense_id: int, today: int, model: str) -> float:
    p_true = learner.p_known[sense_id]
    last = learner.last_seen[sense_id]
    if last is None:
        return p_true
    days = max(0, today - last)
    if model == "fsrs":
        return math.exp(-days / max(learner.stability[sense_id], 0.5))
    halflife = learner.halflife
    decay = 0.5 ** (days / halflife)
    floor = 0.15 * p_true
    return floor + (p_true - floor) * decay


# ---------------------------------------------------------------------------
# Selectors - common interface: choose(candidates, learner_view, today) -> Item
# `learner_view` exposes only what production could see: visible_elo and a
# per-sense p_known ESTIMATE (here, ground-truth p_known_now - a real system's
# estimate would be noisier still, so every selector below is racing under a
# strictly more favorable information condition than production actually has).
# ---------------------------------------------------------------------------

class Selector:
    name = "base"

    def choose(self, candidates: list[Item], est_p_known: list[float], visible_elo: float,
               rng: random.Random) -> Item:
        raise NotImplementedError


def _unknown(item: Item, est_p_known: list[float]) -> float:
    return 1.0 - statistics.mean(est_p_known[s] for s in item.senses)


class SelectorA_LiveObjective(Selector):
    """score(t) = |seeded_elo - user_elo|/400 + vocab_weight*|unknown-0.15|/0.10,
    vocab_weight=1 (LIVE since 2026-09-17, docs/recon-serving.md SS0/SS2).
    Lower is better."""
    name = "A_live_elo_vocab"

    def choose(self, candidates, est_p_known, visible_elo, rng):
        def score(it):
            e = abs(it.difficulty_seeded - visible_elo) / 400.0
            v = abs(_unknown(it, est_p_known) - 0.15) / 0.10
            return e + v
        return min(candidates, key=score)


class SelectorB_LivePlusSchedule(Selector):
    """A, plus a term rewarding senses that have DECAYED since being learned
    (true_p_known - p_known_now, i.e. "due for review") - a BKT/FSRS-style
    scheduling addition layered on the live objective, per S1's proposal."""
    name = "B_live_plus_bkt_fsrs"

    def __init__(self, decayed_lookup):
        self._decayed = decayed_lookup  # sense_id -> due amount, refreshed by caller each pick

    def choose(self, candidates, est_p_known, visible_elo, rng):
        def score(it):
            e = abs(it.difficulty_seeded - visible_elo) / 400.0
            v = abs(_unknown(it, est_p_known) - 0.15) / 0.10
            due = statistics.mean(self._decayed(s) for s in it.senses)
            return e + v - 1.0 * due
        return min(candidates, key=score)


class SelectorC_GainPerMinute(Selector):
    """S3's economic framing: expected BKT learning gain per minute,
    reusing FAMILY_BKT_RATES['standard']['learn'] verbatim as the gain
    model, divided by a fixed per-item time cost. Higher is better."""
    name = "C_gain_per_minute"

    def __init__(self, learn_rate: float):
        self.learn_rate = learn_rate

    def choose(self, candidates, est_p_known, visible_elo, rng):
        def value(it):
            gain = sum(self.learn_rate * (1.0 - est_p_known[s]) for s in it.senses)
            return gain / TEST_TIME_SEC
        return max(candidates, key=value)


class SelectorD_ComputedDifficulty(Selector):
    """S4: nearest-ELO ranking using the CONTENT-computed difficulty
    (Zipf-derived, no response data required) instead of the type-blind
    seeded ELO - directly targets recon-serving.md SS6 defect #2 (48/60 ja
    tests share one ELO because seeding used prose complexity, not task
    type). No vocabulary term - isolates the seeding fix alone."""
    name = "D_computed_difficulty"

    def choose(self, candidates, est_p_known, visible_elo, rng):
        return min(candidates, key=lambda it: abs(it.difficulty_true - visible_elo))


class SelectorE_RandomInTier(Selector):
    """Control: uniform random among candidates within +-200 ELO of the
    learner's visible rating (using the SAME seeded difficulty a real
    learner's dashboard would show), else uniform over the whole pool."""
    name = "E_random_in_tier"

    def choose(self, candidates, est_p_known, visible_elo, rng):
        in_tier = [it for it in candidates if abs(it.difficulty_seeded - visible_elo) <= 200.0]
        pool = in_tier or candidates
        return rng.choice(pool)


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

def response_fraction(learner: SimLearner, item: Item, today: int, model: str,
                       rng: random.Random) -> float:
    """Returns a pct-correct in [0,1], simulated as Binomial(10, p)/10 -
    matching production's real ELO update, which operates on a test's pct
    score, not a single binary outcome (sec_submission_rpcs_auth_gate.sql,
    docs/recon-serving.md SS4)."""
    if model == "fsrs":
        know = statistics.mean(p_known_now(learner, s, today, model) for s in item.senses)
        knowledge_bonus = 400.0 * (know - 0.5)
    else:
        know = statistics.mean(p_known_now(learner, s, today, model) for s in item.senses)
        knowledge_bonus = 400.0 * (know - 0.5)
    ability_eff = learner.ability + knowledge_bonus
    c_floor = 0.25
    logit = (ability_eff - item.difficulty_true) / 200.0
    p = c_floor + (1.0 - c_floor) * (1.0 / (1.0 + math.exp(-logit)))
    successes = sum(1 for _ in range(10) if rng.random() < p)
    return successes / 10.0


def update_knowledge(learner: SimLearner, item: Item, pct: float, today: int, model: str,
                      bkt_rates: dict) -> None:
    correct = pct >= 0.5
    for s in item.senses:
        if model == "pure_irt":
            pass  # no learning at all, by design
        elif model == "fsrs":
            if correct:
                learner.stability[s] = learner.stability[s] * (1.0 + 1.2 * pct)
            else:
                learner.stability[s] = max(0.5, learner.stability[s] * 0.6)
            learner.p_known[s] = min(1.0, learner.p_known[s] + 0.1) if correct else learner.p_known[s]
        else:  # bkt, misspec
            if correct:
                learner.p_known[s] += bkt_rates["learn"] * (1.0 - learner.p_known[s])
            else:
                learner.p_known[s] *= (1.0 - bkt_rates["slip"])
        learner.last_seen[s] = today


# ---------------------------------------------------------------------------
# One full run: one model x one selector, N_LEARNERS learners, N_DAYS days
# ---------------------------------------------------------------------------

def run_one(model: str, selector: Selector, seed: int) -> dict:
    senses, items = build_world(seed)
    learners = make_learners(N_LEARNERS, seed + 1)
    rng = random.Random(seed + 2)

    holdout = set(range(N_SENSES - N_HOLDOUT, N_SENSES))  # top-zipf-rank fixed slice, deterministic

    if model == "misspec":
        bkt_rates = MISSPEC_BKT
        for i, l in enumerate(learners):
            pct_rank = i / max(1, len(learners) - 1)
            l.halflife = 30.0 - pct_rank * 20.0  # higher-ability learners forget FASTER (inverted)
        # also invert the ability->halflife correlation deliberately by ability, not index:
        learners.sort(key=lambda l: l.ability)
        for i, l in enumerate(learners):
            pct_rank = i / max(1, len(learners) - 1)
            l.halflife = 30.0 - pct_rank * 20.0
    else:
        bkt_rates = FAMILY_BKT

    pct_scores: list[float] = []
    mastery_snapshots = {}

    for day in range(N_DAYS):
        for learner in learners:
            def decayed(sense_id, _l=learner, _d=day):
                return max(0.0, _l.p_known[sense_id] - p_known_now(_l, sense_id, day, model))
            if isinstance(selector, SelectorB_LivePlusSchedule):
                selector._decayed = decayed

            in_holdout_window = day >= HOLDOUT_START_DAY
            candidates = [
                it for it in items
                if not (NEVER_RE_SERVE and it.id in learner.served_item_ids)
                and not (in_holdout_window and any(s in holdout for s in it.senses))
            ]
            if not candidates:
                continue
            est_p_known = [p_known_now(learner, s, day, model) for s in range(N_SENSES)]
            item = selector.choose(candidates, est_p_known, learner.visible_elo, rng)
            learner.served_item_ids.add(item.id)

            pct = response_fraction(learner, item, day, model, rng)
            pct_scores.append(pct * 100.0)
            expected = 1.0 / (1.0 + 10 ** ((item.difficulty_seeded - learner.visible_elo) / 400.0))
            learner.visible_elo = min(3000.0, max(400.0, learner.visible_elo + 32.0 * (pct - expected)))
            update_knowledge(learner, item, pct, day, model, bkt_rates)

        if day in (0, 9, 19, 29):
            mastery_snapshots[day] = statistics.mean(
                statistics.mean(p_known_now(l, s, day, model) for s in range(N_SENSES))
                for l in learners
            )

    # retention: recall of holdout senses at "day 30" (one step past the sim horizon)
    retention_vals = [
        p_known_now(l, s, N_DAYS, model)
        for l in learners for s in holdout
    ]
    retention = statistics.mean(retention_vals)

    # time-to-proficiency over the target vocabulary (all non-holdout senses)
    target = [s for s in range(N_SENSES) if s not in holdout]
    crossed_days = []
    for l in learners:
        for s in target:
            if l.p_known[s] >= MASTERY_THRESHOLD:
                crossed_days.append(l.last_seen[s] if l.last_seen[s] is not None else N_DAYS)
    frac_crossed = len(crossed_days) / (len(learners) * len(target))
    median_day_to_mastery = statistics.median(crossed_days) if crossed_days else None

    m1 = sum(1 for p in pct_scores if 60 < p <= 85) / len(pct_scores) if pct_scores else 0.0
    m2 = sum(1 for p in pct_scores if p < 50) / len(pct_scores) if pct_scores else 0.0

    return {
        "model": model,
        "selector": selector.name,
        "retention_day30_holdout": round(retention, 4),
        "frac_target_mastered": round(frac_crossed, 4),
        "median_day_to_mastery": median_day_to_mastery,
        "mastery_curve": {str(k): round(v, 4) for k, v in mastery_snapshots.items()},
        "M1_on_target_rate": round(m1, 4),
        "M2_below_floor_rate": round(m2, 4),
        "n_items_served": len(pct_scores),
    }


def build_selectors() -> list[Selector]:
    return [
        SelectorA_LiveObjective(),
        SelectorB_LivePlusSchedule(lambda s: 0.0),
        SelectorC_GainPerMinute(FAMILY_BKT["learn"]),
        SelectorD_ComputedDifficulty(),
        SelectorE_RandomInTier(),
    ]


def main():
    models = ["bkt", "fsrs", "pure_irt", "misspec"]
    results = []
    for model in models:
        for selector in build_selectors():
            results.append(run_one(model, selector, seed=42))
    print(json.dumps(results, indent=2))
    with open("_bakeoff_out.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
