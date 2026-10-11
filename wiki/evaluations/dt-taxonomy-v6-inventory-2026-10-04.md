# DT Taxonomy v6 — Live Data Inventory (read-only)

Date: 2026-10-04 | Project: `kpfqrjtfxmujzolwsvdq` (Supabase, live) | Task: TASK-836

All queries below are SELECT-only, run via the Supabase `execute_sql` MCP tool against the live
project. No writes were made. `dim_languages`: zh=1, en=2, ja=3.

## Headline: the live dataset is tiny

The entire DT (Dual Translation) feature has **4 submissions total, all from a single user/L1,
all against zh passages**. There are 67 `dt_passage` rows spanning all 3 languages, but no
submissions/errors were ever recorded against ja or en passages. This is effectively smoke-test
data, not real usage — the cutover rewrite (TASK-852) has almost nothing to rewrite.

| Table | Total rows |
|---|---|
| `dt_submission` | 4 (1 distinct `l1_language_id`) |
| `dt_passage` | 67 (3 distinct `l2_language_id`) |
| `dt_error_instance` | 16 (0 orphaned joins to `dt_submission`) |
| `dt_error_profile_entry` | 4 |
| `dt_card` | 4 |
| `dt_card_review` | 5 |

## `dt_error_instance` by subtype (joined via submission → passage for L2)

All 16 rows are zh (`l2_language_id=1`). Zero rows for en or ja.

| l2 | subtype | n |
|---|---|---|
| zh | word_choice | 7 |
| zh | omission | 6 |
| zh | word_order | 2 |
| zh | aspect_marker | 1 |

## `dt_error_profile_entry` by l2 × subtype × remediation_status

All 4 rows are zh. Zero rows for en or ja.

| l2 | subtype | remediation_status | n_entries | total_occurrences (`sum(count)`) |
|---|---|---|---|---|
| zh | aspect_marker | watching | 1 | 1 |
| zh | omission | drilling | 1 | 6 |
| zh | word_choice | drilling | 1 | 7 |
| zh | word_order | watching | 1 | 2 |

## `dt_card` by (language, subtype, card_type)

Language derived as `coalesce(profile_entry.l2_language_id, instance→submission→passage.l2_language_id)`.
All 4 rows are zh.

| l2 | subtype | card_type | n |
|---|---|---|---|
| zh | omission | cloze | 1 |
| zh | omission | isolate_retranslate | 1 |
| zh | word_choice | cloze | 1 |
| zh | word_choice | isolate_retranslate | 1 |

## Explicit split/dropped-slug counts

All zero — none of these slugs have ever been written (consistent with "zh only" above, since
three of the four are ja/en slugs).

| table | lang | subtype | count |
|---|---|---|---|
| dt_error_instance | ja | particle_wa_ga | 0 |
| dt_error_profile_entry | ja | particle_wa_ga | 0 |
| dt_error_instance | ja | particle (historical_alias) | 0 |
| dt_error_profile_entry | ja | particle (historical_alias) | 0 |
| dt_error_instance | en | pronoun_reference | 0 |
| dt_error_profile_entry | en | pronoun_reference | 0 |
| dt_error_instance | ja | script_choice | 0 |
| dt_error_profile_entry | ja | script_choice | 0 |

### `script_choice` — `dt_card` / `dt_card_review` (all three lookup paths)

| metric | count |
|---|---|
| `dt_card` rows by `subtype='script_choice'` | 0 |
| `dt_card` rows via `profile_entry_id` → a `script_choice` ja profile entry | 0 |
| `dt_card` rows via `origin_error_id` → a `script_choice` error instance | 0 |
| union of all three (dedup) | 0 |
| `dt_card_review` rows on those cards | 0 |

TASK-852's ja `script_choice` delete step has nothing to delete today.

## Collision check (profile rows that would collide after rewrite)

Mapping built from `data/eval/taxonomy_merge_2026-09-27/v5_to_merged.csv`, restricted to the
deterministic `1:1` and `merge` rows (splits/drops excluded — those need per-instance review, not
a blind collapse). Joined to `dt_error_profile_entry` on `(l2_language_id, subtype)`, grouped by
`(user_id, l1_language_id, l2_language_id, v6_slug)`, `having count(*) > 1`.

**Result: zero collisions.** The 4 live zh profile entries are `aspect_marker`, `omission`,
`word_choice`, `word_order` — none of the named collision pairs (`ba_construction`+`bei_passive`
→ `ba_bei`; `resultative_complement`+`directional_complement` → `complement`;
`adverbial_order`+`word_order` → `word_order`) have both sides present for any user, so none fire.

## Subtype-bearing column sweep

`information_schema.columns` in `public`, `column_name ilike '%subtype%'` — exactly 3 hits, all
already covered by TASK-842's column-add list:

- `dt_card.subtype`
- `dt_error_instance.subtype`
- `dt_error_profile_entry.subtype`

jsonb probe (text search for `"subtype"` as a substring, since none of these columns are
consistently a flat object):

| location | hits |
|---|---|
| `dt_card.prompt_payload` | 0 |
| `dt_grade.grader_trace` | 0 |
| `dt_grade.diff` | 0 |

No other subtype-bearing column or embedded jsonb key exists. TASK-852/TASK-842 need cover only
the 3 columns above.

## `dt_taxonomy_version` / `dt_rubric_version`

| table | version | is_active |
|---|---|---|
| dt_taxonomy_version | 1 | false |
| dt_taxonomy_version | 2 | false |
| dt_taxonomy_version | 3 | false |
| dt_taxonomy_version | 4 | false |
| dt_taxonomy_version | 5 | **true** |
| dt_rubric_version | 1 | false |
| dt_rubric_version | 2 | false |
| dt_rubric_version | 4 | false |
| dt_rubric_version | 5 | false |
| dt_rubric_version | 6 | **true** |

(`dt_rubric_version` has no row numbered 3 — a taxonomy-naming-alignment skip noted in the v4
row's own description. No v6 taxonomy row exists yet; TASK-837 is still Not Started.)

## FK delete actions on `dt_card` / `dt_card_review`

`pg_constraint.confdeltype` — `'a'` = `NO ACTION` for every FK on both tables, matching the repo's
expectation:

| constraint | child | parent | confdeltype |
|---|---|---|---|
| dt_card_origin_error_id_fkey | dt_card | dt_error_instance | a (NO ACTION) |
| dt_card_profile_entry_id_fkey | dt_card | dt_error_profile_entry | a (NO ACTION) |
| dt_card_user_id_fkey | dt_card | users | a (NO ACTION) |
| dt_card_review_card_id_fkey | dt_card_review | dt_card | a (NO ACTION) |

## Takeaways for downstream tasks

- **TASK-852's rewrite is nearly a no-op on current live data**: 16 error-instance rows, 4 profile
  rows, 4 cards, 5 reviews, all zh, all mapping 1:1 (no merges, no splits, no drops touch any live
  row). The rewrite script still needs to handle the general case (future data, other languages),
  but there is no large backfill risk today.
- Surprising: despite 67 passages spanning all three languages, **ja and en have never produced a
  single graded DT submission** — the feature has essentially only been exercised in zh, and only
  by one account.
- No extra subtype-bearing columns or jsonb-embedded `"subtype"` keys were found beyond the 3
  known columns — TASK-842's column list is already exhaustive.
- Zero collisions and zero `script_choice` rows mean TASK-852's trickiest cases (merge-collision
  aggregation, ja script_choice delete) currently have nothing live to exercise — native-review
  risk for the split subtypes (`particle_wa_ga`, historical `particle`, `pronoun_reference`,
  `topic_comment`, etc.) is also moot today since none of those slugs have any live rows either.
