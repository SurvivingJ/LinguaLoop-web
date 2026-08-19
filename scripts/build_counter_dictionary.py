#!/usr/bin/env python3
"""Seed the Japanese counter (助数詞) dictionary — TASK-530.

The Japanese sibling of ``build_classifier_dictionary.py``. Populates
``dim_counter_distractor_groups``, ``dim_counters`` and
``dim_counter_noun_pairs`` from the curated tables below, which are the
starting corpus the drill and ``counter_match`` both read.

Why the data is hand-curated rather than mined
----------------------------------------------
There is no CC-CEDICT equivalent for Japanese counters — JMdict does not
record which counter a noun takes. Mining it from a corpus is possible but
noisy in the way that matters most: 匹 and 頭 both appear with 犬 in real text
(頭 for large or working dogs), and a frequency-ranked miner would present the
minority reading as simply wrong. The curated set below encodes the pedagogic
answer; ``generate_counter_curation.py`` extends coverage with an LLM pass
whose output is reviewed before merge — the same division of labour as the
classifier pipeline.

Multi-acceptable counters are recorded as multiple rows, with ``is_primary``
marking the one taught first. うさぎ genuinely takes both 羽 (traditional) and
匹 (ordinary modern usage); marking either "wrong" would teach a falsehood, so
the drill accepts both.

Usage
-----
    PYTHONPATH=. python scripts/build_counter_dictionary.py --dry-run
    PYTHONPATH=. python scripts/build_counter_dictionary.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from services.supabase_factory import SupabaseFactory, get_supabase_admin

logger = logging.getLogger('build_counter_dictionary')

JA_LANGUAGE_ID = 3

# ---------------------------------------------------------------------------
# Distractor groups
# ---------------------------------------------------------------------------
# A group is "counters a learner could plausibly confuse for this noun". Foils
# come from the answer's own group, because a foil from an unrelated group
# (枚 for a cat) is rejected on sight and tests nothing.
#
# 'general' is special: the RPC skips it when picking foils, because つ/個 are
# acceptable for so many nouns that using them as distractors would produce
# items with more than one defensible answer.
GROUPS = [
    (1,  'general',        'Universal counters (つ/個) — never used as foils'),
    (2,  'people',         'People and person-like referents'),
    (3,  'animals',        'Animals, split by size and traditional class'),
    (4,  'long_thin',      'Long cylindrical objects'),
    (5,  'flat_thin',      'Flat thin objects'),
    (6,  'bound_volumes',  'Books and bound printed matter'),
    (7,  'machines',       'Machines, vehicles and large appliances'),
    (8,  'vessels',        'Cups, glasses and bowls of a substance'),
    (9,  'buildings',      'Buildings, premises and storeys'),
    (10, 'clothing',       'Garments and worn items'),
    (11, 'correspondence', 'Letters, documents and messages'),
    (12, 'occurrences',    'Times, occasions and repetitions'),
    (13, 'food_portions',  'Portions and servings'),
    (14, 'groupings',      'Sets, pairs, bundles and rows'),
]

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
# (id, counter, reading, semantic_label, group_id, difficulty_tier,
#  frequency_rank, numeral_readings)
#
# numeral_readings records only the numerals whose reading is IRREGULAR. The
# euphonic changes (一本 いっぽん, 三本 さんぼん, 六本 ろっぽん) are the actual
# difficulty of Japanese counters: a learner who has memorised 本 without them
# still cannot say "three pens".
COUNTERS = [
    # --- general -----------------------------------------------------------
    (1, 'つ', 'つ', 'general native-series counter', 1, 1, 1,
     {'1': 'ひとつ', '2': 'ふたつ', '3': 'みっつ', '4': 'よっつ', '5': 'いつつ',
      '6': 'むっつ', '7': 'ななつ', '8': 'やっつ', '9': 'ここのつ', '10': 'とお'}),
    (2, '個', 'こ', 'small discrete objects', 1, 1, 2,
     {'1': 'いっこ', '6': 'ろっこ', '8': 'はっこ', '10': 'じゅっこ'}),
    # --- people ------------------------------------------------------------
    (3, '人', 'にん', 'people', 2, 1, 3,
     {'1': 'ひとり', '2': 'ふたり', '4': 'よにん'}),
    (4, '名', 'めい', 'people (formal / bookings)', 2, 2, 20, {}),
    (5, '方', 'かた', 'people (honorific)', 2, 3, 60, {}),
    (45, '名様', 'めいさま', 'people (honorific, service register)', 2, 4, 135, {}),
    # --- animals -----------------------------------------------------------
    (6, '匹', 'ひき', 'small animals, fish, insects', 3, 1, 5,
     {'1': 'いっぴき', '3': 'さんびき', '6': 'ろっぴき', '8': 'はっぴき',
      '10': 'じゅっぴき'}),
    (7, '頭', 'とう', 'large animals', 3, 2, 25, {}),
    (8, '羽', 'わ', 'birds and rabbits', 3, 2, 40,
     {'3': 'さんば', '6': 'ろっぱ'}),
    (9, '尾', 'び', 'fish (fishmonger / culinary)', 3, 4, 90, {}),
    # --- long thin ---------------------------------------------------------
    (10, '本', 'ほん', 'long cylindrical objects', 4, 1, 4,
     {'1': 'いっぽん', '3': 'さんぼん', '6': 'ろっぽん', '8': 'はっぽん',
      '10': 'じゅっぽん'}),
    (11, '筋', 'すじ', 'streaks, threads of something', 4, 5, 120, {}),
    (12, '振り', 'ふり', 'swords', 4, 5, 140, {}),
    (46, '条', 'じょう', 'streets, streaks, clauses', 4, 5, 145, {}),
    # --- flat thin ---------------------------------------------------------
    (13, '枚', 'まい', 'flat thin objects', 5, 1, 6, {}),
    (14, '葉', 'よう', 'leaves, photographs (literary)', 5, 5, 130, {}),
    (47, '片', 'へん', 'fragments, petals', 5, 5, 150, {}),
    (48, '帖', 'じょう', 'folded paper, tatami sets', 5, 5, 155, {}),
    # --- bound volumes -----------------------------------------------------
    (15, '冊', 'さつ', 'books and bound volumes', 6, 1, 12,
     {'1': 'いっさつ', '8': 'はっさつ', '10': 'じゅっさつ'}),
    (16, '部', 'ぶ', 'copies of a publication', 6, 3, 70, {}),
    (17, '巻', 'かん', 'volumes in a series, scrolls', 6, 3, 80, {}),
    (49, '編', 'へん', 'literary works, compilations', 6, 5, 160, {}),
    # --- machines ----------------------------------------------------------
    (18, '台', 'だい', 'machines, vehicles, appliances', 7, 1, 8, {}),
    (19, '機', 'き', 'aircraft', 7, 4, 100, {}),
    (20, '隻', 'せき', 'ships', 7, 4, 95, {}),
    (21, '両', 'りょう', 'railway carriages', 7, 4, 110, {}),
    # --- vessels -----------------------------------------------------------
    (22, '杯', 'はい', 'cupfuls, glassfuls, bowlfuls', 8, 1, 15,
     {'1': 'いっぱい', '3': 'さんばい', '6': 'ろっぱい', '8': 'はっぱい',
      '10': 'じゅっぱい'}),
    (23, '缶', 'かん', 'cans', 8, 3, 85, {}),
    (24, '瓶', 'びん', 'bottles (as containers of contents)', 8, 3, 88, {}),
    (50, '袋', 'ふくろ', 'bagfuls', 8, 4, 112, {}),
    # --- buildings ---------------------------------------------------------
    (25, '軒', 'けん', 'houses, shops', 9, 2, 30,
     {'1': 'いっけん', '3': 'さんげん', '6': 'ろっけん', '10': 'じゅっけん'}),
    (26, '棟', 'むね', 'buildings (blocks)', 9, 4, 105, {}),
    (27, '階', 'かい', 'floors, storeys', 9, 2, 28,
     {'1': 'いっかい', '3': 'さんがい', '6': 'ろっかい', '10': 'じゅっかい'}),
    (28, '室', 'しつ', 'rooms', 9, 4, 115, {}),
    # --- clothing ----------------------------------------------------------
    (29, '着', 'ちゃく', 'garments (suits, coats, kimono)', 10, 2, 45, {}),
    (30, '足', 'そく', 'pairs of footwear', 10, 2, 50,
     {'1': 'いっそく', '3': 'さんぞく', '8': 'はっそく'}),
    (31, '点', 'てん', 'items (goods, artworks)', 10, 3, 65, {}),
    (51, '枝', 'し', 'accessories on a stem, sprays', 10, 5, 165, {}),
    # --- correspondence ----------------------------------------------------
    (32, '通', 'つう', 'letters, documents', 11, 2, 55, {}),
    (33, '件', 'けん', 'matters, cases, messages', 11, 2, 35, {}),
    (34, '章', 'しょう', 'chapters', 11, 4, 125, {}),
    (52, '項', 'こう', 'clauses, items in a list', 11, 5, 170, {}),
    # --- occurrences -------------------------------------------------------
    (35, '回', 'かい', 'times, occurrences', 12, 1, 10, {}),
    (36, '度', 'ど', 'times, degrees', 12, 2, 33, {}),
    (37, '番', 'ばん', 'ordinal turns, numbers', 12, 2, 38, {}),
    (53, '遍', 'へん', 'repetitions (colloquial)', 12, 5, 175, {}),
    # --- food portions -----------------------------------------------------
    (38, '皿', 'さら', 'plates of food', 13, 3, 75, {}),
    (39, '切れ', 'きれ', 'slices', 13, 3, 78, {}),
    (40, '人前', 'にんまえ', 'servings for N people', 13, 4, 118, {}),
    (54, '玉', 'たま', 'balls of noodles, round portions', 13, 5, 180, {}),
    # --- groupings ---------------------------------------------------------
    (41, '組', 'くみ', 'sets, pairs, groups', 14, 3, 68, {}),
    (42, '束', 'たば', 'bundles', 14, 4, 108, {}),
    (43, '対', 'つい', 'matched pairs', 14, 4, 122, {}),
    (44, '列', 'れつ', 'rows, lines', 14, 4, 128, {}),
]

# ---------------------------------------------------------------------------
# Noun -> counter pairs
# ---------------------------------------------------------------------------
# counter_id -> [nouns]. The common counters carry >= 10 nouns each (the
# TASK-530 acceptance bar); the specialist ones carry fewer because their real
# coverage IS small.
PAIRS = {
    3:  ['人', '学生', '子供', '先生', '友達', '客', '大人', '医者',
         '選手', '警官', '社員', '兄弟'],                              # 人
    6:  ['猫', '犬', '魚', '虫', '鳥', '蛇', '兎', '鼠',
         '蛙', '亀', '蝶', '金魚'],                                    # 匹
    7:  ['牛', '馬', '象', '熊', '獅子', '豚', '鹿', '虎',
         '羊', '駱駝'],                                                # 頭
    8:  ['鶏', '鶴', '雀', '鳩', '烏', '白鳥', '鴨', '鷲',
         '燕', '梟'],                                                  # 羽
    10: ['ペン', '鉛筆', '傘', '瓶', '木', '道', '川', '足',
         '電話', '映画', '歯', '指', 'バナナ', '煙草'],                # 本
    13: ['紙', '写真', 'シャツ', '皿', '切符', '葉書', 'CD', '布団',
         'ピザ', 'チケット', 'カード', '毛布'],                        # 枚
    15: ['本', 'ノート', '雑誌', '辞書', '教科書', '漫画', '手帳', '小説',
         '絵本', '日記'],                                              # 冊
    18: ['車', 'コンピュータ', 'テレビ', '冷蔵庫', '洗濯機', '自転車', 'カメラ',
         'ピアノ', 'エアコン', 'バス', '電子レンジ', 'プリンター'],     # 台
    22: ['コーヒー', 'お茶', '水', 'ビール', 'ご飯', 'ワイン', 'ジュース',
         'スープ', '牛乳', '味噌汁'],                                  # 杯
    25: ['家', '店', '銀行', '病院', 'レストラン', '本屋', '喫茶店', '薬局'],   # 軒
    35: ['試験', '旅行', '会議', '練習', '試合', '授業', '面接', '手術'],       # 回
    2:  ['卵', 'りんご', '箱', '石鹸', '飴', 'ボール', 'みかん', '消しゴム'],   # 個
    1:  ['椅子', '机', '窓', '鞄', '夢', '方法'],                      # つ
    4:  ['客', '参加者', '予約'],                                      # 名
    29: ['スーツ', 'コート', '着物', 'ドレス', '浴衣'],                # 着
    30: ['靴', '靴下', 'スリッパ', '長靴'],                            # 足
    32: ['手紙', 'メール', '書類'],                                    # 通
    # 階 has no noun pairs on purpose: it counts storeys, so the counted thing
    # is the floor itself rather than a noun a learner could be shown. It stays
    # in dim_counters as a plausible foil for the buildings group.
    20: ['船', 'ボート', 'ヨット'],                                    # 隻
    19: ['飛行機', 'ヘリコプター'],                                    # 機
    38: ['カレー', 'サラダ', 'パスタ'],                                # 皿
    39: ['ケーキ', 'パン', '肉', 'チーズ'],                            # 切れ
    41: ['トランプ', '夫婦', '茶碗'],                                  # 組
    16: ['新聞', '資料'],                                              # 部
    17: ['辞典'],                                                      # 巻
    33: ['事故', '注文'],                                              # 件
}

# Nouns whose second counter is genuinely acceptable. Recorded explicitly so
# the drill never marks a correct answer wrong. The counter a noun appears
# under in PAIRS is its primary; these are the alternates.
SECONDARY = {
    '兎':     [8],    # 匹 ordinary modern usage, 羽 traditional
    '鳥':     [8],    # 匹 for small caged birds, 羽 the general bird counter
    '魚':     [9],    # 匹 primary, 尾 in culinary/market register
    '漫画':   [17],   # 冊 for a volume, 巻 within a series
    'メール': [33],   # 通 as correspondence, 件 as a matter
    '葉書':   [32],   # 枚 as paper, 通 as correspondence
    '客':     [4],    # 人 ordinary, 名 in formal/booking register
}


def _merge_approved_curation():
    """Fold data/counter_curation/approved_curation.json into the curated
    tables, if present (produced by merge_counter_curation.py).

    New counters are appended to COUNTERS; accepted nouns are merged into PAIRS
    (first counter listed for a noun) and SECONDARY (the rest). No-op when the
    file is absent, so the plain in-file curated build still works unchanged.

    Curated counters keep their hand-written ``numeral_readings``: the euphonic
    changes (一本 いっぽん, 三本 さんぼん) are the hardest part of the whole topic
    and the part a model gets wrong most often, so an LLM pass never overwrites
    them.
    """
    import json

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'counter_curation', 'approved_curation.json',
    )
    if not os.path.exists(path):
        logger.info('No approved_curation.json; building from in-file curated data only')
        return
    with open(path, 'r', encoding='utf-8') as fh:
        approved = json.load(fh)

    group_ids = {label: gid for gid, label, _ in GROUPS}
    by_counter = {row[1]: row[0] for row in COUNTERS}   # counter -> id
    next_id = max((row[0] for row in COUNTERS), default=0) + 1
    next_rank = max((row[6] for row in COUNTERS), default=0) + 1

    added_counters = 0
    for entry in approved.get('counters', []):
        counter = entry.get('counter')
        if not counter or counter in by_counter:
            continue
        group_id = group_ids.get(entry.get('group'))
        if group_id is None:
            logger.warning('%s: unknown group %r, skipping',
                           counter, entry.get('group'))
            continue
        COUNTERS.append((
            next_id, counter, entry.get('reading', ''),
            entry.get('semantic_label', ''), group_id,
            int(entry.get('difficulty_tier', 4)), next_rank, {},
        ))
        by_counter[counter] = next_id
        next_id += 1
        next_rank += 1
        added_counters += 1

    added_primary = 0
    added_secondary = 0
    for noun, counters in approved.get('noun_counters', {}).items():
        usable = [c for c in counters if c in by_counter]
        if not usable:
            continue
        primary_id = by_counter[usable[0]]
        bucket = PAIRS.setdefault(primary_id, [])
        if noun not in bucket:
            bucket.append(noun)
            added_primary += 1
        for alt in usable[1:]:
            alt_id = by_counter[alt]
            if alt_id == primary_id:
                continue
            alternates = SECONDARY.setdefault(noun, [])
            if alt_id not in alternates:
                alternates.append(alt_id)
                added_secondary += 1

    logger.info('Merged approved curation: +%d counters, +%d primary pairs, '
                '+%d secondary pairs', added_counters, added_primary,
                added_secondary)


def build_rows():
    """Materialise the three tables' rows from the curated tables above."""
    groups = [{'id': gid, 'label': label, 'description': desc}
              for gid, label, desc in GROUPS]

    counters = []
    for (cid, counter, reading, label, group_id, tier, rank, numerals) in COUNTERS:
        counters.append({
            'id': cid,
            'language_id': JA_LANGUAGE_ID,
            'counter': counter,
            'reading': reading,
            'semantic_label': label,
            'example_nouns': (PAIRS.get(cid) or [])[:5],
            'numeral_readings': numerals or None,
            'frequency_rank': rank,
            'distractor_group_id': group_id,
            'difficulty_tier': tier,
        })

    seen = set()
    pairs = []
    for counter_id, nouns in PAIRS.items():
        for noun in nouns:
            key = (noun, counter_id)
            if key in seen:
                continue
            seen.add(key)
            pairs.append({
                'language_id': JA_LANGUAGE_ID,
                'lemma_text': noun,
                'counter_id': counter_id,
                'is_primary': True,
                'frequency_score': 1.0,
                'source': 'curated',
            })

    for noun, counter_ids in SECONDARY.items():
        for counter_id in counter_ids:
            key = (noun, counter_id)
            if key in seen:
                continue
            seen.add(key)
            pairs.append({
                'language_id': JA_LANGUAGE_ID,
                'lemma_text': noun,
                'counter_id': counter_id,
                'is_primary': False,
                'frequency_score': 0.5,
                'source': 'curated',
            })

    return groups, counters, pairs


def audit(counters, pairs) -> list:
    """Problems that would produce a broken drill item. Empty list = healthy."""
    problems = []

    known_groups = {gid for gid, _, _ in GROUPS}
    counter_ids = {c['id'] for c in counters}

    for counter in counters:
        if counter['distractor_group_id'] not in known_groups:
            problems.append(
                f"counter {counter['counter']} references unknown group "
                f"{counter['distractor_group_id']}")

    for pair in pairs:
        if pair['counter_id'] not in counter_ids:
            problems.append(f"pair {pair['lemma_text']} -> unknown counter "
                            f"{pair['counter_id']}")

    # Every non-'general' group needs >= 4 members, or the RPC cannot fill
    # three distractors from within the group and silently falls back to the
    # easy-tier top-up — which produces implausible foils.
    general = {gid for gid, label, _ in GROUPS if label == 'general'}
    by_group = {}
    for counter in counters:
        by_group.setdefault(counter['distractor_group_id'], []).append(counter)
    for gid, members in sorted(by_group.items()):
        if gid not in general and len(members) < 4:
            problems.append(
                f'group {gid} has only {len(members)} counters — the RPC will '
                f'top up from other groups for these nouns')

    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--dry-run', action='store_true',
                        help='report what would be written, write nothing')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    load_dotenv()

    # Fold in LLM-curated content (data/counter_curation/approved_curation.json)
    # before building, if present. No-op when the file is absent.
    _merge_approved_curation()

    groups, counters, pairs = build_rows()
    problems = audit(counters, pairs)

    nouns = {p['lemma_text'] for p in pairs}
    logger.info('%d groups, %d counters, %d pairs over %d distinct nouns',
                len(groups), len(counters), len(pairs), len(nouns))
    logger.info('%d tier-1 (common) counters',
                len([c for c in counters if c['difficulty_tier'] == 1]))
    for problem in problems:
        logger.warning('AUDIT: %s', problem)

    if args.dry_run:
        print(f'dry-run: {len(groups)} groups, {len(counters)} counters, '
              f'{len(pairs)} pairs, {len(problems)} audit warnings')
        return 0

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    db.table('dim_counter_distractor_groups').upsert(
        groups, on_conflict='id').execute()
    db.table('dim_counters').upsert(counters, on_conflict='id').execute()
    for start in range(0, len(pairs), 200):
        db.table('dim_counter_noun_pairs').upsert(
            pairs[start:start + 200],
            on_conflict='language_id,lemma_text,counter_id',
        ).execute()

    print(f'upserted: {len(groups)} groups, {len(counters)} counters, '
          f'{len(pairs)} pairs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
