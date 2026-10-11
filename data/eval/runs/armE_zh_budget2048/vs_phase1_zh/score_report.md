# Exercise-gen quality score -- zh

- Candidate: `data/eval/runs/armE_zh_budget2048`
- Reference: `data/eval/runs/phase1_zh` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=86.43, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.49, reference_pct=0.48, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 11,
  "expected_pairs_total": 280,
  "present_pairs_total": 242,
  "coverage_pct": 86.42857142857143,
  "missing_levels_count": 4,
  "missing_levels": [
    3,
    6,
    7,
    9
  ],
  "per_sense_missing": {
    "10103": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10104": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10106": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10107": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10110": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10111": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10112": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "10117": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10119": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "10125": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10131": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10137": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10156": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10300": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10353": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10382": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10525": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10553": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10803": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "11319": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "11531": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "12012": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "19859": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "19860": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "19867": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "19870": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "19882": [
      [
        9,
        "jumbled_sentence"
      ]
    ]
  }
}
```

### Candidate metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 204,
    "invalid_assets": 1,
    "invalid_rate_pct": 0.49019607843137253,
    "by_asset_type": {
      "prompt1_core": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 28,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 27,
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
        "invalid": 1,
        "invalid_rate_pct": 3.3333333333333335
      },
      "prompt3_transforms_B": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
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
      "total": 36,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 175,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 114,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 12,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 30,
    "total_calls": 523,
    "priced_calls": 523,
    "total_cost_usd": 1.170725,
    "cost_per_sense_mean": 0.039024,
    "cost_per_sense_p50": 0.041316,
    "cost_per_sense_p90": 0.044306,
    "retries_per_sense_mean": 1.0,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 11.04,
      "judge_ladder_p1_sentence": 8.84,
      "vocab_prompt1_core_sentence_repair": 2.62,
      "vocab_prompt3_transforms": 15.14,
      "vocab_prompt2_exercises": 20.0,
      "judge_ladder_l1_distractor": 8.19,
      "cloze_distractor_judge": 0.83,
      "judge_ladder_sentence_validity": 11.71,
      "ladder_syn_ant_generation": 12.08,
      "judge_ladder_relation": 7.43,
      "judge_ladder_sentence_validity__json_repair": 1.35,
      "judge_ladder_relation__json_repair": 0.25,
      "vocab_prompt1_core_sentence_repair__json_repair": 0.37,
      "judge_ladder_l1_distractor__json_repair": 0.16
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 346.25,
    "wall_clock_per_sense_p50_s": 329.38,
    "wall_clock_per_sense_p90_s": 415.19
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