# services/exercise_generation/run_exercise_generation.py

import logging
from services.supabase_factory import get_supabase_admin
from services.test_generation.agents.audio_synthesizer import AudioSynthesizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_vocabulary_batch(
    language_id: int,
    sense_ids: list[int] | None = None,
    force: bool = False,
) -> dict:
    """
    Generate exercises for all dim_word_senses rows of a language,
    or a specific subset if sense_ids is provided.

    TASK-512: routes to the **vocabulary ladder**.
    The ladder is now the sole vocab generator — its items are judge-gated and
    carry ``word_asset_id``, which legacy vocab exercises never did. Legacy
    vocab exercises already in the table keep serving until TASK-518
    deactivates them per sense.

    Two steps per sense, mirroring the admin single-word path:
      1. ``VocabAssetPipeline.generate_for_sense`` — P1/P2/P3 assets + judges.
      2. ``LadderExerciseRenderer.render_all``     — assets -> exercise rows.

    A sense whose assets fail outright is *not* rendered: rendering half-built
    assets is how blank exercises reach learners.
    """
    from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
    from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer

    db          = get_supabase_admin()
    synthesizer = AudioSynthesizer()
    pipeline    = VocabAssetPipeline(db)
    renderer    = LadderExerciseRenderer(db, audio_synthesizer=synthesizer)

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
            asset_result = pipeline.generate_for_sense(
                sid, language_id, force=force,
            )
            status = asset_result.get('status')
            if status == 'failed':
                # Don't render from assets that didn't build — half-built
                # assets render as blank or single-option exercises.
                logger.error(
                    "Sense %d: asset generation failed, not rendering: %s",
                    sid, asset_result.get('errors'),
                )
                results[sid] = {
                    'status': 'failed',
                    'exercise_ids': [],
                    'errors': asset_result.get('errors', []),
                }
                continue

            exercise_ids = renderer.render_all(sid, language_id)
            results[sid] = {
                'status': status,
                'exercise_ids': exercise_ids,
                'errors': asset_result.get('errors', []),
            }
            logger.info(
                "Sense %d: %s, %d exercise(s) rendered",
                sid, status, len(exercise_ids),
            )
        except Exception as exc:
            logger.error("Sense %d failed: %s", sid, exc)
            results[sid] = {'status': 'failed', 'exercise_ids': [], 'error': str(exc)}

    return results


if __name__ == '__main__':
    import argparse
    from services.supabase_factory import SupabaseFactory

    parser = argparse.ArgumentParser(description='Run vocabulary exercise generation batch')
    parser.add_argument('--source',   choices=['vocabulary'], default='vocabulary')
    parser.add_argument('--language', type=int, required=True)
    parser.add_argument('--ids',      nargs='*', type=int)
    args = parser.parse_args()

    SupabaseFactory.initialize()
    run_vocabulary_batch(args.language, sense_ids=args.ids)
