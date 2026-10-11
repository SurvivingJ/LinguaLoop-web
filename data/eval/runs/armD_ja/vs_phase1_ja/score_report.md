# Exercise-gen quality score -- ja

- Candidate: `data/eval/runs/armD_ja`
- Reference: `data/eval/runs/phase1_ja` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=9.73, reference_pct=10.09, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=69.6, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 12,
  "expected_pairs_total": 227,
  "present_pairs_total": 158,
  "coverage_pct": 69.60352422907489,
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
    "34998": [
      [
        1,
        "phonetic_recognition"
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
    "34999": [
      [
        1,
        "kanji_to_reading"
      ],
      [
        1,
        "phonetic_recognition"
      ],
      [
        1,
        "reading_to_kanji"
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
    "35001": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35011": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35017": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35033": [
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
        "morphology_slot"
      ],
      [
        4,
        "particle_selection"
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
    "35039": [
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
    "35055": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35093": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35111": [
      [
        1,
        "phonetic_recognition"
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
        4,
        "particle_selection"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35127": [
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
    "35147": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35201": [
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
    "35227": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35293": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "35311": [
      [
        6,
        "synonym_antonym_match"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35341": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35419": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "35615": [
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "36181": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "36191": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "38099": [
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
    "39661": [
      [
        3,
        "cloze_completion"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "53352": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        6,
        "synonym_antonym_match"
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
    "total_assets": 168,
    "invalid_assets": 0,
    "invalid_rate_pct": 0.0,
    "by_asset_type": {
      "prompt1_core": {
        "total": 26,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 25,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 22,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_A": {
        "total": 26,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 25,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 18,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_B": {
        "total": 26,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "particle": {
      "total": 66,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 63,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 76,
      "rejected": 2,
      "reject_rate_pct": 2.6315789473684212
    },
    "l1_distractor": {
      "total": 157,
      "rejected": 57,
      "reject_rate_pct": 36.30573248407644
    }
  },
  "l1_drop_rate": {
    "l1_variants": 16,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 30,
    "total_calls": 579,
    "priced_calls": 567,
    "total_cost_usd": 1.029109,
    "cost_per_sense_mean": 0.034304,
    "cost_per_sense_p50": 0.039778,
    "cost_per_sense_p90": 0.044838,
    "retries_per_sense_mean": 2.1,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 10.44,
      "judge_ladder_p1_sentence": 8.76,
      "vocab_prompt1_core_sentence_repair": 5.07,
      "vocab_prompt3_transforms": 10.25,
      "ladder_particle_selection_generation": 5.1,
      "vocab_prompt2_exercises": 15.21,
      "ladder_syn_ant_generation": 6.53,
      "cloze_distractor_judge": 0.83,
      "judge_ladder_sentence_validity": 14.94,
      "judge_ladder_particle": 3.96,
      "judge_ladder_relation": 5.72,
      "judge_ladder_l1_distractor": 5.93,
      "judge_ladder_particle__json_repair": 0.16,
      "judge_ladder_l1_distractor__json_repair": 1.05,
      "ladder_l4_morphology_generation": 3.87,
      "vocab_prompt1_core_repair": 2.01,
      "judge_ladder_sentence_validity__json_repair": 0.17
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 352.39,
    "wall_clock_per_sense_p50_s": 382.97,
    "wall_clock_per_sense_p90_s": 446.55
  }
}
```

### Reference metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 152,
    "invalid_assets": 0,
    "invalid_rate_pct": 0.0,
    "by_asset_type": {
      "prompt1_core": {
        "total": 26,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 21,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 15,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_A": {
        "total": 26,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 19,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 19,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_B": {
        "total": 26,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 217,
      "rejected": 86,
      "reject_rate_pct": 39.63133640552996
    },
    "sentence_validity": {
      "total": 135,
      "rejected": 1,
      "reject_rate_pct": 0.7407407407407407
    },
    "particle": {
      "total": 33,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 21,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 22,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 28,
    "total_calls": 475,
    "priced_calls": 471,
    "total_cost_usd": 1.919494,
    "cost_per_sense_mean": 0.068553,
    "cost_per_sense_p50": 0.073114,
    "cost_per_sense_p90": 0.08769,
    "retries_per_sense_mean": 2.4286,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 12.26,
      "judge_ladder_p1_sentence": 10.15,
      "vocab_prompt1_core_sentence_repair": 4.19,
      "ladder_particle_selection_generation": 2.0,
      "vocab_prompt3_transforms": 12.55,
      "vocab_prompt2_exercises": 19.99,
      "judge_ladder_l1_distractor": 14.75,
      "cloze_distractor_judge": 0.45,
      "judge_ladder_sentence_validity": 14.37,
      "judge_ladder_particle": 1.85,
      "ladder_syn_ant_generation": 1.97,
      "judge_ladder_relation": 1.52,
      "ladder_l4_morphology_generation": 1.34,
      "vocab_prompt1_core_repair": 1.6,
      "judge_ladder_l1_distractor__json_repair": 0.48,
      "judge_ladder_relation__json_repair": 0.15,
      "vocab_prompt1_core_repair__json_repair": 0.38
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 510.32,
    "wall_clock_per_sense_p50_s": 522.03,
    "wall_clock_per_sense_p90_s": 664.23
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