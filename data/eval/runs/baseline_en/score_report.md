# Exercise-gen quality score -- en

- Candidate: `data/eval/runs/baseline_en`
- Reference: `data/eval/runs/baseline_en` (run_dir)

## Decision: PASS

| Criterion | Status | Detail |
|---|---|---|
| (a) major-defect rate <= reference + margin | PASS | candidate_pct=0.0, reference_pct=0.0, margin_pp=2.0, source=judge_reject_rate_fallback |
| (b) pairwise loss - win <= margin | SKIPPED | reason=no --pairwise-results provided; run scripts/merge_pairwise_verdicts.py first |
| (c) coverage >= threshold | PASS | coverage_pct=100.0, min_pct=95.0 |
| (d) invalid-asset rate <= reference + margin | PASS | candidate_pct=30.43, reference_pct=30.43, margin_pp=3.0 |

## 1. Automatic metrics

### Coverage (candidate vs reference)
```json
{
  "senses_compared": 30,
  "senses_missing_from_candidate": [],
  "reference_level_type_pairs": 9,
  "expected_pairs_total": 169,
  "present_pairs_total": 169,
  "coverage_pct": 100.0,
  "missing_levels_count": 0,
  "missing_levels": [],
  "per_sense_missing": {}
}
```

### Candidate metrics
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