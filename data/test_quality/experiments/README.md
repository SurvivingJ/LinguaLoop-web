# Test-generation experiments (TASK-923/924/927)

Topic lists are fixed so every arm generates the same (topic, tier) pairs:
`e1_topics.json` (12: 2 per tier T1–T6) and `e2_topics.json` (12: 4 per tier
T1–T3, disjoint from E1). All topics had no test at selection (2026-11-09).
"tier" is the *target* tier; jev assigns the stored one.

Prerequisites: `migrations/fix_question_type_mix_t3_t5_t6.sql` (both),
`migrations/prompt_templates_tier_id.sql` + `seed_tier_question_templates.sql`
(E2), an `OPENROUTER_API_KEY` (jev tier assignment always goes through it).

Run arms **one after another** (cost is attributed by run window), per language:

```bash
# E1 — check modes (TASK-924): 3 arms x 3 languages x 12 = 108 tests
for arm in flag calibrated reject; do for lang in zh en ja; do
  python scripts/run_test_generation_cli.py --language $lang --type reading \
    --topics-file data/test_quality/experiments/e1_topics.json \
    --inactive --no-dedup --qc-modes $arm --run-tag e1-$arm
done; done

# E2 — tier templates (TASK-927): 2 arms x 3 languages x 12 = 72 tests
for arm in off on; do for lang in zh en ja; do
  python scripts/run_test_generation_cli.py --language $lang --type reading \
    --topics-file data/test_quality/experiments/e2_topics.json \
    --inactive --no-dedup --qc-modes calibrated --tier-templates $arm --run-tag e2-$arm
done; done

# Arm-blind review packs, then score
python scripts/build_experiment_review_packs.py e1-flag e1-calibrated e1-reject --out data/test_quality/experiments/e1_review
python scripts/score_experiment.py e1-flag e1-calibrated e1-reject --reviews data/test_quality/experiments/e1_review
```

Pre-registered decision rules are in `wiki/tasklist/test-quality-checks.tasks.md`
(TASK-924, TASK-927) — written before any run.
