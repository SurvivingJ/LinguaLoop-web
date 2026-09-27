# Exercise-gen quality score -- ja

- Candidate: `data/eval/runs/phase1_ja`
- Reference: `data/eval/runs/baseline_ja` (run_dir)

## Decision: FAIL

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=16.05, reference_pct=16.05, margin_pp=2.0, source=pairwise |
| (b) pairwise loss - win <= margin | PASS | loss_minus_win_pp=0.0, margin_pp=10.0 |
| (c) coverage >= threshold | FAIL | coverage_pct=85.61, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 12,
  "expected_pairs_total": 132,
  "present_pairs_total": 113,
  "coverage_pct": 85.60606060606061,
  "missing_levels_count": 6,
  "missing_levels": [
    1,
    2,
    3,
    4,
    6,
    7
  ],
  "per_sense_missing": {
    "34998": [
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "35001": [
      [
        4,
        "particle_selection"
      ]
    ],
    "35009": [
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
        7,
        "spot_incorrect_sentence"
      ]
    ],
    "35017": [
      [
        6,
        "semantic_discrimination"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "35111": [
      [
        1,
        "reading_to_kanji"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "35147": [
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "35293": [
      [
        3,
        "cloze_completion"
      ]
    ],
    "35341": [
      [
        1,
        "phonetic_recognition"
      ],
      [
        6,
        "synonym_antonym_match"
      ]
    ],
    "35615": [
      [
        6,
        "semantic_discrimination"
      ]
    ],
    "39187": [
      [
        3,
        "cloze_completion"
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

### Reference metrics
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

## 2. Blind pairwise review

```json
{
  "total_pairs_in_key": 81,
  "total_judged": 81,
  "unmatched_verdicts": [],
  "missing_verdicts": [],
  "candidate_wins": 14,
  "reference_wins": 14,
  "ties": 53,
  "win_rate_pct": 17.28,
  "loss_rate_pct": 17.28,
  "tie_rate_pct": 65.43,
  "major_defect_rate_candidate": 16.05,
  "major_defect_rate_reference": 16.05,
  "per_sense": [
    {
      "sense_id": "34998",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both sides equivalent quality, no defects found."
    },
    {
      "sense_id": "34998",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Definitions and distractors fine on both sides."
    },
    {
      "sense_id": "34998",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both cloze sentences natural with single defensible answer."
    },
    {
      "sense_id": "34998",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correct and natural; B has one fewer item shown (cosmetic)."
    },
    {
      "sense_id": "34998",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic-discrimination sets well-formed; A has one extra item type (cosmetic)."
    },
    {
      "sense_id": "34998",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "compound-word anchoring"
      ],
      "notes": "A's chunk 'ichi-ni' fuses the target word with the adjacent number, breaking anchoring."
    },
    {
      "sense_id": "35001",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both phonetic distractor sets are legitimate one-mora-different real words."
    },
    {
      "sense_id": "35001",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A's cross-language distractor set is oddly fanciful in one entry but not misleading."
    },
    {
      "sense_id": "35001",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [
        "also-correct distractor"
      ],
      "notes": "Both accept counters/derived words (dai/ko or dai/kikaishiki) that don't grammatically fit the noun slot, equally."
    },
    {
      "sense_id": "35001",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both spot-the-error sets use correct, well-explained grammar points."
    },
    {
      "sense_id": "35001",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both provide one fully rendered chunk set and one stub per pack; rendered ones are correctly anchored."
    },
    {
      "sense_id": "35017",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both phonetic distractor sets are valid one-mora-different real words."
    },
    {
      "sense_id": "35017",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Distractor definitions unrelated and non-ambiguous on both sides."
    },
    {
      "sense_id": "35017",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both natural; B shows only one item vs A's two (cosmetic)."
    },
    {
      "sense_id": "35017",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor",
        "compound-word anchoring"
      ],
      "major_defects_reference": [
        "also-correct distractor"
      ],
      "notes": "B's morphology_slot explanation references an unrelated pattern (tekita) that does not match the shown sentence."
    },
    {
      "sense_id": "35017",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both spot-the-error items grammatically accurate and natural."
    },
    {
      "sense_id": "35017",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both jumbled-sentence sets correctly ordered; minor chunk-boundary style differences only."
    },
    {
      "sense_id": "35111",
      "level": 1,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A's distractor explanation misstates the reading of 'horu' (claims yo->e instead of yo->ho); A also lacks a reading_to_kanji item."
    },
    {
      "sense_id": "35111",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Distractor definitions unrelated and unambiguous on both sides."
    },
    {
      "sense_id": "35111",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [],
      "notes": "B's two morphology_slot items give 'yori'/'yotte' as correct answers that contradict their own sentence templates (one even omits the actually-correct form from the options)."
    },
    {
      "sense_id": "35111",
      "level": 6,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B marks a standard idiomatic construction ('ni yoreba') as incorrect on shaky grounds and includes one word-salad distractor sentence."
    },
    {
      "sense_id": "35111",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correct; A's sentences are more ornate/literary, B's simpler and more natural, roughly offsetting."
    },
    {
      "sense_id": "35111",
      "level": 9,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B's sentences are unnecessarily complex/jargon-heavy for the exercise, no outright errors though."
    },
    {
      "sense_id": "35127",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both phonetic distractor sets legitimate one-mora-different real words."
    },
    {
      "sense_id": "35127",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both unambiguous; B's English homophone-based distractor (naku/naku) is a nice touch but not required for parity."
    },
    {
      "sense_id": "35127",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both natural; B shows only one item vs A's two (cosmetic)."
    },
    {
      "sense_id": "35127",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [
        "also-correct distractor"
      ],
      "notes": "Both packs' second morphology_slot item has no blank marker (identical to original_sentence) with an explanation mismatched to the content -- same bug on both sides."
    },
    {
      "sense_id": "35127",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic-discrimination and antonym items well-formed and correct."
    },
    {
      "sense_id": "35127",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correct; B shows only one variant vs A's two (cosmetic)."
    },
    {
      "sense_id": "35127",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both jumbled-sentence sets correctly ordered and anchored."
    },
    {
      "sense_id": "35147",
      "level": 1,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor",
        "also-correct distractor"
      ],
      "major_defects_reference": [],
      "notes": "A's kanji_to_reading and reading_to_kanji both mislabel 'ikimasu' as reading 'iku', and mark the real match ('iku') as a mere homophone distractor -- would mis-grade learners."
    },
    {
      "sense_id": "35147",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Distractor definitions unrelated and unambiguous on both sides."
    },
    {
      "sense_id": "35147",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [
        "also-correct distractor"
      ],
      "notes": "B's morphology_slot item justifies its answer by referencing 'kinou' (yesterday), which appears nowhere in the shown sentence -- a fabricated rationale with a debatable single answer."
    },
    {
      "sense_id": "35147",
      "level": 6,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A shows only one clean item; B offers three well-formed items (antonym x2, semantic-discrimination) with no errors, better coverage."
    },
    {
      "sense_id": "35147",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both spot-the-error items accurate and natural."
    },
    {
      "sense_id": "35147",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correctly ordered; A's target_word label ('ikenai') doesn't match the actual text (cosmetic metadata slip)."
    },
    {
      "sense_id": "35227",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Distractor definitions unrelated and unambiguous on both sides."
    },
    {
      "sense_id": "35227",
      "level": 3,
      "outcome": "tie",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [
        "also-correct distractor"
      ],
      "notes": "Both packs share one item with random unrelated-object distractors (eraser/spoon/typhoon) and an explanation mentioning 'manabu' that doesn't appear in the sentence."
    },
    {
      "sense_id": "35227",
      "level": 4,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correct, natural, with plausible accepted-answer variants."
    },
    {
      "sense_id": "35227",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic-discrimination and antonym sets well-formed and accurate."
    },
    {
      "sense_id": "35227",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both spot-the-error items accurate and natural."
    },
    {
      "sense_id": "35227",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both jumbled-sentence sets correctly ordered and anchored."
    },
    {
      "sense_id": "35293",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Items are identical between packs."
    },
    {
      "sense_id": "35293",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Distractor definitions unrelated and unambiguous on both sides."
    },
    {
      "sense_id": "35293",
      "level": 7,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B's second item tests an unrelated location-particle error rather than a mistake involving the target adverb itself."
    },
    {
      "sense_id": "35311",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both phonetic distractor sets legitimate one-mora-different real words (B's syllable_count metadata is off but not learner-facing)."
    },
    {
      "sense_id": "35311",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Distractor definitions unrelated and unambiguous on both sides."
    },
    {
      "sense_id": "35311",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "compound-word anchoring"
      ],
      "notes": "A's only item tests 'kanou' solely inside the compound 'kaiketsu-kanou' (resolvable); B tests it as a standalone predicate."
    },
    {
      "sense_id": "35311",
      "level": 4,
      "outcome": "candidate_win",
      "major_defects_candidate": [
        "also-correct distractor"
      ],
      "major_defects_reference": [
        "compound-word anchoring",
        "also-correct distractor"
      ],
      "notes": "B tests 'kanou' inside the compound 'shukka-kanou' and its morphology_slot answer ('kanou-na') duplicates the 'na' already present in the template, producing a doubled-na error."
    },
    {
      "sense_id": "35311",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic-discrimination and antonym sets accurate and well-formed."
    },
    {
      "sense_id": "35311",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correctly flag one grammatical error in 可能 usage; equally solid."
    },
    {
      "sense_id": "35311",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both jumbled-sentence pairs use 可能 correctly and reconstruct cleanly."
    },
    {
      "sense_id": "35331",
      "level": 1,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "A's phonetic_recognition distractors include two homophones (御国/お国, both おくに), weakening the listening contrast versus B's three distinct one-mora variants."
    },
    {
      "sense_id": "35331",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition_match sets are sound; nl.en blocks in both contain stray non-Japanese filler options but none are misleading."
    },
    {
      "sense_id": "35331",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "mismatched explanation text (both A cloze explanations describe a different example sentence than the one shown)"
      ],
      "notes": "A's explanations for both cloze items reference unrelated sentences, which would confuse a learner checking their reasoning."
    },
    {
      "sense_id": "35331",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both provide clean single-error semantic_discrimination sets; A offers one extra variant but no quality gap."
    },
    {
      "sense_id": "35331",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correctly flag one ungrammatical sentence each; A's stated rule about 特には is slightly overgeneralized but the item itself is unambiguous."
    },
    {
      "sense_id": "35341",
      "level": 1,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B omits the phonetic_recognition (L1) item entirely; A's version has three well-differentiated one-mora distractors."
    },
    {
      "sense_id": "35341",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets are clean; nl.en blocks in both contain isolated foreign-language filler options but not misleading."
    },
    {
      "sense_id": "35341",
      "level": 3,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "also-correct distractor (必要 fits 信頼は友達に___なものです as well as 不可欠)",
        "mismatched explanation text referencing a different sentence"
      ],
      "major_defects_reference": [],
      "notes": "A's second cloze variant has a near-synonym distractor that is equally defensible and an explanation that doesn't match the shown sentence."
    },
    {
      "sense_id": "35341",
      "level": 4,
      "outcome": "candidate_win",
      "major_defects_candidate": [
        "cloze_typed accepted-answer list includes forms that are ungrammatical once spliced into this blank's context (generic list not customized per sentence)"
      ],
      "major_defects_reference": [
        "cloze_typed accepted-answer list includes forms that are ungrammatical once spliced into this blank's context (generic list not customized per sentence)",
        "morphology_slot variant B uses unrelated words (重要/必要) as distractors, both of which are also contextually plausible in 集中力が___だと思う"
      ],
      "notes": "B's morphology_slot items stay within clean same-word inflections; A's variant B substitutes near-synonyms that also fit."
    },
    {
      "sense_id": "35341",
      "level": 6,
      "outcome": "reference_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both semantic_discrimination items are clean; B additionally includes a correct antonym-match exercise (不可欠 / 不要)."
    },
    {
      "sense_id": "35341",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "All four spot_incorrect_sentence items correctly flag one error each; B's second item tests sentence-completeness rather than 不可欠-specific grammar, a minor anchoring softness."
    },
    {
      "sense_id": "35341",
      "level": 9,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both jumbled-sentence pairs are grammatical and correctly anchored; B's single-mora chunk 「に」 is an odd but not incorrect split."
    },
    {
      "sense_id": "35419",
      "level": 1,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B's phonetic_recognition distractor 矢盾 is of doubtful lexical validity versus A's three unambiguous real-word distractors."
    },
    {
      "sense_id": "35419",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets are clean aside from the shared foreign-language nl.en artifact."
    },
    {
      "sense_id": "35419",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both use mild suddenly-vs-eventually distractors that are not truly also-correct given the archaic register; B offers two clean items versus A's one."
    },
    {
      "sense_id": "35419",
      "level": 6,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correctly single out one error among particle, conjugation, and word-order mistakes."
    },
    {
      "sense_id": "35419",
      "level": 7,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B repeats the same 覞てに extraneous-particle error across both of its items, reducing error-type diversity versus A's two distinct error types."
    },
    {
      "sense_id": "35615",
      "level": 1,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "B's phonetic_recognition distractor 複舷 is of doubtful lexical validity versus A's three clearly attested real-word distractors."
    },
    {
      "sense_id": "35615",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets are sound; B's nl.en block has more severe language-mixing than A's but neither is misleading."
    },
    {
      "sense_id": "35615",
      "level": 3,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "cloze blank/answer mismatch: template '___て' plus correct_answer '複雑' yields ungrammatical '複雑て' (original sentence requires 複雑すぎて)"
      ],
      "notes": "B's second cloze item's answer does not actually complete the sentence grammatically; A's single item is clean."
    },
    {
      "sense_id": "35615",
      "level": 4,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "cloze_typed accepted-answer lists include forms ungrammatical in context (generic list bug)",
        "morphology_slot variant B correct_answer '複雑に' is inconsistent with the template (already contains 'に' after the blank, producing a doubled にに / mismatch with original_sentence)"
      ],
      "major_defects_reference": [],
      "notes": "B's items use precise single accepted answers matching each blank's context; A repeats the systemic generic-list bug and has an internally inconsistent morphology_slot answer."
    },
    {
      "sense_id": "35615",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correctly identify one conjugation/particle error each; both reuse the same underlying test sentence for one item."
    },
    {
      "sense_id": "35615",
      "level": 9,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "jumbled_sentence variant A is missing its chunks/shuffled_chunks data (incomplete, non-functional exercise)"
      ],
      "notes": "A's variant A only has an original_sentence preview with no reconstruction data; B's two items are both complete."
    },
    {
      "sense_id": "39187",
      "level": 1,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both phonetic_recognition sets include a pair of same-reading distractors (A: 水カビ/ミズカビ; B: 水換え/水替え), an equivalent weakness on each side."
    },
    {
      "sense_id": "39187",
      "level": 2,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both definition sets are clean aside from the shared foreign-language nl.en artifact, more severe but not misleading in B."
    },
    {
      "sense_id": "39187",
      "level": 4,
      "outcome": "candidate_win",
      "major_defects_candidate": [],
      "major_defects_reference": [
        "cloze_typed accepted-answer list includes forms ungrammatical in this blank's context (e.g. '自らの'+'の価値' doubles の) — same systemic bug seen elsewhere"
      ],
      "notes": "B uses a single precise accepted answer per item matching each blank's context; A carries the recurring generic accepted-list bug."
    },
    {
      "sense_id": "39187",
      "level": 6,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "explanation is internally self-contradictory (claims 自ら is the object/目的語 but then gives a corrected form marking it with subject particle が; also gives two different 'correct' forms — with and without が — for the same construction)"
      ],
      "major_defects_reference": [],
      "notes": "A's semantic_discrimination item plus valid antonym-match exercise are both clean and consistent."
    },
    {
      "sense_id": "39187",
      "level": 7,
      "outcome": "tie",
      "major_defects_candidate": [],
      "major_defects_reference": [],
      "notes": "Both correctly identify one particle/usage error each across two items, with sound explanations."
    },
    {
      "sense_id": "39187",
      "level": 9,
      "outcome": "reference_win",
      "major_defects_candidate": [
        "jumbled_sentence variant B is missing its chunks/shuffled_chunks data (incomplete, non-functional exercise)"
      ],
      "major_defects_reference": [],
      "notes": "B's variant B only shows an original_sentence preview with no reconstruction data; A's two items are both complete."
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