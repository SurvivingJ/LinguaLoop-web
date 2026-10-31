# Fat-seed cost optimisation — campaign report

Goal: bring the tool-free fat-seed pipeline (Haiku/Sonnet author → reviewer →
validators) for Japanese word assets from ~$0.19 to **≤ $0.02 per sense**
while holding quality close to the Sonnet + Opus production configuration.

Result: **$0.0225/sense (−88%) at 0.76 ± 0.54 points below production on an
independent Opus/high judge, with the same item-breaking error rate (0.34
fatal defects per sense in both)** (quality option), or **$0.0204/sense at
0.93 ± 0.60 below production, fatal share 0.21 vs 0.19** (budget option).
Both were screened on the same 100-sense test set by the same proxy judge and
then confirmed, paired by sense, under the frozen Opus/high judge.

Everything below ran in a sandbox (`data/exercise_seeding/ja/opt/`); nothing
in the production pipeline or the DB was changed. Adoption needs the config
switch described in §6.

## 1. Headline numbers (gold100: 100 senses, one sense per lemma, 23% with mined sentences)

Screening judge = Opus/medium, rubric 3, single pass; score = 10 − 3·fatal −
1·major − 0.3·minor per sense; credible difference ≥ 0.55 (see appendix).

| config | author | review | $/sense | score | fatal/sense | senses with ≥1 fatal | first-pass check |
|---|---|---|---|---|---|---|---|
| production (`c_base100`) | Sonnet/low, prod cheat sheet, L1 on | Opus/medium full | 0.186 | 7.67 | 0.28 | 0.14 | 97/99 |
| **quality finalist (`c_final3_100`)** | Haiku/medium, sheet v7, core + variant + L6 audits, no L1, no lint loop | Haiku/medium full | **0.0225** | **7.05** | **0.26** | 0.21 | 96/97 |
| `a_v7_audit_100` (first finalist) | same minus L6 audit, lint loop on | Haiku/medium full | 0.0240 | 7.02 | 0.27 | 0.19 | 44/96 |
| **budget finalist (`a_final_100`)** | same author as quality finalist | Haiku/low fatal-only | **0.0204** | 6.42 | 0.26 | 0.20 | 83/97 |
| plain Haiku (`b_norev100`) | Haiku/medium, prod sheet, lint loop | none | 0.0114 | 4.76 | 0.96 | 0.49 | 41/98 |

Independent confirmation (frozen Opus/high, rubric 3, paired on the same
senses; this judge is ~0.5 stricter than the proxy for every arm):

| arm vs production | paired Δ (2SE) | fatal share arm / prod | proxy Δ on same senses |
|---|---|---|---|
| `a_v7_audit_100` | −0.66 (±0.65) | 0.29 ± 0.09 / 0.19 ± 0.08 | −0.71 (±0.59) |
| **`c_final3_100`** (quality) | **−0.76 (±0.54)**; 6.42 vs 7.19 | 0.29 ± 0.09 / 0.20 ± 0.08 (fatal/sense 0.34 vs 0.34) | −0.66 (±0.52) |
| **`a_final_100`** (budget) | **−0.93 (±0.60)**; 6.22 vs 7.15 | 0.21 ± 0.08 / 0.19 ± 0.08 (fatal/sense 0.29 vs 0.33) | −1.24 (±0.62) |

Judge-vs-proxy gaps were 0.05, 0.11 and 0.31 points, so the screening judge
did not mislead the optimisation (it was, if anything, harsher on the budget
option than the independent judge). Non-inferiority within 1 point is
demonstrated for both options; within 0.5 for neither (the 100-sense set
cannot resolve that). Blind read of 20 Opus/high
fatals: 8/10 of the finalist's are genuine content errors; 5/10 of
production's are A/B duplicate-distractor items that a lint fixes trivially
(production never ran the overlap lint), so production's fatal share is
inflated by an easy class and the finalist's residual fatals are the hard kind.
In the second confirmation the same class shows up on the Haiku side: 3 of
the quality finalist's first 11 Opus/high fatals are A/B duplicate blocks
(`c_final3_100` ran with no lint at all), and several others are the judge's
known pedantic alternative readings (「仕方から教えてもらった」, 「長ければと思って
いた」, 「確率を三割だと言われた」, が/の alternation). Enabling the A/B-overlap
rule as prevention or a single repair would remove the first group for
≈$0.001/sense.

## 2. What moved quality (each measured on gold100, same judge)

| lever | effect | cost/sense | notes |
|---|---|---|---|
| **Short structural cheat sheet (v7, 5.2 KB)** replacing the 4.7 KB production sheet + 8–13 KB rule lists | +0.84 vs plain Haiku + review | −$0.002 (shorter prompt) | removes level_3 / level_7 / syn-ant fatals (0.11→0.01, 0.11→0.03, 0.07→0). Every LONGER sheet (v4–v6) scored worse: Haiku's level_6 failure mode shifts to word salad. |
| **Core audit call** (`--core-audit`: per sentence reading / whole-word / sense / natural flags, regenerate failures, mined untouched) | core fatal 0.24 → 0.06 (production 0.16) | $0.0010 | replicated twice; the single most cost-effective change. No score change on its own: fixed core sentences moved level_6 anchors and Haiku wrote new fake-wrong sentences there. |
| **Variant audit call** (`--variant-audit`: level_6 grammatical / only-target-wrong / actually-wrong; level_7 span-on-target / incorrect-is-wrong / corrected-natural) | +0.76 | $0.0042 | level_6 major 0.62→0.45, level_6 fatal 0.23→0.10, particle fatal →0. |
| **Level-6 audit question** (`--l6-audit`: "natural in some ordinary context → cannot be a wrong sentence; explanation must name the misused word and the confused sense") | level_6 fatal 0.10→0.04 (production 0.03); ≈ +0.2 | $0.0006 | cheapest fix of the campaign. |
| **Haiku/medium full patch review** (RFC 6902 patches, no tools) | +0.6 to +0.7 over no review | $0.0062 | removes core fatals and the "unnatural but usable" majors. |
| **Haiku/low fatal-only review** | +0.57 over no review; −0.39 fatal/sense | $0.0027 | same fatal reduction, leaves majors (by design): the entire quality-vs-budget difference. |
| Skip level_1 authoring (renderer builds L1 from the phonetic trie) | 0 quality change, L1 blocks are a defect source | −10% author tokens | production should adopt regardless of model. |

What did not work (all measured, all rejected): Haiku effort high (−0.13,
+22% cost); writing A and B in separate calls (worst arm, 1.9× variant
cost); a whole-document self-check pass; longer rule sheets (v4, v5, v6);
code-lint repair loops (no measurable gain on Sonnet or Haiku, +12–25% cost);
a third repair round; a second review pass (+0.04); core-only review (breaks
anchored blocks); Sonnet as reviewer (worse than Opus and not cheaper); a
Haiku "naturalness polish" pass (Haiku cannot see the collocation defects the
judge counts; 0.70 vs 0.65 core majors).

## 3. Where the quality finalist still loses (Opus/high, points/sense, `c_final3_100` vs production)

Lost: level_6 major +0.27 (0.40 vs 0.13), core major +0.26 (0.59 vs 0.32),
level_4 fatal +0.25 (0.08 vs 0.00), level_7 major +0.15, level_6 minor
+0.13 — "wrong sentences" that are correct uses or wrong for non-sense
reasons, unnatural generated collocations, and a few level_4 forms that
also fit. Gained: core fatal −0.39 (**0.04 vs 0.17**), level_1 −0.27 (it
writes none), synonym_antonym −0.18, particle_selection −0.07. Net +0.55
points/sense of class movement; the paired total is −0.76. The budget
finalist loses the same classes plus the majors the fatal-only reviewer
leaves (core major +0.41, level_6 fatal +0.31, particle major +0.16).

## 4. Production findings independent of the optimisation

Found by code on 356 already-reviewed production documents (Sonnet + Opus):

1. **level_7 corrected sentence identical to a core sentence** in **28%** of
   documents (54% of raw Haiku output): the correct twin is shown beside the
   "incorrect" item and gives the answer away. Lint exists
   (`FAT_SEED_LINT_ALL_BLOCKS=1`); level_7 cannot be declined, so it must be
   prevented (sheet v7 does) or repaired.
2. **Variant B copies variant A's distractors**: level_3 11%, level_4 10%,
   particle_selection verbatim 8%, syn/ant 2%. Half of production's fatals
   in the confirmation run were this class.
3. **particle_selection renders the wrong slot in 4–6% of documents**: the
   renderer blanks the FIRST occurrence of the particle in the anchor; upload
   stores no offset. Fix: carry `particle_offset` through the typed contract;
   until then the author rule is "the first occurrence must be the target's
   slot, else decline" (lint `ps_slot`).
4. **The production cheat sheet teaches a defect**: it suggests the level_3
   explanation 「形は合うが意味が合わない」; Sonnet writes it verbatim on 72%
   of documents and the judge marks it major. Delete the phrase.
5. The production checker accepts a bare-string option in some blocks and
   crashes on it in others (`_remap_options`); it should reject non-dict
   options uniformly. `nt_review.py` now validates patched block shapes.

## 5. Measurement (details in MEASUREMENT_APPENDIX.md)

- Judge: Opus, no tools, lists defects (fatal/major/minor) with JSON paths;
  score derived by code. Rubric 3 scopes out mined sentences and the given
  definition, counts one root cause once. Rubric 4 (mined sentences injected,
  polite-form and L1-count noise removed) is written and smoke-tested, not
  used for scoring.
- Resolution: the 23-sense set cannot resolve < 1.3 points at any number of
  passes (document variance dominates); gold100 single pass resolves 0.55;
  a second pass on gold100 is worthless (0.55 → 0.51). Spend on senses, not
  passes.
- Proxy: Opus/medium correlates 0.96 (arm means) / 0.80 (per sense) with the
  frozen Opus/high judge at 40% less cost; Sonnet/high is too lenient;
  Haiku/high only preserves rank order.
- Staleness: judge records carry a document hash; re-running the judge
  re-judges only changed senses (`--stale` audits every arm).
- Production QA plan: judge a random 10% of each batch (≥100 senses pooled)
  with one Opus/medium pass ($0.0065 per produced sense); primary metric =
  share of senses with ≥1 fatal; trigger at p0 + 2·sqrt(p0(1−p0)/100);
  re-anchor monthly with a 100-sense Opus/high pass.

## 6. Recommended production configuration

Quality option (recommended): author Haiku/medium, sheet
`opt/RULES_CHEATSHEET_v7.md`, `--skip-l1 --core-audit --variant-audit
--l6-audit`, no lint repair loop (keep validators; add the A/B-overlap rule
as prevention text or a single repair — see §1); review Haiku/medium
`nt_review.py` (default shape validation, declines preserved). ≈ $0.0225/sense,
confirmed −0.76 ± 0.54 vs production, equal fatal rate.

Budget option: same author; review `--model haiku --effort low --fatal-only`.
≈ $0.0204/sense; expect ≈0.6 points more "unnatural but usable" majors, same
fatal rate.

Exact arm commands: `opt/ARMS.txt` (`c_final3_100`, `a_final_100`). To adopt,
`scratch_offline/nt_pipeline.py` needs the author/review flags passed through
(today it runs Sonnet/Opus defaults) — a 10-line change, not made yet.

Also adopt regardless of model: skip level_1 authoring; delete the template
phrase from the production sheet; run the overlap and level_7-twin lints as
warnings on existing uploads and repair the hits with the Haiku/low fatal-only
reviewer (~$0.003/sense).

## 7. Spend

Campaign total ≈ $363: pipelines $97, judging $267 (judging dominated by
design; the gold100 switch and the Opus/medium proxy cut it by ~60% per arm;
three Opus/high confirmations ≈ $33). Twenty-one gold100 arms plus nine
23-sense screens; three experimenter agents ran in parallel for ~10 hours.

## 8. Files

- Tool-free pipeline: `scratch_offline/nt_author.py` (audits, cheat-sheet
  flag, skip-l1, extra args), `nt_review.py` (fatal-only, keep-declines,
  resume, shape validation), `nt_judge.py` (frozen judge, proxies, rubrics
  2–4, document hashes), `nt_experiment.py` (arms, `--compare`, `--passes`,
  `--loss`, `--defects`, `--confirm`, `--stale`, `--reliability`, `--proxy`),
  `nt_pipeline.py` (production runner, unchanged config).
- Lints: `services/vocabulary_ladder/fat_seed.py` (opt-in via
  `FAT_SEED_LINT_ALL_BLOCKS=1`, demotion via `FAT_SEED_LINT_SKIP`), tests in
  `tests/test_fat_seed.py` (17 pass with and without the env var).
- Data: `opt/gold/`, `opt/gold100/`, `opt/<arm>/` (documents, judge files,
  usage logs, summary.json), `opt/ARMS.txt` (every command), `opt/BRIEF.md`,
  `opt/RULES_CHEATSHEET_v3..v7.md`, `opt/MEASUREMENT_APPENDIX.md`.

## 9. Production addendum (after adoption)

The quality finalist ran on the production queue at $0.0229/sense. QA samples
(12 runs, 135 senses, Opus/medium rubric 3) came in below gold100: mean 6.21,
fatal/sense 0.47, fatal share 0.29 (gold100: 7.05 / 0.26 / 0.21). Cause: the
production queue puts the senses of one lemma in the same run (122 of the 135
sampled senses had a sibling sense in their run; gold100 had none), and Haiku
confuses sibling senses in the core sentences, which every block inherits.
Controls on the same three production runs (35 senses, same judge):

| config | mean | fatal/sense | fatal share | $/sense |
|---|---|---|---|---|
| Haiku finalist (production) | 6.54 | 0.37 | 0.26 | 0.0235 |
| + sibling guard in prompt/audit | 6.68 | 0.64 | 0.20 | 0.0253 — no effect, not adopted |
| + Sonnet core audit (Haiku writes) | 6.86 | 0.32 | 0.26 | 0.0356 — no effect |
| **Sonnet/low core, Haiku everything else** | **7.46** | **0.09** | **0.06** | **0.0495** |
| Sonnet + Opus (old production, 2 runs) | 7.98 | 0.17 | 0.13 | 0.168 |

Sonnet is not affected by the sibling structure; only the Haiku core is. A
Sonnet core removes the fatals (better than the old pipeline on this metric)
at roughly twice the Haiku price, still −70% against the old pipeline. The
Sonnet core costs $0.028/sense with the v7 sheet (it thinks twice as long as
with the production sheet, $0.023); the audits, variants and review stay
Haiku. Decision (user): adopt the Sonnet-core hybrid for the remaining queue
and re-author the 309 runs (3,632 senses) produced with the Haiku core; their
Haiku outputs are kept beside the new ones as `fat_seed.haiku/`.
`nt_pipeline.py` carries the configuration (`--core-model sonnet
--core-effort low`). Lesson for the gold set: sample sibling senses together,
as production does.
