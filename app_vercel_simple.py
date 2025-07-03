import os
import logging
from flask import Flask, render_template, redirect, session, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from datetime import datetime

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

# Routes
@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect('/dashboard')
    
    # Build OAuth URL directly without url_for
    redirect_uri = 'https://presh-api-dash.vercel.app/callback'
    
    flow = Flow.from_client_config(
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
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account',
        hd=app.config['ALLOWED_DOMAIN']
    )
    
    session['state'] = state
    session['redirect_uri'] = redirect_uri
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return render_template('error.html', error='Authentication failed'), 401
    
    state = session.get('state')
    redirect_uri = session.get('redirect_uri', 'https://presh-api-dash.vercel.app/callback')
    
    flow = Flow.from_client_config(
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
        redirect_uri=redirect_uri,
        state=state
    )
    
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
        return redirect('/dashboard')
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return render_template('error.html', error='Authentication failed'), 500

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
    logout_user()
    session.clear()
    return redirect('/login')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'deployment': 'vercel-simple'
    })

@app.route('/test')
def test():
    return jsonify({
        'status': 'working',
        'message': 'Flask app is running on Vercel (simplified)'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

# For Vercel deployment
# The app variable must be named 'app' for Vercel to recognize it 