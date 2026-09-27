# Exercise-gen quality score -- ja

- Candidate: `data/eval/runs/baseline_ja`
- Reference: `data/eval/exercise_gen_reference_set_2026-09.json` (frozen_reference_json)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | SKIPPED | reason=insufficient data (no judge verdicts and no pairwise results), source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=45.78, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [
    "35059",
    "35065",
    "35069",
    "35125",
    "35143",
    "35189",
    "35215",
    "35241",
    "35351",
    "35371",
    "35397",
    "35403",
    "35443",
    "35681",
    "35739",
    "36279",
    "36309",
    "36521",
    "36861",
    "51788"
  ],
  "reference_level_type_pairs": 12,
  "expected_pairs_total": 249,
  "present_pairs_total": 114,
  "coverage_pct": 45.78313253012048,
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
        7,
        "spot_incorrect_sentence"
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
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "35009": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "35011": [
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
    "35017": [
      [
        4,
        "particle_selection"
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
    "35093": [
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
        7,
        "spot_incorrect_sentence"
      ],
      [
        9,
        "jumbled_sentence"
      ]
    ],
    "35111": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "35147": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "35157": [
      [
        1,
        "kanji_to_reading"
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
    "35201": [
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
    "35211": [
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
    "35293": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "35525": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        2,
        "definition_match"
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
    "35615": [
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "36181": [
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
    "36191": [
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
    "38099": [
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
    "39661": [
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
        4,
        "cloze_typed"
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
    "53352": [
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
    ]
  }
}
```

### Candidate metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 89,
    "invalid_assets": 0,
    "invalid_rate_pct": 0.0,
    "by_asset_type": {
      "prompt1_core": {
        "total": 15,
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
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_A": {
        "total": 15,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 11,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 9,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_B": {
        "total": 15,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 122,
      "rejected": 41,
      "reject_rate_pct": 33.60655737704918
    },
    "sentence_validity": {
      "total": 82,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "particle": {
      "total": 24,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 33,
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
    "senses_with_calls": 16,
    "total_calls": 292,
    "priced_calls": 259,
    "total_cost_usd": 0.937617,
    "cost_per_sense_mean": 0.058601,
    "cost_per_sense_p50": 0.065306,
    "cost_per_sense_p90": 0.0913,
    "retries_per_sense_mean": 5.3125,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 12.28,
      "judge_ladder_p1_sentence": 9.58,
      "vocab_prompt1_core_sentence_repair__json_repair": 0.42,
      "vocab_prompt3_transforms": 11.52,
      "ladder_particle_selection_generation": 1.25,
      "ladder_particle_selection_generation__json_repair": 1.01,
      "vocab_prompt2_exercises": 20.38,
      "ladder_syn_ant_generation__json_repair": 1.75,
      "judge_ladder_l1_distractor": 5.65,
      "cloze_distractor_judge": 0.49,
      "judge_ladder_sentence_validity": 14.55,
      "judge_ladder_particle": 1.92,
      "judge_ladder_l1_distractor__json_repair": 5.13,
      "judge_ladder_relation__json_repair": 0.96,
      "vocab_prompt1_core_sentence_repair": 3.66,
      "ladder_l4_morphology_generation__json_repair": 0.77,
      "ladder_l4_morphology_generation": 1.46,
      "judge_ladder_relation": 2.35,
      "vocab_prompt1_core_repair": 1.49,
      "ladder_syn_ant_generation": 1.95,
      "vocab_prompt1_core__json_repair": 1.05,
      "vocab_prompt2_exercises__json_repair": 0.38
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 298.42,
    "wall_clock_per_sense_p50_s": 68.25,
    "wall_clock_per_sense_p90_s": 764.84
  }
}
```

### Reference metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 274,
    "invalid_assets": 0,
    "invalid_rate_pct": 0.0,
    "by_asset_type": {
      "prompt1_core": {
        "total": 50,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 50,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 50,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 50,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 50,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "llm_types_A": {
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
  "judge_reject_rates": {},
  "l1_drop_rate": {
    "l1_variants": 43,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 0,
    "total_calls": 0,
    "priced_calls": 0,
    "total_cost_usd": null,
    "cost_per_sense_mean": null,
    "cost_per_sense_p50": null,
    "cost_per_sense_p90": null,
    "retries_per_sense_mean": null,
    "per_stage_cost_share_pct": {}
  },
  "wall_clock": {
    "senses_with_timings": 0,
    "wall_clock_per_sense_mean_s": null,
    "wall_clock_per_sense_p50_s": null,
    "wall_clock_per_sense_p90_s": null
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