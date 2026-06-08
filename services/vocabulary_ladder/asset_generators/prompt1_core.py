# services/vocabulary_ladder/asset_generators/prompt1_core.py
"""
Prompt 1: Core Asset Generator

Calls configurable model (default Gemini Flash) to classify a word and
generate base assets: POS, semantic class, definition, pronunciation, IPA,
morphological forms, and 6 example sentences (corpus-first, generate rest).

This is the foundation — Prompts 2 and 3 depend on the output of Prompt 1.
"""

import json
import logging
from typing import Optional

from config import Config
from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.vocabulary_ladder.config import (
    PROMPT1_KEY_MAP, SENTENCE_KEY_MAP, MORPH_FORM_KEY_MAP,
    get_sentence_target, remap_keys,
)
from services.vocabulary_ladder.asset_generators._renderer import render_template

logger = logging.getLogger(__name__)

TASK_NAME = 'vocab_prompt1_core'


class CoreAssetGenerator:
    """Generates Prompt 1 assets: classification, definition, sentences."""

    def __init__(self, db, language_id: int):
        self.db = db
        self.language_id = language_id
        # Lazy-resolved on first generate() — pulls model+template from Supabase.
        self._cfg: dict | None = None

    @property
    def model(self) -> str:
        """Model string for the active prompt config (used by storage layer)."""
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['model']

    def generate(
        self,
        sense_id: int,
        corpus_sentences: list[dict],
    ) -> dict | None:
        """Generate core assets for a word sense.

        Args:
            sense_id: The dim_word_senses ID.
            corpus_sentences: Pre-existing sentences from tests/conversations.
                Each dict has keys: text, target_word (alias-aware: legacy
                rows may have target_substring), source, complexity_tier.

        Returns:
            Descriptive-keyed dict ready for word_assets storage, or None on failure.
        """
        # Load word metadata from DB
        word_data = self._load_word_data(sense_id)
        if not word_data:
            logger.error("Cannot load word data for sense_id=%s", sense_id)
            return None

        lemma = word_data['lemma']
        existing_def = word_data.get('definition', '')
        complexity_tier = word_data.get('complexity_tier', 'T3')

        # Determine how many sentences to generate
        sentences_needed = max(0, Config.VOCAB_SENTENCES_PER_WORD - len(corpus_sentences))

        # Build and send prompt
        prompt_text = self._build_prompt(
            lemma, existing_def, complexity_tier,
            corpus_sentences, sentences_needed,
            sense_id=sense_id,
        )

        cfg = self._cfg  # populated by _build_prompt → _load_template
        raw = self._call_with_retry(prompt_text, cfg, lemma, sense_id)
        if raw is None:
            return None

        # Remap numeric keys to descriptive
        content = self._remap_output(raw)
        if content is None:
            logger.error("Prompt 1 key remapping failed for '%s'", lemma)
            return None

        return content

    def _load_word_data(self, sense_id: int) -> dict | None:
        """Fetch lemma, definition, and tier from DB."""
        try:
            resp = (
                self.db.table('dim_word_senses')
                .select('id, definition, pronunciation, vocab_id, '
                        'dim_vocabulary(lemma, part_of_speech, level_tag)')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            row = resp.data
            if not row:
                return None

            vocab = row.get('dim_vocabulary') or {}
            return {
                'sense_id': sense_id,
                'lemma': vocab.get('lemma', ''),
                'pos': vocab.get('part_of_speech', ''),
                'definition': row.get('definition', ''),
                'pronunciation': row.get('pronunciation', ''),
                'complexity_tier': vocab.get('level_tag') or 'T3',
            }
        except Exception as e:
            logger.error("DB lookup failed for sense %s: %s", sense_id, e)
            return None

    def _build_prompt(
        self,
        lemma: str,
        existing_definition: str,
        complexity_tier: str,
        corpus_sentences: list[dict],
        sentences_needed: int,
        sense_id: int | None = None,
    ) -> str:
        """Load prompt template and fill variables."""
        template = self._load_template()

        corpus_json = json.dumps(
            [{'1': s.get('text', ''), '2': get_sentence_target(s)}
             for s in corpus_sentences],
            ensure_ascii=False,
        ) if corpus_sentences else '[]'

        return render_template(
            template,
            word=lemma,
            existing_definition=existing_definition or 'None provided',
            sense_id=str(sense_id) if sense_id is not None else '',
            sense_definition=existing_definition or '',
            complexity_tier=complexity_tier,
            corpus_sentences_json=corpus_json,
            sentences_needed=sentences_needed,
        )

    def _load_template(self) -> str:
        """Fetch the active prompt template from the database (Supabase-driven)."""
        if self._cfg is None:
            self._cfg = get_template_config(self.db, TASK_NAME, self.language_id)
        return self._cfg['template']

    def _call_with_retry(
        self, prompt_text: str, cfg: dict, lemma: str, sense_id: int,
    ) -> dict | None:
        """Single LLM call with one automatic retry on exception or blank response."""
        for attempt in (1, 2):
            try:
                raw = call_llm(
                    prompt_text,
                    model=cfg['model'],
                    provider=cfg['provider'],
                    temperature=0.3,
                    max_tokens=8192,
                    response_format='json',
                )
            except Exception as e:
                logger.warning(
                    "Prompt 1 LLM call attempt %d failed for '%s' (sense %s): %s",
                    attempt, lemma, sense_id, e,
                )
                if attempt == 2:
                    logger.error(
                        "Prompt 1 gave up for '%s' (sense %s) after 2 attempts",
                        lemma, sense_id,
                    )
                    return None
                continue

            if raw:
                return raw
            if attempt == 1:
                logger.warning(
                    "Prompt 1 returned blank for '%s' (sense %s) — retrying once",
                    lemma, sense_id,
                )
        return None

    def repair(
        self,
        current_content: dict,
        validation_errors: list[str],
        sense_id: int,
    ) -> dict | None:
        """Targeted repair call: fix specific validation errors in an existing P1 asset.

        Sends the current (descriptive-keyed) JSON plus the error list to the
        model, asking it to fix only the flagged fields. Used by the pipeline
        as a last resort before giving up on P1 entirely.

        Returns a descriptive-keyed content dict, or None if the repair fails.
        """
        cfg = self._cfg
        if not cfg:
            return None

        errors_text = '\n'.join(f'- {e}' for e in validation_errors)
        current_json = json.dumps(current_content, ensure_ascii=False, indent=2)

        repair_prompt = (
            "The following vocabulary asset JSON has validation errors. "
            "Fix ONLY the fields needed to resolve the listed errors and return "
            "the complete corrected JSON object unchanged except for those fixes.\n\n"
            f"VALIDATION ERRORS:\n{errors_text}\n\n"
            f"CURRENT JSON:\n{current_json}\n\n"
            "Return ONLY the corrected JSON object, using the same field names."
        )

        try:
            raw = call_llm(
                repair_prompt,
                model=cfg['model'],
                provider=cfg['provider'],
                temperature=0.2,
                max_tokens=8192,
                response_format='json',
            )
        except Exception as e:
            logger.warning("Prompt 1 repair call failed for sense %s: %s", sense_id, e)
            return None

        if not raw:
            return None

        # Repair returns descriptive keys (same as input). Guard against the
        # model reverting to numeric keys by checking for the canonical P1 key.
        if '1' in raw and 'pos' not in raw:
            return self._remap_output(raw)
        return raw

    def repair_sentences(
        self,
        core_asset: dict,
        bad_indices: list[int],
        reasons: dict[int, str],
        sense_id: int,
    ) -> dict[int, str] | None:
        """Rewrite only the flagged base sentences in place, preserving indices.

        Used by the P1 sentence judge (Phase 4): given the sentence indices the
        judge rejected, ask the model for a replacement sentence per index that
        uses the target in the intended sense and register. Returns a map of
        ``{index: new_sentence_text}`` for the indices it could repair, or None
        on failure. The caller splices these into ``core_asset['sentences']`` at
        the SAME positions — sentence count and order are never changed, because
        downstream levels reference sentence indices positionally.
        """
        cfg = self._cfg
        if not cfg or not bad_indices:
            return None

        sentences = core_asset.get('sentences', []) or []
        lemma = get_sentence_target(sentences[0]) if sentences else ''
        definition = core_asset.get('definition', '')
        register = core_asset.get('register') or 'neutral'
        fingerprint = core_asset.get('sense_fingerprint') or ''

        flagged = []
        for idx in bad_indices:
            if 0 <= idx < len(sentences):
                text = sentences[idx].get('text', '')
                problem = reasons.get(idx, 'off-sense or off-register')
                flagged.append(f'{idx}. (problem: {problem}) {text}')
        if not flagged:
            return None

        flagged_text = '\n'.join(flagged)
        # NB: literal JSON braces are doubled because this is an f-string.
        repair_prompt = (
            f'Target word: {lemma}\n'
            f'Intended sense (definition): {definition}\n'
            f'Sense fingerprint: {fingerprint}\n'
            f'Register: {register}\n\n'
            'Each sentence below was rejected by a corpus judge for not using '
            'the target word in the intended sense/register, or for not using '
            'it as a whole word. Rewrite EACH one as a NEW natural sentence that '
            'uses the target word as a whole word in exactly the intended sense '
            'and register. Keep roughly the same length and difficulty.\n\n'
            f'{flagged_text}\n\n'
            'Return JSON ONLY: an object keyed by the original index (as a '
            'string) mapping to the rewritten sentence text. Example: '
            '{{"3": "rewritten sentence ...", "7": "rewritten sentence ..."}}'
        )

        try:
            raw = call_llm(
                repair_prompt,
                model=cfg['model'],
                provider=cfg['provider'],
                temperature=0.4,
                max_tokens=4096,
                response_format='json',
            )
        except Exception as e:
            logger.warning("P1 sentence repair failed for sense %s: %s", sense_id, e)
            return None

        if not isinstance(raw, dict):
            return None

        out: dict[int, str] = {}
        for k, v in raw.items():
            try:
                idx = int(k)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(sentences) and isinstance(v, str) and v.strip():
                out[idx] = v.strip()
        return out or None

    def _remap_output(self, raw: dict) -> dict | None:
        """Transform numeric-keyed LLM output to descriptive keys."""
        try:
            content = {}
            for num_key, desc_key in PROMPT1_KEY_MAP.items():
                if num_key in raw:
                    content[desc_key] = raw[num_key]

            # Remap nested sentence objects
            if 'sentences' in content and isinstance(content['sentences'], list):
                content['sentences'] = [
                    remap_keys(s, SENTENCE_KEY_MAP)
                    if isinstance(s, dict) else s
                    for s in content['sentences']
                ]

            # Remap nested morphological form objects
            if 'morphological_forms' in content and isinstance(content['morphological_forms'], list):
                content['morphological_forms'] = [
                    remap_keys(f, MORPH_FORM_KEY_MAP)
                    if isinstance(f, dict) else f
                    for f in content['morphological_forms']
                ]

            # Ensure syllable_count is int
            if 'syllable_count' in content:
                content['syllable_count'] = int(content['syllable_count'])

            return content

        except Exception as e:
            logger.error("Prompt 1 output remapping error: %s", e)
            return None
