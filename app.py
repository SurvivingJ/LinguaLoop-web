"""
Flask Backend for LinguaLoop Language Learning Platform
Clean, production-ready implementation with proper error handling
"""

from flask import Flask, request, jsonify, make_response, render_template, redirect, url_for, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, jwt_required
from datetime import datetime, timezone
import stripe
from .services.supabase_factory import SupabaseFactory, get_supabase, get_supabase_admin
import logging
import traceback
import os

# Internal imports
from .config import Config
from .services.service_factory import ServiceFactory
from .services.r2_service import R2Service
from .services.prompt_service import PromptService
from .services.auth_service import AuthService
from .middleware.auth import AuthMiddleware, jwt_required as supabase_jwt_required

# Import blueprints
from .routes.auth import auth_bp
from .routes.tests import tests_bp


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
    
    app.logger.info("LinguaLoop application initialized successfully")
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

            # Initialize dimension table cache for fast lookups
            from .services.test_service import DimensionService, get_test_service
            DimensionService.initialize(app.supabase)
            app.test_service = get_test_service()  # Singleton for reuse
            app.logger.info("DimensionService cache and TestService initialized")
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


def _register_blueprints(app):
    """Register all application blueprints"""
    auth_middleware = AuthMiddleware(app.supabase)
    auth_bp.auth_service = app.auth_service
    auth_bp.auth_middleware = auth_middleware

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tests_bp, url_prefix='/api/tests')

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
    
    @app.route('/language-selection')
    def language_selection():
        """Render language selection page"""
        return render_template('language_selection.html')
    
    @app.route('/tests')
    def tests():
        """Render test list page"""
        return render_template('test_list.html')

    @app.route('/test/<slug>/preview')
    def test_preview(slug):
        """Render test preview page (client-side rendered)"""
        return render_template('test_preview.html')

    @app.route('/test/<slug>')
    def test_page(slug):
        """Render test taking page (client-side rendered)"""
        return render_template('test.html')

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
                "stripe": Config.STRIPE_SECRET_KEY is not None
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
        from .services.test_service import DimensionService
        return jsonify({
            'languages': DimensionService.get_all_languages(),
            'test_types': DimensionService.get_all_test_types(),
            'status': 'success'
        })

    @app.route('/api/users/elo', methods=['GET'])
    @supabase_jwt_required
    def get_user_elo_ratings():
        """Get user's ELO ratings across all languages and skills"""
        try:
            # Get user_id from JWT claims
            user_id = g.supabase_claims.get('sub')
            if not user_id:
                return jsonify({"error": "User ID not found in token"}), 401
            
            # ✅ FIXED: Query with correct schema and FK joins
            ratings_result = app.supabase.table('user_skill_ratings')\
                .select('''
                    user_id,
                    language_id,
                    test_type_id,
                    elo_rating,
                    tests_taken,
                    last_test_date,
                    volatility,
                    dim_languages(language_code, language_name),
                    dim_test_types(type_code, type_name)
                ''')\
                .eq('user_id', user_id)\
                .execute()
            
            # ✅ FIXED: Build response with correct field names
            ratings = {}
            for rating in ratings_result.data or []:
                # Get language info from FK join
                lang_info = rating.get('dim_languages') or {}
                language_code = lang_info.get('language_code', 'unknown')
                language_name = lang_info.get('language_name', 'Unknown')
                
                # Get test type info from FK join
                type_info = rating.get('dim_test_types') or {}
                test_type_code = type_info.get('type_code', 'unknown')
                test_type_name = type_info.get('type_name', 'Unknown')
                
                # Nest by language code
                if language_code not in ratings:
                    ratings[language_code] = {
                        'language_name': language_name,
                        'language_id': rating['language_id'],
                        'skills': {}
                    }
                
                # Add skill rating
                ratings[language_code]['skills'][test_type_code] = {
                    'elo_rating': rating['elo_rating'],
                    'tests_taken': rating['tests_taken'],
                    'last_test_date': rating.get('last_test_date'),
                    'volatility': rating.get('volatility', 100),
                    'skill_name': test_type_name,
                    'test_type_id': rating['test_type_id']
                }
            
            return jsonify({
                'status': 'success',
                'ratings': ratings
            })
        
        except Exception as e:
            app.logger.error(f"Error getting user ELO: {e}")
            import traceback
            app.logger.error(traceback.format_exc())
            return jsonify({'error': 'Failed to get ELO ratings'}), 500
    
    @app.route('/api/users/tokens', methods=['GET'])
    @supabase_jwt_required
    def get_token_balance():
        """Get user's current token balance"""
        try:
            # Get user_id from JWT claims instead of querying by email
            user_id = g.supabase_claims.get('sub')
            if not user_id:
                return jsonify({"error": "User ID not found in token"}), 401

            user_result = app.supabase.table('users')\
                .select('tokens, last_free_token_date')\
                .eq('id', user_id)\
                .single()\
                .execute()

            if not user_result.data:
                return jsonify({"error": "User not found"}), 404

            tokens = user_result.data.get('tokens', 0)
            last_free_date = user_result.data.get('last_free_token_date')

            # Check if user should get daily free tokens
            today = datetime.now(timezone.utc).date().isoformat()
            free_tokens_today = Config.DAILY_FREE_TOKENS if hasattr(Config, 'DAILY_FREE_TOKENS') else 0

            if last_free_date != today and free_tokens_today > 0:
                # Grant daily free tokens
                new_tokens = tokens + free_tokens_today
                app.supabase.table('users')\
                    .update({
                        'tokens': new_tokens,
                        'last_free_token_date': today
                    })\
                    .eq('id', user_id)\
                    .execute()
                tokens = new_tokens
            
            return jsonify({
                "total_tokens": tokens,
                "free_tokens_today": free_tokens_today,
                "last_free_token_date": last_free_date or today,
                "status": "success"
            })
        except Exception as e:
            app.logger.error(f"Token balance error: {e}")
            return jsonify({"error": "Failed to get token balance", "status": "error"}), 500
    
    @app.route('/api/users/profile', methods=['GET'])
    @supabase_jwt_required
    def get_user_profile():
        """Get user profile information"""
        try:
            # Get user_id from JWT claims instead of querying by email
            user_id = g.supabase_claims.get('sub')
            if not user_id:
                return jsonify({"error": "User ID not found in token"}), 401

            user_result = app.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .single()\
                .execute()

            if not user_result.data:
                return jsonify({"error": "User not found"}), 404
            
            profile = user_result.data
            # Remove sensitive fields
            profile.pop('password_hash', None)
            
            return jsonify({
                "profile": profile,
                "status": "success"
            })
        except Exception as e:
            app.logger.error(f"Profile error: {e}")
            return jsonify({"error": "Failed to get profile"}), 500

    @app.route('/api/payments/token-packages', methods=['GET'])
    def get_token_packages():
        """Get available token packages"""
        packages = {
            'starter_10': {
                'tokens': 10,
                'price_cents': 199,
                'price_dollars': 1.99,
                'description': 'Starter pack - try the platform'
            },
            'popular_50': {
                'tokens': 50,
                'price_cents': 799,
                'price_dollars': 7.99,
                'description': 'Most popular - great value'
            },
            'premium_200': {
                'tokens': 200,
                'price_cents': 1999,
                'price_dollars': 19.99,
                'description': 'Premium pack - best value'
            }
        }
        return jsonify({"packages": packages, "status": "success"})
    
    @app.route('/api/payments/create-intent', methods=['POST'])
    @supabase_jwt_required
    def create_payment_intent():
        """Create Stripe PaymentIntent for token purchase"""
        try:
            if not stripe.api_key:
                return jsonify({"error": "Payment system not configured"}), 500
            
            data = request.get_json()
            package_id = data.get('package_id')
            
            # Package mapping
            packages = {
                'starter_10': {'tokens': 10, 'amount': 199},
                'popular_50': {'tokens': 50, 'amount': 799},
                'premium_200': {'tokens': 200, 'amount': 1999}
            }
            
            if package_id not in packages:
                return jsonify({"error": "Invalid package"}), 400
            
            package = packages[package_id]
            current_user_email = get_jwt_identity()
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=package['amount'],
                currency='usd',
                metadata={
                    'user_email': current_user_email,
                    'package_id': package_id,
                    'tokens': package['tokens']
                }
            )
            
            return jsonify({
                "client_secret": intent.client_secret,
                "amount": package['amount'],
                "tokens": package['tokens'],
                "status": "success"
            })
        except Exception as e:
            app.logger.error(f"Payment intent error: {e}")
            return jsonify({"error": str(e)}), 500

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
