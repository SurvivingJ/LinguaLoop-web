# DT Grading Gold + Silver Sets — taxonomy v6 (TASK-847)

The v6 (ADR-031 merged taxonomy) counterparts of the v5 gold set in `../dt_gold/` and the
jev silver set. **Generated — do not hand-edit.** Rebuild with:

```
PYTHONPATH=. python scripts/build_dt_gold_v6.py           # write
PYTHONPATH=. python scripts/build_dt_gold_v6.py --check   # fail if the files on disk are stale
```

## The v5 fixtures are frozen

`tests/fixtures/dt_gold/{zh,ja,en}.json` are **not** touched by this build and stay
byte-identical: they remain the v5 regression set (and `derive_bands()` still defaults to
`taxonomy_version=5`) until the v6 cutover. These v6 files are additive.

## Files

| File | Source | Items | Errors |
|------|--------|-------|--------|
| `dt_gold_v6/zh.json` | `tests/fixtures/dt_gold/zh.json` | 30 | 26 |
| `dt_gold_v6/ja.json` | `tests/fixtures/dt_gold/ja.json` | 30 | 27 |
| `dt_gold_v6/en.json` | `tests/fixtures/dt_gold/en.json` + 1 v6-only item | 31 | 28 |
| `dt_silver_v6/zh.json` | `data/eval/jev_dt_2026-09-26/silver/zh_final3.json` | 34 | 33 |
| `dt_silver_v6/ja.json` | `data/eval/jev_dt_2026-09-26/silver/ja_final3.json` | 32 | 29 |
| `dt_silver_v6/en.json` | `data/eval/jev_dt_2026-09-26/silver/en_final3.json` | 34 (of 35) | 33 |

Gold items keep the v5 ids and order. 175 errors total = the 175 entries of the overlay.

**v6-only gold items (TASK-848, 2026-10-06).** After the 30 v5-derived items, a gold file may carry
items with no v5 counterpart, built by the same script from the find/replace specs in
`data/eval/taxonomy_merge_2026-09-27/v6_only_gold_items.json` (`build_item` →
`derive_bands(offline=True, taxonomy_version=6)` → `verify_item`; native v6 labels, no overlay
entry). Today that is one item, `en_v6_ws_02` ("This is like a hand" → "This likes a hand"):
`word_choice`/`wrong_sense`/major, the only narrow `wrong_sense` label. It was agreed by the author and a
blind reviewer (record in `.../wrong_sense_2026-10-05/`). It is a cross-POS homograph under one
headword, so it is not the same-POS polysemy that the 意思 example describes. zh and ja have none
(see `not_added` in the spec file), so `wrong_sense` stays a grader judgement there.

- **label_source / adjudication (`en_v6_ws_02`):** AI author+reviewer, approved for gold by the
  developer 2026-10-07. The item is AI-labelled (no human annotator), and the developer decided it
  stays in v6 GOLD. The reviewer's caveat still applies: `like` as a verb ("enjoy") vs `like` as a
  preposition ("similar to") is a cross-POS homograph under one headword, not same-POS polysemy, so
  this item must not be the only `wrong_sense` coverage. Both fields are recorded on the spec in
  `v6_only_gold_items.json`, and the fixture's `note` carries the gold-status sentence.

## Provenance

- **Labels:** `data/eval/taxonomy_merge_2026-09-27/v6_label_overlay.json` (`final: true`) —
  deterministic v5→v6 CSV mapping plus blind review and the user's Decisions A/B
  (2026-09-27; `false_synonym` rename 2026-10-04). Matched to each fixture error by
  `(item_id, error_index)`; the build fails on any unmatched error or unused label, and on any
  `learner_form`/`corrected_form` disagreement.
- **Per error:** `subtype` = `subtype_v6_target` = overlay `v6_type`; `severity_v2` = overlay
  `v6_severity`; `explanation_variant` (`wrong_word` | `wrong_sense` | `false_synonym`) on
  `word_choice` errors, plus `variant_uncertain: true` where the reviewer flagged it;
  `subtype_v5_target` kept as provenance. Spans and forms are carried unchanged.
  `severity_v1` (pre-TASK-625 residue) is dropped — `severity_v2` may have moved under v6.
- **Bands:** accuracy/fidelity/understandability re-derived with
  `derive_bands(offline=True, taxonomy_version=6)` (dimensions from `merged_taxonomy.json`
  via `dt_gold_seed_helper.V6_DIMENSION`). range/naturalness are adjudicated inputs and are
  carried over unchanged. Every item passes `verify_item`.
- **en_silver_24** carries its `meaning_inversion`/critical error (subject/object swap). The
  silver merge had dropped it; `en_final3.json` was repaired on 2026-09-28 from
  `en_silver_24_fix.json`, and the build re-inserts it from that file if ever fed a pre-repair
  source.

## Held out

- **en_silver_26** (`90 → 9 degrees`) is **not** in `dt_silver_v6/en.json`. Its only error was
  dropped at the silver merge for lack of a severity majority (votes critical/minor/major), so
  it is `kind=single` with 0 errors, fails `verify_item`, and has no overlay label. It needs a
  tie-break label (the en_silver_24 route) before it can join. The build fails if the item gains
  errors upstream while still held out.

## Band changes vs the v5 expected_bands

11 items (`[v5, v6]`): zh_silver_11, zh_silver_18, zh_silver_37, ja_silver_19, en_seed_10,
en_seed_15, en_multi_03, en_multi_04, en_silver_13, en_silver_17, en_silver_22 — identical to
`overlay_band_changes.json`. That file lists a 12th, en_silver_24, only because it was computed
before the 2026-09-28 repair (no error → understandability 2→4). With the error restored,
`meaning_inversion`/critical derives the same 4/2/1 as the v5 `word_choice`/critical label, so it
is unchanged.
