# ZH word assets — upload package

Reviewed fat-seed output for **9585 Chinese senses** (all passed
`check --source reviewed`; rejected and skipped senses are excluded).
**Interim package**: the 900 runs (of 1,603) that had finished when the pipeline was paused on 2026-11-07. A delta package for the remaining runs will follow; build it with `package_upload.py --exclude-csv` against this package's `word_assets.csv`.

`apply_all.sql` and `word_assets.csv` are committed gzipped (`.gz`, over 50 MB raw); `gunzip -k` them first, or use the chunks.

| | |
|---|---|
| `word_assets` rows | 67,095 (7 asset types) |
| UPDATE statements | 19,170 {'dim_vocabulary': 9585, 'dim_word_senses': 9585} |
| language_id | 1 (zh) |
| source | tool-free fat-seed pipeline (scratch_offline/nt_pipeline.py); see the run directories for models |

## Files

- `apply_all.sql` — everything in one transaction (112.6 MB). Use with `psql`.
- `chunks/part_01.sql … part_97.sql` — the same statements in ~0.9 MB files, each its
  own `BEGIN … COMMIT`, UPDATEs at the end. For the Supabase SQL editor, run them in order.
- `word_assets.csv` — the asset rows only (no UPDATEs), for Table Editor import.
- `verify.sql` — row counts to run afterwards.

Every INSERT is `ON CONFLICT (sense_id, asset_type) DO UPDATE`, so re-running a
chunk is harmless. Apply with:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/exercise_seeding/zh/upload/apply_all.sql
```
