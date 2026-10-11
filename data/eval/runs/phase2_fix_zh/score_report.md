# Exercise-gen quality score -- zh

- Candidate: `data/eval/runs/phase2_fix_zh`
- Reference: `data/eval/runs/phase1_zh` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=1.52, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=86.0, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.48, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 5,
  "senses_missing_from_candidate": [
    "10110",
    "10111",
    "10112",
    "10113",
    "10117",
    "10119",
    "10125",
    "10131",
    "10137",
    "10156",
    "10300",
    "10353",
    "10382",
    "10525",
    "10553",
    "10803",
    "11315",
    "11319",
    "11531",
    "12012",
    "19859",
    "19860",
    "19867",
    "19870",
    "19882"
  ],
  "reference_level_type_pairs": 11,
  "expected_pairs_total": 50,
  "present_pairs_total": 43,
  "coverage_pct": 86.0,
  "missing_levels_count": 3,
  "missing_levels": [
    1,
    3,
    7
  ],
  "per_sense_missing": {
    "10103": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10104": [
      [
        3,
        "cloze_completion"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10106": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "10107": [
      [
        7,
        "spot_incorrect_sentence"
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
      "total": 33,
      "rejected": 2,
      "reject_rate_pct": 6.0606060606060606
    },
    "l1_distractor": {
      "total": 6,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 21,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "cloze": {
      "total": 9,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 2,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 5,
    "total_calls": 46,
    "priced_calls": 46,
    "total_cost_usd": 0.05357,
    "cost_per_sense_mean": 0.010714,
    "cost_per_sense_p50": 0.011304,
    "cost_per_sense_p90": 0.011717,
    "retries_per_sense_mean": 1.0,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 15.55,
      "vocab_prompt1_core_sentence_repair": 1.06,
      "judge_ladder_p1_sentence": 5.71,
      "vocab_bundle_generation": 41.57,
      "vocab_prompt2_exercises": 4.91,
      "vocab_prompt3_transforms": 4.72,
      "ladder_syn_ant_generation": 1.75,
      "ladder_bundle_judge": 20.25,
      "judge_ladder_relation": 4.47
    }
  },
  "wall_clock": {
    "senses_with_timings": 5,
    "wall_clock_per_sense_mean_s": 116.37,
    "wall_clock_per_sense_p50_s": 120.33,
    "wall_clock_per_sense_p90_s": 129.48
  }
}
```

### Reference metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 210,
    "invalid_assets": 1,
    "invalid_rate_pct": 0.47619047619047616,
    "by_asset_type": {
      "prompt1_core": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_A": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 30,
        "invalid": 1,
        "invalid_rate_pct": 3.3333333333333335
      },
      "llm_types_B": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 30,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 185,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 54,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 10,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 30,
    "total_calls": 479,
    "priced_calls": 477,
    "total_cost_usd": 1.478446,
    "cost_per_sense_mean": 0.049282,
    "cost_per_sense_p50": 0.050308,
    "cost_per_sense_p90": 0.05912,
    "retries_per_sense_mean": 1.5333,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 13.94,
      "vocab_prompt1_core_sentence_repair": 2.91,
      "judge_ladder_p1_sentence": 10.61,
      "ladder_syn_ant_generation": 3.31,
      "vocab_prompt3_transforms": 14.7,
      "vocab_prompt2_exercises": 30.34,
      "judge_ladder_l1_distractor": 9.36,
      "cloze_distractor_judge": 0.69,
      "judge_ladder_sentence_validity": 9.48,
      "judge_ladder_relation": 3.19,
      "judge_ladder_p1_sentence__json_repair": 0.09,
      "judge_ladder_sentence_validity__json_repair": 0.56,
      "judge_ladder_l1_distractor__json_repair": 0.44,
      "judge_ladder_relation__json_repair": 0.36
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 357.14,
    "wall_clock_per_sense_p50_s": 332.45,
    "wall_clock_per_sense_p90_s": 437.78
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