# Japanese word assets: what is here

| path | what |
|---|---|
| `ja_word_assets_all.sql.gz` | **Everything in one file**: the earlier 959-sense package followed by the 5,152-sense delta. 42,777 `word_assets` upserts and 12,242 UPDATEs in two transactions (10.9 MB gzipped, ~91 MB raw). |
| `upload/` | The earlier 959-sense package: `apply_all.sql`, chunks, CSV, `verify.sql`. |
| `upload_delta/` | The 5,152 new senses as ~1 MB chunks plus `verify.sql`. The single-file version is inside `ja_word_assets_all.sql.gz`. |
| `archive/ja_fatseed_records.tar.gz` | The JSON records of every run (29 MB). Per sense it has the authored document (`words/`), the reviewed document (`reviewed/`) and the review verdict (`review/`). Per run it has `senses.csv`, `check.reviewed.json`, usage/cost logs and QA judge files. |
| `issues/` | Senses the reviewer rejected (dictionary problems) and corpus sentences tagged to the wrong sense. |
| `opt/` | The cost-optimisation campaign: `REPORT.md`, `MEASUREMENT_APPENDIX.md`, arm commands, cheat-sheet versions. |

Apply everything (idempotent: every INSERT is `ON CONFLICT … DO UPDATE`):

```bash
gunzip -c data/exercise_seeding/ja/ja_word_assets_all.sql.gz | psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

Then run `upload/verify.sql` and `upload_delta/verify.sql`. To unpack the
records: `tar -xzf archive/ja_fatseed_records.tar.gz` from this directory.
They extract into `wf/` and `wf2/`. How they were made, and how to do the
same for another language: `.claude/skills/fat-seed-authoring/SKILL.md`.
