"""
Question Generator Agent

Generates comprehension questions for tests using LLM.
Supports 6 semantic question types.
"""

import json
import logging
import traceback
from typing import List, Dict, Optional
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
        difficulty: int = 5,
        prompt_templates: Optional[Dict[str, str]] = None,
        model_override: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate multiple questions for prose content.

        Args:
            prose: The prose/transcript text
            language_name: Target language name
            question_type_codes: List of question type codes to generate
            difficulty: Difficulty level 1-9 (for template)
            prompt_templates: Dict of type_code -> template (optional)
            model_override: Override model for these calls

        Returns:
            List of question dicts with keys: id, question, choices, answer, type_code
        """
        # DEBUG: Log all inputs
        logger.info("=" * 80)
        logger.info("QUESTION GENERATION DEBUG - generate_questions() called")
        logger.info("=" * 80)
        logger.info(f"Language: {language_name}")
        logger.info(f"Question types requested: {question_type_codes}")
        logger.info(f"Difficulty: {difficulty}")
        logger.info(f"Model override: {model_override}")
        logger.info(f"Prompt templates provided: {list(prompt_templates.keys()) if prompt_templates else 'None'}")
        logger.info(f"Prose length: {len(prose)} chars")
        logger.info(f"Prose preview (first 300 chars): {prose[:300]}")
        logger.info("-" * 80)

        questions = []
        previous_questions = []

        for type_code in question_type_codes:
            try:
                question = self._generate_single_question(
                    prose=prose,
                    language_name=language_name,
                    question_type_code=type_code,
                    difficulty=difficulty,
                    previous_questions=previous_questions,
                    prompt_template=prompt_templates.get(type_code) if prompt_templates else None,
                    model_override=model_override
                )

                questions.append({
                    'question': question['Question'],
                    'choices': question['Options'],
                    'answer': question['Answer'],
                    'type_code': type_code
                })

                previous_questions.append(question['Question'])

            except Exception as e:
                logger.error("!" * 80)
                logger.error(f"DEBUG: Failed to generate question type {type_code}")
                logger.error(f"DEBUG: Error: {e}")
                logger.error("!" * 80)
                # Continue with remaining questions
                continue

        logger.info("=" * 80)
        logger.info(f"DEBUG: QUESTION GENERATION COMPLETE")
        logger.info(f"DEBUG: Generated {len(questions)}/{len(question_type_codes)} questions")
        if questions:
            for i, q in enumerate(questions):
                logger.info(f"DEBUG: Question {i+1} ({q['type_code']}): {q['question'][:100]}...")
        else:
            logger.error("DEBUG: NO QUESTIONS WERE GENERATED!")
        logger.info("=" * 80)
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
        difficulty: int,
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
            difficulty: Difficulty level 1-9
            previous_questions: Previously generated questions (for diversity)
            prompt_template: Custom prompt template (optional)
            model_override: Override model for this call

        Returns:
            Dict with keys: Question, Options, Answer
        """
        model = model_override or self.model

        # DEBUG: Log question generation attempt
        logger.info("+" * 60)
        logger.info(f"DEBUG: _generate_single_question() for type: {question_type_code}")
        logger.info(f"DEBUG: Model being used: {model}")
        logger.info(f"DEBUG: Language: {language_name}")
        logger.info(f"DEBUG: Previous questions count: {len(previous_questions)}")
        logger.info(f"DEBUG: Has prompt_template: {prompt_template is not None}")

        # Build prompt
        if prompt_template:
            # Use placeholder names that match actual database templates:
            # {prose}, {difficulty}, {previous_questions}, {language}
            logger.info(f"Using DATABASE template for {question_type_code}")
            logger.info(f"PROSE: {prose}")
            logger.info(f"Difficulty: {difficulty}")
            logger.info(f"Prev: {previous_questions}")
            logger.info(f"Language: {language_name}")
            prompt = prompt_template.format(
                prose=prose,
                difficulty=difficulty,
                previous_questions='; '.join(previous_questions) if previous_questions else 'None',
                language=language_name
            )
            logger.info(f"DEBUG: Template preview (first 500 chars): {prompt}")
        else:
            logger.info(f"Using FALLBACK template for {question_type_code}")
            prompt = self._build_question_prompt(
                prose,
                language_name,
                question_type_code,
                previous_questions
            )

        # DEBUG: Log the FULL prepared prompt
        logger.info("-" * 60)
        logger.info(f"DEBUG: FULL PREPARED PROMPT for {question_type_code}:")
        logger.info("-" * 60)
        logger.info(prompt)
        logger.info("-" * 60)
        logger.info(f"DEBUG: Prompt length: {len(prompt)} chars")
        logger.info(f"DEBUG: Sending request to OpenRouter...")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=test_gen_config.question_temperature,
                timeout=30
            )

            self.api_call_count += 1
            logger.info(f"DEBUG: Received response from OpenRouter (API call #{self.api_call_count})")

            if not response.choices:
                logger.error("DEBUG: response.choices is empty!")
                raise Exception("No response from LLM")

            content = response.choices[0].message.content
            if not content:
                logger.error("DEBUG: response content is empty/None!")
                raise Exception("Empty response from LLM")

            # DEBUG: Log FULL raw LLM response
            logger.info("=" * 60)
            logger.info(f"DEBUG: FULL RAW LLM RESPONSE for {question_type_code}:")
            logger.info("=" * 60)
            logger.info(content)
            logger.info("=" * 60)
            logger.info(f"DEBUG: Response length: {len(content)} chars")

            # Parse JSON response
            logger.info(f"DEBUG: Parsing LLM response...")
            question_data = self._parse_question_response(content.strip())

            logger.info(f"DEBUG: Successfully generated {question_type_code} question!")
            logger.info("+" * 60)
            return question_data

        except Exception as e:
            logger.error("!" * 60)
            logger.error(f"DEBUG: EXCEPTION in question generation for {question_type_code}")
            logger.error(f"DEBUG: Exception type: {type(e).__name__}")
            logger.error(f"DEBUG: Exception message: {e}")
            logger.error(f"DEBUG: LLM Response was: {content if 'content' in locals() else 'No response received'}")
            logger.error("!" * 60)
            logger.error(f"DEBUG: Full traceback:\n{traceback.format_exc()}")
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
        logger.info("DEBUG: _parse_question_response() called")
        logger.info(f"DEBUG: Input content length: {len(content)} chars")
        logger.info(f"DEBUG: Content starts with: {repr(content[:100])}")
        logger.info(f"DEBUG: Content ends with: {repr(content[-100:])}")

        # Clean markdown code blocks
        if content.startswith('```'):
            logger.info("DEBUG: Content starts with ``` - cleaning markdown code blocks")
            content = content.replace('```json', '', 1)
            content = content.replace('```', '', 1)
        if content.endswith('```'):
            logger.info("DEBUG: Content ends with ``` - removing trailing markdown")
            content = content.rsplit('```', 1)[0]

        content = content.strip()
        logger.info(f"DEBUG: After cleanup, content length: {len(content)} chars")
        logger.info(f"DEBUG: Cleaned content preview: {repr(content[:200])}")

        # Find JSON object - use a smarter approach for nested braces
        start_idx = content.find('{')
        logger.info(f"DEBUG: Looking for opening brace, found at index: {start_idx}")

        if start_idx == -1:
            logger.error(f"No opening brace found in response: {content[:200]}")
            logger.error(f"DEBUG: Full content for inspection: {repr(content)}")
            raise ValueError(f"No JSON object found in response: {content[:100]}...")

        # Find matching closing brace by counting braces (ignores braces in strings)
        brace_count = 0
        in_string = False
        escape_next = False
        end_idx = -1

        for i in range(start_idx, len(content)):
            char = content[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break

        logger.info(f"DEBUG: Brace matching complete - end_idx: {end_idx}, final brace_count: {brace_count}")

        if end_idx == -1:
            logger.error(f"No matching closing brace found. Content: {content[:300]}")
            logger.error(f"Final brace_count: {brace_count}, in_string: {in_string}")
            logger.error(f"DEBUG: Full content for inspection: {repr(content)}")
            raise ValueError(f"No matching JSON object closing brace in response")

        json_str = content[start_idx:end_idx + 1]
        logger.info(f"DEBUG: Extracted JSON string ({len(json_str)} chars):")
        logger.info(f"DEBUG: {json_str}")

        try:
            logger.info("DEBUG: Attempting json.loads()...")
            data = json.loads(json_str)
            logger.info(f"DEBUG: JSON parsed successfully! Keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"DEBUG: Error position: line {e.lineno}, col {e.colno}, pos {e.pos}")
            logger.error(f"DEBUG: Failed JSON string: {repr(json_str)}")
            # Try to show context around the error position
            if e.pos is not None and e.pos < len(json_str):
                start = max(0, e.pos - 50)
                end = min(len(json_str), e.pos + 50)
                logger.error(f"DEBUG: Context around error: ...{repr(json_str[start:end])}...")
            raise ValueError(f"Invalid JSON: {str(e)}")

        # Normalize field names - LLMs sometimes use alternative names
        field_mappings = {
            # question_text variants -> Question
            'question_text': 'Question',
            'question': 'Question',
            'questionText': 'Question',
            # choices variants -> Options
            'choices': 'Options',
            'options': 'Options',
            'answers': 'Options',
            # correct_answer variants -> Answer
            'correct_answer': 'Answer',
            'correctAnswer': 'Answer',
            'answer': 'Answer',
        }

        logger.debug(f"Raw JSON keys before normalization: {list(data.keys())}")

        for old_key, new_key in field_mappings.items():
            if old_key in data and new_key not in data:
                data[new_key] = data[old_key]
                logger.debug(f"Normalized field '{old_key}' -> '{new_key}'")

        logger.debug(f"Normalized JSON keys: {list(data.keys())}")

        # Validate required fields
        required = ['Question', 'Options', 'Answer']
        for field in required:
            if field not in data:
                logger.error(f"DEBUG: Missing required field: {field}")
                logger.error(f"DEBUG: Available fields: {list(data.keys())}")
                logger.error(f"DEBUG: Full data: {data}")
                raise ValueError(f"Missing required field: {field}")

        logger.info(f"DEBUG: All required fields present")
        logger.info(f"DEBUG: Question: {data['Question']}")
        logger.info(f"DEBUG: Options type: {type(data['Options'])}, value: {data['Options']}")
        logger.info(f"DEBUG: Answer: {data['Answer']}")

        # Validate options
        if not isinstance(data['Options'], list) or len(data['Options']) != 4:
            logger.error(f"DEBUG: Options validation failed!")
            logger.error(f"DEBUG: Options is list: {isinstance(data['Options'], list)}")
            logger.error(f"DEBUG: Options length: {len(data['Options']) if isinstance(data['Options'], list) else 'N/A'}")
            raise ValueError("Options must be a list of exactly 4 items")

        # Validate answer is in options
        answer = data['Answer'].strip()
        options = [opt.strip() for opt in data['Options']]

        logger.info(f"DEBUG: Stripped answer: {repr(answer)}")
        logger.info(f"DEBUG: Stripped options: {options}")
        logger.info(f"DEBUG: Answer in options: {answer in options}")

        if answer not in options:
            logger.warning(f"DEBUG: Answer not in options, attempting recovery...")
            # Try to match by letter (A, B, C, D)
            if answer in ['A', 'B', 'C', 'D']:
                idx = ord(answer) - ord('A')
                if 0 <= idx < 4:
                    logger.info(f"DEBUG: Answer was letter '{answer}', mapping to option index {idx}")
                    data['Answer'] = options[idx]
            else:
                # Find closest match
                for i, opt in enumerate(options):
                    if answer.lower() in opt.lower() or opt.lower() in answer.lower():
                        logger.info(f"DEBUG: Found partial match at index {i}: {opt}")
                        data['Answer'] = opt
                        break
                else:
                    logger.warning(f"DEBUG: No match found! Answer '{answer}' not in options {options}")
                    logger.warning(f"DEBUG: Falling back to first option")
                    data['Answer'] = options[0]

        data['Options'] = options
        logger.info(f"DEBUG: Final parsed question data:")
        logger.info(f"DEBUG:   Question: {data['Question']}")
        logger.info(f"DEBUG:   Options: {data['Options']}")
        logger.info(f"DEBUG:   Answer: {data['Answer']}")
        logger.info("+" * 60)
        return data

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
