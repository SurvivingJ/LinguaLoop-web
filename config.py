import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'temp-secret-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]

    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')

    TOKEN_COSTS = {
        'take_test': 1,
        'generate_test': 5
    }
    DAILY_FREE_TOKENS = 200

    CORS_ORIGINS = [
        "http://localhost:49640"
    ]

    R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'lingualoopaudio')
    R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else None
    R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL')

    @staticmethod
    def get_audio_url(slug):
        """Construct audio URL from slug"""
        return f"{Config.R2_PUBLIC_URL}/{slug}.mp3"