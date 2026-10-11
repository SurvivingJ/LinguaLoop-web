---
title: "DT Taxonomy v6 Acceptance Gate (TASK-850, 2026-10-08)"
type: evaluation
status: complete
date: 2026-10-08
harness: scripts/run_dt_grading_eval.py (--framework-v2 --live --resume; --taxonomy-file + --fixture-set for the v6 arms)
metrics_module: services/dual_translation/eval_metrics.py
gold_sets: tests/fixtures/dt_gold (v5 control), tests/fixtures/dt_gold_v6 (v6 gold), tests/fixtures/dt_silver_v6 (v6 silver)
artifacts: data/eval/dt_v6_gate_2026-10-08/ (per-arm report .md, checkpoint .ckpt.jsonl, console .log, spend_monitor.log)
verdict: NO-GO
---

# DT Taxonomy v6 Acceptance Gate (TASK-850, 2026-10-08)

The paid gate that decides whether taxonomy v6 ([[decisions/ADR-031-dt-taxonomy-v6-merge]]) may go live
(TASK-853). Each L2 was graded three ways on the same day, with the same rubric and the same model routing,
so model drift since [[evaluations/dt-grading-v2-2026-07-19]] cannot pass for a taxonomy effect:

- **A, the v5 control.** Live taxonomy (v5) on the frozen v5 gold set. `DT_TAXONOMY_VERSION` was unset.
- **B, the v6 candidate.** v6 was loaded offline from `migrations/dt_taxonomy_v6_seed.sql` and graded on the v6
  gold set. The live DB was not touched.
- **C, v6 on silver.** The same v6 load on the v6 silver set. This arm is supplementary evidence only.

All arms used the v2 Detector/Verifier flow (`--framework-v2`) and the **live rubric (v6)**. There was no
`--rubric-file`. No migrations were applied, nothing was activated, and no live tables were written. The grader
path makes no DB writes; the only DB access was reads (language ids, passage tiers, and the sense lookups of
`resolve_variant`).

## Verdict: **NO-GO** (all three L2s fail at least one gate row)

| L2 | Failing rows |
|----|--------------|
| EN | subtype accuracy (.769 < .80, and < .825 = control − .05); overall-band QWK (.431 < .595 = control − .10) |
| ZH | span F1 (.826 < .848 = control − .05); subtype accuracy (.789 < .80, and < .814 = control − .05) |
| JA | subtype accuracy (.810 passes the .80 floor but is < .814 = control − .05, by one item) |

The thresholds are as written in TASK-850; none were loosened. On the v6-specific behaviour, v6 does what it was
built to do: meaning_inversion recall is ≥ .90 in every L2, all four 的/地/得 probes land on de_particle/minor, and
en/zh produced zero exemplar-drop and zero no-template warnings. The failures trace mostly to **gold labels that
contradict v6's own glosses** and to **a decode bug that predates v6** (see Findings). These need decisions before a
re-run. No production code was changed during the gate.

## Gate table (v6 gold vs same-day v5 control)

| L2 | span F1 v5 → v6 (min) | subtype acc v5 → v6 (min) | overall QWK v5 → v6 (min) | MI recall gold+silver (≥ .75) | clean FP v5 → v6 | en/zh warnings | Gate |
|----|----|----|----|----|----|----|----|
| EN | .923 → **.963** (.873) ✅ | .875 → **.769** (.825) ❌ | .695 → **.431** (.595) ❌ | **.900** (9/10) ✅ | .000 → .000 ✅ | 0 drop / 0 no-template ✅ | **NO-GO** |
| ZH | .898 → **.826** (.848) ❌ | .864 → **.789** (.814) ❌ | .535 → **.615** (.435) ✅ | **1.000** (7/7) ✅ | .100 → .100 ✅ | 0 drop / 0 no-template ✅ | **NO-GO** |
| JA | .880 → **.875** (.830) ✅ | .864 → **.810** (.814) ❌ | .643 → **.839** (.543) ✅ | **1.000** (6/6) ✅ | .000 → .000 ✅ | n/a (ja: 29 drops, see §4) | **NO-GO** |

Pooled meaning_inversion recall across all three L2s is 22/23 (.957). The task text says 21 labels; the fixtures
now carry 23: en 2+8, zh 2+5, ja 2+4.

"Clean FP" compares v6 gold with control, both on the same 10 clean passages per L2. On silver, en flagged 2 of its
6 clean items (.333). zh and ja silver were clean (0). Silver clean passages have no control arm.

## Per-dimension QWK (the harness's QWK function)

| L2 | arm | accuracy | understandability | fidelity | range | naturalness | **overall** | overall exact |
|----|-----|----------|-------------------|----------|-------|-------------|-------------|---------------|
| EN | A v5 | .828 | .627 | .561 | .000 | .037 | **.695** | .900 |
| EN | B v6 | .510 | .815 | .854 | .000 | .183 | **.431** | .871 |
| EN | C v6 silver | .571 | .895 | .901 | .428 | .008 | **.860** | .943 |
| ZH | A v5 | .683 | .695 | .794 | 1.000 | .092 | **.535** | .867 |
| ZH | B v6 | .561 | .936 | .865 | 1.000 | .099 | **.615** | .900 |
| ZH | C v6 silver | .612 | .799 | .875 | 1.000 | −.021 | **.718** | .912 |
| JA | A v5 | .149 | .701 | .475 | .000 | .099 | **.643** | .867 |
| JA | B v6 | .412 | .925 | .926 | .000 | .067 | **.839** | .933 |
| JA | C v6 silver | .636 | .520 | .537 | .651 | .050 | **.520** | .906 |

Under v6, understandability and fidelity rise in all three L2s. This is what `meaning_inversion`'s critical
severity should buy. Accuracy falls in en and zh. naturalness and range still carry no signal, as on 2026-07-19.
**EN overall QWK is fragile.** 27 of the 31 expected overall bands are 4, so the drop from .695 to .431 comes from
overall exact agreement moving .900 → .871. That is one more item off by one band (en_multi_01, en_multi_02 and
en_multi_03 each 4→3; en_multi_05 3→4). The ±.1 run-to-run noise documented on 2026-07-19 applies here, but the gate
is applied as written.

## Detection and classification detail

| L2 | arm | span P / R / F1 | TP/FP/FN | subtype acc | sev exact |
|----|-----|-----------------|----------|-------------|-----------|
| EN | A | .960 / .889 / .923 | 24/1/3 | .875 (21/24) | .500 |
| EN | B | 1.000 / .929 / .963 | 26/0/2 | .769 (20/26) | .462 |
| EN | C | .897 / 1.000 / .946 | 35/4/0 | .829 (29/35) | .657 |
| ZH | A | .957 / .846 / .898 | 22/1/4 | .864 (19/22) | .636 |
| ZH | B | .950 / .731 / .826 | 19/1/7 | .789 (15/19) | .789 |
| ZH | C | 1.000 / .758 / .862 | 25/0/8 | .800 (20/25) | .720 |
| JA | A | .957 / .815 / .880 | 22/1/5 | .864 (19/22) | .727 |
| JA | B | 1.000 / .778 / .875 | 21/0/6 | .810 (17/21) | .810 |
| JA | C | 1.000 / .862 / .926 | 25/0/4 | .680 (17/25) | .800 |

## v6-specific metrics

| L2 | arm | MI recall | MI precision | explanation_variant acc (word_choice TPs) | variant_basis | exemplar drops | no-template |
|----|-----|-----------|--------------|------------------------------------------|---------------|----------------|-------------|
| EN | B | 1.000 (2/2) | 1.000 | .500 (1/2) | model 5 | 0 | 0 |
| EN | C | .875 (7/8) | 1.000 | 1.000 (5/5) | model 10 | 0 | 0 |
| ZH | B | 1.000 (2/2) | 1.000 | 1.000 (1/1) | model 3 | 0 | 0 |
| ZH | C | 1.000 (5/5) | .833 (5/6) | .000 (0/1) | model 2 | 0 | 0 |
| JA | B | 1.000 (2/2) | 1.000 | .667 (2/3) | model 3, same_lemma 1 | 29 | 0 |
| JA | C | 1.000 (4/4) | .667 (4/6) | — (0) | — | 32 | 0 |

The control arms emit no variants, as designed. ja A logged one "no explanation template" line under v5, which is
not a gate row. Variant accuracy rests on n ≤ 5 per cell. As TASK-848 asked, `wrong_sense` accuracy is read as n=1:
`en_v6_ws_02` came back `wrong_word`, not `wrong_sense`.

**meaning_inversion behaviour.** There was one miss: `en_silver_25`, typed `word_choice/false_synonym`. There were
three false alarms: `zh_silver_09` (gold `word_choice/major`), `ja_silver_19` (gold `addition/minor`) and
`ja_silver_20` (gold `word_choice/major`). The by-effect rule therefore slightly over-fires in ja silver. None of
the MI-confusion columns (omission, word_choice, preposition, contradiction) absorbed an expected MI.

## Probes

| Probe | Expected | v6 result |
|-------|----------|-----------|
| `en_seed_15` | meaning_inversion | ✅ meaning_inversion/critical (the v5 control typed it preposition/critical) |
| `zh_seed_11` | de_particle/minor | ✅ de_particle/minor |
| `zh_multi_02` | de_particle/minor | ✅ de_particle/minor (the v5 control: de_particles/**major**) |
| `zh_silver_20` | de_particle/minor | ✅ de_particle/minor |
| `zh_silver_29` | de_particle/minor | ✅ de_particle/minor |
| `en_multi_03#0` key → important (variant_uncertain) | false_synonym? | Grader missed the span, so no variant at grade time. `resolve_variant` offline: no zh gloss for en words, so the model's call stands (`false_synonym`→`model`; none→`wrong_word`/`default`) |
| `zh_multi_02#1` 普通 → 简单 (variant_uncertain) | false_synonym? | Grader missed the span. `resolve_variant` offline, bare lemmas: both resolve, their en glosses share no exact term, so a model `false_synonym` is **downgraded to `wrong_word`** (basis `default`). With the phrase forms 普通的图案/简单的图案 the lemma lookup fails and the model's call stands |
| `ja_multi_04#1` 仕事 → 役割 (variant_uncertain) | false_synonym? | Grader typed it `collocation/major`, so no variant. `resolve_variant` offline: same as zh. Bare lemmas → `wrong_word`/`default`. Phrase form → model's call |

So for the two items that can be resolved (zh, ja), the deterministic resolver **refutes** `false_synonym`. Either
those gold labels should be `wrong_word`, or the exact-gloss-intersection rule is too strict for near-synonyms. That
is a labelling decision, not a gate defect.

## Findings: why it failed

1. **Gold labels contradict v6's own glosses (the largest cause).** The v6 fixtures (TASK-847 overlay) predate the
   TASK-839/840 string decisions, and in three places they disagree with the glosses the grader is now given:
   - **ja `keigo`.** All four ja keigo gold labels (`ja_seed_04` 必要だ→必要です, `ja_multi_03` 教え込む→教え込みます,
     `ja_silver_17`, `ja_silver_31`) are だ/です politeness-level errors. The v6 ja keigo gloss says outright that
     politeness level belongs to `register` (「です・ますなど丁寧さのレベル自体は『文体・語調』で扱う」). The grader
     said `register`, which is right by the taxonomy. Scored that way, ja B subtype would be 18/21 (.857) and would
     pass.
   - **zh `measure_word` and 个.** The v6 zh gloss says "通用量词'个'可以接受，不算错误", yet the zh gold marks
     一个→一件 (`zh_seed_01`, `zh_multi_01`), 一个→一只 (`zh_multi_03`) and 这个→这件 (`zh_silver_35`) as errors. All four
     were missed under v6, while the reverse case (一只→一个, `zh_silver_23`) was caught. One was detected and then lost to finding 2. The rest are consistent with the grader obeying
     the gloss.
   - **en `pronoun` split.** "move it → move them" (antecedent-number mismatch, `en_seed_10`, `en_multi_03#2`,
     `en_silver_13`) is gold `word_choice/wrong_word` in v6. The grader says `pronoun`. The v6 en pronoun gloss does
     not list antecedent number, so neither label is clearly wrong. Counting `pronoun` as correct would lift en B
     subtype to 22/26 (.846), which passes.
2. **A decode bug drops whole errors, on v5 and v6 alike (it predates v6).** `_decode_error`
   (`grader_cascade.py:865–870`) drops an error when any enum index is out of range. qwen sometimes copies the subtype
   index into `category` (`category: 8, subtype: 8`), and the error is then discarded with an "out-of-range enum
   index" WARNING. Counts: zh A 1, **zh B 2** (一个→一件, a missing 了), zh C 1; ja A 1, **ja B 3** (incl. だ→です)
   + 1 invalid-span; en 0. Recovering the two zh B drops would give zh B span F1 ≈ .875, which passes. `category`
   follows from the subtype, so a fallback is possible. That is a production-code change and needs its own task.
   The gate must then be re-run for zh and ja.
3. **ja Detector exemplar is dropped under v6.** There were 29 (B) and 32 (C) "dropping the ja Detector exemplar"
   warnings: the live rubric's ja exemplar is `particle_wa_ga`, which v6 does not resolve. The gate requires 0 only
   for en/zh, and the replacement exemplar is already proposed in ADR-031 (TASK-840 notes). It still means every ja
   v6 grade ran without a few-shot.
4. **Pre-existing confusions that v6 did not fix:** zh `complement`→`omission` (心情变→心情变好, the same in control),
   `topic_comment`→`word_order`/`omission` (zh and ja), and en `register`↔`word_choice` ("a sick way"). Severity exact
   is still the weakest en metric (.462).
5. **Model drift is real; the same-day control was the right design.** The en v5 control fell .824 → .695 on
   overall QWK since 2026-07-19. EN now routes Detector and Verifier both to `google/gemini-3.5-flash-lite` (July:
   2.5-flash-lite + 3.5-flash). ZH/JA still use `qwen/qwen3.6-flash` + `qwen/qwen3.7-plus`.

## Decisions needed before a re-run

- **ja keigo vs register gold.** Relabel the four だ/です items to `register`, or change the gloss. The gloss is the
  TASK-840-reviewed ruling.
- **zh 个.** Decide whether 一个 for a noun with a specific classifier is an error. If it is acceptable (the
  current gloss), relabel or drop the four gold errors. If it is an error, the gloss and TASK-839's deviation note
  must change.
- **en "it → them".** Decide whether it is `pronoun` or `word_choice` in v6, and amend the pronoun gloss to match.
- **Decode fallback for category/subtype index confusion** (finding 2). This is a production fix with its own task
  and tests. After it, the zh and ja gates must be re-run.
- Optionally, swap the ja rubric exemplar (finding 3) before the re-run so ja v6 is graded with its few-shot.

Per TASK-850, follow-ups go against 843/845, plus a gold-relabel task under 847. Then re-run all three arms.

## Cost and wall time

| L2 | A v5 | B v6 | C v6 silver | wall time (A‖B, then C) |
|----|------|------|-------------|------------------------|
| EN | $0.046 | $0.063 | $0.077 | ~2 min + 2.5 min |
| ZH | $0.252 | $0.271 | $0.320 | ~35 min + 42 min |
| JA | $0.364 | $0.373 | $0.435 | ~55 min + 63 min |

The harness estimated **$2.20** in total from token counts × the model-arena price map. The OpenRouter key's usage
counter rose by **$3.21** over the session. That is the ceiling, since it may include reasoning tokens and other
processes on the same key. A spend monitor killed nothing: the hard stop was $14.50. The three L2s ran in parallel,
with A and B concurrent and C after them, for **~2 h wall clock**. There were zero skipped items, zero fell-open
grades and no rate-limit retries. ja averaged ~1.8 min per item.

## Reproduce

```
# A (v5 control, DT_TAXONOMY_VERSION unset)
python scripts/run_dt_grading_eval.py --l2 {en|zh|ja} --framework-v2 --live \
    --resume data/eval/dt_v6_gate_2026-10-08/<l2>_A.ckpt.jsonl --out data/eval/dt_v6_gate_2026-10-08/<l2>_A.md
# B / C (v6 offline) — add:
    --taxonomy-file migrations/dt_taxonomy_v6_seed.sql --fixture-set v6          # B
    --taxonomy-file migrations/dt_taxonomy_v6_seed.sql --fixture-set v6_silver   # C
```

## Related Pages
- [[tasklist/dt-taxonomy-v6.tasks]]: TASK-850 (this gate), TASK-853 (cutover, still blocked)
- [[decisions/ADR-031-dt-taxonomy-v6-merge]]
- [[evaluations/dt-grading-v2-2026-07-19]]: the prior v2 baseline (v5 taxonomy)
- [[evaluations/dt-taxonomy-v6-inventory-2026-10-04]]
- [[algorithms/evidence-first-grading.tech]]
