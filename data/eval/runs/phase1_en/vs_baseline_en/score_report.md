# Exercise-gen quality score -- en

- Candidate: `data/eval/runs/phase1_en`
- Reference: `data/eval/runs/baseline_en` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=7.58, reference_pct=6.82, margin_pp=2.0, source=pairwise |
| (b) pairwise loss - win <= margin | PASS | loss_minus_win_pp=-2.27, margin_pp=10.0 |
| (c) coverage >= threshold | FAIL | coverage_pct=83.43, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=14.06, reference_pct=30.43, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 9,
  "expected_pairs_total": 169,
  "present_pairs_total": 141,
  "coverage_pct": 83.4319526627219,
  "missing_levels_count": 6,
  "missing_levels": [
    1,
    2,
    3,
    4,
    6,
    9
  ],
  "per_sense_missing": {
    "13900": [
      [
        1,
        "phonetic_recognition"
      ]
    ],
    "13931": [
      [
        4,
        "word_family"
      ]
    ],
    "13946": [
      [
        3,
        "cloze_completion"
      ],
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "13981": [
      [
        1,
        "phonetic_recognition"
      ]
    ],
    "14010": [
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "14024": [
      [
        4,
        "word_family"
      ]
    ],
    "14033": [
      [
        4,
        "word_family"
      ]
    ],
    "14090": [
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
    "14100": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        4,
        "word_family"
      ]
    ],
    "14390": [
      [
        4,
        "word_family"
      ]
    ],
    "14473": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "15150": [
      [
        4,
        "word_family"
      ]
    ],
    "15328": [
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
    "16031": [
      [
        3,
        "cloze_completion"
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
    "19480": [
      [
        3,
        "cloze_completion"
      ],
      [
        4,
        "word_family"
      ]
    ]
  }
}
```

### Candidate metrics
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

### Reference metrics
```json
{
  "invalid_asset_rate": {
    "total_assets": 184,
    "invalid_assets": 56,
    "invalid_rate_pct": 30.434782608695652,
    "by_asset_type": {
      "prompt1_core": {
        "total": 28,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_A": {
        "total": 21,
        "invalid": 2,
        "invalid_rate_pct": 9.523809523809524
      },
      "prompt3_transforms_A": {
        "total": 28,
        "invalid": 27,
        "invalid_rate_pct": 96.42857142857143
      },
      "llm_types_A": {
        "total": 28,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt2_exercises_B": {
        "total": 23,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      },
      "prompt3_transforms_B": {
        "total": 28,
        "invalid": 27,
        "invalid_rate_pct": 96.42857142857143
      },
      "llm_types_B": {
        "total": 28,
        "invalid": 0,
        "invalid_rate_pct": 0.0
      }
    }
  },
  "judge_reject_rates": {
    "l1_distractor": {
      "total": 54,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "sentence_validity": {
      "total": 110,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "word_family": {
      "total": 60,
      "rejected": 0,
      "reject_rate_pct": 0.0
    },
    "relation": {
      "total": 42,
      "rejected": 0,
      "reject_rate_pct": 0.0
    }
  },
  "l1_drop_rate": {
    "l1_variants": 18,
    "dropped": 0,
    "drop_rate_pct": 0.0,
    "min_surviving_distractors": 3
  },
  "cost": {
    "senses_with_calls": 28,
    "total_calls": 464,
    "priced_calls": 463,
    "total_cost_usd": 3.031752,
    "cost_per_sense_mean": 0.108277,
    "cost_per_sense_p50": 0.117081,
    "cost_per_sense_p90": 0.152248,
    "retries_per_sense_mean": 0.6786,
    "per_stage_cost_share_pct": {
      "vocab_prompt1_core": 2.18,
      "judge_ladder_p1_sentence": 0.85,
      "ladder_l4_morphology_generation": 6.33,
      "vocab_prompt3_transforms": 11.53,
      "ladder_syn_ant_generation": 12.59,
      "vocab_prompt2_exercises": 50.68,
      "ladder_word_family_generation": 10.92,
      "ladder_word_family_generation__json_repair": 1.71,
      "judge_ladder_l1_distractor": 0.52,
      "cloze_distractor_judge": 0.46,
      "judge_ladder_sentence_validity": 0.55,
      "judge_ladder_relation": 0.44,
      "judge_ladder_word_family": 0.34,
      "vocab_prompt1_core_sentence_repair": 0.09,
      "ladder_l4_morphology_generation__json_repair": 0.82
    }
  },
  "wall_clock": {
    "senses_with_timings": 30,
    "wall_clock_per_sense_mean_s": 52.71,
    "wall_clock_per_sense_p50_s": 56.5,
    "wall_clock_per_sense_p90_s": 74.95
  }
}
```

## 2. Blind pairwise review

```json
{
  "total_pairs_in_key": 132,
  "total_judged": 132,
  "unmatched_verdicts": [],
  "missing_verdicts": [],
  "candidate_wins": 15,
  "reference_wins": 12,
  "ties": 105,
  "win_rate_pct": 11.36,
  "loss_rate_pct": 9.09,
  "tie_rate_pct": 79.55,
  "major_defect_rate_candidate": 7.58,
  "major_defect_rate_reference": 6.82,
  "per_sense": [
    {
      "sense_id": "13900",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets have a clearly correct answer and no also-correct distractors."
    },
    {
      "sense_id": "13900",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze items in both packs are correct and unambiguous."
    },
    {
      "sense_id": "13900",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B's word_family item asks for the 'verb' POS matching the bare stem itself (trivial) vs A's legitimate noun derivation 'picker', but this is not a rubric-defined defect."
    },
    {
      "sense_id": "13900",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination/antonym sets are correct; B shows more items but no quality difference."
    },
    {
      "sense_id": "13900",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [
        "broken chunk reconstruction"
      ],
      "major_defects_reference": [
        "broken chunk reconstruction"
      ],
      "notes": "A's only item drops 'you watch?' from the reconstruction; B has one item with the same bug class ('would choose you' instead of 'would you choose') plus a second, fully correct item."
    },
    {
      "sense_id": "13902",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs; no pitch-accent issue (not applicable to English)."
    },
    {
      "sense_id": "13902",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets are correct with no also-correct distractors."
    },
    {
      "sense_id": "13902",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze items correct and natural on both sides."
    },
    {
      "sense_id": "13902",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze/morphology items correct on both sides."
    },
    {
      "sense_id": "13902",
      "level": 9,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "broken chunk reconstruction"
      ],
      "major_defects_reference": [],
      "notes": "A's second item reconstructs to 'Why did go on you arguing...' instead of '...why did you go on arguing...'; both of B's items reconstruct correctly."
    },
    {
      "sense_id": "13929",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs."
    },
    {
      "sense_id": "13929",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "13929",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "template/answer mismatch"
      ],
      "notes": "B's blank template 'Marcus ___s' combined with accepted answer 'works' would render as the non-word 'workss'."
    },
    {
      "sense_id": "13929",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A has more items but B's single item is correct; no defect in either."
    },
    {
      "sense_id": "13929",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination sets are correct and pragmatically sound."
    },
    {
      "sense_id": "13929",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "13931",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs."
    },
    {
      "sense_id": "13931",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "13931",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "insufficient context for single answer"
      ],
      "notes": "B's item 'Then, they are ___.' gives no context to distinguish 'green' from the other adjective distractors (loud/wooden/sleepy)."
    },
    {
      "sense_id": "13931",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "insufficient context for single answer"
      ],
      "major_defects_reference": [],
      "notes": "The same context-free 'Then, they are ___.' sentence recurs in B's typed-cloze item at this level, with no cue pointing to 'green'."
    },
    {
      "sense_id": "13931",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination sets are correct and pragmatically sound."
    },
    {
      "sense_id": "13931",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "13946",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "13946",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both cloze_typed items are correct and natural."
    },
    {
      "sense_id": "13946",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination/antonym sets are correct; A has more items but no quality difference."
    },
    {
      "sense_id": "13946",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "13981",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "13981",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze items correct on both sides; B's 'heavy' distractor is a mild naturalness stretch but not also-correct."
    },
    {
      "sense_id": "13981",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both packs' word_family items are legitimately derived (demand -> demanding); B has one more item but no quality difference."
    },
    {
      "sense_id": "13981",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination sets are correct and pragmatically sound."
    },
    {
      "sense_id": "13981",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "14001",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14001",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B's cloze_typed accepted-list ('systems') would break subject-verb agreement if substituted into 'the defense ___ gets confused,' but this over-leniency doesn't mislead or wrongly grade a learner, so not counted as major."
    },
    {
      "sense_id": "14001",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "14010",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs."
    },
    {
      "sense_id": "14010",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14010",
      "level": 3,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [],
      "notes": "A's distractor 'heterogeneous' is plausibly also-correct as a near-synonym for 'varied/different' in 'People see time in ___ ways.'"
    },
    {
      "sense_id": "14010",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both packs' word_family items are legitimately derived (differ -> different)."
    },
    {
      "sense_id": "14010",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination/antonym sets are correct; B has more items but no quality difference."
    },
    {
      "sense_id": "14010",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "broken chunk reconstruction"
      ],
      "notes": "B's first item reconstructs to 'have used always stories' instead of the grammatical 'have always used stories.'"
    },
    {
      "sense_id": "14015",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs."
    },
    {
      "sense_id": "14015",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14015",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze items correct and unambiguous on both sides."
    },
    {
      "sense_id": "14015",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both packs' word_family items are legitimately derived (roast -> roasting as noun)."
    },
    {
      "sense_id": "14015",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination/antonym sets are correct; A has more items but no quality difference."
    },
    {
      "sense_id": "14015",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "14020",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14020",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both cloze_typed items correct; minor over-lenient accepted-plural lists exist symmetrically and don't mislead learners."
    },
    {
      "sense_id": "14020",
      "level": 9,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "broken chunk reconstruction"
      ],
      "major_defects_reference": [],
      "notes": "A's second item reconstructs to 'is characterized typically' instead of the grammatical 'is typically characterized.'"
    },
    {
      "sense_id": "14024",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs."
    },
    {
      "sense_id": "14024",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14024",
      "level": 3,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [],
      "notes": "A's distractor 'fatuous' (foolish/silly) plausibly also fits 'laughing about the ___ costumes.'"
    },
    {
      "sense_id": "14024",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both packs' cloze/word_family items are correct and natural."
    },
    {
      "sense_id": "14024",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "14033",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets are genuine audio-confusable minimal pairs."
    },
    {
      "sense_id": "14033",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14033",
      "level": 3,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "broken rendering - blank glued to next word"
      ],
      "major_defects_reference": [],
      "notes": "Both of A's items are missing the space after the blank ('___child', '___wooden'), which would render as the glued non-words 'smallchild'/'smallwooden.'"
    },
    {
      "sense_id": "14033",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both packs' items are correct; B additionally tests the comparative 'smaller' well."
    },
    {
      "sense_id": "14033",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination sets are correct and pragmatically sound."
    },
    {
      "sense_id": "14033",
      "level": 9,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "incomplete/broken item"
      ],
      "major_defects_reference": [],
      "notes": "A's second jumbled_sentence item is missing its chunks/shuffled_chunks/correct_ordering data entirely (only the raw sentence is shown)."
    },
    {
      "sense_id": "14040",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14040",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both cloze_typed items correct; symmetric minor over-lenient accepted-form lists on both sides."
    },
    {
      "sense_id": "14040",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A's reconstruction places 'constantly' after the verb ('is evolving constantly') rather than before it as in the quoted original; still natural English, not a major defect."
    },
    {
      "sense_id": "14090",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14090",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both cloze_typed items correct and natural."
    },
    {
      "sense_id": "14090",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Chunk reconstructions correct on both sides."
    },
    {
      "sense_id": "14100",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets correct, no also-correct distractors."
    },
    {
      "sense_id": "14100",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze items correct on both sides; minor borderline near-synonym distractors (hoist/elevate/arrive) not clearly also-correct."
    },
    {
      "sense_id": "14100",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both packs use disciplined single-form accepted answers matching the required grammar exactly; well designed on both sides."
    },
    {
      "sense_id": "14100",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination sets are correct and pragmatically sound."
    },
    {
      "sense_id": "14100",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both jumbled_sentence pairs use 'ascend' naturally and correctly; chunk reconstruction is correct on both sides."
    },
    {
      "sense_id": "14189",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both L1 sets use real, audio-confusable multisyllabic rhymes; no pitch-accent-only issue (English, not tonal)."
    },
    {
      "sense_id": "14189",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options are clearly distinct on both sides, no also-correct risk."
    },
    {
      "sense_id": "14189",
      "level": 3,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor risk"
      ],
      "major_defects_reference": [],
      "notes": "B's distractor 'ecologically advanced agricultural operations' is a plausible fit for the sentence, risking a second defensible answer; A's distractors (financially/geographically/emotionally) are safely implausible."
    },
    {
      "sense_id": "14189",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze/word-family items are correct and naturally anchored on both sides; B has fewer items but that's not a rubric defect."
    },
    {
      "sense_id": "14189",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination sets are unambiguous; both antonym picks (manually/primitively vs traditionally/manually) are the sole defensible antonym."
    },
    {
      "sense_id": "14189",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences are natural and correctly reconstructed."
    },
    {
      "sense_id": "14390",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition distractors are distinct on both sides."
    },
    {
      "sense_id": "14390",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both sides use plausible-but-wrong distractors with no also-correct risk."
    },
    {
      "sense_id": "14390",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze sentences correct and natural on both sides; B omits a word_family item but that is a coverage gap, not a rubric defect."
    },
    {
      "sense_id": "14390",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All semantic_discrimination items unambiguous on both sides; A additionally includes a second item and a synonym_antonym_match B lacks, but content shown is equally correct."
    },
    {
      "sense_id": "14390",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences natural and correctly reconstructed."
    },
    {
      "sense_id": "14473",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "14473",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "also-correct distractor risk"
      ],
      "notes": "A's 'Secret information can leak out at times/in no time' distractors both form coherent alternate readings of the sentence with different but valid meanings; B's distractors for the same slot are cleanly wrong."
    },
    {
      "sense_id": "14473",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both sides' cloze_typed sentences are correct and natural single-answer items."
    },
    {
      "sense_id": "14473",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All semantic_discrimination items correctly labeled on both sides; A also includes synonym_antonym_match items B lacks, but shown content is equally sound."
    },
    {
      "sense_id": "14473",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences natural and correctly reconstructed."
    },
    {
      "sense_id": "15150",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both option sets are real, phonetically close words to 'polychronic'; good audio-confusable design on both sides."
    },
    {
      "sense_id": "15150",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "15150",
      "level": 3,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B offers two well-formed items including a strong contrastive sentence with 'monochronic' as the actual antonym distractor; A has only one item. No correctness defects on A's single item."
    },
    {
      "sense_id": "15150",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze/word-family items correct and natural on both sides; A includes word_family items B lacks, but that's coverage not correctness."
    },
    {
      "sense_id": "15150",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All semantic_discrimination items correctly labeled and unambiguous on both sides."
    },
    {
      "sense_id": "15150",
      "level": 9,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "malformed jumbled_sentence chunking"
      ],
      "major_defects_reference": [],
      "notes": "A's variant A chunk 'Are feeling' is not a valid contiguous span of the original sentence; concatenating the stated chunks in correct_ordering yields 'Are feeling you polychronic today...' which is ungrammatical and does not reconstruct the original. B's items reconstruct correctly."
    },
    {
      "sense_id": "15216",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both option sets are real, close phonetic confusables to 'monochronic'."
    },
    {
      "sense_id": "15216",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "15216",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B provides two well-formed items vs A's one; no correctness issues on A's single item, just less coverage."
    },
    {
      "sense_id": "15216",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze_typed items correct and natural on both sides; both accept a noun form (monochronicity) in an adjective slot equally, so not a distinguishing issue."
    },
    {
      "sense_id": "15216",
      "level": 6,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A includes a synonym_antonym_match item (clean, unambiguous antonym 'polychronic') that B lacks entirely at this level; all shown content is otherwise equally correct."
    },
    {
      "sense_id": "15216",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences correctly reconstructed and natural on both sides."
    },
    {
      "sense_id": "16031",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "16031",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B provides a cloze_typed plus word_family pair (2 items); A has only one cloze_typed item. No correctness issues on either."
    },
    {
      "sense_id": "16031",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "malformed jumbled_sentence chunking"
      ],
      "notes": "B's chunks ('will waterlog','quickly','it') concatenate in the stated order to 'will waterlog quickly it', which does not match the original sentence's 'will quickly waterlog it' -- a chunk mis-segmentation bug. A's item reconstructs correctly."
    },
    {
      "sense_id": "16181",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides (word/pronunciation field mismatch 'better'/'well' is identical on both sides, not a distinguishing issue)."
    },
    {
      "sense_id": "16181",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A provides two correctly-reconstructed jumbled sentences; B provides only one. No correctness defects on either."
    },
    {
      "sense_id": "19458",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "19458",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All cloze items correct with plausible-but-wrong distractors on both sides."
    },
    {
      "sense_id": "19458",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Cloze_typed sentences correct and natural on both sides."
    },
    {
      "sense_id": "19458",
      "level": 6,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B additionally includes a clean synonym_antonym_match item ('consequently' as antonym) that A lacks; all semantic_discrimination items are correctly labeled on both sides."
    },
    {
      "sense_id": "19458",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences correctly reconstructed and natural on both sides."
    },
    {
      "sense_id": "19480",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "19480",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B includes a word_family item that A lacks; all cloze_typed sentences correct and natural on both sides."
    },
    {
      "sense_id": "19480",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All semantic_discrimination and synonym_antonym_match items correctly labeled and unambiguous on both sides."
    },
    {
      "sense_id": "19480",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences correctly reconstructed; one chunk boundary in B splits a compound noun awkwardly but still reconstructs correctly."
    },
    {
      "sense_id": "19521",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both sides use the identical set of four candidate words, just reordered; no substantive difference."
    },
    {
      "sense_id": "19521",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "19521",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All items correct; A's numeric-neighbor distractors (twentieth/eighteenth) are marginally more plausible than B's second item's distractors (loudest/wooden/asleep), but not a major defect."
    },
    {
      "sense_id": "19521",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both sides provide a full cloze_typed + word_family set; all correct and natural."
    },
    {
      "sense_id": "19521",
      "level": 6,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "compound-word/target-word anchoring"
      ],
      "notes": "B's true-usage example 'Chapter nineteen is usually considered the most exciting part of the book' never actually contains the target word 'nineteenth', undermining the exercise's anchoring; A's true/false examples all correctly contain 'nineteenth'."
    },
    {
      "sense_id": "19521",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "malformed jumbled_sentence chunking",
        "compound-word/target-word anchoring"
      ],
      "notes": "B reuses the 'Chapter nineteen...' sentence which lacks the target word 'nineteenth', and its chunks ('is considered','usually') concatenate to 'is considered usually' rather than the original 'is usually considered' -- a segmentation bug. A's items are clean."
    },
    {
      "sense_id": "40142",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both option sets are solid genuine near-homophones of 'Great Wall of China'."
    },
    {
      "sense_id": "40142",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "40142",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All cloze items correct; distractors plausible on both sides, no also-correct risk."
    },
    {
      "sense_id": "40142",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All cloze_typed sentences correct and natural."
    },
    {
      "sense_id": "40142",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All semantic_discrimination items correctly labeled and unambiguous on both sides."
    },
    {
      "sense_id": "40142",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both spot_incorrect_sentence sets correctly flag a single genuine grammar error (missing article / subject-verb agreement / wrong article) with no ambiguity."
    },
    {
      "sense_id": "40142",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All jumbled sentences correctly reconstructed and natural."
    },
    {
      "sense_id": "40248",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both option sets are genuine homophone/near-homophone confusables for 'Peace of Westphalia'."
    },
    {
      "sense_id": "40248",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definition options distinct on both sides."
    },
    {
      "sense_id": "40248",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "weak/implausible distractors (random noise)"
      ],
      "notes": "A's single item uses distractors ('weather report','birthday party','class schedule') totally unrelated to a history-lesson context; B provides two items, one with genuinely plausible historical-term distractors (armistice, peace deal, Treaty of Paris)."
    },
    {
      "sense_id": "40248",
      "level": 4,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A provides two correct, natural cloze_typed items; B provides only one. No correctness issues on either."
    },
    {
      "sense_id": "40248",
      "level": 6,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A provides two well-formed semantic_discrimination items; B provides only one. All shown items are correctly labeled and unambiguous on both sides."
    },
    {
      "sense_id": "40248",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both sides reconstruct correctly; B has one extra item with a minor stray-space tokenization artifact ('other 's independence') that does not affect the ordering task."
    }
  ]
}
```

## 3. Non-inferiority thresholds used
```json
{
  "major_defect_margin_pp": 2.0,
  "pairwise_loss_margin_pp": 10.0,
  "coverage_min_pct": 95.0,
  "invalid_asset_margin_pp": 3.0
}
```