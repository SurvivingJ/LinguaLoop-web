# DT Grading Gold Calibration Sets (TASK-621)

Gold calibration sets for the dual-translation grading eval harness (TASK-622). These are the
**measuring stick** for every later change in the Evidence-First Grading (DT v2) work
(`wiki/algorithms/evidence-first-grading.tech.md`, §10). Every label here is human-adjudicated —
the gold set is never model-graded.

## Files

| File | L2 | Source passages | Composition | Distinct v5 subtypes |
|------|----|----|----|----|
| `en.json` | English | `dt_passage` ids 9–18 (Arduino robot-arm, age tier 3) | 10 clean / 15 single / 5 multi | 13 |
| `zh.json` | Chinese | `dt_passage` ids 1–8 (favorite T-shirt, age tier 6) | 10 clean / 15 single / 5 multi | 12 |
| `ja.json` | Japanese | `dt_passage` ids 19–28 (robot-arm build, age tier 3) | 10 clean / 15 single / 5 multi | 11 |

All passages are real `dt_passage.l2_text` rows from the live project (`kpfqrjtfxmujzolwsvdq`),
pulled 2026-07-05. Each item's `reference` is the **full** passage text verbatim (what production
actually grades); reproductions are faithful copies perturbed at the seeded spans.

## Item schema

```jsonc
{
  "id": "ja_seed_01",              // stable item id
  "kind": "clean | single | multi",
  "source_passage_id": 23,          // dt_passage.id
  "note": "provenance / rationale",
  "reference": "<full l2_text>",
  "reproduction": "<perturbed copy>",
  "expected_errors": [
    {
      "span_repro": [31, 37],       // char offsets into reproduction
      "span_ref":   [31, 37],       // char offsets into reference
      "subtype": "particle",        // CURRENT taxonomy v4 name (dt_taxonomy_version v4)
      "subtype_v5_target": "particle_wa_ga",  // v5 split target (re-tag lands in TASK-626)
      "severity_v1": "global | local",        // OPTIONAL residue: baseline (pre-TASK-625)
                                              //   vocabulary. Nothing reads it (TASK-641);
                                              //   emitted only when the spec supplies it.
      "severity_v2": "minor | major | critical",  // MQM triad (post-TASK-625)
      "learner_form": "部品はセット",
      "corrected_form": "部品がセット"
    }
  ],
  "expected_bands": { "accuracy":3, "understandability":4, "fidelity":4, "range":4, "naturalness":4 }
}
```

Fields beyond the TASK-621 minimum (`id`, `kind`, `note`, `subtype_v5_target`) are additive and
let the harness bucket items and let TASK-626 re-tag mechanically. `severity` is stored in **both**
vocabularies so baseline (global/local) and post-TASK-625 (triad) harness runs both work.

## Provenance (per-item)

Every item was produced the same way, so provenance is uniform rather than per-row:

- **Perturbations: LLM-drafted** (by the Claude session running TASK-621), then **fully
  user-adjudicated** — every subtype, severity, span, and band signed off by the developer.
- **Spans: scripted.** Computed by `scripts/dt_gold_seed_helper.py` from declarative find/replace
  edit specs (never hand-counted). The helper asserts, for every seeded error,
  `reproduction[span_repro] == learner_form` and `reference[span_ref] == corrected_form`.
- **Multi-error items: LLM-drafted + hand-adjudicated** naturalistic combinations (2–4 errors).
- **Clean items:** faithful reproductions differing only by acceptable variation (synonym,
  contraction, kana/kanji or 得/的 variant, optional comma). Expected: zero errors, all bands 4.
  They measure the grader's false-positive rate.

### Expected-band derivation

Bands are **not hand-set**; they are computed by `derive_bands()` from the seeded errors using the
tech-spec §4 formula (severity weights minor/major/critical = 1/5/25; accuracy/fidelity thresholds
t4/t3/t2 = 1/6/15; understandability = 2/6/25; understandability weights 0/2/25). `naturalness` and
`range` are model-judged in production, so they are adjudicated inputs (default 4; lowered by hand
for naturalness-type errors, e.g. topic_comment/collocation/cohesion → naturalness 3).

Those constants are **not** `derive_bands()`'s only source (TASK-641). The same numbers are destined
for `dt_rubric_version.config` as `severity_weights` / `understandability_weights` /
`band_thresholds` (TASK-627 rubric v5), so `derive_bands()` requires an explicit source: either
`rubric_cfg=<active config>` or `offline=True` for the pinned fallback
(`dt_gold_seed_helper.OFFLINE_SCORING_CONFIG` — the values these fixtures were frozen under).
Defaulting silently to the constants is what would let these `expected_bands` and the live grader
drift apart unnoticed. `tests/test_dual_translation_gold_seed_helper.py` fails if the seeded v5
values ever disagree with the fallback — **when it fires, re-derive the fixtures; do not edit the
constants to match.**

## Normalization survival (why these seeds are valid)

Tier 0 (`services/dual_translation/tier0.py`) awards full marks and never calls the grader when a
reproduction differs from the reference only by a normalization-class diff (case, punctuation,
whitespace, full/half width, and — for JA — katakana↔hiragana). The helper verifies every seeded
error is **not** normalization-class (normalized `learner_form` ≠ normalized `corrected_form`) and
that the full reproduction registers a real diff (`grade_dictation` accuracy < 1.0).

**Grader caveat surfaced while building EN:** `grade_dictation._fuzzy_equal` treats words ≥4 chars
within Levenshtein distance 1 as equal, so a lone single-suffix morphology error (make→made,
tells→tell, motors→motor) collapses to accuracy 1.0 and is swallowed at Tier 0. EN
tense/agreement/plural seeds therefore use short-word / large-distance agreement forms that
register (is→was, is→are, these→this). This Tier-0 leniency is itself a target of TASK-623.

## Adjudication record

| L2 | Adjudicated by | Date | Outcome |
|----|----|----|----|
| JA | developer (jamesccmcb) | 2026-07-05 | Approved with 2 changes: dropped `counter_classifier` (no counters in source passages) → replaced with `tense_aspect_ja`; `script_choice` (製作→せいさく) ruled not-an-error for a beginner text → replaced with `verb_conjugation` (ら抜き言葉). und=1 on double-severity multi confirmed correct. |
| ZH | developer (jamesccmcb) | 2026-07-05 | Approved as presented. |
| EN | developer (jamesccmcb) | 2026-07-05 | Approved as presented, including the fuzzy-match handling for morphology seeds. |

## Regenerating

The declarative edit specs live in the session build drivers; the reusable builder/verifier is
`scripts/dt_gold_seed_helper.py` (`build_item`, `verify_item`, `derive_bands`). To re-tag to v5
subtype names in TASK-626, map each error's `subtype` → `subtype_v5_target` and re-run the
verifier. Do not edit the JSON spans by hand — regenerate so span integrity stays guaranteed.

## Coverage (seeded v5 subtypes)

- **EN (13):** article, preposition, tense_aspect, subject_verb_agreement, plural_number,
  pronoun_reference, phrasal_verb, omission, word_choice, word_order, register, collocation,
  cohesion_connective.
- **ZH (12):** classifier, aspect_marker, de_particles, ba_construction, resultative_complement,
  directional_complement, adverbial_order, topic_comment, omission, word_choice, word_order,
  register.
- **JA (11):** particle_wa_ga, particle_case, particle_other, keigo_register, verb_conjugation,
  tense_aspect_ja, topic_comment, omission, word_choice, word_order, register.
