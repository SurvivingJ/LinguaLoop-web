# services/exercise_generation/run_exercise_generation.py

import logging
from services.supabase_factory import get_supabase_admin
from services.test_generation.agents.audio_synthesizer import AudioSynthesizer
from services.exercise_generation.orchestrator import ExerciseGenerationOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_grammar_batch(
    language_id: int,
    phases: list[str] | None = None,
    pattern_ids: list[int] | None = None,
) -> dict:
    """
    Generate exercises for all active grammar patterns of a language,
    or a specific subset if pattern_ids is provided.
    """
    db             = get_supabase_admin()
    synthesizer    = AudioSynthesizer()
    orchestrator   = ExerciseGenerationOrchestrator(db, audio_synthesizer=synthesizer)

    query = db.table('dim_grammar_patterns') \
        .select('id') \
        .eq('language_id', language_id) \
        .eq('is_active', True)
    if pattern_ids:
        query = query.in_('id', pattern_ids)
    patterns = query.execute()

    results = {}
    for row in (patterns.data or []):
        pid = row['id']
        try:
            result = orchestrator.run('grammar', pid, language_id, phases=phases)
            results[pid] = result
            logger.info("Pattern %d: %d exercises", pid, result['total'])
        except Exception as exc:
            logger.error("Pattern %d failed: %s", pid, exc)
            results[pid] = {'error': str(exc)}

    return results


def run_vocabulary_batch(
    language_id: int,
    sense_ids: list[int] | None = None,
) -> dict:
    """
    Generate exercises for all dim_word_senses rows of a language,
    or a specific subset if sense_ids is provided.
    """
    db           = get_supabase_admin()
    synthesizer  = AudioSynthesizer()
    orchestrator = ExerciseGenerationOrchestrator(db, audio_synthesizer=synthesizer)

    if sense_ids:
        # Direct lookup when specific IDs are provided
        all_sense_ids = sense_ids
    else:
        # Two-step query: dim_word_senses has no language_id column,
        # so resolve via dim_vocabulary first
        vocab_rows = db.table('dim_vocabulary') \
            .select('id') \
            .eq('language_id', language_id) \
            .execute()
        vocab_ids = [r['id'] for r in (vocab_rows.data or [])]

        all_sense_ids = []
        for i in range(0, len(vocab_ids), 500):
            chunk = vocab_ids[i:i + 500]
            sense_rows = db.table('dim_word_senses') \
                .select('id') \
                .in_('vocab_id', chunk) \
                .execute()
            all_sense_ids.extend(r['id'] for r in (sense_rows.data or []))

    results = {}
    for sid in all_sense_ids:
        try:
            result = orchestrator.run('vocabulary', sid, language_id)
            results[sid] = result
        except Exception as exc:
            logger.error("Sense %d failed: %s", sid, exc)
            results[sid] = {'error': str(exc)}

    return results


def run_collocation_batch(
    language_id: int,
    collocation_ids: list[int] | None = None,
) -> dict:
    """
    Generate exercises for corpus_collocations rows of a language.
    Requires Plan 5 corpus pipeline to have populated corpus_collocations.
    """
    db           = get_supabase_admin()
    synthesizer  = AudioSynthesizer()
    orchestrator = ExerciseGenerationOrchestrator(db, audio_synthesizer=synthesizer)

    query = db.table('corpus_collocations') \
        .select('id') \
        .eq('language_id', language_id) \
        .gte('pmi_score', 3.0)
    if collocation_ids:
        query = query.in_('id', collocation_ids)
    collocations = query.execute()

    results = {}
    for row in (collocations.data or []):
        cid = row['id']
        try:
            result = orchestrator.run('collocation', cid, language_id)
            results[cid] = result
        except Exception as exc:
            logger.error("Collocation %d failed: %s", cid, exc)
            results[cid] = {'error': str(exc)}

    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run exercise generation batch')
    parser.add_argument('--source',   choices=['grammar', 'vocabulary', 'collocation'], required=True)
    parser.add_argument('--language', type=int, required=True)
    parser.add_argument('--phases',   nargs='*', choices=['A', 'B', 'C', 'D'])
    parser.add_argument('--ids',      nargs='*', type=int)
    args = parser.parse_args()

    if args.source == 'grammar':
        run_grammar_batch(args.language, phases=args.phases, pattern_ids=args.ids)
    elif args.source == 'vocabulary':
        run_vocabulary_batch(args.language, sense_ids=args.ids)
    elif args.source == 'collocation':
        run_collocation_batch(args.language, collocation_ids=args.ids)
