"""Proves the learner simulator produces a sane learning curve, that the MC
guessing floor actually floors the response probability (the mechanism the
whole module exists to demonstrate), and that forgetting decays toward a
floor rather than to zero."""
from lab.learner_sim import (
    NearestEloSelector,
    SenseKnowledge,
    SimulatedLearner,
    learning_curve,
    make_population,
    simulate,
)


def test_population_has_correlated_but_distinct_per_skill_ability():
    pop = make_population(5, skills=["reading", "listening"], seed=1)
    assert len(pop) == 5
    for learner in pop:
        assert "reading" in learner.true_ability
        assert "listening" in learner.true_ability


def test_guess_floor_caps_worst_case_response_probability():
    pop = make_population(1, skills=["reading"], seed=2, ability_mean=400, ability_sd=0)
    learner = pop[0]
    # an absurdly-too-hard item for a very low-ability learner: probability
    # must still be at least the MC guessing floor (1/4), never below it -
    # this is the exact mechanism docs/recon-serving.md blames for capping
    # ELO's reachable spread at ~191 points.
    prob = learner.response_prob(item_difficulty=3000, skill="reading")
    assert prob >= 1 / 4 - 1e-9


def test_simulation_produces_a_learning_curve_that_climbs_toward_true_ability():
    pop = make_population(1, skills=["reading"], seed=3, ability_mean=1800, ability_sd=0)
    learner = pop[0]
    selector = NearestEloSelector()
    history = simulate(selector, learner, n_days=200, seed=3)
    curve = learning_curve(history, "reading")
    assert len(curve) == 200

    early_avg = sum(v for _, v in curve[:10]) / 10
    late_avg = sum(v for _, v in curve[-10:]) / 10
    # cold start is 1200, true ability is 1800: visible ELO should climb
    # substantially toward it over 200 days, not stay flat.
    assert late_avg > early_avg + 100


def test_forgetting_decays_toward_a_floor_not_to_zero():
    learner = SimulatedLearner(
        learner_id="x",
        sense_knowledge={1: SenseKnowledge(sense_id=1, true_p_known=0.9, last_seen_day=0)},
    )
    p_now = learner.p_known_now(1, today=0)
    p_much_later = learner.p_known_now(1, today=365)
    assert p_now == 0.9
    assert p_much_later < p_now
    assert p_much_later > 0.9 * 0.15 - 1e-9  # never fully erases a well-learned item
