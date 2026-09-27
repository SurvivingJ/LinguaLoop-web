"""
Read-only pull of ~60 tests/language from Supabase, stratified across target_age_tier.
Writes exp_b/sample_{zh,en,ja}.json and exp_b/sample_all.json. No DB writes anywhere.
"""
import json
import os
import random
import sys
from collections import defaultdict

from dotenv import load_dotenv

REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"
OUT_DIR = r"C:\Users\James\AppData\Local\Temp\claude\c--Users-James-Documents-Coding-LinguaLoop-WebApp\85c90266-52b8-4fb1-9376-5767d11d3e2a\scratchpad\exp_b"

load_dotenv(os.path.join(REPO, ".env"))

from supabase import create_client  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]

client = create_client(SUPABASE_URL, SUPABASE_KEY)

LANG_NAMES = {1: "zh", 2: "en", 3: "ja"}
TARGET_PER_LANG = 60
random.seed(20260926)

# --- Step 1: pull lightweight index of all active tests -------------------
print("Fetching lightweight test index...")
idx_rows = []
page = 0
page_size = 1000
while True:
    resp = (
        client.table("tests")
        .select("id,language_id,difficulty,target_age_tier,total_attempts,seeded_elo,is_active")
        .eq("is_active", True)
        .not_.is_("target_age_tier", "null")
        .range(page * page_size, page * page_size + page_size - 1)
        .execute()
    )
    rows = resp.data
    idx_rows.extend(rows)
    if len(rows) < page_size:
        break
    page += 1

print(f"Total active tests with target_age_tier: {len(idx_rows)}")

by_lang_tier = defaultdict(list)
for r in idx_rows:
    by_lang_tier[(r["language_id"], r["target_age_tier"])].append(r)

# --- Step 2: stratified sample per language ---------------------------------
sample_ids_by_lang = defaultdict(list)
for lang_id in (1, 2, 3):
    tiers_present = sorted({t for (l, t) in by_lang_tier if l == lang_id})
    if not tiers_present:
        continue
    per_tier_quota = max(1, TARGET_PER_LANG // len(tiers_present))
    chosen = []
    for t in tiers_present:
        pool = by_lang_tier[(lang_id, t)]
        random.shuffle(pool)
        # prefer tests with attempts (empirical signal) but don't exclude the rest
        pool.sort(key=lambda r: (r.get("total_attempts") or 0) > 0, reverse=True)
        chosen.extend(pool[:per_tier_quota])
    # top up to TARGET_PER_LANG from leftover pool across tiers if short
    if len(chosen) < TARGET_PER_LANG:
        chosen_ids = {c["id"] for c in chosen}
        leftover = [r for t in tiers_present for r in by_lang_tier[(lang_id, t)] if r["id"] not in chosen_ids]
        random.shuffle(leftover)
        chosen.extend(leftover[: TARGET_PER_LANG - len(chosen)])
    sample_ids_by_lang[lang_id] = [c["id"] for c in chosen[:TARGET_PER_LANG]]
    print(f"lang {lang_id} ({LANG_NAMES[lang_id]}): tiers={tiers_present} sampled={len(sample_ids_by_lang[lang_id])}")

all_ids = [i for ids in sample_ids_by_lang.values() for i in ids]
print(f"Total sampled ids: {len(all_ids)}")

# --- Step 3: pull full rows (incl. transcript) for sampled ids --------------
print("Fetching full rows for sampled tests...")
full_rows = {}
CHUNK = 50
for i in range(0, len(all_ids), CHUNK):
    chunk_ids = all_ids[i : i + CHUNK]
    resp = (
        client.table("tests")
        .select("id,language_id,difficulty,target_age_tier,transcript,title,seeded_elo,total_attempts,style,slug")
        .in_("id", chunk_ids)
        .execute()
    )
    for r in resp.data:
        full_rows[r["id"]] = r

# --- Step 4: pull test_attempts for sampled ids, aggregate locally ----------
print("Fetching test_attempts for empirical pass-rate/elo signal...")
attempts_by_test = defaultdict(list)
for i in range(0, len(all_ids), CHUNK):
    chunk_ids = all_ids[i : i + CHUNK]
    resp = (
        client.table("test_attempts")
        .select("test_id,percentage,test_elo_before,test_elo_after")
        .in_("test_id", chunk_ids)
        .execute()
    )
    for r in resp.data:
        attempts_by_test[r["test_id"]].append(r)

def agg(test_id):
    rows = attempts_by_test.get(test_id, [])
    if not rows:
        return {"n_attempts": 0, "mean_pct": None, "mean_test_elo_before": None}
    pcts = [r["percentage"] for r in rows if r["percentage"] is not None]
    elos = [r["test_elo_before"] for r in rows if r["test_elo_before"] is not None]
    return {
        "n_attempts": len(rows),
        "mean_pct": sum(pcts) / len(pcts) if pcts else None,
        "mean_test_elo_before": sum(elos) / len(elos) if elos else None,
    }

# --- Step 5: assemble + write per-language JSON -----------------------------
os.makedirs(OUT_DIR, exist_ok=True)
summary = {}
for lang_id, ids in sample_ids_by_lang.items():
    lang_code = LANG_NAMES[lang_id]
    items = []
    for tid in ids:
        row = full_rows.get(tid)
        if not row or not row.get("transcript"):
            continue
        a = agg(tid)
        items.append(
            {
                "id": row["id"],
                "language_id": lang_id,
                "language": lang_code,
                "difficulty": row["difficulty"],
                "target_age_tier": row["target_age_tier"],
                "tier_code": f"T{row['target_age_tier']}",
                "title": row.get("title"),
                "transcript": row["transcript"],
                "seeded_elo": row.get("seeded_elo"),
                "total_attempts_field": row.get("total_attempts"),
                **a,
            }
        )
    out_path = os.path.join(OUT_DIR, f"sample_{lang_code}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    summary[lang_code] = {
        "n": len(items),
        "by_tier": {t: sum(1 for it in items if it["tier_code"] == t) for t in sorted({it["tier_code"] for it in items})},
        "n_with_attempts": sum(1 for it in items if it["n_attempts"] > 0),
    }
    print(f"Wrote {out_path}: {len(items)} items")

with open(os.path.join(OUT_DIR, "sample_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False, indent=2))
