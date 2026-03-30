"""
Flask Backend for LinguaDojo Language Learning Platform
Clean, production-ready implementation with proper error handling
"""

from flask import Flask, request, jsonify, make_response, render_template, redirect, url_for, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime, timezone
import stripe
from services.supabase_factory import SupabaseFactory, get_supabase, get_supabase_admin
import logging
import traceback
import os

# Internal imports
from config import Config
from services.service_factory import ServiceFactory
from services.r2_service import R2Service
from services.prompt_service import PromptService
from services.auth_service import AuthService
from middleware.auth import AuthMiddleware, jwt_required as supabase_jwt_required
from services.dimension_service import DimensionService
from utils.responses import api_success, bad_request, server_error, service_unavailable
from models.requests import VocabularyExtractRequest, ErrorLogRequest
from pydantic import ValidationError

# Import blueprints
from routes.auth import auth_bp
from routes.tests import tests_bp
from routes.reports import reports_bp
from routes.vocabulary import vocabulary_bp
from routes.flashcards import flashcards_bp
from routes.exercises import exercises_bp
from routes.corpus import corpus_bp
from routes.users import users_bp
from routes.payments import payments_bp
from routes.mystery import mystery_bp
from routes.conversations import conversations_bp


def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Disable strict slashes to prevent 308 redirects from /api/tests to /api/tests/
    app.url_map.strict_slashes = False
    
    # Set secret key for sessions
    app.secret_key = config_class.SECRET_KEY if hasattr(config_class, 'SECRET_KEY') else os.urandom(24)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if not config_class.DEBUG else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize JWT
    JWTManager(app)
    
    # Setup CORS
    _setup_cors(app)
    
    # Initialize all services
    _initialize_services(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Register core routes (API + Web pages)
    _register_core_routes(app)
    _register_web_routes(app)
    
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


def _initialize_services(app):
    """Initialize all external services with error handling"""

    # Supabase initialization via centralized factory
    try:
        if Config.SUPABASE_URL and Config.SUPABASE_KEY:
            SupabaseFactory.initialize(
                supabase_url=Config.SUPABASE_URL,
                supabase_key=Config.SUPABASE_KEY,
                service_role_key=Config.SUPABASE_SERVICE_ROLE_KEY
            )
            app.supabase = get_supabase()
            app.supabase_service = get_supabase_admin()
            app.auth_service = AuthService(app.supabase)
            app.logger.info("Supabase clients initialized via SupabaseFactory")

            # Initialize dimension table cache for fast lookups (use service client to bypass RLS)
            from services.test_service import get_test_service
            from services.exercise_session_service import get_exercise_session_service
            DimensionService.initialize(app.supabase_service)
            app.test_service = get_test_service()  # Singleton for reuse
            app.exercise_session_service = get_exercise_session_service()
            app.logger.info("DimensionService cache, TestService, and ExerciseSessionService initialized")
        else:
            raise ValueError("Missing Supabase credentials")
    except Exception as e:
        app.logger.error(f"Supabase initialization failed: {e}")
        app.supabase = None
        app.supabase_service = None
        app.auth_service = None

    try:
        service_factory = ServiceFactory(Config)
        app.service_factory = service_factory
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

    try:
        app.prompt_service = PromptService()
        app.logger.info("Prompt service initialized")
    except Exception as e:
        app.logger.error(f"Prompt service error: {e}")
        app.prompt_service = None

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


def _register_blueprints(app):
    """Register all application blueprints"""
    auth_middleware = AuthMiddleware(app.supabase)
    auth_bp.auth_service = app.auth_service
    auth_bp.auth_middleware = auth_middleware

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tests_bp, url_prefix='/api/tests')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(vocabulary_bp, url_prefix='/api/vocabulary')
    app.register_blueprint(flashcards_bp, url_prefix='/api/flashcards')
    app.register_blueprint(exercises_bp, url_prefix='/api/exercises')
    app.register_blueprint(corpus_bp, url_prefix='/api/corpus')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(mystery_bp, url_prefix='/api/mystery')
    app.register_blueprint(conversations_bp, url_prefix='/api/conversations')

    app.logger.info("Blueprints registered")


def _register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        # Check if it's an API request
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Endpoint not found",
                "status": "not_found"
            }), 404
        # Otherwise, redirect to login or show 404 page
        return redirect(url_for('login'))
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": "Method not allowed",
            "status": "method_not_allowed"
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        app.logger.error(traceback.format_exc())
        
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Internal server error",
                "status": "internal_error"
            }), 500
        return render_template('error.html', error="Internal server error"), 500


def _register_web_routes(app):
    """Register web page routes (HTML rendering)"""
    
    @app.route('/')
    def index():
        """Root route - redirect to login page"""
        return redirect(url_for('login'))
    
    @app.route('/login')
    def login():
        """Render login page"""
        return render_template('login.html')
    
    @app.route('/signup')
    def signup():
        """Render signup page (uses same login.html template)"""
        return render_template('login.html')
    
    @app.route('/welcome')
    def welcome():
        """Render onboarding page for new users"""
        return render_template('onboarding.html')

    @app.route('/language-selection')
    def language_selection():
        """Render language selection page"""
        return render_template('language_selection.html')
    
    @app.route('/tests')
    def tests():
        """Render test list page"""
        return render_template('test_list.html')

    @app.route('/profile')
    def profile():
        """Render user profile page"""
        return render_template('profile.html')

    @app.route('/test/<slug>/preview')
    def test_preview(slug):
        """Render test preview page (client-side rendered)"""
        return render_template('test_preview.html')

    @app.route('/test/<slug>')
    def test_page(slug):
        """Render test taking page (client-side rendered)"""
        return render_template('test.html')

    @app.route('/flashcards')
    def flashcards():
        """Render flashcards review page"""
        return render_template('flashcards.html')

    @app.route('/exercises')
    def exercises():
        """Render exercises practice page"""
        return render_template('exercises.html')

    @app.route('/mysteries')
    def mysteries():
        """Render mystery list page"""
        return render_template('mystery_list.html')

    @app.route('/mystery/<slug>')
    def mystery_page(slug):
        """Render mystery playing page"""
        return render_template('mystery.html')

    @app.route('/conversations')
    def conversations():
        """Render conversation list page"""
        return render_template('conversation_list.html')

    @app.route('/conversation/<conversation_id>')
    def conversation_reader(conversation_id):
        """Render conversation reader page"""
        return render_template('conversation_reader.html')

    @app.route('/logout')
    def logout():
        """Handle logout - redirect to login page"""
        return redirect(url_for('login'))


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
    def extract_vocabulary():
        """Extract vocabulary (lemmas + phrases) from text"""
        if not app.vocab_pipeline:
            return service_unavailable("Vocabulary service unavailable")

        try:
            body = VocabularyExtractRequest.model_validate(request.get_json() or {})
        except ValidationError as e:
            return bad_request(e.errors()[0]['msg'])

        try:
            vocab = app.vocab_pipeline.extract(body.text, body.language_code)
            return api_success({"vocabulary": vocab})
        except ValueError as e:
            return bad_request(str(e))
        except Exception as e:
            app.logger.error(f"Vocabulary extraction failed: {e}")
            app.logger.error(traceback.format_exc())
            return server_error("Vocabulary extraction failed")

    @app.route('/api/errors/log', methods=['POST'])
    @supabase_jwt_required
    def log_error():
        """Log an application error to the app_error_logs table"""
        try:
            body = ErrorLogRequest.model_validate(request.get_json() or {})
        except ValidationError as e:
            return bad_request(e.errors()[0]['msg'])

        try:
            app.supabase_service.table('app_error_logs').insert({
                'error_type': body.error_type[:100],
                'error_message': body.error_message[:Config.MAX_INPUT_LENGTH],
                'url': (body.url or '')[:Config.MAX_INPUT_LENGTH],
                'user_id': g.current_user_id,
                'metadata': body.metadata,
            }).execute()
            return api_success(status_code=201)
        except Exception as e:
            app.logger.error(f"Failed to log error: {e}")
            return server_error("Failed to log error")

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
