"""
Mystery Question Generator Agent

Creates MCQ comprehension questions for each mystery scene.
Scenes 1-4 get 1-2 comprehension questions.
Scene 5 gets a deduction question ("Who did it?").

Supports per-language prompt templates from prompt_templates table.
"""

import json
import logging
from typing import Optional, Dict, List
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import mystery_gen_config

logger = logging.getLogger(__name__)

DEFAULT_QUESTION_SYSTEM_PROMPT = """You are a language assessment expert creating multiple-choice questions
for a murder mystery reading comprehension exercise.

Requirements:
- Questions test precise reading comprehension, vocabulary in context, and logical inference
- Each question has exactly 4 options with 1 correct answer
- Distractors should be plausible but clearly wrong when the text is read carefully
- Questions should be in {language_name} (matching the scene text)
- Difficulty appropriate for CEFR {cefr_level}

Output format: valid JSON only, no markdown."""

DEFAULT_SCENE_QUESTION_PROMPT = """Create {num_questions} multiple-choice comprehension question(s) for this scene:

Scene text:
{scene_text}

Mystery context: {context}

Generate JSON array of questions:
[
    {{
        "question_text": "Question in {language_name}",
        "choices": [
            {{"label": "A", "text": "Option A in {language_name}"}},
            {{"label": "B", "text": "Option B in {language_name}"}},
            {{"label": "C", "text": "Option C in {language_name}"}},
            {{"label": "D", "text": "Option D in {language_name}"}}
        ],
        "correct_answer": "The exact text of the correct option",
        "explanation": "Brief explanation in {language_name}",
        "question_type": "inference|vocabulary|literal"
    }}
]"""

DEFAULT_DEDUCTION_PROMPT = """Create 1 deduction question for the finale of a murder mystery.

The learner has collected these clues across 5 scenes:
{clues_summary}

Suspects: {suspects_summary}

The correct answer is: {solution_suspect}

Generate a JSON array with 1 question. The question should ask who committed the crime.
Options should be the suspect names. Format:
[
    {{
        "question_text": "Based on the evidence, who is responsible?",
        "choices": [
            {{"label": "A", "text": "Suspect 1 name"}},
            {{"label": "B", "text": "Suspect 2 name"}},
            {{"label": "C", "text": "Suspect 3 name"}},
            {{"label": "D", "text": "Suspect 4 name"}}
        ],
        "correct_answer": "Name of the correct suspect",
        "explanation": "{solution_reasoning}",
        "question_type": "inference",
        "is_deduction": true
    }}
]"""


class MysteryQuestionGenerator:
    """Generates MCQ questions for mystery scenes."""

    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or mystery_gen_config.openrouter_api_key
        self.model = model or mystery_gen_config.question_model
        self.client = OpenAI(api_key=self.api_key, base_url=self.OPENROUTER_BASE_URL)
        self.api_call_count = 0
        logger.info(f"MysteryQuestionGenerator initialized with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_scene_questions(
        self,
        scene_text: str,
        story_bible: Dict,
        scene_number: int,
        language_name: str,
        cefr_level: str,
        num_questions: int = 2,
        model_override: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> List[Dict]:
        """Generate comprehension questions for a scene."""
        model = model_override or self.model

        context = f"Mystery: {story_bible['title']}. Scene {scene_number}/5."

        system_msg = DEFAULT_QUESTION_SYSTEM_PROMPT.format(
            language_name=language_name,
            cefr_level=cefr_level,
        )

        if prompt_template:
            user_msg = prompt_template.format(
                num_questions=num_questions,
                scene_text=scene_text,
                context=context,
                language_name=language_name,
            )
        else:
            user_msg = DEFAULT_SCENE_QUESTION_PROMPT.format(
                num_questions=num_questions,
                scene_text=scene_text,
                context=context,
                language_name=language_name,
            )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': user_msg},
            ],
            temperature=mystery_gen_config.question_temperature,
            max_tokens=2000,
        )
        self.api_call_count += 1

        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
            if raw.endswith('```'):
                raw = raw[:-3]

        questions = json.loads(raw)
        if not isinstance(questions, list):
            questions = [questions]

        logger.info(f"Generated {len(questions)} questions for scene {scene_number}")
        return questions

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_deduction_question(
        self,
        story_bible: Dict,
        clue_texts: List[str],
        model_override: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> List[Dict]:
        """Generate the finale deduction question."""
        model = model_override or self.model

        suspects_summary = '; '.join(
            f"{s['name']} ({s.get('motive', 'unknown motive')})"
            for s in story_bible.get('suspects', [])
        )
        clues_summary = '\n'.join(f"- Clue {i+1}: {c}" for i, c in enumerate(clue_texts))

        solution = story_bible.get('solution', {})
        solution_suspect = solution.get('suspect_name', '')
        solution_reasoning = solution.get('reasoning', '')

        if prompt_template:
            user_msg = prompt_template.format(
                clues_summary=clues_summary,
                suspects_summary=suspects_summary,
                solution_suspect=solution_suspect,
                solution_reasoning=solution_reasoning,
            )
        else:
            user_msg = DEFAULT_DEDUCTION_PROMPT.format(
                clues_summary=clues_summary,
                suspects_summary=suspects_summary,
                solution_suspect=solution_suspect,
                solution_reasoning=solution_reasoning,
            )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'Generate a deduction question. Output valid JSON only.'},
                {'role': 'user', 'content': user_msg},
            ],
            temperature=0.5,
            max_tokens=1000,
        )
        self.api_call_count += 1

        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
            if raw.endswith('```'):
                raw = raw[:-3]

        questions = json.loads(raw)
        if not isinstance(questions, list):
            questions = [questions]

        # Mark as deduction
        for q in questions:
            q['is_deduction'] = True

        logger.info("Generated deduction question for finale")
        return questions
