"""Language x content-type timing report for content generation.

Answers "where did the wall clock go" across test-gen and the vocabulary
pipeline (senses, glosses, vocab ladder), split by study language and by
content type (prose, questions, a named judge, a ladder prompt stage, ...),
with both run totals and per-item averages.

Reads two tables, both written best-effort by the generation code itself:

  * ``llm_calls``                  — one row per LLM round-trip
    (services.llm_service.call_llm), with latency_ms + cost_usd.
  * ``generation_stage_timings``   — one row per named wall-clock stage per
    artifact (services.timing.log_stage_seconds), covering the non-LLM time
    a stage spans (DB writes, audio synthesis, tokenization, validation).

These are reported as two SEPARATE sections, not summed: a stage's
duration_ms typically CONTAINS several llm_calls rows (e.g. the test-gen
'questions' stage wraps six question-generation calls plus two judges), so
adding "total LLM time" to "total stage time" would double-count the wall
clock. Read the stage table for "what's slow end-to-end" and the llm_calls
table for "which model call is slow".

Usage:
    # last 24h, default pipelines (test_gen, vocab_ladder, vocab_senses, vocab_glosses)
    python scripts/generation_timing_report.py

    # last 7 days, zh only
    python scripts/generation_timing_report.py --since-hours 168 --language zh

    # just the ladder, exported for a spreadsheet
    python scripts/generation_timing_report.py --pipeline vocab_ladder --csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# Run-as-script bootstrap (mirrors scripts/measure_judge_flag_rate.py): repo
# root on the path and .env loaded before any app service is imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

DEFAULT_PIPELINES = ('test_gen', 'vocab_ladder', 'vocab_senses', 'vocab_glosses')

# task_name / stage_name -> human content-type label. Deliberately incomplete:
# an unmapped name still prints (as "pipeline/name"), so a new task never goes
# missing from the report — it just reads a little uglier until someone adds a
# line here.
CONTENT_TYPE_LABELS: dict[str, str] = {
    # --- test_gen: llm_calls task_name ---
    'topic_translation':             'Test: Topic translation',
    'prose_generation':              'Test: Prose',
    'title_generation':              'Test: Title',
    'question_literal_detail':       'Question: literal_detail',
    'question_vocabulary_context':   'Question: vocabulary_context',
    'question_main_idea':            'Question: main_idea',
    'question_supporting_detail':    'Question: supporting_detail',
    'question_inference':            'Question: inference',
    'question_author_purpose':       'Question: author_purpose',
    'judge_answer_entailment':       'Judge: Answer entailment',
    'judge_distractor_plausibility': 'Judge: Distractor plausibility',
    # --- test_gen: stage_name ---
    'translate':          'Test: Topic translation (stage)',
    'prose':               'Test: Prose (stage)',
    'difficulty_scorer':   'Test: Difficulty scorer',
    'title':                'Test: Title (stage)',
    'questions':            'Test: Questions (stage, incl. judges)',
    'audio':                 'Test: Audio synthesis',
    'vocab_extract':          'Vocab: Extraction (tokenize)',
    'vocab_senses_llm':        'Vocab: Sense generation (stage)',
    # --- vocab_senses: llm_calls task_name (prefix match handled below too) ---
    'vocab_definition_generation': 'Sense: Definition',
    'vocab_sense_selection':       'Sense: Selection',
    # --- vocab_glosses ---
    'vocab_gloss_translation': 'Gloss: Translation',
    # --- vocab_ladder: llm_calls task_name ---
    'vocab_prompt1_core':                 'Ladder P1: Core',
    'vocab_prompt1_core_repair':          'Ladder P1: Repair',
    'vocab_prompt1_core_sentence_repair': 'Ladder P1: Sentence repair',
    'vocab_prompt2_exercises':            'Ladder P2: Exercises',
    'vocab_prompt3_transforms':           'Ladder P3: Spot-incorrect (L7)',
    'vocab_prompt3_transforms_salvage':   'Ladder P3: Salvage',
    'judge_ladder_p1_sentence':           'Judge: P1 sentence',
    'judge_ladder_collocation':           'Judge: Collocation (L5/L8)',
    'judge_ladder_particle':              'Judge: Particle',
    'cloze_distractor_judge':             'Judge: Cloze distractor',
    'judge_ladder_l1_distractor':         'Judge: L1 distractor',
    'judge_ladder_sentence_validity':     'Judge: Sentence validity (L7)',
    'judge_ladder_relation':              'Judge: Relation',
    'judge_ladder_word_family':           'Judge: Word family',
    'judge_translation_uniqueness':       'Judge: Translation uniqueness',
    # --- vocab_ladder: stage_name ---
    'fetch_corpus':          'Ladder: Fetch corpus sentences',
    'p1_generate':            'Ladder P1: Generate (stage)',
    'p1_repair':               'Ladder P1: Repair (stage)',
    'tier_gate':                'Ladder: Tier gate (deterministic)',
    'p1_judge':                  'Ladder P1: Judge (stage)',
    'collocate_grounding':        'Ladder: Collocate grounding',
    'fan_out':                     'Ladder: P2/P3/split/typed fan-out',
}


def _label(pipeline: str, name: str) -> str:
    if name in CONTENT_TYPE_LABELS:
        return CONTENT_TYPE_LABELS[name]
    if name.endswith('__repair') or name.endswith('__json_repair') or name.endswith('__fallback'):
        base = name.split('__', 1)[0]
        if base in CONTENT_TYPE_LABELS:
            return f'{CONTENT_TYPE_LABELS[base]} ({name.split("__", 1)[1]})'
    return f'{pipeline}/{name}'


def _fetch_all(client, table: str, since_iso: str, pipelines: list[str]) -> list[dict]:
    """Page through every row in the window — supabase-py caps a single
    select at (by default) 1000 rows, and a real batch run comfortably
    exceeds that for llm_calls."""
    rows: list[dict] = []
    page_size = 1000
    start = 0
    while True:
        resp = (
            client.table(table)
            .select('*')
            .gte('created_at', since_iso)
            .in_('pipeline', pipelines)
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    quantiles = statistics.quantiles(values, n=100, method='inclusive')
    idx = max(0, min(98, int(pct) - 1))
    return quantiles[idx]


def _aggregate(
    rows: list[dict], *, pipeline_key: str, name_key: str, duration_key: str,
    duration_is_ms: bool, cost_key: str | None,
) -> dict[tuple[str, str, str], dict]:
    """Group rows by (language_code, pipeline, name) -> stats dict."""
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    costs: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in rows:
        duration = row.get(duration_key)
        if duration is None:
            continue
        seconds = (duration / 1000.0) if duration_is_ms else float(duration)
        lang = row.get('language_code') or '??'
        key = (lang, row.get(pipeline_key) or '?', row.get(name_key) or '?')
        groups[key].append(seconds)
        if cost_key and row.get(cost_key) is not None:
            costs[key] += float(row[cost_key])

    stats = {}
    for key, seconds_list in groups.items():
        ms_list = [s * 1000 for s in seconds_list]
        stats[key] = {
            'count': len(seconds_list),
            'total_seconds': sum(seconds_list),
            'avg_ms': sum(ms_list) / len(ms_list),
            'p50_ms': _percentile(ms_list, 50),
            'p95_ms': _percentile(ms_list, 95),
            'total_cost_usd': costs.get(key, 0.0),
        }
    return stats


def _print_section(title: str, stats: dict[tuple[str, str, str], dict], show_cost: bool) -> None:
    print()
    print('=' * 88)
    print(f'  {title}')
    print('=' * 88)
    if not stats:
        print('  (no rows in window)')
        return

    ordered = sorted(stats.items(), key=lambda kv: kv[1]['total_seconds'], reverse=True)
    grand_total = sum(v['total_seconds'] for _, v in ordered)

    header = '  %-6s %-42s %8s %10s %10s' % ('Lang', 'Content type', 'Count', 'Total (s)', '% of total')
    if show_cost:
        header += '  %10s' % 'Cost ($)'
    print(header)
    print('  ' + '-' * (len(header) - 2))
    for (lang, pipeline, name), s in ordered:
        label = _label(pipeline, name)
        pct = (s['total_seconds'] / grand_total * 100) if grand_total else 0.0
        line = '  %-6s %-42s %8d %10.1f %9.1f%%' % (
            lang, label[:42], s['count'], s['total_seconds'], pct,
        )
        if show_cost:
            line += '  %10.4f' % s['total_cost_usd']
        print(line)
    print('  ' + '-' * (len(header) - 2))
    total_line = '  %-6s %-42s %8d %10.1f %9s' % (
        'TOTAL', '', sum(v['count'] for v in stats.values()), grand_total, '100.0%',
    )
    if show_cost:
        total_line += '  %10.4f' % sum(v['total_cost_usd'] for v in stats.values())
    print(total_line)

    print()
    print(f'  {title} -- per item')
    header2 = '  %-6s %-42s %10s %10s %10s' % ('Lang', 'Content type', 'Avg (ms)', 'P50 (ms)', 'P95 (ms)')
    print(header2)
    print('  ' + '-' * (len(header2) - 2))
    for (lang, pipeline, name), s in ordered:
        label = _label(pipeline, name)
        print('  %-6s %-42s %10.0f %10.0f %10.0f' % (
            lang, label[:42], s['avg_ms'], s['p50_ms'], s['p95_ms'],
        ))


def _write_csv(path: str, sections: dict[str, dict[tuple[str, str, str], dict]]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'source', 'language_code', 'pipeline', 'name', 'content_type',
            'count', 'total_seconds', 'avg_ms', 'p50_ms', 'p95_ms', 'total_cost_usd',
        ])
        for source, stats in sections.items():
            for (lang, pipeline, name), s in stats.items():
                writer.writerow([
                    source, lang, pipeline, name, _label(pipeline, name),
                    s['count'], round(s['total_seconds'], 3), round(s['avg_ms'], 1),
                    round(s['p50_ms'], 1), round(s['p95_ms'], 1),
                    round(s['total_cost_usd'], 6),
                ])
    print(f'\nWrote {path}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--since-hours', type=float, default=24.0,
                         help='Look back this many hours (default 24).')
    parser.add_argument('--language', action='append', default=None,
                         help='Restrict to this language_code (zh|en|ja). Repeatable. Default: all.')
    parser.add_argument('--pipeline', action='append', default=None,
                         help=f'Restrict to this pipeline. Repeatable. Default: {", ".join(DEFAULT_PIPELINES)}.')
    parser.add_argument('--csv', default=None, help='Also write the aggregated rows to this CSV path.')
    args = parser.parse_args()

    pipelines = args.pipeline or list(DEFAULT_PIPELINES)
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=args.since_hours)).isoformat()

    SupabaseFactory.initialize()
    client = get_supabase_admin()
    if client is None:
        print('ERROR: could not obtain a Supabase admin client (check env).', file=sys.stderr)
        return 1

    print(f'Window: last {args.since_hours}h (since {since_iso})')
    print(f'Pipelines: {", ".join(pipelines)}')
    if args.language:
        print(f'Languages: {", ".join(args.language)}')
    print()
    print('NOTE: the two sections below are NOT additive -- a stage typically')
    print('contains several LLM calls, so "LLM call time" is a subset of the')
    print('wall clock already counted in "stage wall clock", not extra time.')

    llm_rows = _fetch_all(client, 'llm_calls', since_iso, pipelines)
    stage_rows = _fetch_all(client, 'generation_stage_timings', since_iso, pipelines)

    if args.language:
        wanted = set(args.language)
        llm_rows = [r for r in llm_rows if r.get('language_code') in wanted]
        stage_rows = [r for r in stage_rows if r.get('language_code') in wanted]

    llm_stats = _aggregate(
        llm_rows, pipeline_key='pipeline', name_key='task_name',
        duration_key='latency_ms', duration_is_ms=True, cost_key='cost_usd',
    )
    stage_stats = _aggregate(
        stage_rows, pipeline_key='pipeline', name_key='stage_name',
        duration_key='duration_ms', duration_is_ms=True, cost_key=None,
    )

    _print_section('LLM CALL TIME (llm_calls) -- bottleneck ranking', llm_stats, show_cost=True)
    _print_section('STAGE WALL CLOCK (generation_stage_timings) -- bottleneck ranking', stage_stats, show_cost=False)

    if args.csv:
        _write_csv(args.csv, {'llm_calls': llm_stats, 'generation_stage_timings': stage_stats})

    return 0


if __name__ == '__main__':
    sys.exit(main())
