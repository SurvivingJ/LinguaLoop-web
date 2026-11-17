# Topic batch 2026-11-17 (zh + ja), staged and not yet imported

573 new topic entries for Chinese (zh, Mandarin, Simplified) and Japanese (ja): 248 zh-only, 258
ja-only and 67 shared (`languages: ["zh","ja"]`). Nothing in this directory has been written to the
database. No import, gatekeeper run, embedding call or SQL write was made while preparing it.

| File | What it is |
|------|------------|
| `<category-slug>.json` (35 files) | Importer-valid input, one file per category. Pass the file's category to `--category` when importing. |
| `manifest.json` / `manifest.csv` | Every entry with `topic, languages, category, target_age_tier, lens_code, keywords, keywords_zh, keywords_ja, shared, file`. This is the source of truth for tier and category. |
| `stamp_tiers.sql` | A fallback, **not executed**: it stamps `target_age_tier` after import if the importer is not patched first (see below). |

## Counts

### Per language × tier (new topics; shared ones are counted under both languages)

| Lang | T1 | T2 | T3 | T4 | T5 | T6 | Total |
|------|----|----|----|----|----|----|-------|
| zh new (of which shared) | 45 (15) | 45 (13) | 48 (10) | 60 (10) | 55 (9) | 62 (10) | 315 (67) |
| ja new (of which shared) | 45 (15) | 45 (13) | 52 (10) | 63 (10) | 57 (9) | 63 (10) | 325 (67) |

### Backlog per tier, existing → after import (existing counts from the 343-topic snapshot)

| Lang | T1 | T2 | T3 | T4 | T5 | T6 | Untiered (unchanged) |
|------|----|----|----|----|----|----|----------|
| zh | 21 → 66 | 22 → 67 | 23 → 71 | 20 → 80 | 172 → 227 | 23 → 85 | 43 |
| ja | 21 → 66 | 22 → 67 | 23 → 75 | 20 → 83 | 22 → 79 | 24 → 87 | 33 |

zh T5 was already heavy (172, mostly data-analytics and daily-life topics), so zh's professional weight
goes mainly to T6 and T4. At T5–T6, 65 of 117 zh topics and 64 of 120 ja topics are in economics,
finance, history, science and technology, law, society, medicine, military history or engineering.
About 21% of each language's new topics are shared.

### Per category (topic entries; a shared entry counts once)

| Category | File | zh-only | ja-only | shared | Total | New category? |
|----------|------|--------:|--------:|-------:|------:|:---:|
| Language & Literature | `language-and-literature.json` | 14 | 17 | 1 | 32 | |
| Economics | `economics.json` | 13 | 12 | 6 | 31 | yes |
| Festivals & Customs | `festivals-and-customs.json` | 13 | 14 | 0 | 27 | yes |
| Nature & Animals | `nature-and-animals.json` | 8 | 12 | 7 | 27 | yes |
| Finance & Investing | `finance-and-investing.json` | 13 | 8 | 5 | 26 | yes |
| Health & Medicine | `health-and-medicine.json` | 9 | 8 | 7 | 24 | |
| Cuisine & Food | `cuisine-and-food.json` | 12 | 11 | 0 | 23 | |
| History | `history.json` | 10 | 11 | 2 | 23 | |
| Science & Technology | `science-and-technology.json` | 8 | 7 | 8 | 23 | |
| Sports & Recreation | `sports-and-recreation.json` | 8 | 10 | 3 | 21 | |
| Philosophy & Religion | `philosophy-and-religion.json` | 10 | 9 | 2 | 21 | yes |
| Environment | `environment.json` | 6 | 7 | 5 | 18 | |
| Mathematics | `mathematics.json` | 7 | 4 | 5 | 16 | yes |
| Music & Performance | `music-and-performance.json` | 8 | 8 | 0 | 16 | |
| Travel & Geography | `travel-and-geography.json` | 8 | 7 | 0 | 15 | yes |
| Film, Anime & Games | `film-anime-and-games.json` | 6 | 9 | 0 | 15 | yes |
| Psychology | `psychology.json` | 5 | 6 | 4 | 15 | yes |
| Transportation | `transportation.json` | 5 | 9 | 0 | 14 | |
| Education | `education.json` | 7 | 6 | 1 | 14 | |
| Daily Life & Housing | `daily-life-and-housing.json` | 4 | 9 | 1 | 14 | yes |
| Art & Design | `art-and-design.json` | 7 | 6 | 0 | 13 | |
| Law | `law.json` | 7 | 6 | 0 | 13 | yes |
| Space & Astronomy | `space-and-astronomy.json` | 5 | 3 | 4 | 12 | yes |
| Media & Internet Culture | `media-and-internet-culture.json` | 7 | 4 | 1 | 12 | yes |
| Military History | `military-history.json` | 6 | 6 | 0 | 12 | yes |
| Agriculture | `agriculture.json` | 6 | 5 | 0 | 11 | |
| Engineering | `engineering.json` | 6 | 5 | 0 | 11 | yes |
| Society & Government | `society-and-government.json` | 5 | 6 | 0 | 11 | yes |
| Etiquette | `etiquette.json` | 3 | 7 | 0 | 10 | yes |
| Relationships | `relationships.json` | 3 | 4 | 3 | 10 | yes |
| Business & Commerce | `business-and-commerce.json` | 3 | 6 | 1 | 10 | |
| Fashion | `fashion.json` | 5 | 4 | 0 | 9 | |
| Work & Careers | `work-and-careers.json` | 3 | 6 | 0 | 9 | |
| Architecture | `architecture.json` | 5 | 4 | 0 | 9 | |
| Family | `family.json` | 3 | 2 | 1 | 6 | |

The lenses used are cultural 149, economic 90, practical 83, historical 81, scientific 77, social
69, environmental 17 and comparative 7. All are valid `dim_lens.lens_code` values.

## What the importer carries, and what it drops

The findings come from `services/topic_generation/json_importer.py`,
`import_orchestrator.py`, `database_client.py` and `services/test_generation/orchestrator.py`.

| Field in these files | Accepted by `validate_json`? | Reaches the `topics` row? |
|---|---|---|
| `topic`, `languages` | yes (required) | yes (`concept_english`, plus one queue row per language) |
| `keywords` | yes | yes (`keywords`, and the first five go into the novelty signature) |
| `lens_code` | yes | yes (`lens_id`; an unknown code falls back to `--lens`) |
| `target_age_tier` | yes (unknown keys are ignored) | **no** |
| `category` (per entry) | yes (ignored) | **no**: the whole file goes into `--category`, or `"Import: <filename>"` by default |
| `keywords_by_language` | yes (ignored) | **no** |

**Tier is the blocker.** `JSONTopicEntry` has no tier field, `entry_to_candidate()` never sets
`TopicCandidate.target_age_tier`, and `_process_entry()` calls `db.insert_topic(...)` without
`target_age_tier=`, even though `TopicDatabaseClient.insert_topic` already accepts it. The novelty
check also uses `threshold_for_tier(None)`, the flat 0.85. Test generation then **refuses**
untiered topics: `services/test_generation/orchestrator.py` (around line 381) raises
`ValueError("Topic ... has no target_age_tier set")`. If this batch is imported as-is, every queue
item for it fails until the tiers are stamped.

### Minimal importer change, so that tier is carried (not made; for you to apply)

1. `json_importer.py`, `JSONTopicEntry`: add `target_age_tier: Optional[int] = None`.
2. `json_importer.py`, `_validate_entry`: if `target_age_tier` is present and not `None`, require an
   `int` in 1–6 (reject `bool`).
3. `json_importer.py`, `parse_json`: pass `target_age_tier=item.get('target_age_tier')`.
4. `json_importer.py`, `entry_to_candidate`: pass `target_age_tier=entry.target_age_tier` to `TopicCandidate`.
5. `import_orchestrator.py`, `_process_entry`: use
   `threshold=topic_gen_config.threshold_for_tier(candidate.target_age_tier)`, and add
   `target_age_tier=candidate.target_age_tier` to the `self.db.insert_topic(...)` call. Then update
   the comment around line 269, which says the import path carries no tier.
6. Optional: let a per-entry `category` override `--category`, by resolving `_get_or_create_category`
   per distinct name. This is not needed for this batch, because the files are already one per category.

**Fallback if you import before patching:** run `stamp_tiers.sql` once, after all the files are in.
It sets `target_age_tier` by exact `concept_english` match, and only on rows where it is still `NULL`.
Do not use `scripts/backfill_topic_tiers.py --stamp-tiers` for this batch: it re-derives the tier
with jev, so it may disagree with the intended tier.

### Other importer facts that matter here

- **Shared topics are single entries with `languages: ["zh","ja"]`.** Their import `keywords` are
  English, and zh/ja keyword sets go in `keywords_by_language` and the manifest. I did not split
  them into per-language entries because the `topics` table has no language column and the novelty
  check is global (`match_topics_global`), so a second entry with the same concept would be rejected
  as a near-duplicate of the first, or would create two near-identical rows under `--skip-novelty`.
  English keywords are safe: `test_generation/agents/topic_translator.py` translates the concept and
  keywords into the target language before the prose is written.
- **18 categories are new.** `create_category` inserts them as `active` with `cooldown_days = 0`,
  so they also become eligible for the daily Explorer (`get_next_category`).
- **`--dry-run` does not write to the DB.** It skips category creation, topic insertion, queue
  insertion and the category counter. It does still call the embedding API and, unless
  `--skip-gatekeeper` is set, the gatekeeper LLM, so it costs money but gives a faithful novelty and
  gatekeeper preview against the live corpus. Topics within the same file are only compared with
  each other on a real run, because dry-run inserts nothing.

## Validation

`python -m scripts.run_topic_import --file <f> --validate-only` **could not run in the preparation
environment**. The module import chain (`json_importer` → `database_client` →
`services/supabase_factory`) needs the `postgrest` package, which was not installed. That is a
missing local dependency, not a DB call. As a fallback, I loaded the real
`JSONTopicImporter` (bypassing `services/topic_generation/__init__.py` and stubbing only
`services.supabase_factory`) and ran `validate_json`, `parse_json` and `entry_to_candidate` on every
file. All 35 files passed with 0 errors, and 573 entries parsed. 0 candidates carried a tier, which
confirms the finding above. In a fully installed environment, re-run the CLI check:

```bash
for f in data/topics/staged/2026-11-17/*.json; do
  case "$f" in *manifest.json) continue;; esac
  python -m scripts.run_topic_import --file "$f" --validate-only || echo "FAILED: $f"
done
```

## Dedup method

1. **Authoring:** I wrote the topics against the full list of the 343 existing topics, avoiding
   their concepts. For example, renting, mortgages, gaokao, 996, delivery riders, garbage sorting,
   red envelopes on WeChat, hanfu, square dancing, the double reduction policy and TCM vs Western
   medicine were all left out, or given a clearly different angle.
2. **Cross-language concept pass (manual):** the novelty check ignores language, so a zh topic and a
   ja topic about the same thing would collide. Pairs I removed or reframed for this reason:
   class-cleaning duty, abacus/soroban, multiplication rhymes/kuku, the moon rabbit legend, New Year
   money (otoshidama vs 压岁钱), typhoon days, the Harbin vs Sapporo snow festivals, part-time jobs,
   LINE vs WeChat read receipts, Zen vs Chan (ja uses wabi-sabi instead), the Kibo vs Tiangong space
   stations, and university entrance exams. I also dropped manzai, to stay clear of zh crosstalk.
3. **Automated check** (pure Python, 573 new × 573 new and 573 new × 343 existing):
   - TF-IDF cosine on the normalised English concept (lower-cased, stop words removed, light
     de-pluralising, unigrams and bigrams), flagged at ≥ 0.25;
   - an exact keyword-set overlap of ≥ 2 shared keywords, across en/zh/ja keyword sets;
   - a CJK-character Jaccard of ≥ 0.3 (with ≥ 4 shared characters) on keywords, to catch zh/ja
     pairs that share hanzi or kanji.

   This flagged 48 pairs, and I reviewed every one of them. None was a near-duplicate. The highest
   was 0.46 ("Learning to swim during the summer holiday" vs "Visiting grandma ... summer holidays"),
   and the rest were shared generic words such as *rain*, *moon*, *sleep* and *summer camp*.
   **Exact duplicates: 0.**
4. **Watchlist.** These pairs are distinct by design but sit close in embedding space. If a real
   import or dry run rejects one at the 0.85 global threshold, that is why:
   - **zh vs ja:** Peking opera vs kabuki; the Shanghai marriage market vs konkatsu; long-haul
     truckers vs the 2024 logistics problem; web novels vs isekai light novels; fan clubs (饭圈) vs
     oshikatsu; the demographic dividend vs the falling birth rate; the Tang Code vs the ritsuryō
     state; the arable-land red line vs the food self-sufficiency ratio; China's chips vs Rapidus /
     the 1986 semiconductor agreement; Dujiangyan vs the Tokyo flood channel.
   - **shared vs language-specific:** the 1997 Asian financial crisis vs ja's 1997 Yamaichi/Takugin
     collapse; the shared LLM topic vs zh tokenising Chinese.
   - **new vs existing:** ja renting (key money, guarantors) vs existing zh renting deposits; ja
     garbage day (T2) vs existing zh garbage sorting (T5); ja juku vs existing zh double reduction;
     ja work-style reform vs existing zh 996; zh red envelope from grandma (T1) vs existing WeChat
     red envelopes (T5); zh TCM modernisation vs existing TCM vs Western medicine.

## Sensitivity choices

Excluded on purpose: Tiananmen, Taiwan or Hong Kong sovereignty and politics, Xinjiang, Tibet, the
Cultural Revolution and the Great Leap Forward, COVID policy, the social credit system, Yasukuni,
wartime Japan–China topics, territorial disputes, Article 9, the Fukushima treated-water release and
the death penalty. Taiwan and Hong Kong appear only in cultural or economic framings: night markets,
Mazu, the Star Ferry, yum cha, the HKD peg, the MTR, Wong Kar-wai and Stock Connect.

The topics most likely to draw a gatekeeper flag are still neutral and explanatory, but you may
want to eyeball them:
- SOE reform and the laid-off workers of the 1990s;
- A-share retail investors and the "chives" metaphor;
- the Weibo trending list;
- the First Opium War;
- post-2023 deflationary pressure;
- the shared "balance-sheet recessions: Japan in the 1990s vs China today";
- the 1923 Kanto earthquake (framed as Tokyo's reconstruction).

## Import commands (run later, from the repo root)

Recommended order:
1. Apply the importer patch above.
2. Do a dry-run pass. It makes no DB writes, but it does cost embedding and LLM calls.
3. Do the real import.
4. Run `stamp_tiers.sql`, but only if you skipped the patch.

```bash
cd /path/to/LinguaLoop-web
for f in data/topics/staged/2026-11-17/*.json; do
  case "$f" in *manifest.json) continue;; esac
  cat=$(python -c "import json,sys; print(json.load(open(sys.argv[1]))['category'])" "$f")
  python -m scripts.run_topic_import --file "$f" --category "$cat" --dry-run      # preview
  # python -m scripts.run_topic_import --file "$f" --category "$cat"              # real import
done
```

Single-file example:

```bash
python -m scripts.run_topic_import \
  --file data/topics/staged/2026-11-17/economics.json --category "Economics"
```

The default `--lens cultural` only applies to entries without a `lens_code`, and every entry here
has one. Keep the gatekeeper and novelty checks **on**. Rejections are expected to be few, and they
are the safety net for the watchlist above.
