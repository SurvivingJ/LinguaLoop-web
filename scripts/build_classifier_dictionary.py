#!/usr/bin/env python3
"""
Classifier Dictionary Builder (Mandarin Chinese)

Populates dim_classifier_distractor_groups, dim_classifiers, and
dim_classifier_noun_pairs from a curated, hand-vetted noun-classifier
mapping bundled in this file. No LLM. Fully deterministic and reproducible.

This is the *core curated* layer. Long-tail nouns come from CC-CEDICT via
scripts/import_cedict_classifiers.py, which runs after this script.

The curated dictionary covers ~55 high-frequency classifiers organised into
12 distractor groups, plus ~350 noun mappings (HSK 1-4 + extensions).
Each classifier carries a difficulty_tier (1=core 10, 2=HSK 3-4, 3=HSK 5+,
4=rare) which drives per-user level gating.

Usage:
    python scripts/build_classifier_dictionary.py            # full rebuild
    python scripts/build_classifier_dictionary.py --dry-run  # preview only
"""

import os
import sys
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin

if not SupabaseFactory.is_initialized():
    SupabaseFactory.initialize()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LANGUAGE_ID_ZH = 1


# ============================================================================
# DISTRACTOR GROUPS — semantic confusability buckets
# ============================================================================
GROUPS = [
    ('general',    'General / fallback'),
    ('people',     'People'),
    ('animals',    'Animals'),
    ('long_thin',  'Long / thin objects'),
    ('flat',       'Flat objects'),
    ('bound',      'Bound objects (books, volumes)'),
    ('vehicles',   'Vehicles'),
    ('containers', 'Container measures'),
    ('places',     'Buildings and places'),
    ('garments',   'Garments and pairs'),
    ('events',     'Events and instances'),
    ('plants',     'Plants and flowers'),
]


# ============================================================================
# CLASSIFIERS — (hanzi, pinyin_tonenum, pinyin_display, group_label,
#                semantic_label, example_nouns, difficulty_tier)
# ============================================================================
# Tier semantics:
#   1 = core HSK 1-2 (~10 classifiers, unlock by default)
#   2 = HSK 3-4 (next tier; unlocks once 80% of tier 1 is mastered)
#   3 = HSK 5+
#   4 = advanced/rare
CLASSIFIERS = [
    # ----- Tier 1: core HSK 1-2 -----
    ('个', 'ge4',   'gè',  'general',    'general universal measure',          ['人', '苹果', '问题'], 1),
    ('只', 'zhi1',  'zhī', 'animals',    'small / medium animals; one of pair', ['猫', '狗', '鸟', '手'], 1),
    ('条', 'tiao2', 'tiáo','long_thin',  'long / flexible / strip-shaped',      ['鱼', '蛇', '河', '路', '裤子'], 1),
    ('张', 'zhang1','zhāng','flat',      'flat sheets; faces; mouths',          ['纸', '票', '床', '桌子', '照片'], 1),
    ('本', 'ben3',  'běn', 'bound',      'bound volumes',                       ['书', '杂志', '字典'], 1),
    ('辆', 'liang4','liàng','vehicles',  'wheeled land vehicles',               ['车', '汽车', '自行车'], 1),
    ('杯', 'bei1',  'bēi', 'containers', 'cup of (liquid)',                     ['水', '茶', '咖啡'], 1),
    ('件', 'jian4', 'jiàn','garments',   'clothing items; matters; affairs',    ['衣服', '毛衣', '事'], 1),
    ('双', 'shuang1','shuāng','garments','paired items',                        ['鞋', '袜子', '筷子'], 1),
    ('把', 'ba3',   'bǎ',  'long_thin',  'objects with a handle; handfuls',     ['刀', '伞', '钥匙'], 1),

    # ----- Tier 2: HSK 3-4 -----
    ('位', 'wei4',  'wèi', 'people',     'polite measure for people',           ['老师', '医生', '客人'], 2),
    ('名', 'ming2', 'míng','people',     'formal measure for ranked people',    ['学生', '士兵', '记者'], 2),
    ('口', 'kou3',  'kǒu', 'people',     'household members; mouths',           ['人', '猪'], 2),
    ('头', 'tou2',  'tóu', 'animals',    'large livestock',                     ['牛', '猪', '羊'], 2),
    ('匹', 'pi3',   'pǐ',  'animals',    'horse-like; bolt of cloth',           ['马', '骡子', '布'], 2),
    ('棵', 'ke1',   'kē',  'plants',     'trees and large plants',              ['树', '草', '白菜'], 2),
    ('朵', 'duo3',  'duǒ', 'plants',     'flowers and clouds',                  ['花', '云', '玫瑰'], 2),
    ('座', 'zuo4',  'zuò', 'places',     'mountains, buildings, bridges',       ['山', '楼', '城市', '桥'], 2),
    ('间', 'jian1', 'jiān','places',     'rooms',                               ['房间', '卧室', '教室'], 2),
    ('套', 'tao4',  'tào', 'garments',   'sets of things',                      ['衣服', '西装', '邮票'], 2),
    ('场', 'chang3','chǎng','events',    'events / matches / shows / rain',     ['电影', '比赛', '雨'], 2),
    ('次', 'ci4',   'cì',  'events',     'instances / times',                   ['机会', '比赛', '会议'], 2),
    ('顿', 'dun4',  'dùn', 'events',     'meals / scoldings',                   ['饭', '早饭', '午饭'], 2),
    ('部', 'bu4',   'bù',  'bound',      'films / novels / works / phones',     ['电影', '小说', '电话'], 2),
    ('群', 'qun2',  'qún', 'animals',    'crowds / herds / flocks',             ['人', '羊', '鸟'], 2),
    ('瓶', 'ping2', 'píng','containers', 'bottle of',                           ['水', '酒', '啤酒'], 2),
    ('块', 'kuai4', 'kuài','flat',       'chunks / slabs / pieces',             ['石头', '蛋糕', '肉', '糖', '面包'], 2),
    ('台', 'tai2',  'tái', 'general',    'stationary machines / electronics',   ['电脑', '电视', '冰箱', '钢琴'], 2),
    ('家', 'jia1',  'jiā', 'places',     'businesses / institutions / homes',   ['公司', '商店', '医院'], 2),
    ('首', 'shou3', 'shǒu','events',     'songs / poems',                       ['歌', '诗'], 2),

    # ----- Tier 3: HSK 5+ -----
    ('架', 'jia4',  'jià', 'vehicles',   'aircraft / mounted machines',         ['飞机', '钢琴', '相机'], 3),
    ('艘', 'sou1',  'sōu', 'vehicles',   'boats and ships',                     ['船', '军舰'], 3),
    ('列', 'lie4',  'liè', 'vehicles',   'trains',                              ['火车'], 3),
    ('支', 'zhi1',  'zhī', 'long_thin',  'pen-like rigid items; tunes; troops', ['笔', '烟', '枪'], 3),
    ('根', 'gen1',  'gēn', 'long_thin',  'thin rigid stick-like objects',       ['头发', '柱子', '香蕉'], 3),
    ('束', 'shu4',  'shù', 'plants',     'bouquet / bundle',                    ['花', '玫瑰', '光'], 3),
    ('包', 'bao1',  'bāo', 'containers', 'pack / bag of',                       ['烟', '糖', '饼干'], 3),
    ('袋', 'dai4',  'dài', 'containers', 'sack / large bag of',                 ['米', '面粉', '土豆'], 3),
    ('盒', 'he2',   'hé',  'containers', 'box of',                              ['烟', '巧克力', '饼干'], 3),
    ('碗', 'wan3',  'wǎn', 'containers', 'bowl of',                             ['饭', '面', '汤'], 3),
    ('片', 'pian4', 'piàn','flat',       'slice / thin flat fragment',          ['面包', '叶子', '肉', '药'], 3),
    ('面', 'mian4', 'miàn','flat',       'flat surfaces; mirrors; flags',       ['镜子', '旗子', '墙'], 3),
    ('册', 'ce4',   'cè',  'bound',      'volumes in a set',                    ['书', '画册'], 3),
    ('所', 'suo3',  'suǒ', 'places',     'institutions (school / hospital)',    ['学校', '医院', '大学'], 3),
    ('幅', 'fu2',   'fú',  'flat',       'paintings / scrolls / large flat',    ['画', '地图', '照片'], 3),
    ('枚', 'mei2',  'méi', 'flat',       'small flat objects (coins, stamps)',  ['硬币', '邮票', '戒指', '导弹'], 3),
    ('颗', 'ke1',   'kē',  'general',    'small round / heart-shaped objects',  ['星星', '牙', '心', '珍珠'], 3),
    ('串', 'chuan4','chuàn','plants',    'string / bunch of (grapes, keys)',    ['葡萄', '钥匙', '珍珠'], 3),
    ('阵', 'zhen4', 'zhèn','events',     'gusts / bursts (wind, applause)',     ['风', '雨', '掌声'], 3),
    ('壶', 'hu2',   'hú',  'containers', 'pot of (tea, water)',                 ['茶', '水', '酒'], 3),
    ('锅', 'guo1',  'guō', 'containers', 'pot of (soup, rice)',                 ['汤', '饭', '粥'], 3),

    # ----- Tier 4: advanced / rare -----
    ('栋', 'dong4', 'dòng','places',     'standalone buildings / apartments',   ['楼', '房子', '大厦'], 4),
    ('盆', 'pen2',  'pén', 'plants',     'potted plants; basin of',             ['花', '水'], 4),
    ('瓣', 'ban4',  'bàn', 'plants',     'cloves / segments (garlic, orange)',  ['蒜', '橘子', '花'], 4),
    ('则', 'ze2',   'zé',  'bound',      'news items / jokes / sayings',        ['新闻', '消息', '笑话'], 4),
]


# ============================================================================
# NOUN -> CLASSIFIER(S)
# ============================================================================
# First entry is canonical/primary. Type-mode accepts any acceptable answer.
NOUN_CLASSIFIERS = {
    # People
    '人':    ['个', '位', '口'],
    '老师':  ['位', '个'],
    '医生':  ['位', '个'],
    '学生':  ['个', '名'],
    '朋友':  ['个', '位'],
    '客人':  ['位', '个'],
    '孩子':  ['个'],
    '儿子':  ['个'],
    '女儿':  ['个'],
    '同学':  ['个', '位'],
    '同事':  ['位', '个'],
    '工人':  ['个', '名'],
    '记者':  ['名', '位'],
    '士兵':  ['名', '个'],
    '警察':  ['名', '位'],
    '司机':  ['位', '名'],

    # Animals
    '猫':    ['只'],
    '狗':    ['只', '条'],
    '鸟':    ['只'],
    '鸡':    ['只'],
    '鸭':    ['只'],
    '兔子':  ['只'],
    '老鼠':  ['只'],
    '熊猫':  ['只'],
    '狮子':  ['只', '头'],
    '老虎':  ['只', '头'],
    '鱼':    ['条'],
    '蛇':    ['条'],
    '龙':    ['条'],
    '鲨鱼':  ['条'],
    '牛':    ['头'],
    '猪':    ['头', '口'],
    '羊':    ['只', '头'],
    '驴':    ['头'],
    '象':    ['头'],
    '大象':  ['头'],
    '马':    ['匹'],
    '骡子':  ['匹'],

    # Vehicles
    '车':       ['辆'],
    '汽车':     ['辆'],
    '自行车':   ['辆'],
    '出租车':   ['辆'],
    '卡车':     ['辆'],
    '摩托车':   ['辆'],
    '公交车':   ['辆'],
    '面包车':   ['辆'],
    '火车':     ['列', '辆'],
    '地铁':     ['列', '辆'],
    '飞机':     ['架'],
    '直升机':   ['架'],
    '船':       ['艘'],
    '军舰':     ['艘'],
    '游艇':     ['艘'],

    # Books / bound / electronics
    '书':       ['本', '册'],
    '杂志':     ['本'],
    '笔记本':   ['本'],
    '字典':     ['本'],
    '词典':     ['部', '本'],
    '小说':     ['本', '部'],
    '日记':     ['本'],
    '画册':     ['本', '册'],
    '电影':     ['部', '场'],
    '电话':     ['部', '台'],
    '手机':     ['部'],
    '电视':     ['台'],
    '电脑':     ['台'],
    '冰箱':     ['台'],
    '空调':     ['台'],
    '洗衣机':   ['台'],
    '相机':     ['台', '架'],
    '钢琴':     ['架', '台'],
    '新闻':     ['则', '条'],
    '消息':     ['则', '条'],
    '笑话':     ['则', '个'],

    # Flat things
    '纸':       ['张'],
    '票':       ['张'],
    '床':       ['张'],
    '桌子':     ['张'],
    '椅子':     ['把'],
    '照片':     ['张', '幅'],
    '地图':     ['张', '幅'],
    '邮票':     ['张', '枚', '套'],
    '硬币':     ['枚'],
    '戒指':     ['枚', '只'],
    '画':       ['幅', '张'],
    '嘴':       ['张'],
    '脸':       ['张'],
    '面包':     ['片', '块'],
    '叶子':     ['片'],
    '肉':       ['片', '块'],
    '药':       ['片', '盒', '瓶'],
    '云':       ['朵', '片'],
    '镜子':     ['面'],
    '旗子':     ['面'],
    '国旗':     ['面'],
    '墙':       ['面', '堵'],
    '蛋糕':     ['块', '个'],
    '石头':     ['块'],
    '糖':       ['块', '袋', '包'],
    '巧克力':   ['块', '盒'],
    '香皂':     ['块'],
    '肥皂':     ['块'],

    # Long / thin
    '头发':     ['根'],
    '针':       ['根', '枚'],
    '柱子':     ['根'],
    '香蕉':     ['根', '个'],
    '黄瓜':     ['根'],
    '骨头':     ['根'],
    '笔':       ['支', '只'],
    '铅笔':     ['支'],
    '钢笔':     ['支'],
    '毛笔':     ['支'],
    '蜡烛':     ['支', '根'],
    '烟':       ['支', '包', '盒', '根'],
    '枪':       ['支'],
    '歌':       ['首', '支'],
    '舞':       ['支'],
    '诗':       ['首'],
    '河':       ['条'],
    '路':       ['条'],
    '街':       ['条'],
    '裤子':     ['条'],
    '裙子':     ['条', '件'],
    '毛巾':     ['条'],
    '腰带':     ['条'],
    '腿':       ['条'],
    '胳膊':     ['条'],
    '尾巴':     ['条'],
    '项链':     ['条'],
    '围巾':     ['条'],
    '刀':       ['把'],
    '伞':       ['把'],
    '钥匙':     ['把', '串'],
    '扇子':     ['把'],
    '剪刀':     ['把'],
    '梳子':     ['把'],

    # Containers
    '水':       ['杯', '瓶', '碗', '壶'],
    '茶':       ['杯', '壶'],
    '咖啡':     ['杯'],
    '酒':       ['瓶', '杯', '壶'],
    '啤酒':     ['瓶', '杯'],
    '可乐':     ['瓶', '杯'],
    '牛奶':     ['杯', '瓶'],
    '香水':     ['瓶'],
    '果汁':     ['杯', '瓶'],
    '饭':       ['碗', '顿', '锅'],
    '面':       ['碗'],
    '汤':       ['碗', '锅'],
    '粥':       ['碗', '锅'],
    '饼干':     ['盒', '包'],
    '盐':       ['包', '袋'],
    '米':       ['袋', '碗'],
    '面粉':     ['袋'],
    '土豆':     ['个', '袋'],

    # Buildings / places
    '山':       ['座'],
    '楼':       ['座', '栋'],
    '大厦':     ['座', '栋'],
    '城市':     ['座'],
    '桥':       ['座'],
    '庙':       ['座'],
    '雕像':     ['座'],
    '岛':       ['座'],
    '塔':       ['座'],
    '房间':     ['间'],
    '卧室':     ['间'],
    '教室':     ['间'],
    '办公室':   ['间'],
    '厨房':     ['间'],
    '浴室':     ['间'],
    '学校':     ['所'],
    '医院':     ['所', '家'],
    '大学':     ['所'],
    '房子':     ['所', '间', '栋'],
    '公园':     ['个', '座'],
    '银行':     ['家'],
    '商店':     ['家'],
    '饭馆':     ['家'],
    '餐厅':     ['家'],
    '公司':     ['家'],
    '工厂':     ['家', '座'],

    # Garments / pairs
    '衣服':     ['件', '套'],
    '毛衣':     ['件'],
    '衬衫':     ['件'],
    '外套':     ['件'],
    '大衣':     ['件'],
    '夹克':     ['件'],
    '礼物':     ['件', '份'],
    '事':       ['件'],
    '事情':     ['件'],
    '行李':     ['件'],
    '鞋':       ['双', '只'],
    '袜子':     ['双', '只'],
    '筷子':     ['双', '根'],
    '手套':     ['双', '只'],
    '眼睛':     ['双', '只'],
    '耳朵':     ['只', '双'],
    '手':       ['双', '只'],
    '脚':       ['只', '双'],
    '西装':     ['套', '件'],
    '家具':     ['套', '件'],

    # Events / instances
    '比赛':     ['场', '次'],
    '雨':       ['场', '阵'],
    '雪':       ['场'],
    '梦':       ['场', '个'],
    '考试':     ['场', '次'],
    '演出':     ['场', '次'],
    '会议':     ['次', '场'],
    '机会':     ['次', '个'],
    '风':       ['阵', '场'],
    '掌声':     ['阵'],
    '早饭':     ['顿'],
    '午饭':     ['顿'],
    '晚饭':     ['顿'],
    '早餐':     ['顿'],
    '午餐':     ['顿'],
    '晚餐':     ['顿'],

    # Plants
    '树':       ['棵'],
    '草':       ['棵', '根'],
    '白菜':     ['棵'],
    '葱':       ['棵', '根'],
    '蒜':       ['头', '瓣'],
    '花':       ['朵', '束', '盆'],
    '玫瑰':     ['朵', '束'],
    '葡萄':     ['串', '颗'],
    '荔枝':     ['颗', '串'],

    # Round / small
    '星星':     ['颗'],
    '珍珠':     ['颗', '串'],
    '心':       ['颗', '个'],
    '牙':       ['颗', '个'],

    # Common everyday objects
    '苹果':     ['个', '颗'],
    '橘子':     ['个', '瓣'],
    '梨':       ['个'],
    '西瓜':     ['个'],
    '鸡蛋':     ['个', '颗'],
    '问题':     ['个'],
    '想法':     ['个'],
    '建议':     ['个', '条'],
    '主意':     ['个'],
    '梦想':     ['个'],
    '故事':     ['个', '则'],
    '游戏':     ['个', '场'],

    # Body parts
    '头':       ['个'],
    '鼻子':     ['个'],
}


# ============================================================================
# BUILD
# ============================================================================

def _build_classifier_rows(group_id_map):
    rows = []
    for rank, (hanzi, pinyin, display, group, label, examples, tier) in enumerate(CLASSIFIERS, start=1):
        if group not in group_id_map:
            raise RuntimeError(f"Unknown distractor group '{group}' for classifier {hanzi}")
        rows.append({
            'language_id': LANGUAGE_ID_ZH,
            'hanzi': hanzi,
            'pinyin': pinyin,
            'pinyin_display': display,
            'semantic_label': label,
            'example_nouns': examples,
            'frequency_rank': rank,
            'distractor_group_id': group_id_map[group],
            'difficulty_tier': tier,
        })
    return rows


def _build_pair_rows(classifier_id_map, sense_id_map):
    rows = []
    skipped = []
    for noun_text, acceptable in NOUN_CLASSIFIERS.items():
        for idx, classifier_hanzi in enumerate(acceptable):
            if classifier_hanzi not in classifier_id_map:
                skipped.append((noun_text, classifier_hanzi))
                continue
            rows.append({
                'language_id': LANGUAGE_ID_ZH,
                'noun_sense_id': sense_id_map.get(noun_text),
                'lemma_text': noun_text,
                'classifier_id': classifier_id_map[classifier_hanzi],
                'is_primary': idx == 0,
                'frequency_score': 1.0 / (idx + 1),
                'source': 'curated',
            })
    return rows, skipped


def _fetch_sense_id_map(db):
    result = (
        db.table('dim_vocabulary')
          .select('id, lemma, dim_word_senses(id, sense_rank)')
          .eq('language_id', LANGUAGE_ID_ZH)
          .in_('lemma', list(NOUN_CLASSIFIERS.keys()))
          .execute()
    )
    sense_map = {}
    for row in result.data or []:
        lemma = row.get('lemma')
        senses = row.get('dim_word_senses') or []
        if not senses:
            continue
        senses.sort(key=lambda s: (s.get('sense_rank') or 999, s.get('id') or 0))
        sense_map[lemma] = senses[0]['id']
    return sense_map


def run(dry_run: bool = False):
    db = get_supabase_admin()

    # Distractor groups already seeded by migration
    grp_resp = db.table('dim_classifier_distractor_groups') \
        .select('id, label') \
        .eq('language_id', LANGUAGE_ID_ZH) \
        .execute()
    if not grp_resp.data:
        raise RuntimeError("dim_classifier_distractor_groups empty; apply add_classifier_drill_mode.sql first")
    group_id_map = {r['label']: r['id'] for r in grp_resp.data}
    logger.info(f"Loaded {len(group_id_map)} distractor groups")

    classifier_rows = _build_classifier_rows(group_id_map)
    logger.info(f"Prepared {len(classifier_rows)} classifier rows across {len(set(r['difficulty_tier'] for r in classifier_rows))} tiers")
    if dry_run:
        for r in classifier_rows[:5]:
            logger.info(f"  preview: {r}")

    if not dry_run:
        db.table('dim_classifier_noun_pairs').delete().eq('language_id', LANGUAGE_ID_ZH).execute()
        db.table('dim_classifiers').delete().eq('language_id', LANGUAGE_ID_ZH).execute()
        db.table('dim_classifiers').insert(classifier_rows).execute()
        logger.info(f"Inserted {len(classifier_rows)} classifiers")

    cls_resp = db.table('dim_classifiers') \
        .select('id, hanzi') \
        .eq('language_id', LANGUAGE_ID_ZH) \
        .execute()
    classifier_id_map = {r['hanzi']: r['id'] for r in cls_resp.data or []}

    sense_id_map = _fetch_sense_id_map(db)
    logger.info(f"Matched {len(sense_id_map)}/{len(NOUN_CLASSIFIERS)} nouns to dim_word_senses")

    pair_rows, skipped = _build_pair_rows(classifier_id_map, sense_id_map)
    logger.info(f"Prepared {len(pair_rows)} curated noun-classifier pairs")
    if skipped:
        logger.warning(f"Skipped {len(skipped)} pairs (classifier not in CLASSIFIERS):")
        for noun, cls in skipped[:30]:
            logger.warning(f"  {noun} -> {cls}")

    if dry_run:
        logger.info("Dry-run complete; no rows written")
        return

    for i in range(0, len(pair_rows), 500):
        chunk = pair_rows[i:i + 500]
        db.table('dim_classifier_noun_pairs').insert(chunk).execute()
    logger.info(f"Inserted {len(pair_rows)} curated noun-classifier pairs")
    logger.info("Curated build complete. Run import_cedict_classifiers.py for long-tail coverage.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build curated classifier dictionary for Chinese")
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()
    run(dry_run=args.dry_run)
