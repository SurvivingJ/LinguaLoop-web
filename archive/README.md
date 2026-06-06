# Archived artifacts (history only — not current)

## `db_schema_live_2026-03-18.sql`

A point-in-time dump of the live Supabase schema, extracted 2026-03-18. **Out of
date** — it predates (at least) the 8-arg `process_test_submission`
(furigana + k-factor decay), the Part F `question_attempt_results` table, and the
difficulty-calibration views. Kept for history; do **not** treat it as the
current schema.

For the authoritative schema use the live DB (`pg_get_functiondef`,
`information_schema`, Supabase MCP) and the maintained `migrations/` folder. The
wiki `database/schema.tech.md` page is the maintained human-readable reference.
