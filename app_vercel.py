import os
import logging
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from datetime import datetime
import functools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['ALLOWED_DOMAIN'] = 'preshmarketingsolutions.com'

# Disable OAUTHLIB's HTTPS requirement in development
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

try:
    # Redis configuration for sessions
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis_client
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'presh-api:'
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Initialize extensions
    Session(app)
    csrf = CSRFProtect(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=redis_url
    )
except Exception as e:
    logger.error(f"Error during app initialization: {str(e)}")
    raise

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, email, name, picture):
        self.id = user_id
        self.email = email
        self.name = name
        self.picture = picture
        self.domain = email.split('@')[1] if '@' in email else None

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = session.get('user_data')
        if user_data and user_data.get('id') == user_id:
            return User(
                user_id=user_data['id'],
                email=user_data['email'],
                name=user_data['name'],
                picture=user_data.get('picture')
            )
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
    return None

# Google OAuth setup
def get_google_oauth_flow():
    # For Vercel, we need to handle the redirect URI more carefully
    # Build the redirect URI manually to ensure HTTPS in production
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, use the actual domain
        redirect_uri = 'https://presh-api-dash.vercel.app/callback'
    else:
        # In development, use Flask's url_for
        redirect_uri = url_for('oauth2callback', _external=True)
    
    return Flow.from_client_config(
        {
            "web": {
                "client_id": app.config['GOOGLE_CLIENT_ID'],
                "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "userinfo_uri": "https://openidconnect.googleapis.com/v1/userinfo",
                "issuer": "https://accounts.google.com",
                "redirect_uris": [redirect_uri]
            }
        },
        scopes=['openid', 'email', 'profile'],
        redirect_uri=redirect_uri
    )

# Authentication routes
@app.route('/login')
@limiter.limit("10 per minute")
def login():
    try:
        if current_user.is_authenticated:
            return redirect('/dashboard')
        
        flow = get_google_oauth_flow()
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='select_account',
            hd=app.config['ALLOWED_DOMAIN']
        )
        
        session['state'] = state
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
            'message': 'Error during login'
        }), 500

@app.route('/callback')
@app.route('/oauth2callback')
@limiter.limit("10 per minute")
def oauth2callback():
    if 'error' in request.args:
        logger.error(f"OAuth error: {request.args.get('error')}")
        return render_template('error.html', error='Authentication failed'), 401
    
    if 'state' not in session:
        return redirect(url_for('login'))
    
    flow = get_google_oauth_flow()
    
    try:
        flow.fetch_token(authorization_response=request.url)
        
        credentials = flow.credentials
        request_session = google_requests.Request()
        
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_session,
            app.config['GOOGLE_CLIENT_ID']
        )
        
        email = id_info.get('email')
        if not email or not email.endswith(f"@{app.config['ALLOWED_DOMAIN']}"):
            logger.warning(f"Unauthorized domain access attempt: {email}")
            return render_template('error.html', 
                error=f'Access restricted to @{app.config["ALLOWED_DOMAIN"]} emails only'), 403
        
        user = User(
            user_id=id_info['sub'],
            email=email,
            name=id_info.get('name', email.split('@')[0]),
            picture=id_info.get('picture')
        )
        
        session['user_data'] = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture
        }
        
        login_user(user, remember=True)
        logger.info(f"User logged in: {user.email}")
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return render_template('error.html', error='Authentication failed'), 500

@app.route('/logout')
@login_required
def logout():
    email = current_user.email
    logout_user()
    session.clear()
    logger.info(f"User logged out: {email}")
    return redirect(url_for('login'))

# Main routes
@app.route('/')
def root():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        else:
            return redirect(url_for('login'))
    except Exception as e:
        logger.error(f"Root route error: {str(e)}")
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
            'message': 'Error in root route'
        }), 500

@app.route('/dashboard')
@login_required
def index():
    # Simplified sync scripts for Vercel
    sync_scripts = {
        'notice': {
            'name': 'Important Notice',
            'description': 'Sync operations are not available on Vercel deployment',
            'color': 'yellow',
            'category': 'System'
        }
    }
    
    return render_template('index_secure.html', 
        sync_scripts=sync_scripts,
        user=current_user,
        deployment_type='vercel')

# Simplified API endpoints for Vercel
@app.route('/api/sync/<sync_type>')
@login_required
def start_sync(sync_type):
    return jsonify({
        'error': 'Sync operations are not available on Vercel deployment. Please use a dedicated server for sync operations.',
        'suggestion': 'Consider deploying to Railway, Render, or a VPS for full functionality.'
    }), 503

@app.route('/api/status')
@login_required
def get_status():
    return jsonify({
        'deployment': 'vercel',
        'sync_available': False,
        'user': current_user.email
    })

@app.route('/api/metrics')
@login_required
def get_metrics():
    return jsonify({
        'deployment': 'vercel',
        'message': 'Metrics not available in serverless deployment'
    })

# Test endpoint - no auth required
@app.route('/test')
def test():
    return jsonify({
        'status': 'working',
        'message': 'Flask app is running on Vercel'
    })

# Health check endpoint
@app.route('/health')
@limiter.exempt
def health_check():
    try:
        redis_client.ping()
        redis_status = 'healthy'
    except:
        redis_status = 'unhealthy'
    
    return jsonify({
        'status': 'healthy' if redis_status == 'healthy' else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'deployment': 'vercel',
        'services': {
            'redis': redis_status,
            'app': 'healthy'
        }
    })

# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    return render_template('error.html', error='Unauthorized access'), 401

@app.errorhandler(403)
def forbidden(error):
    return render_template('error.html', error='Access forbidden'), 403

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('error.html', 
        error=f'Rate limit exceeded: {e.description}'), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return render_template('error.html', error='Internal server error'), 500

# For Vercel deployment
# The app variable must be named 'app' for Vercel to recognize it 