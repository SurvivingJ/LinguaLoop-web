"""Shared engine for the offline measure-word curation pipelines.

services.classifier_curation (Mandarin 量词) and services.counter_curation
(Japanese 助数詞) are the same generate -> judge authoring flow with different
wording. Everything that does not depend on the language lives here; each
package keeps its prompts, its noun/meta schemas and its public names.
"""

from __future__ import annotations

import logging
import os
from types import SimpleNamespace

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_MODEL = 'qwen/qwen3.7-plus'


def curation_settings(name: str, *, target_nouns: int) -> SimpleNamespace:
    """Env-overridable settings for one pipeline (``name`` = classifier | counter)."""
    env = name.upper()
    gen_model = os.getenv(f'{env}_GEN_MODEL', _DEFAULT_MODEL)
    output_dir = os.path.join(_ROOT, 'data', f'{name}_curation')
    return SimpleNamespace(
        GEN_MODEL=gen_model,
        JUDGE_MODEL=os.getenv(f'{env}_JUDGE_MODEL', gen_model),
        PIPELINE=f'{name}_curation',
        TARGET_NOUNS=int(os.getenv(f'{env}_TARGET_NOUNS', str(target_nouns))),
        JUDGE_ACCEPT_THRESHOLD=int(os.getenv(f'{env}_JUDGE_THRESHOLD', '4')),
        OUTPUT_DIR=output_dir,
        APPROVED_FILE=os.path.join(output_dir, 'approved_curation.json'),
    )


def group_validator(groups: list[str]):
    """Pydantic validator pinning a ``group`` field to a fixed vocabulary."""
    def _group_known(cls, v: str) -> str:
        if v not in groups:
            raise ValueError(f"group {v!r} not in {groups}")
        return v
    return field_validator('group')(classmethod(_group_known))


class JudgeRatings(BaseModel):
    """Per-noun idiomatic-validity ratings, in the same order as the input."""

    ratings: list[int] = Field(default_factory=list, description="Likert 1-5 per noun")
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def _align_reasons(self) -> 'JudgeRatings':
        if len(self.reasons) < len(self.ratings):
            self.reasons = self.reasons + [''] * (len(self.ratings) - len(self.reasons))
        return self


def structured_call(llm, prompt: str, *, model: str, temperature: float,
                    schema: type[BaseModel], system_prompt: str,
                    pipeline: str, task_name: str):
    """One schema-validated JSON call through the caller's ``call_llm``."""
    return llm(
        prompt,
        model=model,
        temperature=temperature,
        response_format='json_object',
        schema=schema,
        provider='openrouter',
        system_prompt=system_prompt,
        pipeline=pipeline,
        task_name=task_name,
    )


def judge_nouns(llm, item: str, nouns: list[str], semantic_label: str, *,
                prompt_template: str, system_prompt: str,
                model: str, pipeline: str) -> list[int]:
    """Likert 1-5 per noun, in input order; all-5 on any failure (fail-open).

    ``prompt_template`` is formatted with ``item``, ``label`` and ``numbered``.
    """
    if not nouns:
        return []

    prompt = prompt_template.format(
        item=item,
        label=f" ({semantic_label})" if semantic_label else "",
        numbered='\n'.join(f"{i + 1}. {n}" for i, n in enumerate(nouns)),
    )
    try:
        out: JudgeRatings = structured_call(
            llm, prompt, model=model, temperature=0.0, schema=JudgeRatings,
            system_prompt=system_prompt, pipeline=pipeline, task_name='judge_nouns',
        )
    except Exception as exc:
        logger.warning("judge_nouns failed for %s, fail-open: %s", item, exc)
        return [5] * len(nouns)

    ratings = out.ratings
    if len(ratings) != len(nouns):
        logger.warning(
            "judge_nouns length mismatch for %s (%d ratings vs %d nouns), fail-open",
            item, len(ratings), len(nouns),
        )
        return [5] * len(nouns)

    return [max(1, min(5, int(r))) for r in ratings]
