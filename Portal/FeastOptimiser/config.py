import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # Data storage
    DATA_STORE_DIR = os.environ.get('DATA_STORE_DIR', os.path.join(os.path.dirname(__file__), 'data', 'store'))

    # OpenRouter (for all LLM calls)
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
    OPENROUTER_DEFAULT_MODEL = 'openai/gpt-4o-mini'

    # USDA FoodData Central
    USDA_API_KEY = os.environ.get('USDA_API_KEY', '')

    # YouTube Data API v3
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

    # Email notifications
    NOTIFICATION_EMAIL = os.environ.get('NOTIFICATION_EMAIL', '')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
    USER_EMAIL = os.environ.get('USER_EMAIL', '')

    # Scraping
    SCRAPE_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    # Business logic constants
    MAX_VISION_SCREENSHOTS_PER_WEEK = 8
    POINTS_TO_DOLLAR_RATE = 0.005  # 2000 points = $10
    MAX_SRS_INTERVAL_DAYS = 60
