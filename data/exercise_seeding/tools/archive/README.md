# Staged fat-seed exercise archives — NOT applied to the database

Nothing in these archives has been written to Supabase. They are durable copies of
container-local staging output (data/exercise_seeding/ is gitignored, so they are force-added).

| Archive | Contents |
|---|---|
| ja/archive/upload_2026-11-17.tar.gz | Staged ja upload package: 3,298 senses, 23,086 word_assets rows, 7,100 UPDATEs, 38 SQL chunks, verify.sql, overwrites_live_values.csv, README with staging notes |
| ja/archive/payload_all_writes.tar.gz | ja writes.jsonl (restored + new runs) the package was built from |
| zh/archive/upload_2026-11-19.tar.gz | Staged zh upload package: 15,624 senses, 109,368 word_assets rows, 31,248 UPDATEs, 179 SQL chunks, verify.sql, overwrites_live_values.csv, README with staging notes. `apply_all.sql` (186 MB) is left out to stay under GitHub's file-size limit — run the chunks in order, or rebuild it with `scratch_offline/package_upload.py` from payload_all |
| zh/archive/upload_2026-11-19_apply_all.sql.gz | The zh package's `apply_all.sql` (one transaction), gzipped separately to stay under GitHub's file-size limit |
| tools/archive/logs_2026-11-19.tar.gz | Pipeline, assembly, checkpoint and judge logs |
| zh/archive/payload_all_writes.tar.gz | zh writes.jsonl (restored + all 989 new runs) the package was built from |
| zh/archive/payload_restored_writes.tar.gz | zh writes.jsonl re-assembled from restored runs r0000–r0900 (subset of payload_all) |
| ja/archive/new_rNNNN-rNNNN.tar.gz | New ja run records (r0506–r0539) |
| zh/archive/new_rNNNN-rNNNN.tar.gz | New zh run records (r0902–r1890), all 989 finished 2026-11-19 |
| tools/archive/staging_tools.tar.gz | Snapshot/assembly/overwrite-report scripts, exclude CSVs (senses already live), run lists |

Restore: `tar -xzf <archive> -C data/exercise_seeding/<lang>/`.
Review overwrites_live_values.csv before applying any package: some UPDATEs replace existing
non-null dictionary values (semantic_class, POS, pronunciation).

Older records restored for these packages (ja `wf/`, `wf2/r0000–r0505`; zh `wf2/r0000–r0900`) are already in
`main`'s history: `data/exercise_seeding/ja/archive/ja_fatseed_records.tar.gz` (commit 0dce7d1) and
`data/exercise_seeding/zh/archive/zh_fatseed_records_interim.tar.gz` (commit cfb6fd1).
