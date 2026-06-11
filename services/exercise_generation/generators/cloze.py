# services/exercise_generation/generators/cloze.py

import logging

from services.exercise_generation.base_generator import ExerciseGenerator
from services.exercise_generation.cloze_judge import filter_distractors
from services.exercise_generation.judges.base import log_judge_verdict

logger = logging.getLogger(__name__)


class ClozeGenerator(ExerciseGenerator):
    """
    Generates cloze_completion exercises.
    Per sentence: identifies the target word/phrase, blanks it, calls LLM for
    tagged distractors (semantic, form_error, learner_error), then routes them
    through cloze_judge.

    Over-generate / replace (eval HIGH #5): candidates from up to two generation
    batches are POOLED and judged; only judge-accepted distractors are kept, and
    the item ships the first 3 surviving distractors. If fewer than 3 survive the
    judge across both batches the item is BLOCKED (returns None) — rejected
    distractors are never shipped, and the verdict is persisted to llm_calls.
    """

    exercise_type = 'cloze_completion'
    source_type   = 'grammar'

    def __init__(self, db, language_id: int, model: str, source_type: str = 'grammar'):
        super().__init__(db, language_id, model)
        self.source_type = source_type
        self._last_judge_meta: dict | None = None

    def generate_one(self, sentence_dict: dict, source_id: int) -> dict | None:
        self._last_judge_meta = None

        sentence    = sentence_dict['sentence']
        target_word = self._identify_target_word(sentence, source_id)
        if not target_word:
            return None

        blanked = sentence.replace(target_word, '___', 1)
        tier = sentence_dict.get('complexity_tier', 'T3')

        # Pool judge-accepted distractors across up to two generation batches.
        kept: list[str] = []
        tags: dict[str, str] = {}
        rejected_items: list[str] = []
        explanation = ''
        judge_model = 'unknown'
        judge_version = 0
        total_candidates = 0

        for attempt in range(2):
            payload = self._generate_distractors(sentence, blanked, target_word, tier)
            if not payload:
                continue
            if not explanation:
                explanation = payload.get('explanation', '')
            candidates = [d for d in payload['distractors'] if d not in kept]
            total_candidates += len(candidates)
            accepted, judge_meta = filter_distractors(
                self.db,
                sentence_with_blank=blanked,
                correct_answer=target_word,
                distractors=candidates,
                language_id=self.language_id,
            )
            judge_model   = judge_meta['model']
            judge_version = judge_meta['version']
            rejected_items.extend(judge_meta['rejected_items'])
            for d in accepted:
                if d not in kept:
                    kept.append(d)
                    tags[d] = payload['distractor_tags'].get(d, '')
            if len(kept) >= 3:
                break

        if len(kept) < 3:
            # Block the item — never ship judge-rejected distractors to pad it out.
            self._persist_verdict('reject', kept, total_candidates, judge_model, judge_version)
            logger.warning(
                "cloze_judge: only %d/%d distractors survived for '%s'; blocking item",
                len(kept), total_candidates, sentence[:60],
            )
            return None

        kept = kept[:3]
        self._last_judge_meta = {
            'rejected':       len(rejected_items),
            'rejected_items': rejected_items,
            'model':          judge_model,
            'version':        judge_version,
        }
        # accept if nothing was rejected; flag if the judge replaced ≥1 distractor
        verdict = 'accept' if not rejected_items else 'flag'
        self._persist_verdict(verdict, kept, total_candidates, judge_model, judge_version)

        result = {
            'sentence_with_blank': blanked,
            'original_sentence':   sentence,
            'correct_answer':      target_word,
            'options':             [target_word] + kept,
            'distractor_tags':     {d: tags.get(d, '') for d in kept},
            'explanation':         explanation,
            'source_test_id':      sentence_dict.get('test_id'),
        }

        # Include word definition for vocabulary-sourced cloze exercises
        if self.source_type == 'vocabulary':
            definition = self._load_definition(source_id)
            if definition:
                result['word_definition'] = definition

        return result

    def _build_tags(self, source_id: int, sentence_dict: dict) -> dict:
        tags = super()._build_tags(source_id, sentence_dict)
        if self._last_judge_meta is not None:
            tags['cloze_judge'] = self._last_judge_meta
        return tags

    def _persist_verdict(
        self, verdict: str, kept: list[str], total: int, model: str, version: int,
    ) -> None:
        """Write the item-level cloze judge verdict to llm_calls (queryable).

        confidence = fraction of judged candidates kept. task_name matches the
        judge label 'cloze_distractor_judge' (NOT 'judge_%') so verdict queries
        must target it explicitly.
        """
        confidence = (len(kept) / total) if total else 0.0
        log_judge_verdict(
            task_name='cloze_distractor_judge',
            model=model,
            verdict=verdict,
            confidence=confidence,
            pipeline='exercise_gen',
        )

    def _identify_target_word(self, sentence: str, source_id) -> str | None:
        if self.source_type == 'vocabulary':
            row = self.db.table('dim_word_senses') \
                .select('dim_vocabulary(lemma)') \
                .eq('id', source_id).single().execute().data
            vocab = (row or {}).get('dim_vocabulary') or {}
            word = vocab.get('lemma', '')
            return word if word and word.lower() in sentence.lower() else None

        elif self.source_type == 'collocation':
            row = self.db.table('corpus_collocations').select('collocation_text') \
                .eq('id', source_id).single().execute().data
            col = row.get('collocation_text', '') if row else ''
            return col if col and col.lower() in sentence.lower() else None

        elif self.source_type in ('grammar', 'conversation'):
            return self._identify_target_word_via_llm(sentence)

        return None

    def _identify_target_word_via_llm(self, sentence: str) -> str | None:
        """Use the LLM to pick a meaningful word to blank out."""
        template = self.load_prompt_template('cloze_target_selection')
        prompt = template.format(sentence=sentence)
        try:
            result = self.call_llm(prompt, response_format='json')
            word = result.get('target_word', '').strip()
            if word and word.lower() in sentence.lower():
                return word
        except Exception:
            pass
        return None

    def _load_definition(self, source_id: int) -> str:
        row = self.db.table('dim_word_senses') \
            .select('definition') \
            .eq('id', source_id).single().execute().data
        return (row or {}).get('definition', '')

    def _generate_distractors(
        self, original_sentence: str, blanked: str, correct_answer: str, complexity_tier: str,
    ) -> dict | None:
        template = self.load_prompt_template('cloze_distractor_generation')
        prompt   = template.format(
            original_sentence=original_sentence,
            sentence_with_blank=blanked,
            correct_answer=correct_answer,
            complexity_tier=complexity_tier,
        )
        try:
            result = self.call_llm(prompt, response_format='json')
            distractors = result.get('distractors', [])
            # Remove any distractor that duplicates the correct answer
            distractors = [
                d for d in distractors
                if d.lower().strip() != correct_answer.lower().strip()
            ]
            if not distractors:
                return None
            return {
                'distractors':     distractors,
                'distractor_tags': result.get('distractor_tags', {}),
                'explanation':     result.get('explanation', ''),
            }
        except Exception:
            return None
