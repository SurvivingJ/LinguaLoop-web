# TASK-736 drafts — ja L1 redesign options

Referenced from `.claude/reviews/ja-l1-redesign-options.md`. Nothing here is applied
live. These are L1-block-only drafts in the same style as
`data/eval/task735/l1_block_ja.txt` — each would replace the `L1（聞き取り — リスニング
練習）：` section of `vocab_prompt2_exercises` [ja] while L3/L5/L6 and the shared
header stay byte-identical to the live v4 row (id 376).

| file | proposal | mechanism |
|---|---|---|
| `a1_uncapped_enumeration_ja.txt` | A1 | removes the numeric target range entirely; walk-all-positions framing with no anchor number |
| `a2_structured_retrieval_ja.txt` | A2 | forces a visible mora-substitution grid as a scratch field before the answer; chain-of-verification |
| `a3_worked_negatives_ja.txt` | A3 | adds 4 worked (target, rejected candidate, reason) examples spanning all four rejection classes |
| `b_rank_and_explain_ja.txt` | B1/B2 | NOT a drop-in L1 block — a new, much shorter prompt for a proposed new call that only ranks/explains a pre-verified candidate list. Requires a new `prompt_templates` task_name and a new caller; see the report's Track B technical sections. |

## New placeholders (A1–A3 only)

All three thread two new placeholders into the L1 block: `{tier_display}` and
`{tier_age_range}`. **These are not supplied by the current caller** —
`asset_generators/prompt2_exercises.py:_build_prompt` would need two new
`render_template()` kwargs (sourced from `categorical_maps.get_tier_display` /
`TIER_DISPLAY_NAMES`), and the applier's `CALLER_ARGS['vocab_prompt2_exercises']`
set would need the same two keys added or `check_row`'s placeholder check fails
the draft as an unsupported KeyError risk. See the report for the exact diff.

None of the three touches the JSON output contract — same `OPTION_KEY_MAP`
(`"1"`=text, `"2"`=is_correct, `"3"`=explanation), same 4–6-option shape. A2's
scratch field is a sibling top-level key the parser already ignores (traced
through `_remap_output`/`remap_keys` — confirmed safe, not assumed).
