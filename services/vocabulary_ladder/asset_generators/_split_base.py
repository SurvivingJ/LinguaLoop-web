# services/vocabulary_ladder/asset_generators/_split_base.py
"""Shared machinery for the per-exercise-type ladder prompts (TASK-520).

Why levels are being peeled out of P3
-------------------------------------
The P3 monolith asked one model, in one call, for morphology (L4), a crafted
wrong sentence (L7) and a collocation repair (L8). Three consequences, all of
them costs the audit charged against L4 and L8 specifically (B3.2 / B3.4):

* **Coupled failure.** One malformed array killed the whole response. The
  salvage path in ``prompt3_transforms`` exists purely to claw back the other
  two levels from a broken third.
* **Coupled model choice.** Morphology needs a model with real grammatical
  knowledge of the language; spot-incorrect is a much cheaper judgement. One
  ``task_name`` meant one model for both.
* **Coupled retry.** A missing L4 forced a retry that regenerated L7 and L8 too,
  paying three times for one gap.

A generator per type fixes all three, and — because a single-type prompt has
exactly one output shape — lets the response be schema-checked before the
remap instead of guessed at by it.

Contract for subclasses
-----------------------
``TASK_NAME``   ``prompt_templates.task_name`` for this prompt.
``LEVEL``       the ladder level it produces (keys the returned dict).
``TYPE_CODE``   the capability-matrix type, used to look up the output schema.

``_sentence_index``  which P1 sentence this item is built from, or None when
                     the sense cannot support the level at all.
``_prompt_vars``     the template placeholders.
``_remap``           schema-valid raw output → the descriptive level dict the
                     renderer reads.

Return values from :meth:`generate` are three-way on purpose:
``{'level_N': {...}}`` produced, ``{}`` not applicable to this sense (a clean
skip, not an error), ``None`` the generator tried and failed.
"""

from __future__ import annotations

import json
import logging

from services.exercise_generation.schemas import (
    OPTIONS_KEY, SchemaError, error_escape, read_index, validate_ladder_output,
)
from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.vocabulary_ladder.asset_generators._renderer import render_template
from services.vocabulary_ladder.config import (
    LADDER_OPTION_KEY_MAP, get_sentence_target, remap_keys,
)

logger = logging.getLogger(__name__)

# One retry. The split exists so a retry costs one level rather than three;
# a second retry would just pay twice for a prompt that is misbehaving.
_MAX_ATTEMPTS = 2

# language_id → llm_calls.language_code. Same hardcoded map used by
# services/exercise_generation/judges/answer_entailment.py — see there for
# why this isn't DimensionService (needs an app-startup init this offline
# pipeline doesn't do).
_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}


class SplitLevelGenerator:
    """Base for a prompt that produces exactly one ladder level."""

    TASK_NAME: str = ''
    LEVEL: int = 0
    TYPE_CODE: str = ''

    #: LLM sampling temperature. Lower than P3's 0.4 — a single-level prompt
    #: has no need to vary across levels, and determinism makes the schema gate
    #: a stable signal rather than a dice roll.
    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 2048

    def __init__(self, db, language_id: int):
        self.db = db
        self.language_id = language_id
        self._cfg: dict | None = None

    # ------------------------------------------------------------------
    # Template config
    # ------------------------------------------------------------------

    @property
    def cfg(self) -> dict:
        if self._cfg is None:
            self._cfg = get_template_config(self.db, self.TASK_NAME, self.language_id)
        return self._cfg

    @property
    def model(self) -> str:
        return self.cfg['model']

    @property
    def prompt_version(self) -> int:
        return int(self.cfg['version'])

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        sense_id: int,
        core_asset: dict,
        sentence_assignments: dict[int, int],
        used_distractors: list[str] | None = None,
    ) -> dict | None:
        """Generate this level's asset fragment for one sense.

        Returns ``{'level_<LEVEL>': {...}}`` on success, ``{}`` when the sense
        cannot support the level (no usable sentence, no collocate), or None
        when the prompt was run and did not produce schema-valid output.
        """
        sentence_index = self._sentence_index(core_asset, sentence_assignments)
        if sentence_index is None:
            logger.info(
                'L%d skipped for sense %s — no usable sentence for %s',
                self.LEVEL, sense_id, self.TYPE_CODE,
            )
            return {}

        try:
            cfg = self.cfg
        except Exception as exc:
            logger.error(
                'L%d template config unavailable for lang=%s: %s',
                self.LEVEL, self.language_id, exc,
            )
            return None

        prompt = render_template(
            cfg['template'],
            **self._prompt_vars(core_asset, sentence_index, used_distractors or []),
        )

        raw = self._call_with_retry(prompt, cfg, sense_id)
        if raw is None:
            return None

        # The error escape (key 9) is the model's own "this sense cannot carry
        # this exercise" — the same outcome as a failed precondition, so it
        # takes the clean-skip branch rather than the failure one.
        declined = error_escape(raw)
        if declined:
            logger.info(
                'L%d declined by the model for sense %s: %s',
                self.LEVEL, sense_id, declined,
            )
            return {}

        return {f'level_{self.LEVEL}': self._remap(raw, sentence_index)}

    # ------------------------------------------------------------------
    # LLM call + schema gate
    # ------------------------------------------------------------------

    def _call_with_retry(self, prompt: str, cfg: dict, sense_id: int) -> dict | None:
        """Call the prompt, re-asking once if the call or the schema fails.

        Schema failure is retried for the same reason a call failure is: both
        are usually transient model behaviour, and a second sample is far
        cheaper than losing the level. What is *not* retried is an unregistered
        prompt version — that is a configuration error, and re-asking would
        only produce the same ungated output.
        """
        last_errors: list[str] = []

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                raw = call_llm(
                    prompt,
                    model=cfg['model'],
                    provider=cfg['provider'],
                    temperature=self.TEMPERATURE,
                    max_tokens=self.MAX_TOKENS,
                    # Provider-enforced, not just client-side parsed: these
                    # prompts return numeric keys, and a model that drifts
                    # into prose costs a whole retry cycle to discover.
                    response_format='json_object',
                    pipeline='vocab_ladder',
                    task_name=self.TASK_NAME,
                    template_version=cfg['version'],
                    language_code=_LANG_ID_TO_CODE.get(self.language_id),
                )
            except Exception as exc:
                last_errors = [f'LLM call failed: {exc}']
                logger.warning(
                    'L%d attempt %d failed for sense %s: %s',
                    self.LEVEL, attempt, sense_id, exc,
                )
                continue

            try:
                errors = validate_ladder_output(
                    self.TYPE_CODE, int(cfg['version']), raw,
                )
            except SchemaError as exc:
                # Ungated prompt version — a deploy problem, not model noise.
                logger.error('L%d schema gate refused sense %s: %s', self.LEVEL, sense_id, exc)
                return None

            if not errors:
                return raw

            last_errors = errors
            logger.warning(
                'L%d schema check failed on attempt %d for sense %s: %s',
                self.LEVEL, attempt, sense_id, '; '.join(errors[:4]),
            )

        logger.error(
            'L%d produced no schema-valid output for sense %s after %d attempts: %s',
            self.LEVEL, sense_id, _MAX_ATTEMPTS, '; '.join(last_errors[:4]),
        )
        return None

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _sentence_index(
        self, core_asset: dict, sentence_assignments: dict[int, int],
    ) -> int | None:
        raise NotImplementedError

    def _prompt_vars(
        self, core_asset: dict, sentence_index: int, used_distractors: list[str],
    ) -> dict:
        raise NotImplementedError

    def _remap(self, raw: dict, sentence_index: int) -> dict:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def sentences(core_asset: dict) -> list[dict]:
        return (core_asset or {}).get('sentences') or []

    @classmethod
    def sentence_text(cls, core_asset: dict, index: int) -> str:
        sentences = cls.sentences(core_asset)
        if 0 <= index < len(sentences):
            return sentences[index].get('text', '') or ''
        return ''

    @classmethod
    def lemma(cls, core_asset: dict) -> str:
        sentences = cls.sentences(core_asset)
        return get_sentence_target(sentences[0]) if sentences else ''

    @classmethod
    def tier(cls, core_asset: dict) -> str:
        sentences = cls.sentences(core_asset)
        return (sentences[0].get('complexity_tier') if sentences else None) or 'T3'

    @staticmethod
    def option_array(raw: dict) -> list[dict]:
        """The option array, read off the contract's reserved key 0."""
        return read_index(raw, OPTIONS_KEY) or []

    @staticmethod
    def field(raw: dict, key: str | int):
        """One top-level field of an indexed response."""
        return read_index(raw, key)

    @staticmethod
    def descriptive(opt: dict) -> dict:
        """One indexed option object → descriptive keys.

        This is the boundary the numeric contract stops at. Indices exist to
        keep English out of a ZH/JA *prompt*; nothing downstream of the model
        benefits from them, and letting them reach ``word_assets.content``
        would push the translation onto the renderer, the validators and every
        future reader of a stored asset.

        Keys are normalised to strings first so a fixture built in Python with
        int keys remaps the same way a parsed JSON response does.
        """
        return remap_keys(
            {str(k): v for k, v in (opt or {}).items()}, LADDER_OPTION_KEY_MAP,
        )

    @classmethod
    def options_to_content(cls, options: list[dict]) -> dict:
        """Split a schema-valid option array into the renderer's flat shape.

        Takes the indexed shape and returns descriptive keys. Safe to index
        without guarding: the schema has already established exactly four
        well-formed options with exactly one correct.
        """
        remapped = [cls.descriptive(o) for o in options]
        correct = next(o for o in remapped if o.get('is_correct'))
        return {
            'options': remapped,
            'correct_text': correct.get('text', ''),
            'explanations': {
                o.get('text', ''): o.get('explanation', '') for o in remapped
            },
        }

    @staticmethod
    def json_dump(value) -> str:
        return json.dumps(value, ensure_ascii=False)
