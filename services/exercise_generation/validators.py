# services/exercise_generation/validators.py

from services.exercise_generation.config import (
    REQUIRED_FIELDS_BY_TYPE, MCQ_TYPES, EXPECTED_OPTION_COUNT,
)


class ExerciseValidator:
    """
    Runs deterministic structural validation on exercise content dicts.
    No LLM calls. Called after every generate_one() in the base generator.
    """

    def validate(self, content: dict, exercise_type: str) -> tuple[bool, list[str]]:
        """
        Validate a content dict for the given exercise type.
        Returns (True, []) on success; (False, [error_strings]) on failure.
        """
        errors: list[str] = []

        self._check_required_fields(content, exercise_type, errors)

        if exercise_type in MCQ_TYPES:
            self._check_mcq(content, exercise_type, errors)

        dispatch = {
            'jumbled_sentence':        self._check_jumbled_sentence,
            'spot_incorrect_sentence': self._check_spot_incorrect_sentence,
            'spot_incorrect_part':     self._check_spot_incorrect_part,
            'text_flashcard':          self._check_text_flashcard,
            'listening_flashcard':     self._check_listening_flashcard,
            'cloze_completion':        self._check_cloze_completion,
            'semantic_discrimination': self._check_semantic_discrimination,
            'verb_noun_match':         self._check_verb_noun_match,
            'nl_tl_translation':       self._check_nl_tl_translation,
            'phonetic_recognition':    self._check_phonetic_recognition,
            'definition_match':        self._check_definition_match,
            'morphology_slot':         self._check_morphology_slot,
        }
        checker = dispatch.get(exercise_type)
        if checker:
            checker(content, errors)

        critical = [e for e in errors if not e.startswith('WARN:')]
        return (len(critical) == 0), errors

    def _check_required_fields(
        self, content: dict, exercise_type: str, errors: list[str]
    ) -> None:
        for field in REQUIRED_FIELDS_BY_TYPE.get(exercise_type, []):
            if field not in content or content[field] is None:
                errors.append(f"Missing required field: {field}")

    def _check_mcq(
        self, content: dict, exercise_type: str, errors: list[str]
    ) -> None:
        correct  = content.get('correct_answer') or content.get('correct_nl') or content.get('correct')
        options  = content.get('options', [])
        expected = EXPECTED_OPTION_COUNT.get(exercise_type, 4)

        if correct and options:
            if correct not in options:
                errors.append("Correct answer is not present in options")
            if options[0] != correct:
                errors.append("V3 rule violation: correct answer must be options[0]")

        if options:
            if len(options) != len(set(str(o).lower().strip() for o in options)):
                errors.append("Duplicate options detected")
            if len(options) != expected:
                errors.append(f"Expected {expected} options, got {len(options)}")

    def _check_jumbled_sentence(self, content: dict, errors: list[str]) -> None:
        sentence = content.get('original_sentence', '')
        if not sentence or len(sentence.strip()) < 3:
            errors.append("jumbled_sentence requires a non-empty original_sentence")

    def _check_spot_incorrect_sentence(self, content: dict, errors: list[str]) -> None:
        sentences = content.get('sentences', [])
        incorrect = [s for s in sentences if not s.get('is_correct', True)]
        correct   = [s for s in sentences if s.get('is_correct', True)]
        if len(incorrect) != 1:
            errors.append(f"spot_incorrect_sentence must have exactly 1 incorrect sentence, found {len(incorrect)}")
        if len(correct) < 3:
            errors.append(f"spot_incorrect_sentence must have at least 3 correct sentences, found {len(correct)}")
        if len(sentences) == 4 and sentences[3].get('is_correct', True):
            errors.append("V3 rule: incorrect sentence must be sentences[3]")

    def _check_spot_incorrect_part(self, content: dict, errors: list[str]) -> None:
        parts       = content.get('parts', [])
        error_parts = [p for p in parts if p.get('is_error')]
        if len(error_parts) != 1:
            errors.append(f"spot_incorrect_part must have exactly 1 error part, found {len(error_parts)}")
        for ep in error_parts:
            if not ep.get('correct_form'):
                errors.append("Error part must include correct_form")
            if not ep.get('explanation'):
                errors.append("Error part must include explanation")

    def _check_text_flashcard(self, content: dict, errors: list[str]) -> None:
        if not content.get('highlight_word') or content['highlight_word'] not in content.get('front_sentence', ''):
            errors.append("highlight_word must appear in front_sentence (wrapped in **)")
        if not content.get('sense_id'):
            errors.append("text_flashcard must have sense_id")

    def _check_listening_flashcard(self, content: dict, errors: list[str]) -> None:
        url = content.get('front_audio_url', '')
        if not url.startswith('http'):
            errors.append("listening_flashcard front_audio_url must be a valid URL")

    def _check_cloze_completion(self, content: dict, errors: list[str]) -> None:
        if '___' not in content.get('sentence_with_blank', ''):
            errors.append("cloze_completion sentence_with_blank must contain '___'")
        if not content.get('distractor_tags'):
            errors.append("WARN: cloze_completion missing distractor_tags (analytics impact)")

    def _check_semantic_discrimination(self, content: dict, errors: list[str]) -> None:
        sentences    = content.get('sentences', [])
        correct_cnt  = sum(1 for s in sentences if s.get('is_correct'))
        if correct_cnt != 1:
            errors.append(f"semantic_discrimination must have exactly 1 correct sentence, found {correct_cnt}")
        if len(sentences) < 4:
            errors.append("semantic_discrimination requires 4 sentences")

    def _check_verb_noun_match(self, content: dict, errors: list[str]) -> None:
        verbs  = content.get('verbs', [])
        nouns  = content.get('nouns', [])
        pairs  = content.get('valid_pairs', [])
        if len(verbs) < 2 or len(nouns) < 2:
            errors.append("verb_noun_match requires at least 2 verbs and 2 nouns")
        for pair in pairs:
            if not (isinstance(pair, list) and len(pair) == 2):
                errors.append("valid_pairs entries must be [verb_idx, noun_idx] lists")
                break
            v_idx, n_idx = pair
            if v_idx >= len(verbs) or n_idx >= len(nouns):
                errors.append(f"valid_pair {pair} references out-of-bounds index")
                break

    def _check_nl_tl_translation(self, content: dict, errors: list[str]) -> None:
        if not content.get('primary_tl'):
            errors.append("nl_tl_translation must have primary_tl")
        if not content.get('grading_notes'):
            errors.append("nl_tl_translation must have grading_notes")

    def _check_phonetic_recognition(self, content: dict, errors: list[str]) -> None:
        if not content.get('word'):
            errors.append("phonetic_recognition must have 'word'")
        if not content.get('pronunciation') and not content.get('ipa'):
            errors.append("phonetic_recognition must have pronunciation or ipa")
        correct = content.get('correct_answer', '')
        options = content.get('options', [])
        if correct and options and correct not in options:
            errors.append("phonetic_recognition correct_answer not in options")

    def _check_definition_match(self, content: dict, errors: list[str]) -> None:
        if not content.get('correct_definition'):
            errors.append("definition_match must have correct_definition")
        options = content.get('options', [])
        correct = content.get('correct_definition', '')
        if correct and options and correct not in options:
            errors.append("definition_match correct_definition not in options")

    def _check_morphology_slot(self, content: dict, errors: list[str]) -> None:
        if '___' not in content.get('sentence_with_blank', ''):
            errors.append("morphology_slot sentence_with_blank must contain '___'")
        if not content.get('base_form'):
            errors.append("morphology_slot must have base_form")
        if not content.get('form_label'):
            errors.append("morphology_slot must have form_label")
