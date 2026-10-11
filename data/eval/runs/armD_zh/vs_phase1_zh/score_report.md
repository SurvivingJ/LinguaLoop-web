# Exercise-gen quality score -- zh

- Candidate: `data/eval/runs/armD_zh`
- Reference: `data/eval/runs/phase1_zh` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=81.79, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.97, reference_pct=0.48, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 11,
  "expected_pairs_total": 280,
  "present_pairs_total": 229,
  "coverage_pct": 81.78571428571429,
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
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10104": [
      [
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10105": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        6,
        "synonym_antonym_match"
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
    "10106": [
      [
        6,
        "synonym_antonym_match"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10107": [
      [
        3,
        "cloze_completion"
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
        9,
        "jumbled_sentence"
      ]
    ],
    "10112": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10113": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10117": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10119": [
      [
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "10125": [
      [
        6,
        "semantic_discrimination"
      ],
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
        6,
        "semantic_discrimination"
      ]
    ],
    "10156": [
      [
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
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
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "10525": [
      [
        3,
        "cloze_completion"
      ],
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
    "11315": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "11319": [
      [
        7,
        "spot_incorrect_sentence"
      ],
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
        6,
        "semantic_discrimination"
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
        9,
        "jumbled_sentence"
      ]
    ],
    "19870": [
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
    "total_assets": 206,
    "invalid_assets": 2,
    "invalid_rate_pct": 0.970873786407767,
    "by_asset_type": {
      "prompt1_core": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 29,
        "invalid": 1,
        "invalid_rate_pct": 3.4482758620689653
      },
      "llm_types_A": {
        "total": 30,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 29,
        "invalid": 1,
        "invalid_rate_pct": 3.4482758620689653
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
      "total": 39,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 127,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 111,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 13,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 30,
    "total_calls": 525,
    "priced_calls": 525,
    "total_cost_usd": 0.822387,
    "cost_per_sense_mean": 0.027413,
    "cost_per_sense_p50": 0.028193,
    "cost_per_sense_p90": 0.030298,
    "retries_per_sense_mean": 1.0333,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 10.88,
      "judge_ladder_p1_sentence": 7.86,
      "vocab_prompt1_core_sentence_repair": 1.96,
      "vocab_prompt3_transforms": 13.76,
      "ladder_syn_ant_generation": 10.01,
      "vocab_prompt2_exercises": 19.24,
      "judge_ladder_l1_distractor": 9.54,
      "cloze_distractor_judge": 1.2,
      "judge_ladder_sentence_validity": 14.41,
      "judge_ladder_sentence_validity__json_repair": 2.63,
      "judge_ladder_relation": 8.51
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 254.51,
    "wall_clock_per_sense_p50_s": 253.95,
    "wall_clock_per_sense_p90_s": 296.31
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