# services/vocabulary_ladder/asset_generators/prompt3_transforms.py
"""
Prompt 3: Grammar & Structure Exercise Generator

Calls configurable model (default Claude Sonnet) to generate exercise content
for levels 4 (morphology slot), 7 (spot incorrect sentence), and 8 (collocation
repair). Single LLM call for all included levels.
"""

import json
import logging
import re

from config import Config
from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.vocabulary_ladder.config import (
    PROMPT3_LEVELS, OPTION_KEY_MAP, DEFAULT_SENTENCE_ASSIGNMENTS,
    SENTENCE_ASSIGNMENTS_A, L7_CORRECT_INDICES_A,
    get_sentence_target, remap_keys,
)
from services.vocabulary_ladder.asset_generators._renderer import render_template

logger = logging.getLogger(__name__)

TASK_NAME = 'vocab_prompt3_transforms'


def _whole_word_match(text: str, word: str) -> bool:
    """Return True if `word` appears as a whole word in `text` (case-insensitive)."""
    if not text or not word:
        return False
    return re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE) is not None


class TransformAssetGenerator:
    """Generates Prompt 3 assets: morphology, spot-incorrect, collocation repair."""

    def __init__(self, db, language_id: int):
        self.db = db
        self.language_id = language_id
        self._cfg: dict | None = None

    @property
    def model(self) -> str:
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['model']

    def generate(
        self,
        sense_id: int,
        core_asset: dict,
        active_levels: list[int],
        sentence_assignments: dict[int, int] | None = None,
        l7_correct_indices: list[int] | None = None,
        used_distractors: list[str] | None = None,
    ) -> dict | None:
        """Generate exercise assets for Prompt 3 levels.

        Args:
            sense_id: The dim_word_senses ID.
            core_asset: Output from Prompt 1 (descriptive keys).
            active_levels: Which ladder levels are active for this word.
            sentence_assignments: Map of level → sentence index.
                Defaults to SENTENCE_ASSIGNMENTS_A.
            l7_correct_indices: Sentence indices for L7 correct sentences.
                Defaults to L7_CORRECT_INDICES_A.
            used_distractors: Distractor texts already assigned elsewhere in
                this item set; passed to the LLM so it doesn't repeat them.
                Defaults to [].

        Returns:
            Descriptive-keyed dict with level_4, level_7, level_8 keys,
            or None on failure.
        """
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A
        if l7_correct_indices is None:
            l7_correct_indices = L7_CORRECT_INDICES_A
        if used_distractors is None:
            used_distractors = []

        p3_active = sorted(lv for lv in active_levels if lv in PROMPT3_LEVELS)
        if not p3_active:
            logger.warning("No Prompt 3 levels active for sense %s", sense_id)
            return {}

        # If L8 is requested but the primary collocate doesn't appear as a
        # whole word in the chosen sentence, drop L8 — better than emitting
        # an exercise we know is broken.
        if 8 in p3_active and not self._can_generate_l8(core_asset, sentence_assignments):
            logger.warning(
                "Skipping L8 for sense %s — primary_collocate not a whole-word "
                "match in the chosen sentence", sense_id,
            )
            p3_active = [lv for lv in p3_active if lv != 8]
            if not p3_active:
                return {}

        # Sentence assignment used for the LLM call AND the remap fallback —
        # if we had to pick a non-default sentence for L8, both sides need
        # to agree so the rendered exercise points at the correct sentence.
        effective_assignments = dict(sentence_assignments)
        l8_idx = self._pick_l8_sentence_index(core_asset, sentence_assignments)
        if l8_idx is not None:
            effective_assignments[8] = l8_idx

        prompt_text = self._build_prompt(
            core_asset, p3_active, effective_assignments, l7_correct_indices,
            used_distractors,
        )
        cfg = self._cfg

        raw = self._call_with_retry(prompt_text, cfg, p3_active, sense_id)
        if raw is None:
            return None

        result = self._remap_output(raw, p3_active, effective_assignments)

        # Post-parse correctness check on L8: the LLM has been observed to
        # flip which option it labels correct. Verify the labeled-correct
        # option matches primary_collocate; if not, retry once and on failure
        # drop L8 cleanly rather than ship a wrong exercise.
        if 8 in p3_active and not self._l8_correctness_ok(result, core_asset):
            logger.warning(
                "L8 correctness check failed for sense %s — retrying once",
                sense_id,
            )
            raw_retry = self._call_with_retry(prompt_text, cfg, p3_active, sense_id)
            if raw_retry is not None:
                result = self._remap_output(raw_retry, p3_active, effective_assignments)
            if not self._l8_correctness_ok(result, core_asset):
                logger.error(
                    "L8 correctness still wrong for sense %s after retry — dropping L8",
                    sense_id,
                )
                result.pop('level_8', None)

        return result

    def _can_generate_l8(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> bool:
        """Sanity-check inputs needed for L8 before we even call the LLM."""
        collocate = (core_asset.get('primary_collocate') or '').strip()
        if not collocate or collocate.lower() == 'null':
            return False
        return self._pick_l8_sentence_index(core_asset, sentence_assignments) is not None

    def _pick_l8_sentence_index(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> int | None:
        """Choose a sentence index for L8 that contains the primary collocate.

        Prefers the variant's assigned index, then scans the rest of the pool.
        Returns None if no sentence contains the collocate as a whole word.
        """
        collocate = (core_asset.get('primary_collocate') or '').strip()
        if not collocate or collocate.lower() == 'null':
            return None

        sentences = core_asset.get('sentences', []) or []
        if not sentences:
            return None

        preferred = sentence_assignments.get(8, 4)
        # Try the assigned index first, then the rest in order.
        order = [preferred] + [i for i in range(len(sentences)) if i != preferred]
        for idx in order:
            if 0 <= idx < len(sentences):
                sent_text = sentences[idx].get('text', '')
                if _whole_word_match(sent_text, collocate):
                    return idx
        return None

    def _l8_correctness_ok(self, result: dict, core_asset: dict) -> bool:
        """Verify the L8 'correct' option actually equals primary_collocate."""
        l8 = result.get('level_8') or {}
        options = l8.get('options') or []
        correct = [o for o in options if o.get('is_correct')]
        if len(correct) != 1:
            return False
        target_collocate = (core_asset.get('primary_collocate') or '').strip()
        labeled = (correct[0].get('text') or '').strip()
        if labeled.lower() != target_collocate.lower():
            return False
        # Distractors must not duplicate the correct option.
        wrong_texts = [
            (o.get('text') or '').strip().lower()
            for o in options if not o.get('is_correct')
        ]
        if labeled.lower() in wrong_texts:
            return False
        return True

    def _call_with_retry(
        self, prompt_text: str, cfg: dict, p3_active: list[int], sense_id: int,
    ) -> dict | None:
        """Single LLM call, retry once if any active level is missing or call fails.

        On total JSON-parse failure we make a salvage attempt in 'text' mode and
        try to extract the top-level level keys ("4"/"7"/"8") independently —
        Sonnet sometimes drops a comma deep inside the L4/L8 options array,
        which kills strict JSON parsing for the entire response and would
        otherwise sink L7 too. Salvage means at worst we lose the broken level,
        not all three.
        """
        last_parse_error = None
        for attempt in (1, 2):
            try:
                raw = call_llm(
                    prompt_text,
                    model=cfg['model'],
                    provider=cfg['provider'],
                    temperature=0.4,
                    max_tokens=8192,
                    response_format='json',
                )
            except Exception as e:
                last_parse_error = e
                logger.warning(
                    "Prompt 3 LLM call attempt %d failed for sense %s: %s",
                    attempt, sense_id, e,
                )
                if attempt == 2:
                    logger.error(
                        "Prompt 3 strict-JSON failed twice for sense %s — attempting salvage",
                        sense_id,
                    )
                    salvaged = self._salvage_from_text(prompt_text, cfg, p3_active, sense_id)
                    if salvaged:
                        logger.warning(
                            "Prompt 3 salvaged levels %s for sense %s (partial response)",
                            sorted(salvaged.keys()), sense_id,
                        )
                        return salvaged
                    logger.error("Prompt 3 salvage produced nothing for sense %s", sense_id)
                    return None
                continue

            missing = [lv for lv in p3_active if str(lv) not in (raw or {})]
            if not missing:
                return raw
            if attempt == 1:
                logger.warning(
                    "Prompt 3 missing levels %s for sense %s — retrying once",
                    missing, sense_id,
                )
            else:
                logger.error(
                    "Prompt 3 still missing levels %s for sense %s after retry — accepting partial",
                    missing, sense_id,
                )
                return raw
        return None

    def _salvage_from_text(
        self, prompt_text: str, cfg: dict, p3_active: list[int], sense_id: int,
    ) -> dict | None:
        """Last-ditch salvage when strict JSON parsing fails.

        Asks the LLM for the same response in plain text mode, then uses
        json.JSONDecoder.raw_decode to peel off each top-level level key
        independently. A malformed L4 array no longer prevents L7 from
        being recovered.
        """
        try:
            text = call_llm(
                prompt_text,
                model=cfg['model'],
                provider=cfg['provider'],
                temperature=0.4,
                max_tokens=8192,
                response_format='text',
            )
        except Exception as e:
            logger.error("Prompt 3 salvage call failed for sense %s: %s", sense_id, e)
            return None

        if not isinstance(text, str) or not text.strip():
            return None

        decoder = json.JSONDecoder()
        salvaged: dict = {}
        for level in p3_active:
            key = str(level)
            # Search for "<key>": (with optional whitespace) anywhere in the body.
            pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*')
            for m in pattern.finditer(text):
                try:
                    value, _ = decoder.raw_decode(text, m.end())
                except json.JSONDecodeError:
                    continue
                salvaged[key] = value
                break  # first successful parse wins
        return salvaged or None

    def _build_prompt(
        self, core_asset: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
        l7_correct_indices: list[int],
        used_distractors: list[str],
    ) -> str:
        """Load prompt template and fill variables."""
        template = self._load_template()

        sentences = core_asset.get('sentences', [])
        sentences_json = json.dumps(
            [{'index': i, 'text': s.get('text', ''), 'target': get_sentence_target(s)}
             for i, s in enumerate(sentences)],
            ensure_ascii=False,
        )

        morphological_forms = core_asset.get('morphological_forms', [])
        morph_json = json.dumps(morphological_forms, ensure_ascii=False)

        # L8 anchors: even when L8 is inactive, the template references these
        # vars so we must always supply non-empty placeholder strings. The
        # caller has already ensured sentence_assignments[8] points at a
        # sentence containing the collocate (when L8 is active).
        l8_idx = sentence_assignments.get(8, 4)
        l8_sentence_text = ''
        if 0 <= l8_idx < len(sentences):
            l8_sentence_text = sentences[l8_idx].get('text', '')
        l8_collocate_word = (core_asset.get('primary_collocate') or '').strip() or 'null'

        return render_template(
            template,
            word=self._extract_lemma(core_asset),
            pos=core_asset.get('pos', ''),
            semantic_class=core_asset.get('semantic_class', ''),
            complexity_tier=self._extract_tier(core_asset),
            primary_collocate=core_asset.get('primary_collocate') or 'null',
            register=core_asset.get('register') or 'neutral',
            sense_fingerprint=core_asset.get('sense_fingerprint') or '',
            sentences_json=sentences_json,
            morphological_forms_json=morph_json,
            active_levels_json=json.dumps([str(lv) for lv in active_levels]),
            used_distractors_json=json.dumps(used_distractors, ensure_ascii=False),
            level_4_sentence_index=sentence_assignments.get(4, 1),
            level_7_correct_indices=json.dumps(l7_correct_indices),
            level_8_sentence_index=l8_idx,
            level_8_sentence_text=l8_sentence_text,
            level_8_collocate_word=l8_collocate_word,
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template from the database (Supabase-driven)."""
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['template']

    def _remap_output(
        self, raw: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Transform numeric-keyed LLM output to descriptive level keys."""
        result = {}

        for level in active_levels:
            level_key = str(level)
            if level_key not in raw:
                logger.warning("Prompt 3 missing level %s in output", level)
                continue

            level_data = raw[level_key]

            if level == 4:
                result['level_4'] = self._remap_level_4(level_data, sentence_assignments)
            elif level == 7:
                result['level_7'] = self._remap_level_7(level_data)
            elif level == 8:
                result['level_8'] = self._remap_level_8(level_data, sentence_assignments)

        return result

    def _remap_level_4(self, data: dict | list, sentence_assignments: dict[int, int]) -> dict:
        """Remap Level 4 morphology slot output."""
        if isinstance(data, list):
            options = [remap_keys(opt, OPTION_KEY_MAP) for opt in data]
            correct = [o for o in options if o.get('is_correct')]
            explanations = {o.get('text', ''): o.get('explanation', '') for o in options}

            return {
                'options': options,
                'correct_form': correct[0].get('text', '') if correct else '',
                'explanations': explanations,
                'sentence_index': sentence_assignments.get(4, 1),
                'base_form': data.get('4', '') if isinstance(data, dict) else '',
                'form_label': data.get('5', '') if isinstance(data, dict) else '',
            }

        if isinstance(data, dict):
            # The v2 template puts the options array at sub-key "1" inside the
            # level dict. Earlier shapes used either an 'options' key or
            # "0".."3" as separate option dicts; keep all paths working so a
            # remap fix is robust to any LLM shape drift.
            options = []
            if isinstance(data.get('options'), list):
                options = [remap_keys(o, OPTION_KEY_MAP) for o in data['options']]
            elif isinstance(data.get('1'), list):
                options = [remap_keys(o, OPTION_KEY_MAP) for o in data['1']]
            elif any(isinstance(data.get(str(i)), dict) for i in range(4)):
                options = [remap_keys(data[str(i)], OPTION_KEY_MAP) for i in range(4) if str(i) in data]

            correct = [o for o in options if o.get('is_correct')]
            explanations = {o.get('text', ''): o.get('explanation', '') for o in options}

            return {
                'options': options,
                'correct_form': correct[0].get('text', '') if correct else '',
                'base_form': data.get('4', ''),
                'form_label': data.get('5', ''),
                'sentence_index': int(data.get('6', sentence_assignments.get(4, 1))),
                'explanations': explanations,
            }

        return {}

    def _remap_level_7(self, data: dict) -> dict:
        """Remap Level 7 spot-incorrect sentence output."""
        if not isinstance(data, dict):
            return {}

        return {
            'incorrect_sentence': data.get('1', ''),
            'corrected_sentence': data.get('2', ''),
            'error_description': data.get('3', ''),
            'correct_sentence_indices': data.get('4', [0, 1, 2]),
        }

    def _remap_level_8(self, data: dict | list, sentence_assignments: dict[int, int]) -> dict:
        """Remap Level 8 collocation repair output."""
        if isinstance(data, list):
            options = [remap_keys(opt, OPTION_KEY_MAP) for opt in data]
            correct = [o for o in options if o.get('is_correct')]
            explanations = {o.get('text', ''): o.get('explanation', '') for o in options}

            return {
                'options': options,
                'correct_collocate': correct[0].get('text', '') if correct else '',
                'explanations': explanations,
                'sentence_index': sentence_assignments.get(8, 4),
            }

        if isinstance(data, dict):
            # The v2 template puts the options array at sub-key "1" inside the
            # level dict (mirroring level 4). Keep an 'options' fallback for
            # older shapes.
            options = []
            if isinstance(data.get('options'), list):
                options = [remap_keys(o, OPTION_KEY_MAP) for o in data['options']]
            elif isinstance(data.get('1'), list):
                options = [remap_keys(o, OPTION_KEY_MAP) for o in data['1']]

            correct = [o for o in options if o.get('is_correct')]
            return {
                'options': options,
                'correct_collocate': correct[0].get('text', '') if correct else '',
                'error_collocate': data.get('5', ''),
                'sentence_index': int(data.get('4', sentence_assignments.get(8, 4))),
                'explanations': {o.get('text', ''): o.get('explanation', '') for o in options},
            }

        return {}

    def _extract_lemma(self, core_asset: dict) -> str:
        sentences = core_asset.get('sentences', [])
        if sentences:
            return get_sentence_target(sentences[0])
        return ''

    def _extract_tier(self, core_asset: dict) -> str:
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('complexity_tier', 'T3')
        return 'T3'
