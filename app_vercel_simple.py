import os
import logging
from flask import Flask, render_template, redirect, session, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from datetime import datetime
import urllib.parse

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

# Simple session storage using cookies (no Redis for debugging)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class
class User(UserMixin):
    def __init__(self, user_id, email, name, picture):
        self.id = user_id
        self.email = email
        self.name = name
        self.picture = picture

@login_manager.user_loader
def load_user(user_id):
    user_data = session.get('user_data')
    if user_data and user_data.get('id') == user_id:
        return User(
            user_id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            picture=user_data.get('picture')
        )
    return None

def get_oauth_config():
    """Get OAuth configuration with proper redirect URI"""
    redirect_uri = 'https://presh-api-dash.vercel.app/callback'
    
    return {
        "web": {
            "client_id": app.config['GOOGLE_CLIENT_ID'],
            "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "userinfo_uri": "https://openidconnect.googleapis.com/v1/userinfo",
            "issuer": "https://accounts.google.com",
            "redirect_uris": [redirect_uri]
        }
    }, redirect_uri

# Routes
@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login():
    try:
        if current_user.is_authenticated:
            return redirect('/dashboard')
        
        # Check if required OAuth config is present
        if not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
            logger.error("Missing Google OAuth configuration")
            return render_template('error.html', 
                error='OAuth configuration missing. Please contact administrator.'), 500
        
        oauth_config, redirect_uri = get_oauth_config()
        
        flow = Flow.from_client_config(
            oauth_config,
            scopes=['openid', 'email', 'profile'],
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='select_account',
            hd=app.config['ALLOWED_DOMAIN']
        )
        
        session['oauth_state'] = state
        session['redirect_uri'] = redirect_uri
        
        logger.info(f"OAuth login initiated, redirecting to: {authorization_url}")
        return redirect(authorization_url)
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return render_template('error.html', 
            error=f'Login failed: {str(e)}'), 500

@app.route('/callback')
def callback():
    try:
        logger.info(f"OAuth callback received with args: {request.args}")
        
        # Check for OAuth errors
        if 'error' in request.args:
            error_msg = request.args.get('error')
            logger.error(f"OAuth error: {error_msg}")
            return render_template('error.html', 
                error=f'Authentication failed: {error_msg}'), 401
        
        # Check for required parameters
        if 'code' not in request.args:
            logger.error("Missing authorization code in callback")
            return render_template('error.html', 
                error='Missing authorization code'), 400
        
        # Get state from session
        session_state = session.get('oauth_state')
        request_state = request.args.get('state')
        
        if not session_state:
            logger.error("Missing state in session")
            return render_template('error.html', 
                error='Session expired. Please try logging in again.'), 401
        
        if session_state != request_state:
            logger.error(f"State mismatch: session={session_state}, request={request_state}")
            return render_template('error.html', 
                error='Invalid state parameter'), 401
        
        # Get stored redirect URI
        redirect_uri = session.get('redirect_uri', 'https://presh-api-dash.vercel.app/callback')
        oauth_config, _ = get_oauth_config()
        
        # Create flow with state
        flow = Flow.from_client_config(
            oauth_config,
            scopes=['openid', 'email', 'profile'],
            redirect_uri=redirect_uri,
            state=session_state
        )
        
        # Manually construct the authorization response URL
        # This is more reliable than using request.url in serverless environments
        auth_response = f"{redirect_uri}?{request.query_string.decode()}"
        logger.info(f"Constructed authorization response: {auth_response}")
        
        # Fetch token
        flow.fetch_token(authorization_response=auth_response)
        
        credentials = flow.credentials
        request_session = google_requests.Request()
        
        # Verify the token
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_session,
            app.config['GOOGLE_CLIENT_ID']
        )
        
        logger.info(f"Token verified for user: {id_info.get('email')}")
        
        # Check domain restriction
        email = id_info.get('email')
        if not email:
            logger.error("No email in token")
            return render_template('error.html', 
                error='No email provided by Google'), 400
        
        if not email.endswith(f"@{app.config['ALLOWED_DOMAIN']}"):
            logger.warning(f"Unauthorized domain: {email}")
            return render_template('error.html', 
                error=f'Access restricted to @{app.config["ALLOWED_DOMAIN"]} emails only'), 403
        
        # Create user
        user = User(
            user_id=id_info['sub'],
            email=email,
            name=id_info.get('name', email.split('@')[0]),
            picture=id_info.get('picture')
        )
        
        # Store user data in session
        session['user_data'] = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture
        }
        
        # Clean up OAuth session data
        session.pop('oauth_state', None)
        session.pop('redirect_uri', None)
        
        login_user(user, remember=True)
        logger.info(f"User successfully logged in: {user.email}")
        
        return redirect('/dashboard')
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return render_template('error.html', 
            error=f'Authentication failed: {str(e)}'), 500

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index_secure.html', 
        sync_scripts={'notice': {
            'name': 'Important Notice',
            'description': 'Sync operations are not available on Vercel',
            'color': 'yellow',
            'category': 'System'
        }},
        user=current_user,
        deployment_type='vercel')

@app.route('/logout')
@login_required
def logout():
    email = current_user.email
    logout_user()
    session.clear()
    logger.info(f"User logged out: {email}")
    return redirect('/login')

@app.route('/health')
def health():
    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'deployment': 'vercel-simple',
        'oauth_configured': bool(client_id and client_secret),
        'config_status': {
            'client_id_set': bool(client_id),
            'client_secret_set': bool(client_secret),
            'client_id_preview': client_id[:20] + '...' if client_id else None,
            'secret_key_set': bool(app.config.get('SECRET_KEY')),
            'flask_env': app.config.get('FLASK_ENV', 'not_set')
        }
    })

@app.route('/test')
def test():
    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    return jsonify({
        'status': 'working',
        'message': 'Flask app is running on Vercel (simplified)',
        'oauth_configured': bool(client_id and client_secret)
    })

@app.route('/debug/oauth')
def debug_oauth():
    """Debug endpoint to check OAuth configuration"""
    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    return jsonify({
        'oauth_config': {
            'client_id_set': bool(client_id),
            'client_secret_set': bool(client_secret),
            'client_id_preview': client_id[:20] + '...' if client_id else None,
            'redirect_uri': 'https://presh-api-dash.vercel.app/callback',
            'allowed_domain': app.config.get('ALLOWED_DOMAIN'),
            'secret_key_set': bool(app.config.get('SECRET_KEY')),
            'flask_env': app.config.get('FLASK_ENV')
        },
        'session_info': {
            'has_oauth_state': 'oauth_state' in session,
            'has_redirect_uri': 'redirect_uri' in session,
            'session_keys': list(session.keys())
        },
        'environment_variables': {
            'GOOGLE_CLIENT_ID': 'SET' if os.environ.get('GOOGLE_CLIENT_ID') else 'NOT SET',
            'GOOGLE_CLIENT_SECRET': 'SET' if os.environ.get('GOOGLE_CLIENT_SECRET') else 'NOT SET',
            'SECRET_KEY': 'SET' if os.environ.get('SECRET_KEY') else 'NOT SET',
            'FLASK_ENV': os.environ.get('FLASK_ENV', 'NOT SET')
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', error='Internal server error'), 500

# For Vercel deployment
# The app variable must be named 'app' for Vercel to recognize it 