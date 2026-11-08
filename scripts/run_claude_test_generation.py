#!/usr/bin/env python3
"""Generate comprehension tests from a hand-written topic plan, with every
generation call served by headless Claude Code (``claude -p``).

This is the Claude Code counterpart of ``scripts/run_test_generation_cli.py``
and ``scripts/run_content_build.py``. It does not fork the pipeline: every test
still goes through ``TestGenerationOrchestrator._generate_test`` unchanged, from
topic translation through prose, jev tier, dedup, questions + judges, audio,
save, furigana/pitch, and sense matching/creation. This script only adds what a
curated plan needs and the batch runner cannot do:

* **Targets specific topics.** ``run_batch`` drains *any* pending queue item for
  the language (135 older ja items at the time of writing) and gives them a
  balanced tier schedule that ignores each topic's tier. Here each plan row
  becomes its own topic + queue item, run through ``run_single`` so the
  topic's ``target_age_tier`` is what the passage is written for.
* **A per-topic brief.** Format (dialogue, diary, notice…), grammar focus and a
  JLPT-level character range are appended to the live ``prose_generation``
  prompt via the ``extra_instruction`` hook the dedup retry already uses. The
  plan's own Japanese title replaces the topic-translation call, and the
  test row's ``style`` follows the format.
* **Headless Claude for every generation call, including phrase detection.**
  ``call_llm`` callers switch via ``set_default_provider('claude_cli')``. The
  one raw-client caller, ``PhraseDetector`` (fed ``ProseWriter.client``, which
  is hard-wired to OpenRouter), is rebuilt on the Claude client here.
* **Per-task models.** ``--author-model`` (default opus) serves prose, title
  and questions; ``--model`` (default sonnet) serves everything else (sense
  matching/creation, judges, phrase detection). See CLAUDE_CLI_MODEL_BY_TASK in
  services/claude_cli_client.py.

What deliberately stays off the Claude CLI (none of it is text generation):
jev tier assignment (OpenRouter decisions API; the per-language calibration
tables were fitted against jev, ADR-029), OpenAI embeddings (topic signature,
passage dedup) and Azure TTS. The run therefore still needs OPENROUTER_API_KEY,
OPENAI_API_KEY and the Azure speech keys in ``.env``.

Phases (comma-separated ``--phases``; default ``import,tests,report``)
---------------------------------------------------------------------
import     Plan rows → categories (created if missing), topics (with
           target_age_tier) and one pending production_queue row each.
           Idempotent: a row already imported is reused, never duplicated.
preflight  ``run_content_build``'s ladder preflight (prompt rows, models).
canary     ``run_content_build``'s one-sense ladder canary.
tests      One test per plan row through ``run_single``. A row that produced
           no test gets a fresh queue item on the next run. Checkpointed after
           every row.
assets     ``run_content_build``'s select + ladder phases over the senses the
           new tests introduced (word_assets + exercises), same provider.
report     Per-test table (tier target vs assigned, length, questions, senses)
           to stdout and ``data/content_builds/<run_id>.md``.

Usage
-----
    # parse the plan and print every brief — no network, no writes
    python scripts/run_claude_test_generation.py --dry-run --only 1-5

    # first five topics end to end
    python scripts/run_claude_test_generation.py --only 1-5

    # the rest, then build exercise assets for the new senses
    python scripts/run_claude_test_generation.py --resume <RUN_ID> \\
        --phases import,tests,assets,report --yes

State lives in ``data/content_builds/<run_id>.json`` (the same directory and
format as ``run_content_build``, extended with a ``plan`` section), so the
assets phase is literally run_content_build's code over this run's tests.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_PLAN = os.path.join(ROOT, 'data', 'topic_plans', 'ja_n5_n4_topics.md')
SKILL_FILE = os.path.join(
    ROOT, '.claude', 'skills', 'lingualoop-generation', 'SKILL.md',
)
ALL_PHASES = ('import', 'preflight', 'canary', 'tests', 'assets', 'report')
DEFAULT_PHASES = ('import', 'tests', 'report')

# Tasks the author model serves; everything else gets --model.
AUTHOR_TASKS = ('prose_generation', 'title_generation', 'question_*')

logger = logging.getLogger('claude_test_gen')


# ── the plan ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PlanRow:
    """One row of the topic plan table."""
    num: int
    level: str          # 'N5' | 'N4'
    tier: int           # 1-6, the generation target
    theme: str          # Japanese theme label, keys THEME_CATEGORY
    title_ja: str
    title_en: str
    fmt: str            # FORMAT_SPECS key
    grammar: str


# Passage length follows the JLPT level, not the tier: a past-tense N5 diary
# targets T2 (the ja T1 prompt allows present tense only) but stays N5-short.
LEVEL_CHAR_RANGE = {'N5': (80, 150), 'N4': (150, 300)}

# format -> (tests.style, Japanese instruction). tests_style_check allows
# academic | conversational | business | casual | technical.
FORMAT_SPECS = {
    'narrative': ('academic',
                  '地の文で書いた短い文章。一つの場面や話題について、順序よく説明する。'),
    'diary': ('casual',
              '一人称の日記。最初の行は「〇月〇日（〇曜日）」のような日付にする。'),
    'dialogue': ('conversational',
                 '二人の会話。各発話を新しい行にし、「田中：」「マリア：」のように話者の名前と全角コロンで始める。'
                 '最初に場面を説明する一文を置いてもよい。'),
    'notice': ('academic',
               'お知らせ・案内文。最初の行に短い見出しを書き、その後に読み手への説明を続ける。'),
    'email': ('casual',
              'メール。宛名（例：「山田先生」）で始め、あいさつ、本文、結び、差出人の名前で終える。'),
    'letter': ('casual',
               '手紙。宛名で始め、あいさつ、本文、結び、差出人の名前で終える。'),
}

# Theme -> (category name, lens code). Daily Life / Travel / Japanese Culture
# are created on first import (decision 2026-11-08); categories are shared, so
# topic generation for other languages will explore them too.
THEME_CATEGORY = {
    '自己紹介・家族': ('Family', 'social'),
    '毎日の生活': ('Daily Life', 'practical'),
    '食べ物': ('Cuisine & Food', 'practical'),
    '買い物': ('Daily Life', 'practical'),
    '町・交通': ('Transportation', 'practical'),
    '学校': ('Education', 'practical'),
    '仕事': ('Work & Careers', 'practical'),
    '趣味・週末': ('Sports & Recreation', 'social'),
    '季節・行事': ('Japanese Culture', 'cultural'),
    '健康': ('Health & Medicine', 'practical'),
    '旅行': ('Travel', 'practical'),
    '家・近所': ('Daily Life', 'practical'),
    '連絡・約束': ('Daily Life', 'social'),
    '文化・マナー': ('Japanese Culture', 'cultural'),
}
NEW_CATEGORY_DESCRIPTIONS = {
    'Daily Life': 'Everyday routines, errands, home, neighbourhood and communication.',
    'Travel': 'Trips, bookings, transport hubs, sightseeing and souvenirs.',
    'Japanese Culture': 'Seasons, festivals, customs and manners in Japan.',
}

_ROW_RE = re.compile(r'^\|\s*(\d+)\s*\|')


def normalise_format(raw: str) -> str:
    """'narrative (instructions)' -> 'narrative'; 'email/letter' -> 'email'."""
    base = re.sub(r'\(.*?\)', '', raw).strip().lower()
    base = base.split('/')[0].strip()
    if base not in FORMAT_SPECS:
        raise ValueError(f'unknown format {raw!r}')
    return base


def parse_plan(path: str) -> list[PlanRow]:
    """Read the plan's markdown table.

    Expected columns: # | Lvl | Tier | Theme | 日本語 | English | Format |
    Grammar focus. Raises on a malformed row rather than skipping it: a plan
    that silently loses rows reports a clean run with fewer tests.
    """
    rows: list[PlanRow] = []
    with open(path, encoding='utf-8') as fh:
        for lineno, line in enumerate(fh, 1):
            if not _ROW_RE.match(line):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) != 8:
                raise ValueError(f'{path}:{lineno}: expected 8 columns, got {len(cells)}')
            num, level, tier, theme, ja, en, fmt, grammar = cells
            if level not in LEVEL_CHAR_RANGE:
                raise ValueError(f'{path}:{lineno}: unknown level {level!r}')
            if not re.fullmatch(r'T[1-6]', tier):
                raise ValueError(f'{path}:{lineno}: bad tier {tier!r}')
            if theme not in THEME_CATEGORY:
                raise ValueError(f'{path}:{lineno}: theme {theme!r} has no category')
            rows.append(PlanRow(
                num=int(num), level=level, tier=int(tier[1:]), theme=theme,
                title_ja=ja, title_en=en, fmt=normalise_format(fmt),
                grammar=grammar,
            ))
    nums = [r.num for r in rows]
    if len(nums) != len(set(nums)):
        raise ValueError(f'{path}: duplicate row numbers')
    if not rows:
        raise ValueError(f'{path}: no plan rows found')
    return rows


def parse_only(spec: Optional[str]) -> Optional[set[int]]:
    """'1-5,9,12-13' -> {1,2,3,4,5,9,12,13}; None -> None (all rows)."""
    if not spec:
        return None
    out: set[int] = set()
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            lo, hi = (int(x) for x in part.split('-', 1))
            if lo > hi:
                raise ValueError(f'bad range {part!r}')
            out.update(range(lo, hi + 1))
        else:
            out.add(int(part))
    return out


# ── the brief ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TopicBrief:
    """Everything the generation wrappers need for one topic."""
    num: int
    title_ja: str
    style: str
    char_min: int
    char_max: int
    instruction: str


def build_brief(row: PlanRow) -> TopicBrief:
    """Render the per-topic instruction appended to the prose prompt.

    Written in Japanese to match the ja prose_generation template it is
    appended to, and phrased as an addition to that template's rules (which
    still govern register per tier) rather than a replacement.
    """
    style, fmt_text = FORMAT_SPECS[row.fmt]
    lo, hi = LEVEL_CHAR_RANGE[row.level]
    lines = [
        '',
        '---',
        '',
        '**このテストだけの追加指定（上の指定と矛盾する場合はこちらを優先）：**',
        '',
        f'*   **題名・場面:** 「{row.title_ja}」（{row.title_en}）。日本で暮らす人の、ふつうの日常の一場面として書く。',
        f'*   **形式:** {fmt_text}',
        f'*   **文法の焦点:** {row.grammar} を、文章の中で自然に2回以上使う。',
        f'*   **学習者のレベル:** JLPT {row.level}。語彙と文法は{row.level}までのものだけを使う。',
        f'*   **文字数:** {lo}〜{hi}文字。',
        '*   **登場人物:** 実在の人物や店の名前は使わない。名前は「田中さん」「マリアさん」のような一般的なものにする。',
        '*   **出力:** 本文のみ。マークダウン記号（#、*、- など）は使わない。',
    ]
    if row.level == 'N5' and row.tier >= 2:
        lines.append('*   **時制:** 過去形（〜ました／〜でした）を使ってよい。')
    lines.append('')
    return TopicBrief(
        num=row.num, title_ja=row.title_ja, style=style,
        char_min=lo, char_max=hi, instruction='\n'.join(lines),
    )


# ── the orchestrator ───────────────────────────────────────────────────────

def make_orchestrator_class():
    """Build the subclass lazily so ``--dry-run`` never imports the pipeline."""
    from services.llm_service import get_client
    from services.test_generation.orchestrator import TestGenerationOrchestrator
    from services.vocabulary.pipeline import VocabularyExtractionPipeline

    class ClaudeTestGenerationOrchestrator(TestGenerationOrchestrator):
        """TestGenerationOrchestrator with per-topic briefs and an all-Claude
        vocabulary path. No step of ``_generate_test`` is reimplemented: the
        brief is applied by wrapping three collaborators on this instance."""

        def __init__(self, briefs: dict, test_type: str = 'listening'):
            super().__init__()
            self.briefs = briefs                    # topic_id (str) -> TopicBrief
            # run_single -> _process_queue_item never passes test_type, so the
            # base class would always build 'listening'; apply it here.
            self.test_type = test_type
            self.test_ids: dict[str, str] = {}      # topic_id -> test_id
            self._tls = threading.local()
            self._lock = threading.Lock()

            # PhraseDetector calls client.chat.completions.create directly on
            # the client it is handed, and ProseWriter.client is hard-wired to
            # OpenRouter — the one generation call --provider would miss.
            claude = get_client('claude_cli')
            self.prose_writer.client = claude
            self.vocab_pipeline = VocabularyExtractionPipeline(
                openai_client=claude, db_client=self.db,
            )

            self._wrap_prose_writer()
            self._wrap_topic_translator()
            self._wrap_insert_test()

        def _brief(self) -> Optional[TopicBrief]:
            return getattr(self._tls, 'brief', None)

        def _wrap_prose_writer(self):
            original = self.prose_writer.generate_prose

            def generate_prose(*args, **kwargs):
                brief = self._brief()
                if brief is not None:
                    kwargs['word_count_min'] = brief.char_min
                    kwargs['word_count_max'] = brief.char_max
                    # Brief first, then the dedup nudge on a retry.
                    kwargs['extra_instruction'] = (
                        brief.instruction + (kwargs.get('extra_instruction') or '')
                    )
                return original(*args, **kwargs)

            self.prose_writer.generate_prose = generate_prose

        def _wrap_topic_translator(self):
            original = self.topic_translator.translate

            def translate(*args, **kwargs):
                brief = self._brief()
                if brief is not None:
                    # The plan already carries the Japanese title; translating
                    # the English one back would only lose it.
                    return brief.title_ja, []
                return original(*args, **kwargs)

            self.topic_translator.translate = translate

        def _wrap_insert_test(self):
            original = self.db.insert_test

            def insert_test(test):
                result = original(test)
                brief = self._brief()
                if brief is not None:
                    self.db.client.table('tests').update(
                        {'style': brief.style}
                    ).eq('id', str(test.id)).execute()
                with self._lock:
                    self.test_ids[str(test.topic_id)] = str(test.id)
                return result

            self.db.insert_test = insert_test

        def _generate_test(self, topic, *args, **kwargs):
            self._tls.brief = self.briefs.get(str(topic.id))
            kwargs['test_type'] = self.test_type
            try:
                return super()._generate_test(topic, *args, **kwargs)
            finally:
                self._tls.brief = None

    return ClaudeTestGenerationOrchestrator


# ── state ──────────────────────────────────────────────────────────────────

def new_state(args, rows: list[PlanRow]) -> dict:
    """A run_content_build-compatible state, plus this script's plan section."""
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    lang_ids = {'zh': 1, 'en': 2, 'ja': 3}
    return {
        'run_id': f'{args.language}-claude-{stamp}',
        'language': args.language,
        'language_id': lang_ids[args.language],
        'started': datetime.now(timezone.utc).isoformat(),
        'config': {
            'tests': len(rows), 'test_type': args.test_type, 'tier_id': None,
            'max_senses': args.max_senses, 'sense_workers': args.sense_workers,
            'canary_senses': 1,
            'plan': os.path.relpath(args.plan, ROOT),
            'author_model': args.author_model, 'model': args.model,
        },
        'phases_done': [],
        'tests': {'generated': 0, 'failed': 0, 'test_ids': []},
        'canary': {},
        'senses': {'selected': [], 'done': {}, 'failed': {}},
        'plan': {},      # str(num) -> {topic_id, queue_id, status, test_id, ...}
    }


# ── phases ─────────────────────────────────────────────────────────────────

def phase_import(db, state: dict, rows: list[PlanRow]) -> None:
    from services.topic_generation.agents.archivist import Archivist
    from services.topic_generation.agents.embedder import EmbeddingService
    from services.topic_generation.database_client import (
        TopicDatabaseClient as TopicDb,
    )

    tdb = TopicDb()
    embedder = EmbeddingService()
    archivist = Archivist.__new__(Archivist)   # signature builder only; no DB/LLM
    lid = state['language_id']
    pending_id = tdb._get_status_id('pending')

    categories: dict[str, object] = {}
    lenses: dict[str, object] = {}
    created = reused = 0
    print(f'\n── import: {len(rows)} plan rows ' + '─' * 40)

    for row in rows:
        entry = state['plan'].setdefault(str(row.num), {})
        if entry.get('topic_id') and entry.get('queue_id'):
            continue

        cat_name, lens_code = THEME_CATEGORY[row.theme]
        if cat_name not in categories:
            cat = tdb.get_category_by_name(cat_name)
            if cat is None:
                cat = tdb.create_category(
                    cat_name, NEW_CATEGORY_DESCRIPTIONS.get(cat_name),
                )
                print(f'  created category {cat_name!r} (id={cat.id})')
            categories[cat_name] = cat
        if lens_code not in lenses:
            lens = tdb.get_lens_by_code(lens_code)
            if lens is None:
                raise RuntimeError(f'lens {lens_code!r} not found')
            lenses[lens_code] = lens
        cat, lens = categories[cat_name], lenses[lens_code]

        # Reuse a topic this plan already created (state file lost or edited).
        existing = (db.table('topics').select('id')
                    .eq('concept_english', row.title_en)
                    .eq('category_id', cat.id).limit(1).execute().data)
        if existing:
            topic_id = existing[0]['id']
            reused += 1
        else:
            keywords = [f'JLPT {row.level}', row.fmt]
            signature = archivist.construct_semantic_signature(
                category_name=cat.name, concept=row.title_en,
                lens=lens, keywords=keywords,
            )
            topic_id = str(tdb.insert_topic(
                category_id=cat.id, concept=row.title_en, lens_id=lens.id,
                keywords=keywords, embedding=embedder.embed_single(signature),
                semantic_signature=signature, target_age_tier=row.tier,
            ))
            created += 1

        entry['topic_id'] = topic_id
        entry['queue_id'] = ensure_queue_item(db, topic_id, lid, pending_id)
        entry.setdefault('status', 'pending')
        save_state(state)

    print(f'  topics created={created} reused={reused}  '
          f'queued={sum(1 for r in rows if state["plan"][str(r.num)].get("queue_id"))}')


def ensure_queue_item(db, topic_id: str, language_id: int, pending_id: int) -> str:
    """The pending queue row for (topic, language), created if there is none."""
    found = (db.table('production_queue').select('id')
             .eq('topic_id', topic_id).eq('language_id', language_id)
             .eq('status_id', pending_id).limit(1).execute().data)
    if found:
        return found[0]['id']
    row = (db.table('production_queue').insert({
        'topic_id': topic_id, 'language_id': language_id,
        'status_id': pending_id,
    }).execute().data)[0]
    return row['id']


def phase_tests(db, state: dict, rows: list[PlanRow], workers: int,
                test_type: str = 'listening') -> None:
    from uuid import UUID
    from services.exercise_generation.judges.base import (
        BatchModeThreadPoolExecutor, batch_mode,
    )
    from services.jev_client import JevError
    from services.exercise_generation.judges.base import JudgeUnavailable
    from concurrent.futures import as_completed

    lid = state['language_id']
    todo = [r for r in rows if state['plan'].get(str(r.num), {}).get('status') != 'done']
    print(f'\n── tests: {len(todo)} of {len(rows)} rows × {workers} worker(s) '
          + '─' * 20)
    if not todo:
        print('  nothing to do')
        return
    missing = [r.num for r in todo if not state['plan'].get(str(r.num), {}).get('topic_id')]
    if missing:
        raise RuntimeError(f'rows {missing} not imported — run the import phase first')

    briefs = {state['plan'][str(r.num)]['topic_id']: build_brief(r) for r in todo}
    orchestrator = make_orchestrator_class()(briefs, test_type=test_type)
    pending_id = orchestrator.db._get_status_id('pending')

    # A row whose earlier attempt produced nothing has a completed/failed queue
    # item; give it a fresh pending one rather than editing history.
    for r in todo:
        entry = state['plan'][str(r.num)]
        entry['queue_id'] = ensure_queue_item(db, entry['topic_id'], lid, pending_id)
    save_state(state)

    def run_one(row: PlanRow) -> dict:
        entry = state['plan'][str(row.num)]
        t0 = time.time()
        n = orchestrator.run_single(UUID(entry['queue_id']))
        return {'generated': n, 'seconds': round(time.time() - t0, 1)}

    t_start = time.time()
    done = 0
    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run_one, r): r for r in todo}
            for fut in as_completed(futures):
                row = futures[fut]
                entry = state['plan'][str(row.num)]
                done += 1
                try:
                    out = fut.result()
                except (JudgeUnavailable, JevError) as exc:
                    # Infrastructure, not content: record and keep going would
                    # just fail every remaining row the same way.
                    entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                    save_state(state)
                    pool.shutdown(cancel_futures=True)
                    raise
                except Exception as exc:  # noqa: BLE001 — record, continue
                    entry.update(status='failed', error=f'{type(exc).__name__}: {exc}')
                    logger.error('row %d raised: %s', row.num, exc)
                else:
                    test_id = orchestrator.test_ids.get(entry['topic_id'])
                    if out['generated'] and test_id:
                        entry.update(status='done', test_id=test_id,
                                     seconds=out['seconds'], error=None)
                        entry.update(read_back(db, test_id))
                    else:
                        entry.update(status='failed', seconds=out['seconds'],
                                     error='no test generated (see log)')
                ids = [e['test_id'] for e in state['plan'].values() if e.get('test_id')]
                state['tests'].update(
                    test_ids=ids, generated=len(ids),
                    failed=sum(1 for e in state['plan'].values()
                               if e.get('status') == 'failed'),
                )
                save_state(state)
                tier = entry.get('assigned_tier')
                flag = '' if tier is None or tier <= row.tier else f'  (assigned T{tier} > target T{row.tier})'
                print(f'  [{done}/{len(todo)}] #{row.num} {row.title_ja}: '
                      f'{entry["status"]}{flag}')

    print(f'  {state["tests"]["generated"]} tests total in this run, '
          f'{state["tests"]["failed"]} failed  ({time.time() - t_start:.0f}s)')


def read_back(db, test_id: str) -> dict:
    """What the report needs, read from the stored rows (not from memory)."""
    t = (db.table('tests')
         .select('slug, title, transcript, target_age_tier, audio_url, style, '
                 'vocab_sense_ids, vocab_sense_stats, furigana_payload')
         .eq('id', test_id).single().execute().data) or {}
    q = (db.table('questions').select('id', count='exact')
         .eq('test_id', test_id).execute())
    stats = t.get('vocab_sense_stats') or {}
    return {
        'slug': t.get('slug'), 'title': t.get('title'),
        'assigned_tier': t.get('target_age_tier'),
        'chars': len(t.get('transcript') or ''),
        'questions': q.count or 0,
        'style': t.get('style'),
        'has_audio': bool(t.get('audio_url')),
        'has_furigana': bool(t.get('furigana_payload')),
        'senses_linked': len(t.get('vocab_sense_ids') or []),
        'senses_created': stats.get('senses_created', 0),
        'senses_reused': stats.get('senses_reused', 0),
        'senses_deferred': stats.get('senses_deferred', 0),
    }


def phase_report(state: dict, rows: list[PlanRow]) -> str:
    lines = [
        f'# Claude test generation — {state["run_id"]}',
        '',
        f'Plan: `{state["config"]["plan"]}` · author model: '
        f'{state["config"]["author_model"]} · other calls: {state["config"]["model"]}',
        '',
        '| # | 日本語 | status | tier (target→assigned) | chars | Qs | style | audio | senses (new/reused/deferred) |',
        '|---|---|---|---|---|---|---|---|---|',
    ]
    over = deferred = 0
    for r in rows:
        e = state['plan'].get(str(r.num), {})
        if not e:
            continue
        at = e.get('assigned_tier')
        over += bool(at and at > r.tier)
        deferred += e.get('senses_deferred', 0) or 0
        tier = f'T{r.tier}→T{at}' if at else f'T{r.tier}→?'
        lines.append(
            f'| {r.num} | {r.title_ja} | {e.get("status", "-")} | {tier} | '
            f'{e.get("chars", "")} | {e.get("questions", "")} | {e.get("style", "")} | '
            f'{"yes" if e.get("has_audio") else ""} | '
            f'{e.get("senses_linked", "")} ({e.get("senses_created", "")}/'
            f'{e.get("senses_reused", "")}/{e.get("senses_deferred", "")}) |'
        )
    failed = [(n, e.get('error')) for n, e in state['plan'].items()
              if e.get('status') == 'failed']
    lines += ['', f'Tests above their target tier (kept, by decision): {over}']
    if failed:
        lines += ['', '## Failed rows', ''] + [f'- #{n}: {err}' for n, err in failed]
    if deferred:
        lines += [
            '', '## Follow-up',
            '', f'{deferred} words were deferred past the inline cap. Seed and relink them:',
            '', '```bash',
            f'python scripts/backfill_senses.py --language {state["language"]} --provider claude-cli',
            f'python scripts/relink_deferred_vocab.py --language {state["language"]}',
            '```',
        ]
    lines += [
        '', 'Then the non-LLM assets:', '', '```bash',
        f'python -m scripts.backfill_sense_embeddings --language {state["language_id"]}',
        'python scripts/build_test_sentences.py --apply',
        '```', '',
    ]
    text = '\n'.join(lines)
    from scripts.run_content_build import STATE_DIR
    path = os.path.join(STATE_DIR, f'{state["run_id"]}.md')
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('\n' + text)
    print(f'report written to {os.path.relpath(path, ROOT)}')
    return text


# ── main ───────────────────────────────────────────────────────────────────

def save_state(state: dict) -> None:
    from scripts.run_content_build import save_state as _save
    _save(state)


def configure_claude_env(args) -> None:
    """Set the headless transport's knobs *before* any service import reads them.

    CLAUDE_CLI_MODEL is a module constant in services.claude_cli_client, read at
    import, so it must be in the environment first.
    """
    os.environ['CLAUDE_CLI_MODEL'] = args.model
    os.environ['CLAUDE_CLI_MODEL_BY_TASK'] = ','.join(
        f'{task}={args.author_model}' for task in AUTHOR_TASKS
    )
    os.environ.setdefault('CLAUDE_CLI_SYSTEM_PROMPT_FILE', SKILL_FILE)
    # Inner fan-out per test. With --workers tests in flight this bounds the
    # number of concurrent `claude -p` processes at workers × this.
    os.environ['TEST_GEN_VOCAB_SENSE_WORKERS'] = str(args.sense_call_workers)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description='Generate tests from a topic plan with headless Claude.',
    )
    ap.add_argument('--plan', default=DEFAULT_PLAN, help='topic plan markdown')
    ap.add_argument('--language', default='ja', choices=('ja', 'zh', 'en'))
    ap.add_argument('--only', help='plan rows to run, e.g. 1-5,9')
    ap.add_argument('--phases', default=','.join(DEFAULT_PHASES),
                    help=f'comma list from {",".join(ALL_PHASES)}')
    ap.add_argument('--resume', metavar='RUN_ID', help='continue a run')
    ap.add_argument('--test-type', default='listening',
                    choices=('listening', 'reading'),
                    help='listening (default) stores audio + transcript, so the '
                         'test is offered in both listening and reading mode')
    ap.add_argument('--author-model', default='opus',
                    help='Claude model for prose, title and questions')
    ap.add_argument('--model', default='sonnet',
                    help='Claude model for every other call')
    ap.add_argument('--workers', type=int, default=1,
                    help='tests in flight (clamped to the CLI ceiling)')
    ap.add_argument('--sense-call-workers', type=int, default=2,
                    help='concurrent sense calls inside one test')
    ap.add_argument('--max-senses', type=int, default=150,
                    help='assets phase: cap on senses to build')
    ap.add_argument('--sense-workers', type=int, default=2,
                    help='assets phase: senses in flight')
    ap.add_argument('--dry-run', action='store_true',
                    help='parse the plan and print briefs; no network, no writes')
    ap.add_argument('--yes', action='store_true',
                    help='skip the confirmation before tests/assets')
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=os.getenv('TEST_GEN_LOG_LEVEL', 'INFO').upper(),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    for noisy in ('httpx', 'httpcore', 'openai', 'urllib3'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    rows = parse_plan(args.plan)
    only = parse_only(args.only)
    if only is not None:
        unknown = sorted(only - {r.num for r in rows})
        if unknown:
            ap.error(f'--only names rows not in the plan: {unknown}')
        rows = [r for r in rows if r.num in only]

    if args.dry_run:
        for r in rows:
            b = build_brief(r)
            cat, lens = THEME_CATEGORY[r.theme]
            print(f'#{r.num} {r.level} T{r.tier} [{cat} / {lens}] style={b.style} '
                  f'{b.char_min}-{b.char_max}字  {r.title_ja} — {r.title_en}')
            print(b.instruction)
        print(f'{len(rows)} rows parsed; nothing written.')
        return 0

    phases = [p.strip() for p in args.phases.split(',') if p.strip()]
    bad = [p for p in phases if p not in ALL_PHASES]
    if bad:
        ap.error(f'unknown phases {bad}')

    configure_claude_env(args)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, '.env'))

    from scripts.provider_arg import apply_provider, clamp_concurrency
    apply_provider('claude-cli')        # probes the CLI; fails before any write
    args.workers = clamp_concurrency('claude-cli', args.workers)
    args.sense_workers = clamp_concurrency('claude-cli', args.sense_workers)

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    import scripts.run_content_build as rcb
    if args.resume:
        state = rcb.load_state(args.resume)
        state.setdefault('plan', {})
        print(f'resuming {args.resume} (phases done: {state["phases_done"] or "none"})')
    else:
        state = new_state(args, parse_plan(args.plan))
        save_state(state)
        print(f'run id: {state["run_id"]}')

    if any(p in phases for p in ('tests', 'assets')) and not args.yes:
        reply = input(f'About to run {phases} over {len(rows)} plan rows with '
                      f'{args.author_model}/{args.model}. Continue? [y/N] ')
        if reply.strip().lower() != 'y':
            print('aborted')
            return 1

    if 'import' in phases:
        phase_import(db, state, rows)
        state['phases_done'].append('import')
        save_state(state)
    if 'preflight' in phases:
        problems = rcb.phase_preflight(db, state)
        if problems:
            print('\nPREFLIGHT FAILED:\n  ' + '\n  '.join(problems))
            return 1
        state['phases_done'].append('preflight')
        save_state(state)
    if 'canary' in phases:
        if not rcb.phase_canary(db, state):
            return 1
        state['phases_done'].append('canary')
        save_state(state)
    if 'tests' in phases:
        phase_tests(db, state, rows, args.workers, test_type=args.test_type)
        state['phases_done'].append('tests')
        save_state(state)
    if 'assets' in phases:
        state['config']['max_senses'] = args.max_senses
        state['config']['sense_workers'] = args.sense_workers
        rcb.phase_select(db, state)
        rcb.phase_ladder(db, state)
        state['phases_done'].append('assets')
        save_state(state)
    if 'report' in phases:
        phase_report(state, rows)

    return 1 if state['tests'].get('failed') else 0


if __name__ == '__main__':
    sys.exit(main())
