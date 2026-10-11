# Exercise-gen quality score -- zh

- Candidate: `data/eval/runs/armB_zh`
- Reference: `data/eval/runs/phase1_zh` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=84.29, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | FAIL | candidate_pct=3.96, reference_pct=0.48, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 11,
  "expected_pairs_total": 280,
  "present_pairs_total": 236,
  "coverage_pct": 84.28571428571429,
  "missing_levels_count": 7,
  "missing_levels": [
    1,
    2,
    3,
    4,
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
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10104": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10106": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "10110": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "10111": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10112": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "10113": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10117": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10119": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10125": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10137": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "10156": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "10300": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10382": [
      [
        3,
        "cloze_completion"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10525": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10553": [
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "10803": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "pinyin_to_hanzi"
      ],
      [
        1,
        "tone_id_word"
      ],
      [
        2,
        "definition_match"
      ],
      [
        3,
        "cloze_completion"
      ],
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
    "11315": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "11531": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "19859": [
      [
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "19860": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "19867": [
      [
        1,
        "phonetic_recognition"
      ]
    ],
    "19870": [
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "cloze_typed"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "19882": [
      [
        6,
        "semantic_discrimination"
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
    "total_assets": 202,
    "invalid_assets": 8,
    "invalid_rate_pct": 3.9603960396039604,
    "by_asset_type": {
      "prompt1_core": {
        "total": 30,
        "invalid": 1,
        "invalid_rate_pct": 3.3333333333333335
      },
      "prompt2_exercises_A": {
        "total": 28,
        "invalid": 1,
        "invalid_rate_pct": 3.5714285714285716
      },
      "prompt3_transforms_A": {
        "total": 28,
        "invalid": 2,
        "invalid_rate_pct": 7.142857142857143
      },
      "llm_types_A": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 29,
        "invalid": 1,
        "invalid_rate_pct": 3.4482758620689653
      },
      "prompt3_transforms_B": {
        "total": 29,
        "invalid": 3,
        "invalid_rate_pct": 10.344827586206897
      },
      "llm_types_B": {
        "total": 29,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 24,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 108,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 90,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 8,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 30,
    "total_calls": 525,
    "priced_calls": 525,
    "total_cost_usd": 0.27631,
    "cost_per_sense_mean": 0.00921,
    "cost_per_sense_p50": 0.009508,
    "cost_per_sense_p90": 0.010231,
    "retries_per_sense_mean": 0.6333,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 18.38,
      "judge_ladder_p1_sentence": 6.28,
      "vocab_prompt1_core_sentence_repair": 0.98,
      "ladder_syn_ant_generation": 7.89,
      "vocab_prompt3_transforms": 15.12,
      "vocab_prompt2_exercises": 30.33,
      "judge_ladder_l1_distractor": 4.41,
      "cloze_distractor_judge": 3.36,
      "judge_ladder_sentence_validity": 8.87,
      "judge_ladder_relation": 4.39
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 55.14,
    "wall_clock_per_sense_p50_s": 55.38,
    "wall_clock_per_sense_p90_s": 59.89
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