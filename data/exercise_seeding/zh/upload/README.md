# ZH word assets — upload package

Reviewed fat-seed output for **16361 Chinese senses** (all passed
`check --source reviewed`; rejected and skipped senses are excluded).
**Final package.** Every passing sense from the 1,603 runs, in its Opus/low second-review version (`wf3/`). It replaces the interim package of 2026-11-07 (9,585 senses, first-pass review only): apply this one instead. If the interim one is already applied, applying this one is still safe, because every INSERT updates on conflict.

`apply_all.sql` and `word_assets.csv` are committed gzipped (`.gz`, over 50 MB raw). Run `gunzip -k` on them first, or use the chunks.

| | |
|---|---|
| `word_assets` rows | 114,527 (7 asset types) |
| UPDATE statements | 32,722 {'dim_vocabulary': 16361, 'dim_word_senses': 16361} |
| language_id | 1 (zh) |
| source | tool-free fat-seed pipeline (scratch_offline/nt_pipeline.py); see the run directories for models |

## Files

- `apply_all.sql` — everything in one transaction (191.2 MB). Use with `psql`.
- `chunks/part_01.sql … part_164.sql` — the same statements in ~0.9 MB files, each its
  own `BEGIN … COMMIT`, UPDATEs at the end. For the Supabase SQL editor, run them in order.
- `word_assets.csv` — the asset rows only (no UPDATEs), for Table Editor import.
- `verify.sql` — row counts to run afterwards.

Every INSERT is `ON CONFLICT (sense_id, asset_type) DO UPDATE`, so re-running a
chunk is harmless. Apply with:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/exercise_seeding/zh/upload/apply_all.sql
```
