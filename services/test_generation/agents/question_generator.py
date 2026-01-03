"""
Question Generator Agent

Generates comprehension questions for tests using LLM.
Supports 6 semantic question types.
"""

import json
import logging
from typing import List, Dict, Optional
from uuid import uuid4
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import test_gen_config

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Generates comprehension questions using LLM."""

    # OpenRouter base URL
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

    # Question type descriptions for prompting
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
        """
        Initialize the Question Generator.

        Args:
            api_key: OpenRouter API key (defaults to config)
            model: LLM model to use (defaults to config)
        """
        self.api_key = api_key or test_gen_config.openrouter_api_key
        self.model = model or test_gen_config.default_question_model
        self.api_call_count = 0

        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.OPENROUTER_BASE_URL
        )

        logger.info(f"QuestionGenerator initialized with model: {self.model}")

    def generate_questions(
        self,
        prose: str,
        language_name: str,
        question_type_codes: List[str],
        prompt_templates: Optional[Dict[str, str]] = None,
        model_override: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate multiple questions for prose content.

        Args:
            prose: The prose/transcript text
            language_name: Target language name
            question_type_codes: List of question type codes to generate
            prompt_templates: Dict of type_code -> template (optional)
            model_override: Override model for these calls

        Returns:
            List of question dicts with keys: id, question, choices, answer, type_code
        """
        questions = []
        previous_questions = []

        for i, type_code in enumerate(question_type_codes):
            try:
                question = self._generate_single_question(
                    prose=prose,
                    language_name=language_name,
                    question_type_code=type_code,
                    previous_questions=previous_questions,
                    prompt_template=prompt_templates.get(type_code) if prompt_templates else None,
                    model_override=model_override
                )

                questions.append({
                    'id': str(uuid4()),
                    'question': question['Question'],
                    'choices': question['Options'],
                    'answer': question['Answer'],
                    'type_code': type_code,
                    'display_order': i + 1
                })

                previous_questions.append(question['Question'])

            except Exception as e:
                logger.error(f"Failed to generate question type {type_code}: {e}")
                # Continue with remaining questions
                continue

        logger.info(f"Generated {len(questions)}/{len(question_type_codes)} questions")
        return questions

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def _generate_single_question(
        self,
        prose: str,
        language_name: str,
        question_type_code: str,
        previous_questions: List[str],
        prompt_template: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Dict:
        """
        Generate a single question of specified type.

        Args:
            prose: The prose/transcript text
            language_name: Target language
            question_type_code: Type of question to generate
            previous_questions: Previously generated questions (for diversity)
            prompt_template: Custom prompt template (optional)
            model_override: Override model for this call

        Returns:
            Dict with keys: Question, Options, Answer
        """
        model = model_override or self.model

        # Build prompt
        if prompt_template:
            prompt = prompt_template.format(
                transcript=prose,
                language=language_name,
                previous_questions='; '.join(previous_questions) if previous_questions else 'None'
            )
        else:
            prompt = self._build_question_prompt(
                prose,
                language_name,
                question_type_code,
                previous_questions
            )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=test_gen_config.question_temperature,
                timeout=30
            )

            self.api_call_count += 1

            if not response.choices:
                raise Exception("No response from LLM")

            content = response.choices[0].message.content
            if not content:
                raise Exception("Empty response from LLM")

            # Parse JSON response
            question_data = self._parse_question_response(content.strip())

            logger.debug(f"Generated {question_type_code} question successfully")
            return question_data

        except Exception as e:
            logger.error(f"Question generation failed for {question_type_code}: {e}")
            raise

    def _build_question_prompt(
        self,
        prose: str,
        language: str,
        question_type_code: str,
        previous_questions: List[str]
    ) -> str:
        """Build prompt for question generation."""
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
1. Write the question and all options in {language}
2. Create exactly 4 answer options
3. Only one option should be correct
4. Make distractors plausible but clearly incorrect
5. Avoid questions similar to previously asked ones
6. Match the cognitive level ({type_info['cognitive_level']}/3) in complexity

Return ONLY valid JSON in this exact format:
{{
    "Question": "Your question text here?",
    "Options": ["Option A", "Option B", "Option C", "Option D"],
    "Answer": "The correct option text (must match exactly one of the Options)"
}}
"""

    def _parse_question_response(self, content: str) -> Dict:
        """Parse and validate question response from LLM."""
        # Clean markdown code blocks
        if content.startswith('```'):
            content = content.replace('```json', '', 1)
            content = content.replace('```', '', 1)
        if content.endswith('```'):
            content = content.rsplit('```', 1)[0]

        content = content.strip()

        # Find JSON object
        start_idx = content.find('{')
        end_idx = content.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_str = content[start_idx:end_idx + 1]
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in response: {json_str[:100]}...")
        else:
            raise ValueError(f"No JSON object found in response: {content[:100]}...")

        # Validate required fields
        required = ['Question', 'Options', 'Answer']
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate options
        if not isinstance(data['Options'], list) or len(data['Options']) != 4:
            raise ValueError("Options must be a list of exactly 4 items")

        # Validate answer is in options
        answer = data['Answer'].strip()
        options = [opt.strip() for opt in data['Options']]

        if answer not in options:
            # Try to match by letter (A, B, C, D)
            if answer in ['A', 'B', 'C', 'D']:
                idx = ord(answer) - ord('A')
                if 0 <= idx < 4:
                    data['Answer'] = options[idx]
            else:
                # Find closest match
                for opt in options:
                    if answer.lower() in opt.lower() or opt.lower() in answer.lower():
                        data['Answer'] = opt
                        break
                else:
                    logger.warning(f"Answer '{answer}' not in options, using first option")
                    data['Answer'] = options[0]

        data['Options'] = options
        return data

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
