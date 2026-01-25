# config.py
"""
Unified application configuration - Single source of truth.
All configuration should be accessed via this module.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration class"""

    # ==========================================================================
    # CORE SETTINGS
    # ==========================================================================
    SECRET_KEY = os.environ.get('SECRET_KEY', 'temp-secret-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # ==========================================================================
    # JWT SETTINGS
    # ==========================================================================
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]

    # ==========================================================================
    # CORS - Uses environment variable with fallback
    # ==========================================================================
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            'CORS_ORIGINS',
            'http://localhost:49640,http://localhost:3000,http://localhost:5000'
        ).split(',')
        if origin.strip()
    ]

    # ==========================================================================
    # AI SERVICE CONFIGURATION
    # ==========================================================================
    USE_OPENROUTER = os.getenv('USE_OPENROUTER', 'false').lower() == 'true'
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    # Language-specific model configuration for OpenRouter
    AI_MODELS = {
        'english': {
            'transcript': 'google/gemini-2.0-flash-001',
            'questions': 'google/gemini-2.0-flash-001'
        },
        'chinese': {
            'transcript': 'deepseek/deepseek-chat',
            'questions': 'deepseek/deepseek-chat'
        },
        'japanese': {
            'transcript': 'qwen/qwen-2.5-72b-instruct',
            'questions': 'qwen/qwen-2.5-72b-instruct'
        }
    }
    DEFAULT_AI_MODEL = 'gpt-4o-mini'

    # ==========================================================================
    # DATABASE (SUPABASE)
    # ==========================================================================
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    # ==========================================================================
    # LANGUAGE CONFIGURATION - Single source of truth
    # ==========================================================================
    LANGUAGES = {
        1: {'code': 'cn', 'name': 'chinese', 'display': 'Chinese'},
        2: {'code': 'en', 'name': 'english', 'display': 'English'},
        3: {'code': 'jp', 'name': 'japanese', 'display': 'Japanese'},
    }
    VALID_LANGUAGE_IDS = set(LANGUAGES.keys())
    LANGUAGE_ID_TO_NAME = {k: v['name'] for k, v in LANGUAGES.items()}
    LANGUAGE_CODE_TO_ID = {v['code']: k for k, v in LANGUAGES.items()}

    # ==========================================================================
    # TOKEN ECONOMY - Single source of truth
    # ==========================================================================
    TOKEN_COSTS = {
        'take_test': 1,
        'generate_test': 5,
    }
    DAILY_FREE_TOKENS = int(os.environ.get('DAILY_FREE_TOKENS', '2'))

    TOKEN_PACKAGES = {
        'starter_10': {'tokens': 10, 'price_cents': 199, 'description': 'Starter pack'},
        'popular_50': {'tokens': 50, 'price_cents': 799, 'description': 'Most popular'},
        'premium_200': {'tokens': 200, 'price_cents': 1999, 'description': 'Best value'},
    }

    # ==========================================================================
    # PAYMENTS (STRIPE)
    # ==========================================================================
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')

    # ==========================================================================
    # STORAGE (CLOUDFLARE R2)
    # ==========================================================================
    R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'linguadojoaudio')
    R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else None
    R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', 'https://audio.linguadojo.com')

    # ==========================================================================
    # LEGACY AWS (kept for backwards compatibility)
    # ==========================================================================
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    @staticmethod
    def get_audio_url(slug: str) -> str:
        """Construct audio URL from slug"""
        return f"{Config.R2_PUBLIC_URL}/{slug}.mp3"

    @staticmethod
    def get_model_for_language(language: str, task: str = 'transcript') -> str:
        """Get optimal model for language and task"""
        if not Config.USE_OPENROUTER:
            return Config.DEFAULT_AI_MODEL
        lang_config = Config.AI_MODELS.get(language.lower(), Config.AI_MODELS['english'])
        return lang_config.get(task, Config.DEFAULT_AI_MODEL)

    @staticmethod
    def get_language_name(language_id: int) -> str:
        """Get language name from ID"""
        return Config.LANGUAGE_ID_TO_NAME.get(language_id, 'unknown')

    @staticmethod
    def get_language_id(code: str) -> int:
        """Get language ID from code"""
        return Config.LANGUAGE_CODE_TO_ID.get(code.lower(), 1)
