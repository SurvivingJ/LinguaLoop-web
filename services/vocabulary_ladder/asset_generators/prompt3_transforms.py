# services/vocabulary_ladder/asset_generators/prompt3_transforms.py
"""
Prompt 3: Spot-Incorrect Sentence Generator (L7)

Once the shared "grammar & structure" prompt for levels 4, 7 and 8. L4
(morphology) and L8 (collocation repair) moved to their own ``task_name``s in
TASK-520 — see ``l4_morphology.py`` and ``l8_repair.py`` — leaving this prompt
with the one level that was never the problem: crafting a single sentence that
is wrong for a stated reason.

What the split removed from this module
---------------------------------------
* The two remap functions that guessed between four possible option-array
  shapes. Those branches only existed because nothing validated the response;
  the split levels are schema-gated before remap instead.
* The L8 input pre-gate (``_can_generate_l8`` / ``_pick_l8_sentence_index``).
  Scanning for a sentence that attests the collocate is L8's own precondition
  and now lives with L8, where returning None skips one level rather than
  editing a shared level list.

What deliberately stayed
------------------------
The JSON salvage path. L7 is a single level now, so a malformed response no
longer risks taking two others down with it — but the salvage is cheap, already
proven against this model, and still turns "lost the level" into "recovered
the level" often enough to keep.
"""

import json
import logging
import re

from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.vocabulary_ladder.config import (
    PROMPT3_MONOLITH_LEVELS, SENTENCE_ASSIGNMENTS_A, L7_CORRECT_INDICES_A,
    PROMPT3_TYPE_FOR_LEVEL, prompt3_levels_for_context,
    get_sentence_target,
)
from services.vocabulary_ladder.asset_generators._renderer import render_template

logger = logging.getLogger(__name__)

TASK_NAME = 'vocab_prompt3_transforms'


class TransformAssetGenerator:
    """Generates the Prompt 3 asset: the L7 spot-incorrect sentence."""

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
        semantic_class: str | None = None,
        capability_context: dict | None = None,
    ) -> dict | None:
        """Generate exercise assets for the levels this prompt still owns.

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
            semantic_class: Ratified semantic_class for this word. Supplying
                it (with `capability_context`) enables per-type gating — see
                below. Omitting it keeps the pre-TASK-514 level-only behaviour.
            capability_context: Facts about this word that capability
                `requires` tokens can test (`morph_forms`, `pronunciation`, …),
                as built by `VocabAssetPipeline._capability_context`.

        Returns:
            Descriptive-keyed dict with a level_7 key, or None on failure.
        """
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A
        if l7_correct_indices is None:
            l7_correct_indices = L7_CORRECT_INDICES_A
        if used_distractors is None:
            used_distractors = []

        # Per-type gating (TASK-514/B5). `active_levels` says the *level* is
        # live; it does not say this prompt owns the capability keeping it
        # alive. The gate runs over the whole P3 family and is then narrowed to
        # what this prompt still emits, so the split levels stay governed by
        # the same rule without this prompt trying to produce them.
        p3_active = sorted(lv for lv in active_levels if lv in PROMPT3_MONOLITH_LEVELS)
        if semantic_class is not None:
            gated = prompt3_levels_for_context(
                active_levels, semantic_class, self.language_id, capability_context,
            )
            dropped = [lv for lv in p3_active if lv not in gated]
            if dropped:
                logger.info(
                    "Sense %s: per-type gate dropped P3 level(s) %s "
                    "(no enabled %s row for language_id=%s semantic_class=%s)",
                    sense_id, dropped,
                    [PROMPT3_TYPE_FOR_LEVEL.get(lv) for lv in dropped],
                    self.language_id, semantic_class,
                )
            p3_active = [lv for lv in p3_active if lv in gated]

        if not p3_active:
            logger.warning("No Prompt 3 levels active for sense %s", sense_id)
            return {}

        prompt_text = self._build_prompt(
            core_asset, p3_active, sentence_assignments, l7_correct_indices,
            used_distractors,
        )
        cfg = self._cfg

        raw = self._call_with_retry(prompt_text, cfg, p3_active, sense_id)
        if raw is None:
            return None

        return self._remap_output(raw, p3_active)

    def _call_with_retry(
        self, prompt_text: str, cfg: dict, p3_active: list[int], sense_id: int,
    ) -> dict | None:
        """Single LLM call, retry once if any active level is missing or call fails.

        On total JSON-parse failure we make a salvage attempt in 'text' mode and
        try to extract the top-level level keys independently — Sonnet
        sometimes drops a comma deep inside an array, which kills strict JSON
        parsing for the entire response. Salvage means at worst we lose the
        broken level, not the whole call.
        """
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
        independently.
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

        # L4/L8 placeholders are still supplied even though this prompt no
        # longer asks for those levels: `render_template` raises on any
        # placeholder the template mentions but the caller omits, and the
        # currently-seeded template rows predate the split. Extra kwargs are
        # ignored, so this keeps working against both the old rows and the
        # narrowed ones the TASK-520 migration installs. `active_levels_json`
        # is the contract that actually stops L4/L8 being emitted.
        l8_idx = sentence_assignments.get(8, 4)
        l8_sentence_text = ''
        if 0 <= l8_idx < len(sentences):
            l8_sentence_text = sentences[l8_idx].get('text', '')

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
            morphological_forms_json=json.dumps(
                core_asset.get('morphological_forms', []), ensure_ascii=False,
            ),
            active_levels_json=json.dumps([str(lv) for lv in active_levels]),
            used_distractors_json=json.dumps(used_distractors, ensure_ascii=False),
            level_4_sentence_index=sentence_assignments.get(4, 1),
            level_7_correct_indices=json.dumps(l7_correct_indices),
            level_8_sentence_index=l8_idx,
            level_8_sentence_text=l8_sentence_text,
            level_8_collocate_word=(core_asset.get('primary_collocate') or '').strip() or 'null',
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template from the database (Supabase-driven)."""
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['template']

    def _remap_output(self, raw: dict, active_levels: list[int]) -> dict:
        """Transform numeric-keyed LLM output to descriptive level keys."""
        result = {}
        for level in active_levels:
            level_key = str(level)
            if level_key not in raw:
                logger.warning("Prompt 3 missing level %s in output", level)
                continue
            if level == 7:
                result['level_7'] = self._remap_level_7(raw[level_key])
        return result

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
