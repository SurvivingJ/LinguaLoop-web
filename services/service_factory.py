from .openai_service import OpenAIService
from .prompt_service import PromptService
from ..config import Config
from .r2_service import R2Service

class ServiceFactory:
    def __init__(self, config):
        self.config = config
        self._openai_service = None
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
        if self._openai_service is None:
            if self.config.OPENAI_API_KEY:
                from openai import OpenAI
                openai_client = OpenAI(api_key=self.config.OPENAI_API_KEY)
                self._openai_service = OpenAIService(openai_client, self.config)
        return self._openai_service