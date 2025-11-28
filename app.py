"""
LinguaLoop Flask Application
Main entry point for the web application
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import os
import logging
from datetime import datetime, timedelta
import jwt

# Initialize Flask app
app = Flask(__name__)

# ============================================
# Configuration
# ============================================

class Config:
    """Flask configuration"""
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # JWT configuration
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-key-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24
    
    # API configuration
    API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')
    
    # Database
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    # Storage (Cloudflare R2)
    R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
    R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY')
    R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'lingualoop')
    
    # OpenAI
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Environment
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'

app.config.from_object(Config)
Session(app)
CORS(app)

# ============================================
# Logging Setup
# ============================================

logging.basicConfig(
    level=logging.INFO if Config.ENV == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# Authentication Decorators
# ============================================

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'success': False, 'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'success': False, 'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
            request.user_id = data['user_id']
            request.user_email = data['email']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def login_required(f):
    """Decorator for routes that require authenticated user"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    
    return decorated

# ============================================
# Helper Functions
# ============================================

def create_jwt_token(user_id: str, email: str) -> str:
    """Create JWT token for user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    return token

def api_response(success: bool, data=None, error=None, status_code=200):
    """Standardized API response"""
    response = {
        'success': success,
        'data': data,
        'error': error,
        'timestamp': datetime.utcnow().isoformat()
    }
    return jsonify(response), status_code

# ============================================
# Routes - Pages
# ============================================

@app.route('/')
def index():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html', hide_navbar=True)

@app.route('/language-selection')
@login_required
def language_selection():
    """Language selection page"""
    return render_template('language_selection.html')

@app.route('/home')
@login_required
def home():
    """Home/dashboard page"""
    user_data = {
        'email': session.get('email'),
        'id': session.get('user_id')
    }
    return render_template('home.html', user_data=user_data)

@app.route('/test-list')
@login_required
def test_list():
    """Browse tests page"""
    selected_language = request.args.get('language', '')
    return render_template('test_list.html', selected_language=selected_language)

@app.route('/test-preview')
@login_required
def test_preview():
    """Test preview page"""
    test_id = request.args.get('id')
    if not test_id:
        return redirect(url_for('test_list'))
    return render_template('test_preview.html', test_id=test_id)

@app.route('/test')
@login_required
def take_test():
    """Active test page"""
    test_id = request.args.get('id')
    if not test_id:
        return redirect(url_for('test_list'))
    return render_template('test.html', test_id=test_id)

@app.route('/results')
@login_required
def results():
    """Test results page"""
    attempt_id = request.args.get('id')
    if not attempt_id:
        return redirect(url_for('home'))
    return render_template('results.html', attempt_id=attempt_id)

@app.route('/generate-test')
@login_required
def generate_test():
    """Generate test page"""
    return render_template('generate_test.html')

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

# ============================================
# Routes - API
# ============================================

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to user email"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        is_registration = data.get('is_registration', False)
        
        # Validate email
        if not email or '@' not in email:
            return api_response(False, error='Invalid email address', status_code=400)
        
        # TODO: Implement OTP sending logic
        logger.info(f"OTP requested for email: {email}")
        
        return api_response(
            True,
            data={'message': 'OTP sent successfully'},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error sending OTP: {str(e)}")
        return api_response(False, error='Failed to send OTP', status_code=500)

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and authenticate user"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        token = data.get('token', '').strip()
        
        # Validate input
        if not email or not token:
            return api_response(False, error='Email and token required', status_code=400)
        
        if len(token) != 6 or not token.isdigit():
            return api_response(False, error='Invalid OTP format', status_code=400)
        
        # TODO: Implement OTP verification logic
        # For now, create test user
        user_id = f"user_{email.replace('@', '_')}"
        session['user_id'] = user_id
        session['email'] = email
        
        jwt_token = create_jwt_token(user_id, email)
        
        logger.info(f"User authenticated: {email}")
        
        return api_response(
            True,
            data={
                'jwt_token': jwt_token,
                'user': {
                    'id': user_id,
                    'email': email,
                    'created_at': datetime.utcnow().isoformat()
                }
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return api_response(False, error='Failed to verify OTP', status_code=500)

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    """Logout user"""
    session.clear()
    return api_response(True, data={'message': 'Logged out successfully'})

@app.route('/api/tests', methods=['GET'])
@token_required
def get_tests():
    """Get list of tests with optional filters"""
    try:
        language = request.args.get('language', '').lower()
        test_type = request.args.get('test_type', '').lower()
        difficulty = request.args.get('difficulty', type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # TODO: Implement test fetching from database
        tests = []
        
        logger.info(f"Tests fetched for user {request.user_id}")
        
        return api_response(
            True,
            data={'tests': tests, 'total': len(tests)},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error fetching tests: {str(e)}")
        return api_response(False, error='Failed to fetch tests', status_code=500)

@app.route('/api/tests/<test_id>', methods=['GET'])
@token_required
def get_test_detail(test_id):
    """Get detailed test information"""
    try:
        # TODO: Implement test detail fetching
        test = {}
        
        if not test:
            return api_response(False, error='Test not found', status_code=404)
        
        return api_response(True, data=test)
    except Exception as e:
        logger.error(f"Error fetching test detail: {str(e)}")
        return api_response(False, error='Failed to fetch test', status_code=500)

@app.route('/api/tests/<test_id>/submit', methods=['POST'])
@token_required
def submit_test(test_id):
    """Submit test responses and get results"""
    try:
        data = request.get_json()
        responses = data.get('responses', [])
        
        # Validate responses
        if not responses or not isinstance(responses, list):
            return api_response(False, error='Invalid responses format', status_code=400)
        
        # TODO: Implement test evaluation and scoring
        result = {
            'score': 0,
            'total': len(responses),
            'elo_change': 0,
            'new_elo': 0
        }
        
        logger.info(f"Test submitted by user {request.user_id}: {test_id}")
        
        return api_response(True, data=result)
    except Exception as e:
        logger.error(f"Error submitting test: {str(e)}")
        return api_response(False, error='Failed to submit test', status_code=500)

@app.route('/api/users/profile', methods=['GET'])
@token_required
def get_user_profile():
    """Get user profile and stats"""
    try:
        # TODO: Implement user profile fetching
        profile = {
            'id': request.user_id,
            'email': request.user_email,
            'tests_taken': 0,
            'current_elo': 1200,
            'tokens_remaining': 100,
            'languages': []
        }
        
        return api_response(True, data=profile)
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return api_response(False, error='Failed to fetch profile', status_code=500)

@app.route('/api/tests/generate', methods=['POST'])
@token_required
def generate_test_route():
    """Generate a custom test using AI"""
    try:
        data = request.get_json()
        language = data.get('language', '').strip()
        topic = data.get('topic', '').strip()
        difficulty = data.get('difficulty', 5, type=int)
        test_type = data.get('test_type', 'reading').lower()
        
        # Validate input
        if not language or not topic:
            return api_response(False, error='Language and topic required', status_code=400)
        
        if difficulty < 1 or difficulty > 9:
            return api_response(False, error='Difficulty must be between 1-9', status_code=400)
        
        # TODO: Implement AI test generation
        logger.info(f"Test generation requested by user {request.user_id}")
        
        return api_response(
            True,
            data={
                'test_id': 'new_test_id',
                'status': 'generating',
                'message': 'Generating your custom test...'
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error generating test: {str(e)}")
        return api_response(False, error='Failed to generate test', status_code=500)

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message='Page not found'), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message='Internal server error'), 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return render_template('error.html', 
                         error_code=403, 
                         error_message='Access forbidden'), 403

# ============================================
# Context Processors
# ============================================

@app.context_processor
def inject_config():
    """Inject config values into templates"""
    return {
        'current_year': datetime.now().year,
        'app_name': 'LinguaLoop',
        'app_version': '1.0.0'
    }

# ============================================
# Application Initialization
# ============================================

@app.before_request
def before_request():
    """Before request hook"""
    session.permanent = True
    app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME
    session.modified = True

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Cleanup on request end"""
    pass

# ============================================
# CLI Commands
# ============================================

@app.cli.command()
def init_db():
    """Initialize database"""
    logger.info("Initializing database...")
    # TODO: Implement database initialization

@app.cli.command()
def seed_db():
    """Seed database with sample data"""
    logger.info("Seeding database...")
    # TODO: Implement database seeding

# ============================================
# Main
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = Config.DEBUG
    
    logger.info(f"Starting LinguaLoop on port {port} (debug={debug})")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )
