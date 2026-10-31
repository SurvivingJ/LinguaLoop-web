# Fat-seed cost optimisation — shared brief for experimenters

Goal: bring the tool-free fat-seed pipeline (author -> review -> check) for
Japanese word assets to **<= $0.02 per sense total pipeline cost** while
keeping quality as close as possible to the current Sonnet+Opus baseline.
Pipeline cost = author + repair + review (+ review-repair) calls. The judge is
measurement overhead and is NOT counted.

## Where things are
Repo: /home/user/LinguaLoop-web (run everything from here). Branch
claude/exciting-babbage-qf4q7w. `git commit`/`push` are DENIED in this
environment: never try. Never write to the Supabase DB. Never touch
`data/exercise_seeding/ja/wf2/`, `wf/`, `upload/`, `payload*` (production).
The production pipeline is paused; do not start it.

Scripts (all in `scratch_offline/`, all "tool-free": the model gets a prompt,
replies with JSON, the script writes files and runs the validators):
- `nt_author.py RUN --model M --effort E --variant-batch N --width W --skip-l1 --cheatsheet PATH`
  cores per brief -> `plan` -> variants (batches) -> `check` -> up to 2 repair rounds.
  Logs every call to RUN/fat_seed/nt_usage.jsonl (cost_usd, output tokens, thinking).
- `nt_review.py SRC OUT --model M --effort E --batch N` patch reviewer (RFC 6902
  patches), writes fat_seed/reviewed/ and fat_seed/review/, one repair round.
- `nt_judge.py RUN --source reviewed|words [--tag _x]` FROZEN judge: Opus/high,
  lists defects (fatal/major/minor); score = 10 - 3*fatal - 1*major - 0.3*minor.
  Output RUN/fat_seed/judge.<source>.v2<tag>.json. Do NOT change the rubric or
  model without agreement (every arm would need re-judging). `--tag` gives a
  second independent pass on the same documents.
- `nt_experiment.py ARM [flags...]` runs one arm on the 23-sense gold set
  (`opt/gold/senses.csv`, split in 2 run dirs `opt/ARM/r00`, `r01`), then the
  judge, and writes `opt/ARM/summary.json`. `--compare` prints all arms.
  Flags: --author-model --author-effort --review-model --review-effort
  --skip-l1 --lint-all --cheatsheet PATH --variant-batch --review-batch
  --no-review --width --chunks. Re-running the same ARM resumes (existing
  words/reviewed/judge files are reused, nothing is re-paid).
- Launch long runs detached: `setsid nohup python3 scratch_offline/nt_experiment.py ARM ... > LOG 2>&1 < /dev/null & disown`
  then wait with an `until` loop on the log (`ARM DONE` / `Traceback`). Scripts
  are loaded at process start: editing a script while an arm runs does not
  affect that arm (but `fat_seed.py` lint changes DO apply live, because
  `check` is a fresh subprocess each time).
- Env `FAT_SEED_LINT_ALL_BLOCKS=1` (set by `--lint-all`) enables the opt-in
  lints in `services/vocabulary_ladder/fat_seed.py::lint_variants`: A/B
  distractor overlap on every option block, and level_7 corrected_sentence ==
  core sentence. Tests: `PYTHONPATH=. python3 -m pytest tests/test_fat_seed.py -q`
  (run with and without the env var).
- Validators the author must pass: `scripts/fat_seed_runner.py check` through
  `scratch_offline/run.py` (offline DB shim). Model rates seen: Sonnet out $10/M,
  Opus out $20/M, Haiku ~ $1/M-ish (cost_usd in the usage log is authoritative).
- Prompt material: `data/exercise_seeding/ja/RULES_CHEATSHEET.md` (production
  v2, do not edit), `opt/RULES_CHEATSHEET_v3.md` (haiku-tuned variant),
  `.claude/skills/fat-seed-authoring/SKILL.md` "Block reference" (goes into the
  author system prompt), `.claude/skills/fat-seed-review/SKILL.md`.

## Results so far (judge v2, single pass, 23 senses)
arm | $/sense | score | fatal | major | minor | notes
base (sonnet/low author, opus/medium review) | 0.175 | 6.20 | 0.26 | 1.26 | 6.04 | production config
nol1 (base + skip level_1) | 0.156 | 5.86 | 0.35 | 2.09 | 5.30 | level_1 comes from the phonetic trie in prod, so skipping is allowed
lint (nol1 + --lint-all) | 0.183 | 6.85 | 0.22 | 1.65 | 4.35 | lint adds repair rounds; minors drop
haiku (haiku/low author, opus review, L1 on) | 0.110 | 4.58 | 0.43 | 2.52 | 6.57 | author stage only $0.0076/sense
revsonnet (sonnet author, sonnet review) | 0.152 | 4.26 | 0.78 | 3.09 | 5.17 | REJECTED: sonnet reviewer is bad and not cheaper
Interrupted (resume by re-running the same command): h_low_hrev, h_med_hrev,
h_med_norev, h_med_v3 — see `opt/*/experiment.log` and the command lines in
`opt/ARMS.txt`.

**Judge noise**: judging `base` twice gave means 6.20 vs 5.34 (per-sense corr
0.75, mean |diff| 1.1). A single-pass difference under ~1.0 is NOT evidence.
Decision rule: any arm you want to recommend must be judged twice (second pass
with `--tag _rep`) and reported as the mean of both passes, with fatal counts.

**Known systematic defects** (found by code on 349 already-reviewed
production docs; the Opus reviewer misses them): B copies A's distractors in
level_3 (11%), level_4 (10%), particle_selection verbatim (8%), syn/ant (2%);
level_7 corrected_sentence identical to a core sentence (28%: gives the answer
away). Haiku's dominant judge defects: that level_7 twin issue, level_7 error
not on the target word, generic level_3 explanations copied from the cheat
sheet ("形は合うが意味が合わない"), A/B shared distractors, and explanations that
contradict the core definition.

## Rules of engagement
- Name your arms with your track prefix (`a_`, `b_`, `c_`) so they never
  collide. One `opt/<arm>/` per arm. Keep every arm's exact command line in
  `opt/ARMS.txt` (append a line).
- File ownership (to avoid clobbering each other): Track A owns
  `scratch_offline/nt_author.py` and cheat sheets under `opt/`; Track B owns
  `services/vocabulary_ladder/fat_seed.py` lints (always behind the opt-in env
  var), `tests/test_fat_seed.py`, `scratch_offline/nt_review.py`; Track C owns
  `scratch_offline/nt_judge.py` and `nt_experiment.py`. Need a change in a file
  you do not own? Describe it in your report instead of editing. Additive,
  backward-compatible flags only; never change defaults.
- Spend freely but record it: report total $ spent on your arms (sum of
  cost_usd in nt_usage.jsonl, pipeline and judge separately).
- Report in English, concisely: a results table (cost/sense by stage, judge
  mean over 2 passes, fatal/major/minor per sense, first-pass check), what you
  conclude, what you recommend adopting, and what you would try next.

## Protocol update (orchestrator, after Track C's measurement report)
- The 23-sense `gold` set cannot resolve differences under ~1.3 points at any
  number of passes (judge-free document variance dominates). STOP adding
  `_rep` Opus/high passes on `gold` arms; they do not buy resolution.
- New gold set: `opt/gold100/` (100 senses, one sense per lemma, 23% with
  mined sentences = population share). Use `--gold gold100 --chunks 8`
  (12-13 senses per run, like production).
- Screening judge is now **Opus/medium, rubric 3, single pass**:
  `--judge-model opus --judge-effort medium --judge-rubric 3` on
  `nt_experiment.py` (file `judge.<src>.v3.opus-medium.json`; `summary.json`
  reads it automatically). Rubric 3 = v2 plus scope rules: mined sentences and
  the given definition are out of scope, one root cause counted once, polite
  forms at T1-T2 not a defect, "fits the blank" fatal only for plain/polite
  readings. Opus/high 2-pass stays for final confirmation of the winner only.
- Resolution on gold100 single-pass is ~0.7 points (2*SE). Report fatal/sense
  beside the score; fatal is the stable severity.
- Baselines on gold100 (`c_base100`, `c_lint100`) are being run by Track C;
  compare against them, not against the 23-sense numbers.
- `nt_experiment.py --defects ARM`, `--fatals ARM`, `--show ARM SID`,
  `--passes`, `--reliability`, `--proxy NAME` exist for analysis (Track C).
