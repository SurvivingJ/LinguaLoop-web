"""
Question Generator Agent

Generates comprehension questions for tests using LLM.
Supports 6 semantic question types.
"""

import logging
from typing import List, Dict, Optional

from pydantic import ValidationError

from services.llm_service import call_llm

from ..config import test_gen_config
from ..schemas import MCQuestion

# Verdict ordering used to find worst distractor outcome.
_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}

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
        self.api_key = api_key or test_gen_config.openrouter_api_key
        self.model = model or test_gen_config.default_question_model
        self.api_call_count = 0
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

        questions: List[Dict] = []
        previous_questions: List[str] = []

        for type_code in question_type_codes:
            try:
                question = self._generate_single_question(
                    prose=prose,
                    language_name=language_name,
                    question_type_code=type_code,
                    difficulty=difficulty,
                    previous_questions=previous_questions,
                    prompt_template=prompt_templates.get(type_code) if prompt_templates else None,
                    model_override=model_override,
                    seed=seed,
                    template_version=template_version,
                )

                q_entry = {
                    'question': question.question_text,
                    'choices': question.choices,
                    'answer': question.answer,
                    'correct_answer_index': question.correct_answer_index,
                    'type_code': type_code,
                }
                if question.distractor_types:
                    q_entry['distractor_types'] = question.distractor_types

                # LLM judge gate — runs only when caller passes db + language_id.
                # Failure mode: safe_accept() — judges never block the pipeline on error.
                if db is not None and language_id is not None:
                    q_entry = self._apply_judges(
                        q_entry=q_entry,
                        prose=prose,
                        db=db,
                        language_id=language_id,
                        type_code=type_code,
                    )
                    if q_entry is None:
                        # Judge hard-rejected this question — skip it.
                        continue

                questions.append(q_entry)
                previous_questions.append(question.question_text)

            except Exception as e:
                logger.error(f"Failed to generate {type_code}: {e}")
                continue

        logger.info(f"Generated {len(questions)}/{len(question_type_codes)} questions")
        return questions

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
    ) -> MCQuestion:
        """Generate a single question of specified type.

        Returns the validated MCQuestion. Raises ValidationError if both
        the initial LLM call and the schema-aware repair retry produce
        malformed output (e.g. answer not in choices, fewer than 4 choices).
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

        logger.debug(f"Prompt for {question_type_code}: {len(prompt)} chars")

        try:
            question = call_llm(
                prompt,
                model=model,
                temperature=test_gen_config.question_temperature,
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
    ) -> Optional[Dict]:
        """Run answer-entailment and distractor-plausibility judges on a question.

        Returns the (possibly annotated) q_entry dict, or None if a judge
        hard-rejects the question.  Attaches ``_judge_flags`` to the dict when
        one or more judges flag (but do not reject) the question.

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
            return None

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
        if worst_dp and worst_dp.verdict == 'reject':
            logger.info(
                "Judge rejected %s distractors (conf=%.2f): %s",
                type_code, worst_dp.confidence, worst_dp.reason,
            )
            return None

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

        return q_entry

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
