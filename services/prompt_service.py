import logging
import os
import threading
import time
import weakref
from typing import Optional

logger = logging.getLogger(__name__)


def get_template_config(db, task_name: str, language_id: int) -> dict:
    """Fetch the active prompt template, model, and provider for a task/language.

    Single source of truth for "how do I run this LLM call for this task" —
    paired so a prompt can only ship with its intended model.

    Args:
        db: Supabase client.
        task_name: Row key in prompt_templates (e.g. 'vocab_prompt2_exercises').
        language_id: 1=Chinese, 2=English, 3=Japanese.

    Returns:
        dict with keys: template, model, provider, version.

    Raises:
        RuntimeError: if no active row exists, or if model/provider is null.
            No silent fallback — operator must populate the table.
    """
    resp = (
        db.table('prompt_templates')
        .select('template_text, model, provider, version')
        .eq('task_name', task_name)
        .eq('language_id', language_id)
        .eq('is_active', True)
        .order('version', desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise RuntimeError(
            f"No active prompt_templates row for task_name={task_name!r} "
            f"language_id={language_id}. Insert a row with model+provider populated."
        )
    row = resp.data[0]
    model = row.get('model')
    provider = row.get('provider')
    if not model:
        raise RuntimeError(
            f"prompt_templates row for {task_name!r}/lang={language_id} "
            f"v{row.get('version')} has no model configured."
        )
    if not provider:
        raise RuntimeError(
            f"prompt_templates row for {task_name!r}/lang={language_id} "
            f"v{row.get('version')} has no provider configured."
        )
    return {
        'template': row['template_text'],
        'model': model,
        'provider': provider,
        'version': row['version'],
    }


def get_template_text(db, task_name: str, language_id: int) -> str:
    """Fetch the active template_text for a task/language — prompt text only.

    Use this for prompt-text-only lookups where the model is resolved
    elsewhere (e.g. generators that share one exercise model resolved from
    ``cloze_distractor_generation``). Unlike ``get_template_config`` it does
    NOT require model/provider to be populated, so prompt-only rows
    (cloze_target_selection, semantic_discrimination_from_context,
    context_spectrum_generation, …) resolve without inventing a model.

    Critically, it filters by ``language_id`` and ``is_active`` and orders by
    ``version`` desc — fixing the language-blind selection bug where a
    Chinese prompt could be served for an English generation (and vice versa)
    because the old loader keyed on ``task_name`` + ``version`` alone.

    Raises:
        RuntimeError: if no active row exists for the task/language. No silent
            cross-language fallback — a missing per-language prompt fails loud.
    """
    resp = (
        db.table('prompt_templates')
        .select('template_text, version')
        .eq('task_name', task_name)
        .eq('language_id', language_id)
        .eq('is_active', True)
        .order('version', desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise RuntimeError(
            f"No active prompt_templates row for task_name={task_name!r} "
            f"language_id={language_id}."
        )
    return resp.data[0]['template_text']


TEMPLATE_CACHE_TTL_SECONDS = int(os.getenv('PROMPT_TEMPLATE_CACHE_TTL', '300'))
_FALLBACK_LANGUAGE_ID = 2

_template_cache: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
_template_cache_lock = threading.Lock()


def clear_template_cache() -> None:
    """Drop every cached template so the next lookup re-reads the table."""
    with _template_cache_lock:
        _template_cache.clear()


def _fetch_template_text(db, task_name: str, language_id: int) -> Optional[str]:
    resp = (
        db.table('prompt_templates')
        .select('template_text')
        .eq('task_name', task_name)
        .eq('language_id', language_id)
        .eq('is_active', True)
        .order('version', desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0]['template_text'] if resp.data else None


def load_template_text(
    db,
    task_name: str,
    language_id: int,
    *,
    required: bool = True,
    ttl: Optional[float] = None,
) -> Optional[str]:
    """Active template text for a task, with English fallback and a TTL cache.

    Looks up (task_name, language_id), then English when the language has no
    row. Hits are cached per client for ``ttl`` seconds (default
    TEMPLATE_CACHE_TTL_SECONDS; 0 disables), so a prompt edit is picked up
    without a restart. Misses are never cached.

    Raises:
        RuntimeError: required=True and no active row in either language.
    """
    ttl = TEMPLATE_CACHE_TTL_SECONDS if ttl is None else ttl
    key = (task_name, language_id)
    per_client = None
    if ttl > 0:
        try:
            with _template_cache_lock:
                per_client = _template_cache.setdefault(db, {})
                hit = per_client.get(key)
        except TypeError:  # client cannot be weak-referenced: skip caching
            per_client, hit = None, None
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]

    text = _fetch_template_text(db, task_name, language_id)
    if text is not None:
        logger.debug("Loaded prompt template: %s for language_id=%s", task_name, language_id)
    elif language_id != _FALLBACK_LANGUAGE_ID:
        text = _fetch_template_text(db, task_name, _FALLBACK_LANGUAGE_ID)
        if text is not None:
            logger.debug("Loaded fallback English prompt template: %s", task_name)

    if text is None:
        if required:
            raise RuntimeError(
                f"No active prompt_templates row for task_name={task_name!r} "
                f"language_id={language_id} (and no English fallback). "
                f"Populate the table; there is no hardcoded prompt fallback."
            )
        logger.warning("Prompt template not found: %s for language_id=%s", task_name, language_id)
        return None

    if per_client is not None:
        with _template_cache_lock:
            per_client[key] = (time.monotonic(), text)
    return text


class PromptService:
    """Service for loading and formatting prompt templates"""
    
    def __init__(self):
        self.prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        self._prompt_cache = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        Load a prompt template from file with caching
        
        Args:
            prompt_name (str): Name of prompt file (without .txt extension)
            
        Returns:
            str: Prompt template content
        """
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]
        
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_content = f.read().strip()
                self._prompt_cache[prompt_name] = prompt_content
                return prompt_content
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        except Exception as e:
            raise Exception(f"Error loading prompt {prompt_name}: {e}")
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Load and format a prompt template with variables
        
        Args:
            prompt_name (str): Name of prompt file
            **kwargs: Variables to format into the prompt
            
        Returns:
            str: Formatted prompt ready for AI
        """
        prompt_template = self.load_prompt(prompt_name)
        
        try:
            return prompt_template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing template variable {e} for prompt {prompt_name}")
    
