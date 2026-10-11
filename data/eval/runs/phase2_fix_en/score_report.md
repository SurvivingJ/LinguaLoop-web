# Exercise-gen quality score -- en

- Candidate: `data/eval/runs/phase2_fix_en`
- Reference: `data/eval/runs/phase1_en` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=1.56, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=93.33, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=14.06, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 5,
  "senses_missing_from_candidate": [
    "13898",
    "13929",
    "13931",
    "13946",
    "13981",
    "14001",
    "14010",
    "14015",
    "14020",
    "14024",
    "14033",
    "14040",
    "14090",
    "14189",
    "14390",
    "14544",
    "15150",
    "15216",
    "16031",
    "16181",
    "19458",
    "19480",
    "19521",
    "40142",
    "40248"
  ],
  "reference_level_type_pairs": 10,
  "expected_pairs_total": 30,
  "present_pairs_total": 28,
  "coverage_pct": 93.33333333333333,
  "missing_levels_count": 2,
  "missing_levels": [
    1,
    6
  ],
  "per_sense_missing": {
    "13902": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ]
  }
}
```

### Candidate metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 35,
    "invalid_assets": 0,
    "invalid_rate_pct": 0.0,
    "by_asset_type": {
      "prompt1_core": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_A": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_B": {
        "total": 5,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "sentence_validity": {
      "total": 32,
      "rejected": 2,
      "reject_rate_pct": 6.25
    },
    "relation": {
      "total": 3,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "word_family": {
      "total": 15,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "collocation": {
      "total": 2,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 0,
    "dropped": 0,
    "drop_rate_pct": null,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 5,
    "total_calls": 85,
    "priced_calls": 85,
    "total_cost_usd": 0.064746,
    "cost_per_sense_mean": 0.012949,
    "cost_per_sense_p50": 0.012917,
    "cost_per_sense_p90": 0.015111,
    "retries_per_sense_mean": 0.4,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 15.73,
      "judge_ladder_p1_sentence": 5.92,
      "vocab_bundle_generation": 39.79,
      "vocab_prompt2_exercises": 4.04,
      "judge_ladder_sentence_validity": 8.73,
      "cloze_distractor_judge": 5.68,
      "judge_ladder_l1_distractor": 5.43,
      "judge_ladder_relation": 5.08,
      "judge_ladder_word_family": 3.91,
      "vocab_prompt1_core_sentence_repair": 0.52,
      "vocab_prompt3_transforms": 3.15,
      "ladder_l4_morphology_generation": 1.42,
      "judge_ladder_collocation": 0.6
    }
  },
  "wall_clock": {
    "senses_with_timings": 5,
    "wall_clock_per_sense_mean_s": 99.69,
    "wall_clock_per_sense_p50_s": 94.91,
    "wall_clock_per_sense_p90_s": 124.02
  }
}
```

### Reference metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 192,
    "invalid_assets": 27,
    "invalid_rate_pct": 14.0625,
    "by_asset_type": {
      "prompt1_core": {
        "total": 30,
        "invalid": 1,
        "invalid_rate_pct": 3.3333333333333335
      },
      "prompt2_exercises_A": {
        "total": 25,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 26,
        "invalid": 12,
        "invalid_rate_pct": 46.15384615384615
      },
      "llm_types_A": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 26,
        "invalid": 1,
        "invalid_rate_pct": 3.8461538461538463
      },
      "prompt3_transforms_B": {
        "total": 27,
        "invalid": 13,
        "invalid_rate_pct": 48.148148148148145
      },
      "llm_types_B": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "sentence_validity": {
      "total": 169,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 48,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "word_family": {
      "total": 27,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "l1_distractor": {
      "total": 45,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 15,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 30,
    "total_calls": 481,
    "priced_calls": 481,
    "total_cost_usd": 0.867898,
    "cost_per_sense_mean": 0.02893,
    "cost_per_sense_p50": 0.031798,
    "cost_per_sense_p90": 0.038795,
    "retries_per_sense_mean": 1.1667,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 7.47,
      "judge_ladder_p1_sentence": 2.66,
      "vocab_prompt1_core_sentence_repair": 0.25,
      "vocab_prompt3_transforms": 20.28,
      "ladder_l4_morphology_generation": 4.75,
      "vocab_prompt2_exercises": 42.4,
      "judge_ladder_l1_distractor": 2.02,
      "cloze_distractor_judge": 1.92,
      "judge_ladder_sentence_validity": 2.81,
      "ladder_syn_ant_generation": 8.85,
      "ladder_word_family_generation": 4.28,
      "judge_ladder_relation": 1.59,
      "judge_ladder_word_family": 0.43,
      "vocab_prompt1_core_repair": 0.25,
      "judge_ladder_relation__json_repair": 0.04
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 92.07,
    "wall_clock_per_sense_p50_s": 91.12,
    "wall_clock_per_sense_p90_s": 115.83
  }
}
```

## 2. Blind pairwise review

No pairwise results yet. Packs are at `<candidate>/pairwise_packs/pack_NN.md`; have a fresh-context reviewer return `{sense_id, level, preferred, major_defects_A, major_defects_B, notes}` JSON lines, then run `python scripts/merge_pairwise_verdicts.py --candidate <candidate dir> --verdicts <file(s)>` and re-run this script with `--pairwise-results` to fold the result into the decision.

## 3. Non-inferiority thresholds used
```json
{
  "major_defect_margin_pp": 2.0,
  "pairwise_loss_margin_pp": 10.0,
  "coverage_min_pct": 95.0,
  "invalid_asset_margin_pp": 3.0
}
```