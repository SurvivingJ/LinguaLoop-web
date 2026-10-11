# Exercise-gen quality score -- zh

- Candidate: `data/eval/runs/phase2_bundle_zh`
- Reference: `data/eval/runs/phase1_zh` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=1.25, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | FAIL | coverage_pct=32.5, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | FAIL | candidate_pct=5.41, reference_pct=0.48, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 11,
  "expected_pairs_total": 280,
  "present_pairs_total": 91,
  "coverage_pct": 32.5,
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
        3,
        "cloze_completion"
      ]
    ],
    "10106": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "10110": [
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
    "10111": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10112": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10117": [
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
    "10119": [
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
    "10125": [
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "10131": [
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
    "10137": [
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
    "10156": [
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
    "10300": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "phonetic_recognition"
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
    "10353": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "phonetic_recognition"
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
    "10382": [
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
    "10525": [
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
    "10553": [
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
        6,
        "semantic_discrimination"
      ],
      [
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "11319": [
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
    "11531": [
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
    "12012": [
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
    "19859": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "phonetic_recognition"
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
    "19860": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "phonetic_recognition"
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
    "19867": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "phonetic_recognition"
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
    "19870": [
      [
        1,
        "hanzi_to_pinyin"
      ],
      [
        1,
        "phonetic_recognition"
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
    "19882": [
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
    ]
  }
}
```

### Candidate metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 74,
    "invalid_assets": 4,
    "invalid_rate_pct": 5.405405405405405,
    "by_asset_type": {
      "prompt1_core": {
        "total": 11,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 9,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_A": {
        "total": 11,
        "invalid": 2,
        "invalid_rate_pct": 18.181818181818183
      },
      "llm_types_A": {
        "total": 11,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 10,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 11,
        "invalid": 2,
        "invalid_rate_pct": 18.181818181818183
      },
      "llm_types_B": {
        "total": 11,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 12,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 60,
      "rejected": 3,
      "reject_rate_pct": 5.0
    },
    "relation": {
      "total": 33,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "cloze": {
      "total": 18,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 4,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 11,
    "total_calls": 86,
    "priced_calls": 86,
    "total_cost_usd": 0.100576,
    "cost_per_sense_mean": 0.009143,
    "cost_per_sense_p50": 0.009974,
    "cost_per_sense_p90": 0.010546,
    "retries_per_sense_mean": 0.9091,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 18.5,
      "vocab_prompt1_core_sentence_repair": 1.25,
      "judge_ladder_p1_sentence": 5.69,
      "vocab_bundle_generation": 43.77,
      "ladder_syn_ant_generation": 3.5,
      "ladder_bundle_judge": 18.97,
      "judge_ladder_relation": 3.81,
      "vocab_prompt2_exercises": 2.89,
      "vocab_prompt3_transforms": 0.64,
      "judge_ladder_sentence_validity": 0.41,
      "cloze_distractor_judge": 0.35,
      "judge_ladder_l1_distractor": 0.22
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 37.57,
    "wall_clock_per_sense_p50_s": 0.84,
    "wall_clock_per_sense_p90_s": 113.53
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