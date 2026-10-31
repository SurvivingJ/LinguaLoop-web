# JA word assets — delta package (senses not in the earlier 959-sense package)

Reviewed fat-seed output for **5152 Japanese senses** (all passed
`check --source reviewed`; rejected and skipped senses are excluded).
Delta package: the 959 senses of the earlier package are excluded.

| | |
|---|---|
| `word_assets` rows | 36,064 (7 asset types) |
| UPDATE statements | 10,324 {'dim_vocabulary': 5162, 'dim_word_senses': 5162} |
| language_id | 3 (ja) |
| source models | Sonnet core / Haiku audits, variants and review (runs r0069+), Sonnet + Opus (earlier runs) |

## Files

> In git only `chunks/`, `verify.sql` and this README are committed: `apply_all.sql` (77 MB)
> and `word_assets.csv` (60 MB) exceed GitHub's 50 MB guidance. Rebuild them with
> `cat chunks/part_*.sql > apply_all.sql` (each chunk is its own transaction), or regenerate
> both from the captured writes with `python3 scratch_offline/package_upload.py
> data/exercise_seeding/ja/payload_wf/writes.jsonl data/exercise_seeding/ja/upload_delta
> --exclude-csv data/exercise_seeding/ja/upload/word_assets.csv`.

- `apply_all.sql` — everything in one transaction (80.2 MB). Use with `psql`.
- `chunks/part_01.sql … part_63.sql` — the same statements in ~0.9 MB files, each its
  own `BEGIN … COMMIT`, UPDATEs at the end. For the Supabase SQL editor, run them in order.
- `word_assets.csv` — the asset rows only (no UPDATEs), for Table Editor import.
- `verify.sql` — row counts to run afterwards.

Every INSERT is `ON CONFLICT (sense_id, asset_type) DO UPDATE`, so re-running a
chunk is harmless. Apply with:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/exercise_seeding/ja/upload_delta/apply_all.sql
```
