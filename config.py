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
    # No default — Config.validate() refuses to start with these unset.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # ==========================================================================
    # TRUSTED DEVICE / "REMEMBER THIS DEVICE"
    # ==========================================================================
    # Long-lived rolling session credential issued when the user checks the
    # "Remember this device" box on login. Stored as a hashed token in the
    # trusted_devices table and as an HttpOnly cookie on the device.
    REMEMBER_DEVICE_DURATION = timedelta(days=180)
    DEVICE_COOKIE_NAME = "lingualoop_device"
    DEVICE_COOKIE_PATH = "/api/auth"

    # ==========================================================================
    # REFRESH TOKEN COOKIE
    # ==========================================================================
    # The Supabase refresh token is stored in an HttpOnly/Secure/SameSite=Lax
    # cookie (invisible to JS) instead of localStorage, so an XSS payload can't
    # read it and mint long-lived sessions. Only the short-lived access token
    # (jwt_token) stays in JS-readable storage. Scoped to /api/auth so it's only
    # sent to the auth endpoints that rotate it.
    REFRESH_COOKIE_NAME = "lingualoop_refresh"
    REFRESH_COOKIE_PATH = "/api/auth"
    REFRESH_COOKIE_DURATION = timedelta(days=30)
    # Salt for sha256(ip + salt) audit hashing — *not* a security boundary,
    # just keeps raw IPs out of the DB. Falls back to SECRET_KEY if unset.
    DEVICE_IP_HASH_SALT = os.environ.get('DEVICE_IP_HASH_SALT', '')

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
    # Language codes are ISO 639-1 (zh, en, ja). Single source of truth.
    LANGUAGES = {
        1: {'code': 'zh', 'name': 'chinese', 'display': 'Chinese'},
        2: {'code': 'en', 'name': 'english', 'display': 'English'},
        3: {'code': 'ja', 'name': 'japanese', 'display': 'Japanese'},
    }
    VALID_LANGUAGE_IDS = set(LANGUAGES.keys())
    LANGUAGE_ID_TO_NAME = {k: v['name'] for k, v in LANGUAGES.items()}
    LANGUAGE_CODE_TO_ID = {v['code']: k for k, v in LANGUAGES.items()}

    # ==========================================================================
    # FEATURE FLAGS
    # ==========================================================================
    # Listening Lab — speed-graded listening comprehension. Two-level gating:
    # this env flag controls whether the API blueprint and web routes are
    # registered at all (off = full 404), and each listening_lab_passages row
    # has its own is_active boolean so an admin can roll passages out
    # individually after QA.
    LISTENING_LAB_ENABLED = os.environ.get('LISTENING_LAB_ENABLED', 'False').lower() == 'true'

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
    # VOCABULARY LADDER PIPELINE
    # ==========================================================================
    # Model selection lives in Supabase (prompt_templates.model + .provider),
    # paired per (task_name, language_id). Use services.prompt_service.
    # get_template_config() to fetch. No code-level default — missing rows
    # fail loudly so misconfiguration surfaces immediately.
    VOCAB_DOJO_SESSION_SIZE = int(os.getenv('VOCAB_DOJO_SESSION_SIZE', '20'))
    VOCAB_SENTENCES_PER_WORD = 10

    # ==========================================================================
    # EXERCISE SCHEDULING
    # ==========================================================================
    DEFAULT_EXERCISE_SESSION_SIZE = 20
    MIN_EXERCISE_SESSION_SIZE = 5
    MAX_EXERCISE_SESSION_SIZE = 50
    EXERCISE_COOLDOWN_DAYS = 7              # Don't re-serve same exercise_id within N days
    EXERCISE_SLOT_DISTRIBUTION = {
        'due_review': 0.40,
        'active_learning': 0.40,
        'new_words': 0.20,
    }

    # ==========================================================================
    # STUDY PLANS — Phase 13 orchestrator
    # ==========================================================================
    # Global kill switch. When False, get_or_create_daily_load falls through
    # to legacy _compute_daily_load and the orchestrator never fires. Rollback
    # is "set to False and redeploy". See ADR-013.
    # Flipped to True (default) on 2026-05-22 after pre-launch wipe per R4.2.
    # Set STUDY_PLAN_ENABLED=false in the env to roll back without a deploy.
    STUDY_PLAN_ENABLED = os.getenv('STUDY_PLAN_ENABLED', 'True').lower() == 'true'

    # Default daily-minutes assigned at onboarding / backfill.
    STUDY_PLAN_DEFAULT_DAILY_MINUTES = 30

    # Tier C objective coefficients. value(s) is in [0,1]; α applies
    # per-minute, so 30 min of practice contributes up to 0.6 units —
    # comparable to a high-value test slot. γ keeps the spacing penalty as
    # a tiebreaker, not a dictator.
    STUDY_PLAN_TIER_C_ALPHA_M = 0.02   # maintenance per-minute value
    STUDY_PLAN_TIER_C_ALPHA_A = 0.02   # acquisition per-minute value
    STUDY_PLAN_TIER_C_GAMMA   = 0.15   # spacing-penalty weight

    # Seed minutes per test type, used by services.test_time_estimate when
    # dim_test_types.expected_minutes_p50 has not yet accrued ≥30 samples.
    # Mirrors the per-type seed in the SQL helper of the same name in
    # phase13_build_daily_session.sql so the two never drift.
    TEST_TYPE_MINUTES = {
        'reading':       6,
        'listening':     5,
        'dictation':     6,
        'pinyin':        4,
        'classifier_drill': 4,
        'pitch_accent':  4,
    }

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
            language_id: Integer key from the LANGUAGES dict (1=ZH, 2=EN, 3=JA).

        Returns:
            Lowercase language name, or 'unknown' if the ID is not recognised.
        """
        return Config.LANGUAGE_ID_TO_NAME.get(language_id, 'unknown')

    @staticmethod
    def get_language_id(code: str) -> int:
        """Map a two-letter language code to its numeric ID.

        Args:
            code: ISO 639-1 two-letter code (e.g. 'zh', 'en', 'ja'). Case-insensitive.

        Returns:
            Integer language ID, defaulting to 1 (Chinese) if code is not found.
        """
        return Config.LANGUAGE_CODE_TO_ID.get(code.lower(), 1)

    @classmethod
    def validate(cls) -> None:
        """Refuse to start the app if any required secret is missing.

        Called once from create_app() before Supabase clients are initialized,
        so a missing env var fails with a clear message instead of silently
        falling back to an insecure default.
        """
        required = {
            'SECRET_KEY': cls.SECRET_KEY,
            'SUPABASE_URL': cls.SUPABASE_URL,
            'SUPABASE_KEY': cls.SUPABASE_KEY,
            'SUPABASE_SERVICE_ROLE_KEY': cls.SUPABASE_SERVICE_ROLE_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: "
                + ", ".join(missing)
                + ". Set them in .env or the deployment environment."
            )
