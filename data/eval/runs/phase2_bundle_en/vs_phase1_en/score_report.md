# Exercise-gen quality score -- en

- Candidate: `data/eval/runs/phase2_bundle_en`
- Reference: `data/eval/runs/phase1_en` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=1.35, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=39.68, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=3.57, reference_pct=14.06, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 10,
  "expected_pairs_total": 189,
  "present_pairs_total": 75,
  "coverage_pct": 39.682539682539684,
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
    "13902": [
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
        "synonym_antonym_match"
      ]
    ],
    "13929": [
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "13946": [
      [
        6,
        "synonym_antonym_match"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "14001": [
      [
        1,
        "phonetic_recognition"
      ]
    ],
    "14010": [
      [
        4,
        "word_family"
      ]
    ],
    "14015": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        4,
        "word_family"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "14033": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
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
    "14040": [
      [
        2,
        "definition_match"
      ],
      [
        4,
        "cloze_typed"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "14090": [
      [
        2,
        "definition_match"
      ],
      [
        4,
        "cloze_typed"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "14100": [
      [
        2,
        "definition_match"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "cloze_typed"
      ],
      [
        4,
        "morphology_slot"
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
    "14189": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
      ],
      [
        4,
        "word_family"
      ],
      [
        6,
        "semantic_discrimination"
      ],
      [
        6,
        "synonym_antonym_match"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "14390": [
      [
        2,
        "definition_match"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "cloze_typed"
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
    "14473": [
      [
        2,
        "definition_match"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "cloze_typed"
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
    "14544": [
      [
        2,
        "definition_match"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "cloze_typed"
      ],
      [
        4,
        "morphology_slot"
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
    "15150": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
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
    "15216": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
      ],
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
    "16031": [
      [
        2,
        "definition_match"
      ],
      [
        4,
        "cloze_typed"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "16181": [
      [
        1,
        "phonetic_recognition"
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
        6,
        "synonym_antonym_match"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "19458": [
      [
        2,
        "definition_match"
      ],
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "cloze_typed"
      ],
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
    "19480": [
      [
        2,
        "definition_match"
      ],
      [
        4,
        "cloze_typed"
      ],
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
    "19521": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
      ],
      [
        4,
        "word_family"
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
    "40142": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
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
    "40248": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "cloze_typed"
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
    ]
  }
}
```

### Candidate metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 84,
    "invalid_assets": 3,
    "invalid_rate_pct": 3.5714285714285716,
    "by_asset_type": {
      "prompt1_core": {
        "total": 12,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 12,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 12,
        "invalid": 3,
        "invalid_rate_pct": 25.0
      },
      "llm_types_A": {
        "total": 12,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 12,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 12,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_B": {
        "total": 12,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 21,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 89,
      "rejected": 6,
      "reject_rate_pct": 6.741573033707865
    },
    "relation": {
      "total": 12,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "word_family": {
      "total": 33,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "collocation": {
      "total": 1,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 7,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 12,
    "total_calls": 176,
    "priced_calls": 176,
    "total_cost_usd": 0.144012,
    "cost_per_sense_mean": 0.012001,
    "cost_per_sense_p50": 0.011189,
    "cost_per_sense_p90": 0.015914,
    "retries_per_sense_mean": 0.8333,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 17.55,
      "judge_ladder_p1_sentence": 6.09,
      "vocab_bundle_generation": 40.91,
      "vocab_prompt3_transforms": 6.67,
      "judge_ladder_sentence_validity": 8.62,
      "cloze_distractor_judge": 5.59,
      "judge_ladder_l1_distractor": 5.0,
      "vocab_prompt2_exercises": 1.77,
      "judge_ladder_relation": 3.02,
      "judge_ladder_word_family": 3.13,
      "vocab_prompt1_core_sentence_repair": 0.95,
      "ladder_l4_morphology_generation": 0.31,
      "judge_ladder_word_family__json_repair": 0.25,
      "judge_ladder_collocation": 0.14
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 36.45,
    "wall_clock_per_sense_p50_s": 0.91,
    "wall_clock_per_sense_p90_s": 99.38
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