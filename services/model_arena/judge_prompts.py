"""Strict-rubric judge prompt builders for blind model comparison."""

import json
from typing import Sequence


PROSE_DIMENSIONS = [
    'naturalness',
    'vocabulary_appropriateness',
    'grammar_accuracy',
    'topic_adherence',
    'engagement',
    'length_compliance',
    'difficulty_calibration',
]

QUESTION_DIMENSIONS = [
    'question_quality',
    'distractor_quality',
    'cognitive_level_match',
    'answer_correctness',
    'language_accuracy',
]


def _truncate(text: str, max_chars: int = 2500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + '\n[…truncated…]'


def build_prose_judge_prompt(
    *,
    language_name: str,
    tier: str,
    difficulty: int,
    topic_concept: str,
    word_count_min: int,
    word_count_max: int,
    labeled_responses: Sequence[tuple[str, str]],
) -> str:
    """`labeled_responses`: ordered sequence of (label, prose) pairs."""
    labels = [lbl for lbl, _ in labeled_responses]

    blocks = []
    for label, prose in labeled_responses:
        blocks.append(f"=== RESPONSE {label} ===\n{_truncate(prose)}\n")
    responses_block = '\n'.join(blocks)

    schema_lines = []
    for label in labels:
        schema_lines.append(
            f'    "{label}": {{\n'
            f'      "naturalness": <1-10 integer>,\n'
            f'      "vocabulary_appropriateness": <1-10 integer>,\n'
            f'      "grammar_accuracy": <1-10 integer>,\n'
            f'      "topic_adherence": <1-10 integer>,\n'
            f'      "engagement": <1-10 integer>,\n'
            f'      "length_compliance": <1-10 integer>,\n'
            f'      "difficulty_calibration": <1-10 integer>,\n'
            f'      "reasoning": "<2-4 sentence justification>"\n'
            f'    }}'
        )
    schema = '{\n  "evaluations": {\n' + ',\n'.join(schema_lines) + '\n  }\n}'

    return f"""You are an expert evaluator of language-learning content.

You will rate {len(labeled_responses)} prose passages, all written in {language_name} for learners
at complexity tier {tier} (difficulty {difficulty}/9).

The intended topic was: "{topic_concept}"
Target length: {word_count_min}-{word_count_max} words.

Tier reference (T1 easiest → T6 hardest):
- T1: only basic verbs and concrete nouns; one idea per sentence; no abstract concepts.
- T2: compound sentences (and/but/because); concrete topics; no idioms.
- T3: light idioms; conditional sentences; everyday conversational language.
- T4: standard adult grammar; abstract nouns; moderate domain jargon.
- T5: complex subordinate clauses; cultural idioms; rich descriptive vocabulary.
- T6: high-register vocabulary; precise jargon; advanced rhetorical devices.

Evaluate each response on these 7 dimensions using a strict 1-10 scale:

1. NATURALNESS — does it read like native content?
   1-3 stilted, machine-like; 4-6 occasional awkward phrasing; 7-9 natural flow; 10 indistinguishable from native writing.

2. VOCABULARY_APPROPRIATENESS — vocabulary calibrated to {tier}?
   1-3 wildly mismatched; 4-6 some words too easy/hard; 7-9 well-calibrated; 10 perfect.

3. GRAMMAR_ACCURACY — is the grammar correct for the level?
   1-3 multiple errors; 4-6 minor errors; 7-9 correct with appropriate complexity; 10 flawless.

4. TOPIC_ADHERENCE — does it address the intended topic?
   1-3 barely on-topic; 4-6 wanders or superficial; 7-9 well-focused; 10 excellent depth.

5. ENGAGEMENT — would a learner want to keep reading?
   1-3 boring/generic; 4-6 readable but unremarkable; 7-9 interesting; 10 captivating.

6. LENGTH_COMPLIANCE — is it within the target range?
   10 = within range. Deduct 1 point per ~10% deviation outside the bounds.

7. DIFFICULTY_CALIBRATION — does the actual difficulty match the {tier} target?
   1-3 wrong tier entirely; 4-6 inconsistent; 7-9 well-calibrated; 10 perfect match.

CRITICAL JUDGING RULES:
- Use the FULL 1-10 range. Do not cluster everything around 7-8.
- Differentiate between responses. Identical scores across all responses suggest you are not reading carefully.
- Be willing to give a 10 for excellence and a 1-3 for clear failure.
- The order of responses below is randomised — do not let position influence your scores.
- Judge ONLY the response content. Do not be swayed by length alone.

{responses_block}

Return ONLY valid JSON matching this exact schema (no markdown, no commentary):
{schema}
"""


def build_questions_judge_prompt(
    *,
    language_name: str,
    tier: str,
    difficulty: int,
    shared_prose: str,
    labeled_question_sets: Sequence[tuple[str, list[dict]]],
) -> str:
    """`labeled_question_sets`: ordered sequence of (label, list_of_questions).
    Each question dict has keys: question, choices, answer, type_code.
    """
    labels = [lbl for lbl, _ in labeled_question_sets]

    blocks = []
    for label, questions in labeled_question_sets:
        rendered = json.dumps(questions, indent=2, ensure_ascii=False)
        blocks.append(f"=== RESPONSE {label} (question set) ===\n{_truncate(rendered, 4000)}\n")
    responses_block = '\n'.join(blocks)

    schema_lines = []
    for label in labels:
        schema_lines.append(
            f'    "{label}": {{\n'
            f'      "question_quality": <1-10 integer>,\n'
            f'      "distractor_quality": <1-10 integer>,\n'
            f'      "cognitive_level_match": <1-10 integer>,\n'
            f'      "answer_correctness": <1-10 integer>,\n'
            f'      "language_accuracy": <1-10 integer>,\n'
            f'      "reasoning": "<2-4 sentence justification>"\n'
            f'    }}'
        )
    schema = '{\n  "evaluations": {\n' + ',\n'.join(schema_lines) + '\n  }\n}'

    return f"""You are an expert evaluator of language-learning comprehension questions.

All sets of multiple-choice questions below were written for the SAME prose passage in
{language_name} at complexity tier {tier} (difficulty {difficulty}/9).

=== SHARED PROSE PASSAGE ===
{_truncate(shared_prose, 3000)}

Each question has fields: question, choices (4 options), answer (correct option text),
and type_code (e.g. literal_detail / vocabulary_context / main_idea / supporting_detail /
inference / author_purpose).

Evaluate each response on these 5 dimensions using a strict 1-10 scale:

1. QUESTION_QUALITY — clear, unambiguous, genuinely tests comprehension?
   1-3 ambiguous/trivial; 4-6 acceptable but flawed; 7-9 solid; 10 excellent.

2. DISTRACTOR_QUALITY — are wrong answers plausible-but-wrong (not obviously wrong)?
   1-3 distractors are nonsense or near-duplicates; 4-6 mixed quality; 7-9 well-crafted; 10 expertly designed.

3. COGNITIVE_LEVEL_MATCH — does the actual cognitive demand match the declared type_code?
   E.g. an "inference" question should require inference, not just literal recall.

4. ANSWER_CORRECTNESS — re-check each marked answer against the prose. Is it actually correct?
   1-3 multiple wrong answers; 4-6 one wrong; 7-9 all correct; 10 all correct AND the only defensible choice.

5. LANGUAGE_ACCURACY — are all questions and options in {language_name} with correct grammar?
   1-3 errors or English contamination; 4-6 minor issues; 7-9 clean; 10 flawless.

CRITICAL JUDGING RULES:
- Use the FULL 1-10 range. Differentiate between responses.
- ANSWER_CORRECTNESS is the most important dimension — be ruthless about wrong answer keys.
- The order of responses is randomised — do not let position influence your scores.

{responses_block}

Return ONLY valid JSON matching this exact schema (no markdown, no commentary):
{schema}
"""
