"""
Question Generator Agent

Generates comprehension questions for tests using LLM.
Supports 6 semantic question types.
"""

import logging
from typing import List, Dict, Optional, Tuple

from pydantic import ValidationError

from services.llm_service import call_llm

from ..config import get_test_gen_config
from ..schemas import MCQuestion
from .question_validator import QuestionValidator

# Verdict ordering used to find worst distractor outcome.
_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}

# Distractor-plausibility hard-reject floor. The judge's `confidence` is the
# distractor's *plausibility* (low = implausible/too-obvious); classify() marks
# anything < 0.6 as 'reject'. Killing a question for a merely "somewhat obvious"
# distractor (0.35–0.6) starved mid-tier zh/ja tests (all 5 questions dropped,
# 0/5). Only a *clearly* implausible distractor (< this floor) — e.g. an absurd
# or actually-correct/oversharp option — now hard-rejects the question; the
# 0.35–0.6 band is tolerated. Answer-entailment rejects (a correctness gate)
# are unaffected.
_DP_HARD_REJECT_BELOW = 0.35

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Generates comprehension questions using LLM."""

    # Question type descriptions for prompting (used only by the legacy
    # inline fallback below; the active path loads templates from the
    # prompt_templates table via the orchestrator).
    QUESTION_TYPE_PROMPTS = {
        'literal_detail': {
            'name': 'Literal Detail',
            'instruction': 'Ask about a specific fact or detail explicitly stated in the text. The answer should be directly findable in the passage.',
            'cognitive_level': 1
        },
        'vocabulary_context': {
            'name': 'Vocabulary in Context',
            'instruction': 'Ask about the meaning of a word or phrase as used in the passage. Focus on how context shapes meaning.',
            'cognitive_level': 1
        },
        'main_idea': {
            'name': 'Main Idea',
            'instruction': 'Ask about the central theme, main point, or overall purpose of the passage or a paragraph.',
            'cognitive_level': 2
        },
        'supporting_detail': {
            'name': 'Supporting Detail',
            'instruction': 'Ask about information that supports or explains the main ideas in the passage.',
            'cognitive_level': 2
        },
        'inference': {
            'name': 'Inference',
            'instruction': 'Ask about something not directly stated but that can be concluded from the information given.',
            'cognitive_level': 3
        },
        'author_purpose': {
            'name': 'Author Purpose/Tone',
            'instruction': 'Ask about why the author wrote the passage, their attitude, or the intended effect on readers.',
            'cognitive_level': 3
        }
    }

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize the Question Generator.

        api_key is retained for backwards-compatible callers; the unified
        llm_service uses OPENROUTER_API_KEY from the environment.
        """
        cfg = get_test_gen_config()
        self.api_key = api_key or cfg.openrouter_api_key
        self.model = model or cfg.default_question_model
        self.api_call_count = 0
        # Owned validator so each question type is generated → judged →
        # validated as a unit inside generate_questions, and regenerated with
        # feedback on any rejection. The orchestrator's post-hoc
        # validate_all_questions then acts as a cheap idempotent safety net.
        self._validator = QuestionValidator()
        logger.info(f"QuestionGenerator initialized with model: {self.model}")

    def generate_questions(
        self,
        prose: str,
        language_name: str,
        question_type_codes: List[str],
        difficulty: int = 5,
        prompt_templates: Optional[Dict[str, str]] = None,
        model_override: Optional[str] = None,
        seed: Optional[int] = None,
        language_id: Optional[int] = None,
        template_version: Optional[int] = None,
        db=None,
    ) -> List[Dict]:
        """Generate multiple questions for prose content.

        Returns a list of dicts with keys: question, choices, answer,
        correct_answer_index, type_code, distractor_types (optional).
        """
        logger.info(f"Generating {len(question_type_codes)} questions for {language_name} (diff={difficulty})")

        max_attempts = max(1, get_test_gen_config().question_regen_attempts)

        questions: List[Dict] = []
        # Texts of the questions we have KEPT so far — the "what we already have"
        # signal fed to the next type so it avoids overlap.
        kept_texts: List[str] = []
        # Per-question rejection reasons for THIS run (judge hard-rejects AND
        # validator failures across all regen attempts), surfaced to the
        # orchestrator for funnel diagnostics. Reset on every call.
        self.last_rejections: List[Dict] = []

        for type_code in question_type_codes:
            q_entry, attempt_rejections = self._generate_validated_question(
                prose=prose,
                language_name=language_name,
                question_type_code=type_code,
                difficulty=difficulty,
                kept_questions=kept_texts,
                prompt_template=prompt_templates.get(type_code) if prompt_templates else None,
                model_override=model_override,
                seed=seed,
                template_version=template_version,
                language_id=language_id,
                db=db,
                max_attempts=max_attempts,
            )

            # Record every rejected attempt for the funnel diagnostic (these are
            # the original/per-attempt rejects, kept even when a later attempt of
            # the same type ultimately succeeds).
            if attempt_rejections:
                self.last_rejections.extend(attempt_rejections)

            if q_entry is None:
                continue

            questions.append(q_entry)
            kept_texts.append(q_entry['question'])

        logger.info(f"Generated {len(questions)}/{len(question_type_codes)} questions")
        return questions

    def _generate_validated_question(
        self,
        prose: str,
        language_name: str,
        question_type_code: str,
        difficulty: int,
        kept_questions: List[str],
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None,
        seed: Optional[int] = None,
        template_version: Optional[int] = None,
        language_id: Optional[int] = None,
        db=None,
        max_attempts: int = 2,
    ) -> Tuple[Optional[Dict], List[Dict]]:
        """Generate one question of a type, retrying with feedback on rejection.

        Closes the generate → judge → validate funnel for a SINGLE question type
        so a recoverable defect no longer aborts the whole test. Loops up to
        ``max_attempts``:

        1. ``_generate_single_question`` — passes ``kept_questions`` (overlap
           context) and an accumulating ``avoid_context`` of prior rejected
           attempts for this type (see ``_append_avoid``).
        2. Judge gate (only when ``db`` + ``language_id`` are supplied): on hard
           reject, fold the reason into ``avoid_context`` and retry.
        3. Validator gate (always): on fail, fold the error into
           ``avoid_context`` and retry.
        4. On pass, return the question.

        Returns ``(q_entry | None, attempt_rejections)`` where
        ``attempt_rejections`` is the list of per-attempt rejection diagnostic
        records ``{type_code, stage, confidence, reason}`` for this type, which
        the caller folds into ``last_rejections``.
        """
        avoid_context = ""
        attempt_rejections: List[Dict] = []

        for attempt in range(1, max_attempts + 1):
            try:
                question = self._generate_single_question(
                    prose=prose,
                    language_name=language_name,
                    question_type_code=question_type_code,
                    difficulty=difficulty,
                    previous_questions=kept_questions,
                    prompt_template=prompt_template,
                    model_override=model_override,
                    seed=seed,
                    template_version=template_version,
                    avoid_context=avoid_context,
                )
            except Exception as e:
                # call_llm already retries transient API errors via tenacity, so
                # anything here is exhausted-transient or a hard schema failure.
                # No usable text to fold into feedback — just retry within budget.
                logger.error(
                    "Attempt %d/%d: failed to generate %s: %s: %s",
                    attempt, max_attempts, question_type_code,
                    type(e).__name__, e,
                )
                continue

            q_entry = {
                'question': question.question_text,
                'choices': question.choices,
                'answer': question.answer,
                'correct_answer_index': question.correct_answer_index,
                'type_code': question_type_code,
            }
            if question.distractor_types:
                q_entry['distractor_types'] = question.distractor_types

            # --- Judge gate (only when caller passes db + language_id) ---
            # Failure mode: safe_accept() — judges never block on internal error.
            if db is not None and language_id is not None:
                judged_entry, rejection = self._apply_judges(
                    q_entry=q_entry,
                    prose=prose,
                    db=db,
                    language_id=language_id,
                    type_code=question_type_code,
                )
                if judged_entry is None:
                    if rejection:
                        attempt_rejections.append(rejection)
                        avoid_context = self._append_avoid(
                            avoid_context, question.question_text,
                            rejection.get('reason') or 'judge rejected',
                        )
                    logger.info(
                        "Attempt %d/%d: %s judge-rejected, "
                        "regenerating with feedback",
                        attempt, max_attempts, question_type_code,
                    )
                    continue
                q_entry = judged_entry

            # --- Validator gate (structure, content, overlap vs kept) ---
            is_valid, error = self._validator.validate_question(
                q_entry, prose, kept_questions
            )
            if not is_valid:
                attempt_rejections.append({
                    'type_code': question_type_code,
                    'stage': 'validator',
                    'confidence': None,
                    'reason': error,
                })
                avoid_context = self._append_avoid(
                    avoid_context, question.question_text,
                    error or 'failed validation',
                )
                logger.info(
                    "Attempt %d/%d: %s validator-rejected (%s), "
                    "regenerating with feedback",
                    attempt, max_attempts, question_type_code, error,
                )
                continue

            # Passed both gates.
            return q_entry, attempt_rejections

        # Budget exhausted without a surviving question for this type.
        logger.warning(
            "Exhausted %d attempt(s) for %s — no surviving question",
            max_attempts, question_type_code,
        )
        return None, attempt_rejections

    @staticmethod
    def _append_avoid(avoid_context: str, question_text: str, reason: str) -> str:
        """Append one rejected-attempt line to the accumulating avoid context."""
        line = f'- "{question_text}" -> rejected: {reason}'
        return f"{avoid_context}\n{line}" if avoid_context else line

    def _generate_single_question(
        self,
        prose: str,
        language_name: str,
        question_type_code: str,
        difficulty: int,
        previous_questions: List[str],
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None,
        seed: Optional[int] = None,
        template_version: Optional[int] = None,
        avoid_context: str = "",
    ) -> MCQuestion:
        """Generate a single question of specified type.

        Returns the validated MCQuestion. Raises ValidationError if both
        the initial LLM call and the schema-aware repair retry produce
        malformed output (e.g. answer not in choices, fewer than 4 choices).

        ``avoid_context`` (optional) is a pre-formatted block of this type's
        previously rejected attempts + reasons; when non-empty it is appended to
        the prompt so the regen avoids repeating the same mistake. Appending in
        code (rather than a template placeholder) keeps this migration-free for
        both the DB-template and legacy inline paths.
        """
        model = model_override or self.model

        if prompt_template:
            prompt = prompt_template.format(
                prose=prose,
                difficulty=difficulty,
                previous_questions='; '.join(previous_questions) if previous_questions else 'None',
                language=language_name,
            )
        else:
            prompt = self._build_question_prompt(
                prose,
                language_name,
                question_type_code,
                previous_questions,
            )

        if avoid_context:
            prompt = (
                f"{prompt}\n\n"
                "PREVIOUS REJECTED ATTEMPTS FOR THIS QUESTION TYPE — "
                "do NOT repeat these mistakes:\n"
                f"{avoid_context}\n"
                "Write a different question of the same type that avoids the "
                "issue(s) above."
            )

        logger.debug(f"Prompt for {question_type_code}: {len(prompt)} chars")

        try:
            question = call_llm(
                prompt,
                model=model,
                temperature=get_test_gen_config().question_temperature,
                response_format='json_object',
                schema=MCQuestion,
                seed=seed,
                timeout=30,
                pipeline='test_gen',
                task_name=f'question_{question_type_code}',
                template_version=template_version,
            )
        except ValidationError as e:
            logger.error(
                f"Question schema validation failed (after repair) for "
                f"{question_type_code}: {e.errors()[0]['msg'] if e.errors() else e}"
            )
            raise
        except Exception as e:
            logger.error(f"Question generation failed for {question_type_code}: {e}")
            raise

        self.api_call_count += 1
        logger.info(f"Generated {question_type_code} question (answer_index={question.correct_answer_index})")
        return question

    def _build_question_prompt(
        self,
        prose: str,
        language: str,
        question_type_code: str,
        previous_questions: List[str]
    ) -> str:
        """Build legacy inline prompt for question generation.

        Used only when no DB template is supplied for the question type;
        the active code path passes templates from prompt_templates via the
        orchestrator.
        """
        type_info = self.QUESTION_TYPE_PROMPTS.get(
            question_type_code,
            {'name': 'General', 'instruction': 'Ask a comprehension question.', 'cognitive_level': 1}
        )

        previous_text = '; '.join(previous_questions) if previous_questions else 'None'

        return f"""Generate a multiple-choice comprehension question in {language}.

PASSAGE:
{prose}

QUESTION TYPE: {type_info['name']}
INSTRUCTION: {type_info['instruction']}

PREVIOUSLY ASKED QUESTIONS: {previous_text}

Requirements:
1. Write the question and ALL choices ONLY in {language}. Do not use English.
2. Create exactly 4 answer choices, all distinct.
3. Exactly one choice is correct.
4. Each incorrect choice (distractor) is tagged with a type:
   - "semantic": plausible word/phrase that is wrong in meaning
   - "grammatical": correct word used in wrong grammatical form
   - "contextual": correct word/phrase used in wrong context or register
5. Avoid questions similar to previously asked ones.
6. Match the cognitive level ({type_info['cognitive_level']}/3) in complexity.

Return ONLY valid JSON in this exact shape:
{{
    "question_text": "Your question text in {language}",
    "choices": ["Choice 1", "Choice 2", "Choice 3", "Choice 4"],
    "answer": "The correct choice (must exactly match one element of choices)",
    "explanation": "Brief explanation of why the correct answer is correct",
    "distractor_types": ["semantic", null, "contextual", "grammatical"]
}}

The `answer` field must reproduce one of the four `choices` strings verbatim.
The `distractor_types` array uses null for the correct choice's slot.
"""

    def _apply_judges(
        self,
        q_entry: Dict,
        prose: str,
        db,
        language_id: int,
        type_code: str,
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Run answer-entailment and distractor-plausibility judges on a question.

        Returns ``(q_entry, None)`` on accept/flag — the (possibly annotated)
        q_entry dict — or ``(None, rejection)`` when a judge hard-rejects the
        question, where ``rejection`` is a diagnostic record
        ``{type_code, stage, confidence, reason}`` collected by the caller into
        ``last_rejections``. Attaches ``_judge_flags`` to the dict when one or
        more judges flag (but do not reject) the question.

        Judges use safe_accept() on any internal error, so this method never
        raises and never blocks the pipeline.
        """
        # Lazy imports avoid a circular dependency:
        #   question_generator → answer_entailment → test_generation.schemas
        #   → test_generation.__init__ → orchestrator → question_generator
        from services.exercise_generation.judges.answer_entailment import (
            judge_answer_entailment,
        )
        from services.exercise_generation.judges.distractor_plausibility import (
            judge_distractor_plausibility,
        )

        question_text = q_entry['question']
        answer        = q_entry['answer']
        distractors   = [c for c in q_entry['choices'] if c != answer]

        # --- Answer entailment ---
        ae = judge_answer_entailment(
            db=db,
            passage=prose,
            question_text=question_text,
            answer=answer,
            language_id=language_id,
        )
        if ae.verdict == 'reject':
            logger.info(
                "Judge rejected %s answer (conf=%.2f): %s",
                type_code, ae.confidence, ae.reason,
            )
            return None, {
                'type_code': type_code,
                'stage': 'answer_entailment',
                'confidence': ae.confidence,
                'reason': ae.reason,
            }

        # --- Distractor plausibility ---
        dp_outcomes = judge_distractor_plausibility(
            db=db,
            passage=prose,
            question_text=question_text,
            answer=answer,
            distractors=distractors,
            language_id=language_id,
        )
        worst_dp = min(
            dp_outcomes,
            key=lambda o: _VERDICT_ORDER.get(o.verdict, 2),
            default=None,
        )
        if (
            worst_dp
            and worst_dp.verdict == 'reject'
            and worst_dp.confidence < _DP_HARD_REJECT_BELOW
        ):
            logger.info(
                "Judge rejected %s distractors (conf=%.2f): %s",
                type_code, worst_dp.confidence, worst_dp.reason,
            )
            return None, {
                'type_code': type_code,
                'stage': 'distractor_plausibility',
                'confidence': worst_dp.confidence,
                'reason': worst_dp.reason,
            }
        # A 'reject' in the tolerated 0.35–0.6 band: keep the question but record
        # the weak distractor as a flag so it's still surfaced for later review.
        if worst_dp and worst_dp.verdict == 'reject':
            logger.info(
                "Distractor reject tolerated for %s (conf=%.2f >= %.2f floor): %s",
                type_code, worst_dp.confidence, _DP_HARD_REJECT_BELOW,
                worst_dp.reason,
            )

        # --- Collect flags ---
        judge_flags: Dict = {}
        if ae.verdict == 'flag':
            judge_flags['answer_entailment'] = {
                'confidence': ae.confidence,
                'reason': ae.reason,
            }
        flagged_dp = [
            (d, o) for d, o in zip(distractors, dp_outcomes)
            if o.verdict == 'flag'
        ]
        if flagged_dp:
            judge_flags['distractor_plausibility'] = [
                {'distractor': d, 'confidence': o.confidence, 'reason': o.reason}
                for d, o in flagged_dp
            ]
        if judge_flags:
            q_entry['_judge_flags'] = judge_flags

        return q_entry, None

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
