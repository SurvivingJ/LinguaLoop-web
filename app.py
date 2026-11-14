"""
Flask Backend for LinguaDojo Language Learning Platform
Clean, production-ready implementation with proper error handling
"""

from flask import Flask, request, jsonify, make_response, g
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
import stripe
from services.supabase_factory import (
    SupabaseFactory, SupabaseConfigError, get_supabase, get_supabase_admin,
)
import logging
import os

# Internal imports
from config import Config
from services.service_factory import ServiceFactory
from services.r2_service import R2Service
from services.auth_service import AuthService
from services.device_service import DeviceService
from middleware.auth import jwt_required as supabase_jwt_required
from services.dimension_service import DimensionService
from utils.responses import api_errors, api_success, bad_request, service_unavailable
from utils.validation import json_body
from models.requests import VocabularyExtractRequest, ErrorLogRequest
from pydantic import ValidationError
from web.errors import register_error_handlers
from web.pages import register_pages
from web.rate_limits import init_rate_limits
from web.scheduler import init_scheduler
from web.security import init_request_size_limit, init_security_headers

# Import blueprints
from routes.auth import auth_bp
from routes.tests import tests_bp
from routes.reports import reports_bp
from routes.vocabulary import vocabulary_bp
from routes.flashcards import flashcards_bp
from routes.corpus import corpus_bp
from routes.users import users_bp
from routes.payments import payments_bp
from routes.vocab_dojo import vocab_dojo_bp
from routes.vocab_admin import vocab_admin_bp
from routes.calibration import calibration_bp
from routes.common import get_db
from routes.drills import classifier_drill_bp, counter_drill_bp
from routes.practice import practice_bp
from routes.study_plan import study_plan_bp
from routes.study_session import study_session_bp
from routes.dual_translation import dual_translation_bp
from routes.test_intros import test_intros_bp
from routes.word_list_import import word_list_import_bp


def create_app(config_class=Config):
    """Create and configure Flask application"""
    config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust X-Forwarded-* from the immediate proxy hop so request.is_secure
    # and request.remote_addr reflect the real client. Required for the
    # trusted-device cookie's Secure flag to be set correctly when Flask
    # runs behind a reverse proxy (Cloud Run, fly.io, Heroku, nginx, ...).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Disable strict slashes to prevent 308 redirects from /api/tests to /api/tests/
    app.url_map.strict_slashes = False

    # Set secret key for sessions (validate() guarantees this is set).
    app.secret_key = config_class.SECRET_KEY
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if not config_class.DEBUG else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    _setup_cors(app)
    init_security_headers(app)
    init_request_size_limit(app)

    # Compression + content-hashed, long-cached static URLs (latency 2026-11)
    from services.static_assets import init_static_assets
    init_static_assets(app)

    _initialize_services(app, config_class)
    # Test apps never run background jobs.
    if not app.config.get('TESTING'):
        _initialize_scheduler(app)

    _register_blueprints(app)
    register_error_handlers(app)
    _register_core_routes(app)
    register_pages(app)

    # After every route exists: limits are attached by endpoint name.
    init_rate_limits(app)

    app.logger.info("LinguaDojo application initialized successfully")
    return app


def _setup_cors(app):
    """Configure CORS with proper settings"""
    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "supports_credentials": True,
            "max_age": 86400
        }
    })
    
    @app.before_request
    def handle_preflight():
        """Handle CORS preflight requests"""
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin', '')
            response = make_response()
            
            if origin in Config.CORS_ORIGINS or "*" in Config.CORS_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = origin
            elif Config.CORS_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = Config.CORS_ORIGINS[0]
            
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, Accept'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response


def _initialize_services(app, config_class=Config):
    """Initialize all external services with error handling"""

    # Supabase initialization via centralized factory
    try:
        if Config.SUPABASE_URL and Config.SUPABASE_KEY:
            SupabaseFactory.initialize(
                supabase_url=Config.SUPABASE_URL,
                supabase_key=Config.SUPABASE_KEY,
                service_role_key=Config.SUPABASE_SERVICE_ROLE_KEY,
                postgrest_timeout=Config.SUPABASE_POSTGREST_TIMEOUT,
                # Test configurations run on mocked clients.
                require_service_role=not getattr(config_class, 'TESTING', False),
            )
            app.supabase = get_supabase()
            app.supabase_service = get_supabase_admin()
            app.auth_service = AuthService(app.supabase)
            app.device_service = DeviceService(supabase_admin=app.supabase_service)
            app.logger.info("Supabase clients initialized via SupabaseFactory")

            # Initialize dimension table cache for fast lookups (use service client to bypass RLS)
            from services.test_service import get_test_service
            from services.practice_session_service import get_practice_session_service
            DimensionService.initialize(app.supabase_service)
            # Build the singletons now, before worker threads can race to.
            get_test_service()
            get_practice_session_service()
            app.logger.info("DimensionService cache, TestService, and PracticeSessionService initialized")
        else:
            raise ValueError("Missing Supabase credentials")
    except SupabaseConfigError:
        raise
    except Exception as e:
        app.logger.error(f"Supabase initialization failed: {e}")
        app.supabase = None
        app.supabase_service = None
        app.auth_service = None
        app.device_service = None

    try:
        service_factory = ServiceFactory(Config)
        app.openai_service = service_factory.openai_service if Config.OPENAI_API_KEY else None
        app.logger.info(f"OpenAI service: {'enabled' if app.openai_service else 'disabled'}")
    except Exception as e:
        app.logger.error(f"Service factory error: {e}")
        app.openai_service = None

    try:
        app.r2_service = R2Service(Config) if Config.R2_ACCESS_KEY_ID else None
        app.logger.info(f"R2 service: {'enabled' if app.r2_service else 'disabled'}")
    except Exception as e:
        app.logger.error(f"R2 service error: {e}")
        app.r2_service = None

    try:
        if Config.STRIPE_SECRET_KEY:
            stripe.api_key = Config.STRIPE_SECRET_KEY
            app.logger.info("Stripe configured")
        else:
            app.logger.warning("Stripe not configured")
    except Exception as e:
        app.logger.error(f"Stripe initialization error: {e}")

    # Vocabulary extraction pipeline
    try:
        if app.openai_service and app.supabase_service:
            from services.vocabulary import VocabularyExtractionPipeline
            from services.test_generation.database_client import TestDatabaseClient

            vocab_db = TestDatabaseClient()
            app.vocab_pipeline = VocabularyExtractionPipeline(
                openai_client=app.openai_service.client,
                db_client=vocab_db,
            )
            app.logger.info("Vocabulary extraction pipeline initialized")
        else:
            app.vocab_pipeline = None
            app.logger.warning("Vocabulary pipeline disabled (missing OpenAI or Supabase)")
    except Exception as e:
        app.logger.error(f"Vocabulary pipeline error: {e}")
        app.vocab_pipeline = None


def _initialize_scheduler(app):
    """Start the background scheduler (jobs are declared in web/scheduler.py)."""
    init_scheduler(app)


def _register_blueprints(app):
    """Register all application blueprints"""
    auth_bp.auth_service = app.auth_service
    auth_bp.device_service = app.device_service

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tests_bp, url_prefix='/api/tests')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(vocabulary_bp, url_prefix='/api/vocabulary')
    app.register_blueprint(flashcards_bp, url_prefix='/api/flashcards')
    app.register_blueprint(corpus_bp, url_prefix='/api/corpus')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(vocab_dojo_bp, url_prefix='/api/vocab-dojo')
    app.register_blueprint(vocab_admin_bp, url_prefix='/api/admin/vocab')
    app.register_blueprint(calibration_bp, url_prefix='/api/calibration')
    app.register_blueprint(classifier_drill_bp, url_prefix='/api/classifier-drill')
    app.register_blueprint(counter_drill_bp, url_prefix='/api/counter-drill')
    # Phase 12/13: unified Practice surface + Study Plan orchestration.
    app.register_blueprint(practice_bp, url_prefix='/api/practice')
    app.register_blueprint(study_plan_bp, url_prefix='/api/study-plan')
    app.register_blueprint(study_session_bp, url_prefix='/api/study-session')
    app.register_blueprint(dual_translation_bp, url_prefix='/api/dual-translation')
    app.register_blueprint(test_intros_bp)
    app.register_blueprint(word_list_import_bp)

    app.logger.info("Blueprints registered")


def _register_core_routes(app):
    """Register core application API routes"""

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.2.0",
            "services": {
                "openai": app.openai_service is not None,
                "supabase": app.supabase is not None,
                "auth": app.auth_service is not None,
                "r2": app.r2_service is not None,
                "stripe": Config.STRIPE_SECRET_KEY is not None,
                "vocabulary": app.vocab_pipeline is not None
            }
        })
    
    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Get public configuration"""
        return jsonify({
            "features": {
                "ai_generation": app.openai_service is not None,
                "database": app.supabase is not None,
                "payments": Config.STRIPE_SECRET_KEY is not None,
                "audio_generation": app.openai_service is not None
            },
            "token_costs": Config.TOKEN_COSTS if hasattr(Config, 'TOKEN_COSTS') else {},
            "daily_free_tokens": Config.DAILY_FREE_TOKENS if hasattr(Config, 'DAILY_FREE_TOKENS') else 0
        })

    @app.context_processor
    def _inline_metadata():
        """/api/metadata, embedded in every page (latency 2026-11).

        Pages awaited this fetch before their first real API call. It is served
        from DimensionService's in-memory cache, so embedding it costs no
        database work. None (client fetches as before) unless both lists are
        cached.
        """
        langs = DimensionService.get_all_languages()
        types = DimensionService._test_types_metadata
        if isinstance(langs, list) and langs and isinstance(types, list) and types:
            return {'lingua_metadata': {'languages': langs, 'test_types': types, 'status': 'success'}}
        return {'lingua_metadata': None}

    @app.route('/api/metadata', methods=['GET'])
    def get_metadata():
        """Return available languages and test types from cached dimension tables"""
        return jsonify({
            'languages': DimensionService.get_all_languages(),
            'test_types': DimensionService.get_all_test_types(),
            'status': 'success'
        })

    @app.route('/api/vocabulary/extract', methods=['POST'])
    @supabase_jwt_required
    @api_errors("Vocabulary extraction failed")
    def extract_vocabulary():
        """Extract vocabulary (lemmas + phrases) from text"""
        try:
            body = VocabularyExtractRequest.model_validate(json_body())
        except ValidationError as e:
            return bad_request(e.errors()[0]['msg'])

        if not app.vocab_pipeline:
            return service_unavailable("Vocabulary service unavailable")

        try:
            vocab = app.vocab_pipeline.extract(body.text, body.language_code)
            return api_success({"vocabulary": vocab})
        except ValueError as e:
            return bad_request(str(e))

    @app.route('/api/errors/log', methods=['POST'])
    @supabase_jwt_required
    @api_errors("Failed to log error")
    def log_error():
        """Log an application error to the app_error_logs table"""
        try:
            body = ErrorLogRequest.model_validate(json_body())
        except ValidationError as e:
            return bad_request(e.errors()[0]['msg'])

        get_db().table('app_error_logs').insert({
            'error_type': body.error_type[:100],
            'error_message': body.error_message[:Config.MAX_INPUT_LENGTH],
            'url': (body.url or '')[:Config.MAX_INPUT_LENGTH],
            'user_id': g.current_user_id,
            'metadata': body.metadata,
        }).execute()
        return api_success(status_code=201)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    create_app().run(host='0.0.0.0', port=port, debug=Config.DEBUG)
