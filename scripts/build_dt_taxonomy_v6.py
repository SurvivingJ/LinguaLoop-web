#!/usr/bin/env python3
"""Build migrations/dt_taxonomy_v6_seed.sql from the ADR-031 source data (TASK-837).

The JSON under data/eval/taxonomy_merge_2026-09-27/ is the single source of truth
for Dual Translation taxonomy v6; this script turns it into the seed migration so
nobody hand-edits a 40 KB jsonb literal. Output is deterministic: re-running on
unchanged inputs rewrites the SQL byte-for-byte (LF line endings, fixed key order).

Inputs:
  * merged_taxonomy.json  - per-L2 v6 type lists (zh 20 / ja 23 / en 20) + fields.
                            List order IS the _decode_error subtype index contract.
  * v5_to_merged.csv      - every v5 subtype -> v6 type(s) with mapping kind.
  * v6_strings.json       - OPTIONAL (TASK-838): subtype_glosses / templates /
                            variant_templates. Absent -> those keys are emitted empty
                            and the seed header says it must not be activated.
  * migrations/dt_taxonomy_v5_seed.sql - v5 subtype_meta, copied verbatim for every
                            v5 slug that v6 drops/renames (historical aliases).

What the seed does: INSERT version 6 with is_active = false. It never deactivates
v5 and never touches another row; activation is TASK-853's cutover.

Usage:
  python scripts/build_dt_taxonomy_v6.py           # (re)write the seed
  python scripts/build_dt_taxonomy_v6.py --check   # exit 1 if the seed is stale
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import string
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "eval" / "taxonomy_merge_2026-09-27"
MERGED_PATH = DATA_DIR / "merged_taxonomy.json"
MAPPING_PATH = DATA_DIR / "v5_to_merged.csv"
STRINGS_PATH = DATA_DIR / "v6_strings.json"
V5_SEED_PATH = ROOT / "migrations" / "dt_taxonomy_v5_seed.sql"
OUT_PATH = ROOT / "migrations" / "dt_taxonomy_v6_seed.sql"

VERSION = 6
L2S = ("en", "ja", "zh")
# Same pair-key order as the v5 seed: each L2 baseline followed by its directed pairs.
PAIR_ORDER = ("en", "ja-en", "zh-en", "ja", "en-ja", "zh-ja", "zh", "en-zh", "ja-zh")
MAPPING_KINDS = ("1:1", "merge", "split", "dropped")

# Fields that must agree across languages for a slug to share one global
# subtype_meta entry (scoring reads only .dimension, but a disagreement on any of
# these would mean the global meta is wrong for some L2).
UNIFORM_FIELDS = ("dimension", "default_severity", "treatable", "cloze_suitable", "class")

# Split rows whose CSV target lists several v6 types: the bulk-remap target
# (ADR-031 user decision 2026-10-04 #2 - closest type, flagged for review).
CLOSEST_SPLIT_TARGET = {"particle": "case_particle"}

# ADR-031 / TASK-839-840: type judgements reviewed by AI (Opus) only.
NATIVE_REVIEW_FLAG = {
    "zh": ["separable_verb", "coverb", "connective (major)", "de_particle (scope: any 的/地/得 misuse)",
           "ba_bei", "complement", "semantic_anomaly", "contradiction", "meaning_inversion",
           "word_choice/false_synonym"],
    "ja": ["transitivity_voice", "modification", "clause_linkage", "kanji_choice (accuracy)",
           "wa_ga (narrowed)", "tam", "semantic_anomaly", "contradiction", "meaning_inversion",
           "script_choice (dropped)"],
    "en": ["complementation", "lexical_form (accuracy)", "pronoun (split; antecedent/number kept 2026-10-09)", "semantic_anomaly",
           "contradiction", "meaning_inversion"],
}


class BuildError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_merged(path: pathlib.Path = MERGED_PATH) -> dict[str, list[dict]]:
    merged = json.loads(path.read_text(encoding="utf-8"))
    if set(merged) != set(L2S):
        raise BuildError(f"{path.name}: expected languages {sorted(L2S)}, got {sorted(merged)}")
    for l2, types in merged.items():
        ids = [t["id"] for t in types]
        if len(ids) != len(set(ids)):
            raise BuildError(f"{path.name}: duplicate type id in {l2}")
    return merged


def load_v5_meta(path: pathlib.Path = V5_SEED_PATH) -> dict[str, dict]:
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", path.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        raise BuildError(f"no $taxonomy$ literal in {path.name}")
    return json.loads(m.group(1))["subtype_meta"]


def load_mapping(path: pathlib.Path = MAPPING_PATH) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("lang") or "").strip()]
    for r in rows:
        if r["mapping_kind"] not in MAPPING_KINDS:
            raise BuildError(f"{path.name}: unknown mapping_kind {r['mapping_kind']!r} for {r['v5_subtype']!r}")
    return rows


def load_strings(path: pathlib.Path = STRINGS_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# v6_strings.json validation (TASK-838)
# ---------------------------------------------------------------------------

STRING_LANGS = ("en", "ja", "zh")
# The only placeholders grader_cascade.render_explanation substitutes.
TEMPLATE_PLACEHOLDERS = {"learner_form", "corrected_form"}
PROVENANCE_TAGS = ("v5_verbatim", "ai_draft", "native_reviewed")
STRINGS_KEYS = {"_meta", "subtype_glosses", "templates", "variant_templates", "provenance", "v5_renamed_from"}
WORD_CHOICE_VARIANTS = ("wrong_word", "wrong_sense", "false_synonym")


def template_fields(template: str) -> set[str]:
    """Every str.format field name in a template (raises ValueError on a malformed brace)."""
    return {name for _, name, _, _ in string.Formatter().parse(template) if name is not None}


def _check_template(where: str, template) -> None:
    if not isinstance(template, str) or not template.strip():
        raise BuildError(f"{where}: empty template")
    try:
        fields = template_fields(template)
    except ValueError as exc:
        raise BuildError(f"{where}: bad template placeholders ({exc})") from exc
    if not fields <= TEMPLATE_PLACEHOLDERS:
        raise BuildError(f"{where}: unknown placeholders {sorted(fields - TEMPLATE_PLACEHOLDERS)}")
    try:
        template.format(learner_form="X", corrected_form="Y")
    except (ValueError, KeyError, IndexError) as exc:
        raise BuildError(f"{where}: bad template placeholders ({exc})") from exc


def validate_strings(strings: dict, merged: dict[str, list[dict]]) -> None:
    """Fail loudly unless every v6 pair slug has a gloss and a template in en/ja/zh,
    templates use only the explainer's placeholders, the word_choice variant
    templates are complete, and every string carries a provenance tag."""
    extra = set(strings) - STRINGS_KEYS
    if extra:
        raise BuildError(f"v6_strings.json: unknown top-level keys {sorted(extra)}")
    slugs = {t["id"] for l2 in L2S for t in merged[l2]}
    glosses, templates = strings.get("subtype_glosses", {}), strings.get("templates", {})
    for key, table in (("subtype_glosses", glosses), ("templates", templates)):
        stray = set(table) - slugs
        if stray:
            raise BuildError(f"v6_strings.json {key}: slugs not in v6 {sorted(stray)}")
    prov = strings.get("provenance", {})
    for slug in sorted(slugs):
        for lang in STRING_LANGS:
            gloss = glosses.get(slug, {}).get(lang)
            if not isinstance(gloss, str) or not gloss.strip():
                raise BuildError(f"subtype_glosses[{slug}][{lang}] missing")
            if "{" in gloss or "}" in gloss:
                raise BuildError(f"subtype_glosses[{slug}][{lang}] contains a brace")
            _check_template(f"templates[{slug}][{lang}]", templates.get(slug, {}).get(lang))
            for key in ("subtype_glosses", "templates"):
                tag = prov.get(key, {}).get(slug, {}).get(lang)
                if tag not in PROVENANCE_TAGS:
                    raise BuildError(f"provenance.{key}[{slug}][{lang}] = {tag!r}")
    variants = strings.get("variant_templates", {})
    if set(variants) != {"word_choice"} or set(variants["word_choice"]) != set(WORD_CHOICE_VARIANTS):
        raise BuildError("variant_templates must be exactly word_choice: wrong_word / wrong_sense / false_synonym")
    for variant in WORD_CHOICE_VARIANTS:
        for lang in STRING_LANGS:
            _check_template(f"variant_templates.word_choice[{variant}][{lang}]",
                            variants["word_choice"][variant].get(lang))
            tag = prov.get("variant_templates", {}).get("word_choice", {}).get(variant, {}).get(lang)
            if tag not in PROVENANCE_TAGS:
                raise BuildError(f"provenance.variant_templates.word_choice[{variant}][{lang}] = {tag!r}")


def ai_drafted_by_language(strings: dict) -> dict[str, list[str]]:
    """{lang: [slug, ...]} for every slug with an ai_draft gloss/template in that
    language (+ word_choice/<variant> entries) - the native-review flag list."""
    prov = strings.get("provenance", {})
    out: dict[str, list[str]] = {lang: [] for lang in STRING_LANGS}
    for key in ("subtype_glosses", "templates"):
        for slug, per_lang in prov.get(key, {}).items():
            for lang, tag in per_lang.items():
                if tag == "ai_draft" and slug not in out[lang]:
                    out[lang].append(slug)
    for variant, per_lang in prov.get("variant_templates", {}).get("word_choice", {}).items():
        for lang, tag in per_lang.items():
            if tag == "ai_draft":
                out[lang].append(f"word_choice/{variant}")
    return out


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

def build_pairs(merged: dict[str, list[dict]]) -> dict[str, dict]:
    pairs = {}
    for key in PAIR_ORDER:
        l2 = key.split("-")[-1]
        pairs[key] = {"subtypes": [t["id"] for t in merged[l2]]}
    return pairs


def _v6_meta_entry(slug: str, per_lang: dict[str, dict]) -> dict:
    first = next(iter(per_lang.values()))
    for field in UNIFORM_FIELDS:
        values = {l2: t[field] for l2, t in per_lang.items()}
        if len(set(map(json.dumps, values.values()))) > 1:
            raise BuildError(f"{slug}.{field} differs across languages {values}; a global subtype_meta cannot hold it")
    buckets = {l2: t["jev_bucket"] for l2, t in per_lang.items()}
    # jev buckets are per-language in jev itself; keep a scalar when every L2 that
    # carries the slug agrees, else an {l2: bucket} map (nothing reads it yet).
    jev_bucket = first["jev_bucket"] if len(set(buckets.values())) == 1 else buckets
    return {
        "dimension": first["dimension"],
        "default_severity": first["default_severity"],
        "treatable": first["treatable"],
        "cloze_suitable": first["cloze_suitable"],
        "jev_bucket": jev_bucket,
        "class": first["class"],
    }


def build_subtype_meta(merged: dict[str, list[dict]], v5_meta: dict[str, dict]) -> dict[str, dict]:
    by_slug: dict[str, dict[str, dict]] = {}
    for l2 in L2S:  # en, ja, zh - first-seen order, like v5
        for t in merged[l2]:
            by_slug.setdefault(t["id"], {})[l2] = t
    meta = {slug: _v6_meta_entry(slug, per_lang) for slug, per_lang in by_slug.items()}
    # Every v5 slug v6 no longer lists stays resolvable during the transition.
    for slug, v5_entry in v5_meta.items():
        if slug in meta:
            continue
        entry = dict(v5_entry)
        entry["historical_alias"] = True
        meta[slug] = entry
    return meta


def _v5_slug(raw: str) -> str:
    # "particle (historical_alias)" -> "particle"
    return raw.split("(")[0].strip()


def build_legacy_aliases(mapping: list[dict], merged: dict[str, list[dict]]) -> dict[str, dict]:
    v6_ids = {l2: {t["id"] for t in merged[l2]} for l2 in L2S}
    aliases: dict[str, dict] = {}
    for row in mapping:
        l2, slug, kind = row["lang"].strip(), _v5_slug(row["v5_subtype"]), row["mapping_kind"]
        target_raw = row["merged_type(s)"].strip()
        if kind == "dropped":
            target = None
        elif "|" in target_raw:
            if slug not in CLOSEST_SPLIT_TARGET:
                raise BuildError(f"{l2}/{slug}: multi-target {target_raw!r} needs a CLOSEST_SPLIT_TARGET entry")
            target = CLOSEST_SPLIT_TARGET[slug]
            if target not in target_raw.split("|"):
                raise BuildError(f"{l2}/{slug}: closest target {target!r} not among {target_raw!r}")
        else:
            target = target_raw
        if target is not None and target not in v6_ids[l2]:
            raise BuildError(f"{l2}/{slug}: target {target!r} is not a v6 {l2} type")
        entry = {"to": target, "kind": kind}
        if slug in aliases and aliases[slug] != entry:
            raise BuildError(f"{slug}: languages disagree on its mapping ({aliases[slug]} vs {entry})")
        aliases[slug] = entry
    return aliases


def build_taxonomy(merged, v5_meta, mapping, strings) -> dict:
    meta = build_subtype_meta(merged, v5_meta)
    aliases = build_legacy_aliases(mapping, merged)
    missing = set(v5_meta) - set(aliases)
    if missing:
        raise BuildError(f"v5 slugs with no v5_to_merged.csv row: {sorted(missing)}")
    unresolvable = [s for s in aliases if s not in meta]
    if unresolvable:
        raise BuildError(f"legacy slugs missing from subtype_meta: {unresolvable}")
    if strings is not None:
        validate_strings(strings, merged)
    strings = strings or {}
    taxonomy = {
        "pairs": build_pairs(merged),
        "subtype_meta": meta,
        "legacy_aliases": aliases,
        "subtype_glosses": strings.get("subtype_glosses", {}),
        "templates": strings.get("templates", {}),
    }
    if "variant_templates" in strings:
        taxonomy["variant_templates"] = strings["variant_templates"]
    return taxonomy


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _description(strings_present: bool) -> str:
    text = (
        "ADR-031 dual-translation taxonomy v6 (TASK-837) - v5 merged with the jev grammar taxonomy: "
        "EN 20 / JA 23 / ZH 20 types (8 shared translation-level types + jev grammar types + "
        "semantic_anomaly / contradiction / meaning_inversion). subtype_meta adds jev_bucket and class; "
        "every v5 slug v6 drops is kept as a historical_alias, and legacy_aliases maps all v5 slugs to v6 "
        "(1:1 / merge / split / dropped) for exemplar resolution and the cutover rewrite. Seeded INACTIVE; "
        "activated by the TASK-853 cutover. "
    )
    text += ("Glosses/templates from v6_strings.json (AI first draft, native review pending)."
             if strings_present else
             "Glosses/templates NOT yet authored (TASK-838) - do not activate.")
    return text


def _wrap_flag(label: str, items: list[str]) -> str:
    return "\n".join(textwrap.wrap(f"{label}: {', '.join(items)}", width=76,
                                   initial_indent="--   ", subsequent_indent="--       ",
                                   break_on_hyphens=False))


def _header(strings: dict | None) -> str:
    strings_present = strings is not None
    flag_lines = "\n".join(_wrap_flag(l2.upper(), items) for l2, items in NATIVE_REVIEW_FLAG.items())
    if strings_present:
        drafted = ai_drafted_by_language(strings)
        flag_lines += (
            "\n-- AI-DRAFTED STRINGS (provenance ai_draft in v6_strings.json; first drafts,\n"
            "-- same caveat as the v1-v5 seeds / ADR-019), by the language they are written in:\n"
            + "\n".join(_wrap_flag(lang.upper(), items) for lang, items in drafted.items() if items)
        )
    strings_line = (
        "--   subtype_glosses / templates / variant_templates merged from v6_strings.json\n"
        "--   (TASK-838; per-string provenance v5_verbatim | ai_draft lives in that file).\n"
        "--   variant_templates.word_choice[wrong_word|wrong_sense|false_synonym][l1] are\n"
        "--   the per-variant Rule templates (TASK-846); templates.word_choice is the fallback."
        if strings_present else
        "--   subtype_glosses / templates are EMPTY: v6_strings.json (TASK-838) does not\n"
        "--   exist yet. Under this row every gloss falls back to the bare slug and every\n"
        "--   explanation to the generic fallback - DO NOT ACTIVATE until it is regenerated."
    )
    return f"""-- ============================================================================
-- Dual Translation - taxonomy v6 seed (TASK-837, ADR-031 v5 + jev merge)
-- GENERATED by scripts/build_dt_taxonomy_v6.py from
-- data/eval/taxonomy_merge_2026-09-27/{{merged_taxonomy.json, v5_to_merged.csv}}
-- (+ v6_strings.json when present). DO NOT EDIT BY HAND - edit the source data
-- and re-run the builder (output is byte-identical on unchanged inputs).
--
-- INACTIVE SEED: inserts version 6 with is_active = false and touches no other
-- row. v5 stays the active taxonomy; activation is the TASK-853 cutover (run
-- after the TASK-852 history rewrite). Re-applying only refreshes taxonomy +
-- description - it never changes is_active.
--
-- Keys:
--   pairs           9 keys (en/ja/zh baselines + 6 directed L1-L2); each directed
--                   list equals its L2 baseline in merged_taxonomy.json order.
--                   Order IS the _decode_error index contract.
--   subtype_meta    global, keyed by slug: dimension, default_severity
--                   (minor|major|critical), treatable, cloze_suitable, jev_bucket,
--                   class. jev_bucket is a scalar when every L2 agrees, else an
--                   {{l2: bucket}} map (word_order, cohesion_connective,
--                   topic_comment). Every v5 slug absent from v6 is kept, copied
--                   from the v5 seed, with historical_alias: true and in no pairs
--                   list, so un-rewritten rows and a rollback restore still resolve.
--   legacy_aliases  {{v5_slug: {{to: v6 slug | null, kind: 1:1|merge|split|dropped}}}}
--                   for every v5_to_merged.csv row. Split rows map to the closest
--                   v6 type (particle -> case_particle); script_choice -> null.
--                   Read by exemplar resolution (TASK-841) and the rewrite (TASK-852).
{strings_line}
--
-- NATIVE-REVIEW FLAG (type judgements and strings are AI-reviewed only;
-- TASK-839 zh / TASK-840 ja, non-blocking for cutover per ADR-019):
{flag_lines}
--
-- Shape/totality/alias/safety guarded by tests/test_dual_translation_taxonomy_v6.py.
-- ============================================================================
"""


def render_sql(taxonomy: dict, strings: dict | None) -> str:
    strings_present = strings is not None
    body = json.dumps(taxonomy, ensure_ascii=False, indent=2)
    if "$taxonomy$" in body:
        raise BuildError("taxonomy JSON contains the $taxonomy$ dollar-quote tag")
    description = _description(strings_present)
    if "'" in description:
        raise BuildError("description must not contain a single quote")
    keys_line = ", ".join(taxonomy)
    return (
        _header(strings)
        + f"""
BEGIN;

-- Inactive upsert: no UPDATE of any other row, and ON CONFLICT leaves is_active alone.
INSERT INTO public.dt_taxonomy_version (version, is_active, taxonomy, description)
VALUES (
    {VERSION},
    false,
    $taxonomy${body}$taxonomy$::jsonb,
    '{description}'
)
ON CONFLICT (version) DO UPDATE
    SET taxonomy = EXCLUDED.taxonomy,
        description = EXCLUDED.description;

COMMIT;

-- ============================================================================
-- Verification (run manually after applying):
--   SELECT version, is_active FROM public.dt_taxonomy_version ORDER BY version;
--       -- expect a v6 row with is_active = false; the active row is still 5
--   SELECT jsonb_object_keys(taxonomy) FROM public.dt_taxonomy_version WHERE version = 6;
--       -- expect: {keys_line}
--   SELECT jsonb_array_length(taxonomy->'pairs'->'zh'->'subtypes'),
--          jsonb_array_length(taxonomy->'pairs'->'ja'->'subtypes'),
--          jsonb_array_length(taxonomy->'pairs'->'en'->'subtypes')
--     FROM public.dt_taxonomy_version WHERE version = 6;   -- expect 20, 23, 20
-- ============================================================================
"""
    )


def build_sql() -> str:
    strings = load_strings()
    taxonomy = build_taxonomy(load_merged(), load_v5_meta(), load_mapping(), strings)
    return render_sql(taxonomy, strings)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the seed on disk is stale; write nothing")
    args = ap.parse_args(argv)
    sql = build_sql()
    current = OUT_PATH.read_bytes().decode("utf-8") if OUT_PATH.exists() else None
    if args.check:
        if current != sql:
            print(f"STALE: {OUT_PATH.relative_to(ROOT)} differs from the builder output", file=sys.stderr)
            return 1
        print(f"OK: {OUT_PATH.relative_to(ROOT)} is up to date")
        return 0
    with OUT_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(sql)
    print(f"{'unchanged' if current == sql else 'wrote'}: {OUT_PATH.relative_to(ROOT)} ({len(sql.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
