# DT Grading Eval — v2 (EN)

- **Run date:** 2026-10-09
- **L2 / L1:** en / zh
- **Items graded:** 35 (clean 6 / single 26 / multi 3)
- **Grader:** v2 Detector/Verifier cascade (`grade_submission(framework_v2=True)`), slugs: —
- **Fixture set:** v6_silver
- **Taxonomy:** CANDIDATE v6 from `migrations/dt_taxonomy_v6_seed.sql` (pre-seeded into the config cache; live DB taxonomy not modified)
- **Tokens:** 0 in / 0 out — model calls: 0
- **Est. cost:** $0.0000 USD (model-arena pricing)

## Span detection (relaxed ≥50% overlap)

| precision | recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.000 | 0 | 0 | 35 |

## Classification + false positives

| metric | value |
|---|---|
| Subtype accuracy (matched pairs, vs v4) | n/a (0/0) |
| Severity exact (triad minor/major/critical) | n/a (n=0) |
| **Severity within-one (triad)** | n/a |
| **Clean-passage FP rate (items flagged)** | 0.000 (6 clean items) |
| Clean-passage mean spurious errors/item | 0.000 (0 total) |

## Per-dimension band agreement

| dimension | QWK | exact | adjacent | n |
|---|---|---|---|---|
| accuracy | n/a | n/a | n/a | 0 |
| understandability | n/a | n/a | n/a | 0 |
| fidelity | n/a | n/a | n/a | 0 |
| range | n/a | n/a | n/a | 0 |
| naturalness | n/a | n/a | n/a | 0 |
| **overall_band** | n/a | n/a | n/a | 0 |

## Taxonomy v6 metrics

| metric | value |
|---|---|
| meaning_inversion recall | 0.000 (0/8) |
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
  "n_items": 35,
  "kind_counts": {
    "clean": 6,
    "single": 26,
    "multi": 3
  },
  "span": {
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0,
    "tp": 0,
    "fp": 0,
    "fn": 35
  },
  "subtype_accuracy": {
    "correct": 0,
    "total": 0,
    "accuracy": NaN
  },
  "severity": {
    "exact": NaN,
    "within_one": NaN,
    "n": 0
  },
  "clean_fp": {
    "item_fp_rate": 0.0,
    "mean_errors": 0.0,
    "total_errors": 0,
    "n": 6
  },
  "bands": {
    "accuracy": {
      "qwk": NaN,
      "exact": NaN,
      "adjacent": NaN,
      "n": 0
    },
    "understandability": {
      "qwk": NaN,
      "exact": NaN,
      "adjacent": NaN,
      "n": 0
    },
    "fidelity": {
      "qwk": NaN,
      "exact": NaN,
      "adjacent": NaN,
      "n": 0
    },
    "range": {
      "qwk": NaN,
      "exact": NaN,
      "adjacent": NaN,
      "n": 0
    },
    "naturalness": {
      "qwk": NaN,
      "exact": NaN,
      "adjacent": NaN,
      "n": 0
    }
  },
  "overall": {
    "qwk": NaN,
    "exact": NaN,
    "adjacent": NaN,
    "n": 0
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
      "n_expected": 8,
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
