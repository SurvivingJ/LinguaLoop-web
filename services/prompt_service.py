import os
from typing import Dict, Any

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
        except Exception:
            return []
