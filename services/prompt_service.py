import logging
import os
from typing import Dict, Any

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
    
    def get_available_prompts(self) -> list:
        """Get list of available prompt files"""
        try:
            return [
                f[:-4] for f in os.listdir(self.prompts_dir) 
                if f.endswith('.txt')
            ]
        except OSError as e:
            logging.getLogger(__name__).warning(f"Cannot list prompts: {e}")
            return []
