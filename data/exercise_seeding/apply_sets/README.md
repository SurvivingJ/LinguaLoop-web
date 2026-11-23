# Apply sets — draft sense-id lists (2026-11-23), nothing applied

Comma-separated `dim_word_senses.id` lists for [[tasklist/zh-ja-content-seeding.tasks]] (TASK-1100).
Drafts: recompute after the space decision (TASK-1097) and a fresh drift check.

| File | Senses | Source package |
|------|-------:|----------------|
| `zh_from_final.txt` | 11,174 | final zh package, branch `claude/zh-word-assets-10k` commit `e2747db` (`data/exercise_seeding/zh/upload/`): its 11,199 senses not in the DB on 2026-11-23, minus 25 in `calibration_anchor_blocklist` |
| `zh_from_2026-11-19.txt` | 4,940 | `data/exercise_seeding/zh/upload_2026-11-19/`: its senses not in the final package (4,947), minus 7 blocklisted |
| `ja.txt` | 3,298 | `data/exercise_seeding/ja/upload_2026-11-17/` (drop its 68 ja `part_of_speech` overwrites when applying) |

Overwrite check for a list: `python scratch_offline/staging/package_updates.py <apply_all.sql[.gz]> --senses <list>`.
