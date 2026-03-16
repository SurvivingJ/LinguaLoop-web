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
    # ELO & GAME CONSTANTS
    # ==========================================================================
    DEFAULT_ELO_RATING = 1400
    DEFAULT_VOLATILITY = 100
    MAX_DAILY_TESTS = 3
    POOR_PERFORMANCE_THRESHOLD = 70  # percentage
    DAILY_TEST_COOLDOWN_SECONDS = 86400
    SUPABASE_BATCH_CHUNK_SIZE = 500
    MAX_INPUT_LENGTH = 2000

    # ==========================================================================
    # TOKEN ECONOMY - Single source of truth
    # ==========================================================================
    TOKEN_COSTS = {
        'take_test': 1,
        'generate_test': 5,
    }
    DAILY_FREE_TOKENS = int(os.environ.get('DAILY_FREE_TOKENS', '2'))

    TOKEN_PACKAGES = {
        'starter_10': {
            'tokens': 10, 'price_cents': 199, 'price_dollars': 1.99,
            'description': 'Starter pack - try the platform',
        },
        'popular_50': {
            'tokens': 50, 'price_cents': 799, 'price_dollars': 7.99,
            'description': 'Most popular - great value',
        },
        'premium_200': {
            'tokens': 200, 'price_cents': 1999, 'price_dollars': 19.99,
            'description': 'Premium pack - best value',
        },
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
        """Construct the full public audio URL for a test.

        Args:
            slug: The test slug used as the audio filename (without extension).

        Returns:
            Full URL to the .mp3 file on the R2 CDN.
        """
        return f"{Config.R2_PUBLIC_URL}/{slug}.mp3"

    @staticmethod
    def get_model_for_language(language: str, task: str = 'transcript') -> str:
        """Select the AI model to use for a given language and task.

        When OpenRouter is disabled, returns the default OpenAI model.
        Otherwise looks up the language-specific model from AI_MODELS.

        Args:
            language: Language name (e.g. 'chinese', 'english', 'japanese').
            task: The generation task — 'transcript' or 'questions'.

        Returns:
            Model identifier string suitable for the chat completions API.
        """
        if not Config.USE_OPENROUTER:
            return Config.DEFAULT_AI_MODEL
        lang_config = Config.AI_MODELS.get(language.lower(), Config.AI_MODELS['english'])
        return lang_config.get(task, Config.DEFAULT_AI_MODEL)

    @staticmethod
    def get_language_name(language_id: int) -> str:
        """Map a numeric language ID to its canonical name.

        Args:
            language_id: Integer key from the LANGUAGES dict (1=CN, 2=EN, 3=JP).

        Returns:
            Lowercase language name, or 'unknown' if the ID is not recognised.
        """
        return Config.LANGUAGE_ID_TO_NAME.get(language_id, 'unknown')

    @staticmethod
    def get_language_id(code: str) -> int:
        """Map a two-letter language code to its numeric ID.

        Args:
            code: Two-letter code (e.g. 'cn', 'en', 'jp'). Case-insensitive.

        Returns:
            Integer language ID, defaulting to 1 (Chinese) if code is not found.
        """
        return Config.LANGUAGE_CODE_TO_ID.get(code.lower(), 1)
