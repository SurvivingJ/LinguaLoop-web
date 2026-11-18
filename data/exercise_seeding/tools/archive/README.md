# Staged fat-seed exercise archives — NOT applied to the database

Nothing in these archives has been written to Supabase. They are durable copies of
container-local staging output (data/exercise_seeding/ is gitignored, so they are force-added).

| Archive | Contents |
|---|---|
| ja/archive/upload_2026-11-17.tar.gz | Staged ja upload package: 3,298 senses, 23,086 word_assets rows, 7,100 UPDATEs, 38 SQL chunks, verify.sql, overwrites_live_values.csv, README with staging notes |
| ja/archive/payload_all_writes.tar.gz | ja writes.jsonl (restored + new runs) the package was built from |
| zh/archive/payload_restored_writes.tar.gz | zh writes.jsonl re-assembled from restored runs r0000–r0900 |
| ja/archive/new_rNNNN-rNNNN.tar.gz | New ja run records (r0506–r0539) |
| zh/archive/new_rNNNN-rNNNN.tar.gz | New zh run records (r0902–r1890), added hourly while the pipeline runs |
| tools/archive/staging_tools.tar.gz | Snapshot/assembly/overwrite-report scripts, exclude CSVs (senses already live), run lists |

Restore: `tar -xzf <archive> -C data/exercise_seeding/<lang>/`.
Review overwrites_live_values.csv before applying any package: some UPDATEs replace existing
non-null dictionary values (semantic_class, POS, pronunciation).
