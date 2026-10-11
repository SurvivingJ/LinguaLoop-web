# DT Grading Eval — v2 (ZH)

- **Run date:** 2026-10-09
- **L2 / L1:** zh / en
- **Items graded:** 30 (clean 10 / single 15 / multi 5)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: qwen/qwen3.6-flash
- **Fixture set:** v6
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 5,143 in / 5,762 out — model calls: 2
- **Est. cost:** $0.0074 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 1.000 | 0.038 | 0.074 | 1 | 0 | 25 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | 1.000 (1/1) |
| Severity exact (triad minor/major/critical) | 1.000 (n=1) |
| **Severity within-one (triad)** | 1.000 |
| **Clean-passage FP rate (items flagged)** | 0.000 (10 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | 1.000 | 1.000 | 1.000 | 4 |
| understandability | 1.000 | 1.000 | 1.000 | 4 |
| fidelity | 1.000 | 1.000 | 1.000 | 4 |
| range | 1.000 | 1.000 | 1.000 | 2 |
| naturalness | 1.000 | 1.000 | 1.000 | 2 |
| **overall_band** | 1.000 | 1.000 | 1.000 | 4 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.000 (0/2) |
| meaning_inversion precision | n/a (0/0) |
| explanation_variant accuracy (word_choice TPs) | n/a (0/0; 0 with no predicted variant) |
| variant_basis distribution | default=0, model=0, same_lemma=0, shared_gloss=0 |
| exemplar-drop warnings (must be 0 for en/zh) | 0 |
| "no explanation template" lines | 0 |

### meaning_inversion confusion (span-matched pairs; rows = expected, cols = predicted)

| expected \ predicted | meaning_inversion | omission | word_choice | preposition | contradiction | other |
|---|---|---|---|---|---|---|
| meaning_inversion | 0 | 0 | 0 | 0 | 0 | 0 |
| omission | 0 | 0 | 0 | 0 | 0 | 0 |
| word_choice | 0 | 0 | 0 | 0 | 0 | 0 |
| preposition | 0 | 0 | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 | 0 | 0 |
| other | 0 | 0 | 0 | 0 | 0 | 0 |

## Raw metrics (JSON)

```json
{
  "n_items": 30,
  "kind_counts": {
    "clean": 10,
    "single": 15,
    "multi": 5
  },
  "span": {
    "precision": 1.0,
    "recall": 0.038461538461538464,
    "f1": 0.07407407407407407,
    "tp": 1,
    "fp": 0,
    "fn": 25
  },
  "subtype_accuracy": {
    "correct": 1,
    "total": 1,
    "accuracy": 1.0
  },
  "severity": {
    "exact": 1.0,
    "within_one": 1.0,
    "n": 1
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 10
  },
  "bands": {
    "accuracy": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 4
    },
    "understandability": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 4
    },
    "fidelity": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 4
    },
    "range": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 2
    },
    "naturalness": {
      "qwk": 1.0,
      "exact": 1.0,
      "adjacent": 1.0,
      "n": 2
    }
  },
  "overall": {
    "qwk": 1.0,
    "exact": 1.0,
    "adjacent": 1.0,
    "n": 4
  },
  "v6": {
    "mi_confusion": {
      "labels": [
        "meaning_inversion",
        "omission",
        "word_choice",
        "preposition",
        "contradiction",
        "other"
      ],
      "matrix": {
        "meaning_inversion": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "omission": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "word_choice": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "preposition": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "contradiction": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        },
        "other": {
          "meaning_inversion": 0,
          "omission": 0,
          "word_choice": 0,
          "preposition": 0,
          "contradiction": 0,
          "other": 0
        }
      }
    },
    "meaning_inversion": {
      "subtype": "meaning_inversion",
      "tp": 0,
      "n_expected": 2,
      "n_predicted": 0,
      "recall": 0.0,
      "precision": NaN
    },
    "explanation_variant": {
      "correct": 0,
      "total": 0,
      "pred_missing": 0,
      "accuracy": NaN,
      "variant_basis": {
        "default": 0,
        "model": 0,
        "same_lemma": 0,
        "shared_gloss": 0
      }
    }
  }
}
```
