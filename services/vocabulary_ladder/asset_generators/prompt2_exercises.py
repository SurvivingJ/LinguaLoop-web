# services/vocabulary_ladder/asset_generators/prompt2_exercises.py
"""
Prompt 2: Lexical & Semantic Exercise Generator

Calls configurable model (default Claude Sonnet) to generate exercise content
for levels 1 (phonetic), 3 (cloze), 5 (collocation gap), and 6 (semantic
discrimination). Single LLM call for all included levels.

Only includes instructions for active levels — if L5 is skipped for a
concrete noun, the prompt simply omits Level 5 entirely.
"""

import json
import logging

from config import Config
from services.llm_service import call_llm, ladder_qwen_reasoning_mode
from services.prompt_service import get_template_config
from services.vocabulary_ladder.config import (
    PROMPT2_LEVELS, OPTION_KEY_MAP, DEFAULT_SENTENCE_ASSIGNMENTS,
    SENTENCE_ASSIGNMENTS_A, get_sentence_target, remap_keys,
)
from services.vocabulary_ladder.asset_generators._renderer import render_template

logger = logging.getLogger(__name__)

TASK_NAME = 'vocab_prompt2_exercises'
_PIPELINE = 'vocab_ladder'

# max_tokens cap (primary/retry AND the scoped repair call below share this
# one constant). RE-DERIVED 2026-10-03 (ADR-028 cost work) from the old flat
# 8192, using MEASURED completion_tokens. Source: data/eval/runs/
# phase2_bundle_*/ + phase2_fix_*/ + phase2_smoke_ja_v3/ + phase2_smoke_zh_r/
# *.json llm_calls for vocab_prompt2_exercises (reasoning OFF for qwen in
# these runs). Every language's own sample is individually thin (<10):
#   en n=4  p99=669  max=671
#   zh n=6  p99=759  max=763
#   ja n=1  p99=1003 max=1003
# pooled across languages (same generator/template family, just a different
# language's content) n=11, p99=979, max=1003 -- just over the n>=10
# analogous-task threshold, so used directly rather than borrowing an
# unrelated task; flagged here as thin. cap = max(ceil(p99*2),
# ceil(max*1.25)) = 1959, rounded up to 2000. At qwen3.7-plus's $1.28/M
# completion price this cuts the worst-case reservation (ja, the language
# with the single largest observed value) from ~$0.011/request to
# ~$0.003/request.
_MAX_TOKENS_RIGHTSIZED = 2000

# Pre-2026-10-03 (reasoning-safe) cap. This module runs on a qwen model (see
# TASK-813); when `LADDER_QWEN_REASONING=on` (the default) restores Phase-1
# reasoning-left-on behaviour, reasoning tokens count toward `max_tokens` and
# the right-sized cap above (derived from reasoning-OFF measurements) would
# truncate.
_MAX_TOKENS_REASONING_SAFE = 8192


def _max_tokens() -> int:
    return (_MAX_TOKENS_REASONING_SAFE if ladder_qwen_reasoning_mode() != 'off'
            else _MAX_TOKENS_RIGHTSIZED)


# language_id → llm_calls.language_code — see prompt1_core.py.
_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}


def _coerce_index(value, default: int) -> int:
    """Best-effort int coercion for an LLM-supplied sentence index.

    The response schema doesn't guarantee a JSON number here, and a string
    index silently surviving this remap is exactly what produced en's
    bundle-mode 0-exercise renders (item 6): `TypeError` several layers
    downstream, with no error/skip ever recorded for the sense.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class ExerciseAssetGenerator:
    """Generates Prompt 2 assets: phonetic, cloze, collocation gap, semantic."""

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
        used_distractors: list[str] | None = None,
    ) -> dict | None:
        """Generate exercise assets for Prompt 2 levels.

        Args:
            sense_id: The dim_word_senses ID.
            core_asset: Output from Prompt 1 (descriptive keys).
            active_levels: Which ladder levels are active for this word.
            sentence_assignments: Map of level → sentence index to use.
                Defaults to SENTENCE_ASSIGNMENTS_A for backward compat.
            used_distractors: Distractor texts already assigned elsewhere in
                this item set; passed to the LLM so it doesn't repeat them.
                Defaults to [].

        Returns:
            Descriptive-keyed dict with level_1, level_3, level_5, level_6 keys,
            or None on failure.
        """
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A
        if used_distractors is None:
            used_distractors = []

        # Filter to only P2 levels that are active
        p2_active = sorted(lv for lv in active_levels if lv in PROMPT2_LEVELS)
        if not p2_active:
            logger.warning("No Prompt 2 levels active for sense %s", sense_id)
            return {}

        prompt_text = self._build_prompt(
            core_asset, p2_active, sentence_assignments, used_distractors,
        )
        cfg = self._cfg

        raw = self._call_with_retry(
            prompt_text, cfg, p2_active, sense_id,
            core_asset, sentence_assignments, used_distractors,
        )
        if raw is None:
            return None

        return self._remap_output(raw, p2_active, sentence_assignments)

    def _call_with_retry(
        self, prompt_text: str, cfg: dict, p2_active: list[int], sense_id: int,
        core_asset: dict | None = None,
        sentence_assignments: dict[int, int] | None = None,
        used_distractors: list[str] | None = None,
    ) -> dict | None:
        """Single LLM call, retry once if any active level is missing or call fails.

        Bound: at most 3 real calls per step (primary + retry + one scoped
        repair — see below), up from TASK-810's cap of 2. The retry-cap
        regression (families that used to recover via a 3rd/4th call now fail
        outright) showed 2 was too tight specifically for the "missing a
        level or two after both attempts" case, which a full extra attempt at
        every active level wastes money solving — the repair call below asks
        ONLY for the missing levels instead.
        """
        raw: dict | None = None
        for attempt in (1, 2):
            try:
                raw = call_llm(
                    prompt_text,
                    model=cfg['model'],
                    provider=cfg['provider'],
                    temperature=0.4,
                    max_tokens=_max_tokens(),
                    response_format='json',
                    pipeline=_PIPELINE,
                    task_name=TASK_NAME,
                    template_version=cfg.get('version'),
                    language_code=_LANG_ID_TO_CODE.get(self.language_id),
                    call_role='retry' if attempt > 1 else 'primary',
                    sense_id=sense_id,
                    allow_internal_repair=False,
                )
            except Exception as e:
                logger.warning(
                    "Prompt 2 LLM call attempt %d failed for sense %s: %s",
                    attempt, sense_id, e,
                )
                if attempt == 2:
                    logger.error("Prompt 2 gave up for sense %s after 2 attempts", sense_id)
                    return None
                raw = None
                continue

            missing = [lv for lv in p2_active if str(lv) not in (raw or {})]
            if not missing:
                return raw
            if attempt == 1:
                logger.warning(
                    "Prompt 2 missing levels %s for sense %s — retrying once",
                    missing, sense_id,
                )
            else:
                logger.warning(
                    "Prompt 2 still missing levels %s for sense %s after retry "
                    "— attempting one scoped repair call", missing, sense_id,
                )

        if raw is None:
            return None
        missing = [lv for lv in p2_active if str(lv) not in raw]
        if missing and core_asset is not None:
            repaired = self._repair_missing_levels(
                core_asset, missing, sentence_assignments or {},
                used_distractors or [], sense_id, cfg,
            )
            if repaired:
                for lv in missing:
                    key = str(lv)
                    if key in repaired:
                        raw[key] = repaired[key]
        return raw

    def _repair_missing_levels(
        self, core_asset: dict, missing_levels: list[int],
        sentence_assignments: dict[int, int], used_distractors: list[str],
        sense_id: int, cfg: dict,
    ) -> dict | None:
        """ONE bounded, scoped repair call asking ONLY for `missing_levels`.

        Reuses `_build_prompt` with `active_levels` narrowed to just the
        missing set — the template already only instructs for the levels
        listed there (see the module docstring: "if L5 is skipped ... the
        prompt simply omits Level 5 entirely"), so this is a smaller, cheaper
        ask than a full retry of every active level, and it is tagged
        `call_role='repair'` so it's distinguishable in `llm_calls` from the
        primary/retry pair above.
        """
        prompt_text = self._build_prompt(
            core_asset, missing_levels, sentence_assignments, used_distractors,
        )
        try:
            raw = call_llm(
                prompt_text,
                model=cfg['model'],
                provider=cfg['provider'],
                temperature=0.4,
                max_tokens=_max_tokens(),
                response_format='json',
                pipeline=_PIPELINE,
                task_name=TASK_NAME,
                template_version=cfg.get('version'),
                language_code=_LANG_ID_TO_CODE.get(self.language_id),
                call_role='repair',
                sense_id=sense_id,
                allow_internal_repair=False,
            )
        except Exception as e:
            logger.warning(
                "Prompt 2 scoped repair call failed for sense %s (levels %s): %s",
                sense_id, missing_levels, e,
            )
            return None
        still_missing = [lv for lv in missing_levels if str(lv) not in (raw or {})]
        if still_missing:
            logger.warning(
                "Prompt 2 scoped repair still missing levels %s for sense %s",
                still_missing, sense_id,
            )
        return raw

    def _build_prompt(
        self, core_asset: dict, active_levels: list[int],
        sentence_assignments: dict[int, int],
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

        return render_template(
            template,
            word=self._extract_lemma(core_asset),
            pos=core_asset.get('pos', ''),
            semantic_class=core_asset.get('semantic_class', ''),
            complexity_tier=self._extract_tier(core_asset),
            definition=core_asset.get('definition', ''),
            primary_collocate=core_asset.get('primary_collocate') or 'null',
            register=core_asset.get('register') or 'neutral',
            sense_fingerprint=core_asset.get('sense_fingerprint') or '',
            sentences_json=sentences_json,
            active_levels_json=json.dumps([str(lv) for lv in active_levels]),
            used_distractors_json=json.dumps(used_distractors, ensure_ascii=False),
            level_3_sentence_index=sentence_assignments.get(3, 0),
            level_5_sentence_index=sentence_assignments.get(5, 2),
            level_6_sentence_index=sentence_assignments.get(6, 3),
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
                logger.warning("Prompt 2 missing level %s in output", level)
                continue

            level_data = raw[level_key]

            if level == 6:
                result[f'level_{level}'] = self._remap_level_6(
                    level_data, sentence_assignments)
            else:
                if isinstance(level_data, list):
                    result[f'level_{level}'] = self._remap_options(
                        level_data, level, sentence_assignments)
                else:
                    result[f'level_{level}'] = level_data

        return result

    def _remap_options(
        self, options: list, level: int,
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Remap a list of option objects for L1, L3, L5."""
        remapped = [remap_keys(opt, OPTION_KEY_MAP) for opt in options]

        correct = [o for o in remapped if o.get('is_correct')]

        explanations = {}
        for opt in remapped:
            text = opt.get('text', '')
            if text:
                explanations[text] = opt.get('explanation', '')

        result = {
            'options': remapped,
            'explanations': explanations,
            'sentence_index': sentence_assignments.get(level),
        }

        if correct:
            result['correct_answer'] = correct[0].get('text', '')
        if level == 5 and correct:
            result['correct_collocate'] = correct[0].get('text', '')

        return result

    def _remap_level_6(
        self, level_data: dict | list,
        sentence_assignments: dict[int, int],
    ) -> dict:
        """Remap Level 6 semantic discrimination output."""
        if isinstance(level_data, dict):
            # TASK-8xx (en bundle-mode 0-exercise renders, item 6): the model
            # is not schema-guaranteed to emit the sentence index as a JSON
            # number — a string index here survives remap/validation
            # untouched and later blows up `correct_idx < len(sentences)` in
            # `exercise_renderer._gather_bundle_judge_requests` with
            # `TypeError: '<' not supported between instances of 'str' and
            # 'int'`, observed live on en senses 13900/13902. Coerce once,
            # here, so every downstream reader gets a real int.
            correct_idx = _coerce_index(
                level_data.get('1'), sentence_assignments.get(6, 3),
            )
            wrong_sentences = level_data.get('2', [])
            if isinstance(wrong_sentences, list):
                wrong_sentences = [
                    {'text': s.get('1', ''), 'explanation': s.get('2', '')}
                    if isinstance(s, dict) else s
                    for s in wrong_sentences
                ]
            return {
                'correct_sentence_index': correct_idx,
                'wrong_sentences': wrong_sentences,
            }
        return {'correct_sentence_index': sentence_assignments.get(6, 3), 'wrong_sentences': []}

    def _extract_lemma(self, core_asset: dict) -> str:
        """Extract the word text from core asset sentences."""
        sentences = core_asset.get('sentences', [])
        if sentences:
            return get_sentence_target(sentences[0])
        return ''

    def _extract_tier(self, core_asset: dict) -> str:
        """Extract complexity tier from first sentence or default."""
        sentences = core_asset.get('sentences', [])
        if sentences:
            return sentences[0].get('complexity_tier', 'T3')
        return 'T3'
