from services.ai_service import AIService
from services.prompt_service import PromptService
from config import Config
from services.r2_service import R2Service

class ServiceFactory:
    def __init__(self, config):
        self.config = config
        self._ai_service = None
        self._prompt_service = None
        self._r2_service = None
    
    @property
    def r2_service(self):
        """Lazy-load R2 service"""
        if self._r2_service is None and self.config.R2_ACCESS_KEY_ID:
            self._r2_service = R2Service(self.config)
        return self._r2_service
    
    @property
    def prompt_service(self):
        """Lazy initialization of PromptService"""
        if self._prompt_service is None:
            self._prompt_service = PromptService()
        return self._prompt_service
    
    @property
    def openai_service(self):
        """Initialize AI service with OpenRouter support"""
        if self._ai_service is None:
            use_openrouter = getattr(self.config, 'USE_OPENROUTER', False)

            if use_openrouter and getattr(self.config, 'OPENROUTER_API_KEY', None):
                # Use OpenRouter with language-specific models
                from openai import OpenAI
                openai_client = OpenAI(
                    api_key=self.config.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                self._ai_service = AIService(
                    openai_client,
                    self.config,
                    self.prompt_service,
                    use_openrouter=True
                )
            elif self.config.OPENAI_API_KEY:
                # Use OpenAI with default models
                from openai import OpenAI
                openai_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
                self._ai_service = AIService(
                    openai_client,
                    self.config,
                    self.prompt_service,
                    use_openrouter=False
                )
        return self._ai_service