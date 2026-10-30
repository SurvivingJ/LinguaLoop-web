# JA word assets — upload package

Reviewed fat-seed output for **959 Japanese senses** (all passed
`check --source reviewed`; rejected senses are excluded).

| | |
|---|---|
| `word_assets` rows | 6,713 (7 asset types × 959 senses) |
| `dim_word_senses` / `dim_vocabulary` UPDATEs | 1,918 (pronunciation, IPA, register, morphological_forms; POS, semantic_class) |
| language_id | 3 (ja) |

Pre-checked against the live DB (2026-10-24): all 959 sense ids exist, none
had any `word_assets` yet, and `UNIQUE (sense_id, asset_type)` is present.
A sample INSERT + UPDATEs was run inside a rolled-back transaction to confirm
the column types.

## Files

- `apply_all.sql` — everything in one transaction (14 MB). Use with `psql`.
- `chunks/part_01.sql … part_16.sql` — same statements split into ~0.9 MB
  files, each its own `BEGIN … COMMIT`. Parts 01–15 are `word_assets` upserts;
  part 16 holds the last upserts plus all UPDATEs. Use these for the Supabase SQL editor (paste one at a
  time, in order).
- `word_assets.csv` — the 6,713 asset rows only (no UPDATEs), for Table
  Editor CSV import. `content` is JSON text; `validation_warnings` is a JSON
  array string.
- `verify.sql` — row counts to run afterwards.

## How to apply

Option A (recommended):

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f data/exercise_seeding/ja/upload/apply_all.sql
```

Option B: Supabase SQL editor → run `chunks/part_01.sql` … `part_16.sql`
in order.

Every INSERT is `ON CONFLICT (sense_id, asset_type) DO UPDATE`, so re-running
a file is safe.

## Verify

Run `verify.sql`. Expected: `assets = 6713`, `senses = 959`, every asset type
= 959.
