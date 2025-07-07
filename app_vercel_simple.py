#!/usr/bin/env python3
"""
Full-featured API Sync Monitor for Vercel deployment
Includes all sync operations, static file serving, and real-time updates
"""

import os
import json
import logging
import threading
import queue
import subprocess
from datetime import datetime, timedelta
from collections import deque, defaultdict
from flask import Flask, render_template, redirect, session, request, jsonify, Response, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
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

# Google OAuth Scopes
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Disable OAUTHLIB's HTTPS requirement in development
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Global storage for sync operations
logs = deque(maxlen=2000)
active_syncs = {}
sync_history = deque(maxlen=100)
metrics = {
    'jobs_today': 0,
    'jobs_completed': 0,
    'jobs_failed': 0,
    'total_records_synced': 0,
    'avg_duration': 0,
    'durations': deque(maxlen=50)
}
event_queue = queue.Queue()

# Available sync scripts
SYNC_SCRIPTS = {
    'hubspot_companies': {
        'name': 'HubSpot Companies',
        'script': 'hubspot_companies_sync.py',
        'description': 'Sync companies from HubSpot to database',
        'color': 'orange',
        'category': 'HubSpot',
        'estimated_duration': 120,
        'object_type': 'companies'
    },
    'hubspot_contacts': {
        'name': 'HubSpot Contacts',
        'script': 'hubspot_contacts_sync.py',
        'description': 'Sync contacts from HubSpot to database',
        'color': 'amber',
        'category': 'HubSpot',
        'estimated_duration': 180,
        'object_type': 'contacts'
    },
    'hubspot_deals': {
        'name': 'HubSpot Deals',
        'script': 'hubspot_deals_sync.py',
        'description': 'Sync deals from HubSpot to database',
        'color': 'emerald',
        'category': 'HubSpot',
        'estimated_duration': 240,
        'object_type': 'deals'
    },
    'hubspot_line_items': {
        'name': 'HubSpot Line Items',
        'script': 'hubspot_line_items_sync.py',
        'description': 'Sync line items from HubSpot to database',
        'color': 'purple',
        'category': 'HubSpot',
        'estimated_duration': 120,
        'object_type': 'line_items'
    },
    'clients': {
        'name': 'Wrike Clients',
        'script': 'clients_sync.py',
        'description': 'Sync client folders from Wrike',
        'color': 'blue',
        'category': 'Wrike',
        'estimated_duration': 60,
        'object_type': 'folders'
    },
    'parent_projects': {
        'name': 'Parent Projects',
        'script': 'parentprojects_sync.py',
        'description': 'Sync parent project folders from Wrike',
        'color': 'green',
        'category': 'Wrike',
        'estimated_duration': 90,
        'object_type': 'projects'
    },
    'child_projects': {
        'name': 'Child Projects',
        'script': 'childprojects_sync.py',
        'description': 'Sync child project folders from Wrike',
        'color': 'purple',
        'category': 'Wrike',
        'estimated_duration': 150,
        'object_type': 'projects'
    },
    'tasks': {
        'name': 'Wrike Tasks',
        'script': 'tasks_sync.py',
        'description': 'Sync tasks from Wrike',
        'color': 'teal',
        'category': 'Wrike',
        'estimated_duration': 300,
        'object_type': 'tasks'
    },
    'deliverables': {
        'name': 'Wrike Deliverables',
        'script': 'deliverables_sync.py',
        'description': 'Sync deliverables from Wrike',
        'color': 'red',
        'category': 'Wrike',
        'estimated_duration': 180,
        'object_type': 'deliverables'
    }
}

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

# Sync utility functions
def add_log(level, message, sync_type=None, object_count=None, user_email=None):
    """Add a log entry with timestamp and broadcast to SSE clients."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message,
        'sync_type': sync_type,
        'object_count': object_count,
        'user': user_email
    }
    logs.append(log_entry)
    
    update_metrics_from_log(log_entry)
    
    event_data = {
        'type': 'log',
        'data': log_entry
    }
    try:
        event_queue.put_nowait(json.dumps(event_data))
    except queue.Full:
        pass

def update_metrics_from_log(log_entry):
    """Update metrics based on log entry."""
    if log_entry['level'] == 'SUCCESS':
        metrics['jobs_completed'] += 1
        if log_entry.get('object_count'):
            metrics['total_records_synced'] += log_entry['object_count']
    elif log_entry['level'] == 'ERROR':
        metrics['jobs_failed'] += 1
    
    metrics['jobs_today'] = metrics['jobs_completed'] + metrics['jobs_failed']

def broadcast_status_update(sync_type, status):
    """Broadcast sync status update to SSE clients."""
    event_data = {
        'type': 'status',
        'sync_type': sync_type,
        'data': status
    }
    try:
        event_queue.put_nowait(json.dumps(event_data))
    except queue.Full:
        pass

def broadcast_metrics_update():
    """Broadcast metrics update to SSE clients."""
    event_data = {
        'type': 'metrics',
        'data': get_current_metrics()
    }
    try:
        event_queue.put_nowait(json.dumps(event_data))
    except queue.Full:
        pass

def get_current_metrics():
    """Get current metrics including system info."""
    try:
        import psutil
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
    except ImportError:
        system_metrics = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0
        }
    
    return {
        'active_jobs': len([s for s in active_syncs.values() if s.get('status') == 'running']),
        'completed_today': metrics['jobs_completed'],
        'failed_today': metrics['jobs_failed'],
        'total_records_synced': metrics['total_records_synced'],
        'system': system_metrics
    }

def run_sync_script(sync_type, limit=None, user_email=None):
    """Run a sync script with user tracking."""
    script_info = SYNC_SCRIPTS.get(sync_type)
    if not script_info:
        add_log('ERROR', f'Unknown sync type: {sync_type}', user_email=user_email)
        return

    script_name = script_info['script']
    
    if not os.path.exists(script_name):
        add_log('ERROR', f'Script not found: {script_name}', sync_type, user_email=user_email)
        return
    
    start_time = datetime.now()
    add_log('INFO', f'Starting {script_info["name"]} sync...', sync_type, user_email=user_email)
    
    try:
        cmd = ['python', '-u', script_name]
        if limit:
            cmd.append(str(limit))
        
        active_syncs[sync_type] = {
            'started': start_time,
            'script': script_name,
            'status': 'running',
            'estimated_completion': start_time + timedelta(seconds=script_info['estimated_duration']),
            'object_type': script_info['object_type'],
            'records_processed': 0,
            'user': user_email
        }
        
        broadcast_status_update(sync_type, active_syncs[sync_type])
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,
            universal_newlines=True,
            env=env
        )
        
        records_processed = 0
        
        while True:
            poll_result = process.poll()
            output_line = process.stdout.readline()
            
            if output_line:
                line = output_line.strip()
                level = 'INFO'
                
                if ' - ERROR - ' in line or 'ERROR' in line.upper():
                    level = 'ERROR'
                elif ' - WARNING - ' in line or 'WARNING' in line.upper():
                    level = 'WARNING'
                elif 'synced' in line.lower() or 'completed' in line.lower():
                    level = 'SUCCESS'
                
                add_log(level, line, sync_type, user_email=user_email)
            
            if poll_result is not None and not output_line:
                break
        
        return_code = process.poll()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        sync_record = {
            'sync_type': sync_type,
            'started': start_time.isoformat(),
            'completed': end_time.isoformat(),
            'duration': duration,
            'status': 'completed' if return_code == 0 else 'failed',
            'records_processed': records_processed,
            'return_code': return_code,
            'user': user_email
        }
        sync_history.append(sync_record)
        
        metrics['durations'].append(duration)
        if len(metrics['durations']) > 0:
            metrics['avg_duration'] = sum(metrics['durations']) / len(metrics['durations'])
        
        if return_code == 0:
            add_log('SUCCESS', f'{script_info["name"]} sync completed successfully!', 
                sync_type, records_processed, user_email)
            active_syncs[sync_type]['status'] = 'completed'
        else:
            add_log('ERROR', f'{script_info["name"]} sync failed with return code {return_code}', 
                sync_type, user_email=user_email)
            active_syncs[sync_type]['status'] = 'failed'
            
    except Exception as e:
        add_log('ERROR', f'Error running {script_info["name"]} sync: {str(e)}', sync_type, user_email=user_email)
        active_syncs[sync_type]['status'] = 'failed'
    
    finally:
        broadcast_status_update(sync_type, active_syncs[sync_type])
        broadcast_metrics_update()

# Static file serving
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

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
            scopes=GOOGLE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
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
        
        if 'error' in request.args:
            error_msg = request.args.get('error')
            logger.error(f"OAuth error: {error_msg}")
            return render_template('error.html', 
                error=f'Authentication failed: {error_msg}'), 401
        
        if 'code' not in request.args:
            logger.error("Missing authorization code in callback")
            return render_template('error.html', 
                error='Missing authorization code'), 400
        
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
        
        redirect_uri = session.get('redirect_uri', 'https://presh-api-dash.vercel.app/callback')
        oauth_config, _ = get_oauth_config()
        
        flow = Flow.from_client_config(
            oauth_config,
            scopes=GOOGLE_SCOPES,
            redirect_uri=redirect_uri,
            state=session_state
        )
        
        auth_response = f"{redirect_uri}?{request.query_string.decode()}"
        logger.info(f"Constructed authorization response: {auth_response}")
        
        flow.fetch_token(authorization_response=auth_response)
        
        credentials = flow.credentials
        request_session = google_requests.Request()
        
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_session,
            app.config['GOOGLE_CLIENT_ID']
        )
        
        logger.info(f"Token verified for user: {id_info.get('email')}")
        
        email = id_info.get('email')
        if not email:
            logger.error("No email in token")
            return render_template('error.html', 
                error='No email provided by Google'), 400
        
        if not email.endswith(f"@{app.config['ALLOWED_DOMAIN']}"):
            logger.warning(f"Unauthorized domain: {email}")
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
        sync_scripts=SYNC_SCRIPTS,
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

@app.route('/clear-session')
def clear_session():
    session.clear()
    logger.info("Session cleared")
    return redirect('/login')

# API Routes
@app.route('/api/sync/<sync_type>')
@login_required
def start_sync(sync_type):
    if sync_type not in SYNC_SCRIPTS:
        return jsonify({'error': f'Unknown sync type: {sync_type}'}), 400
    
    if sync_type in active_syncs and active_syncs[sync_type].get('status') == 'running':
        return jsonify({'error': f'{SYNC_SCRIPTS[sync_type]["name"]} sync is already running'}), 400
    
    limit = request.args.get('limit', type=int)
    
    logger.info(f"Sync initiated by {current_user.email}: {sync_type}")
    
    thread = threading.Thread(target=run_sync_script, args=(sync_type, limit, current_user.email))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': f'{SYNC_SCRIPTS[sync_type]["name"]} sync started',
        'sync_type': sync_type,
        'estimated_duration': SYNC_SCRIPTS[sync_type]['estimated_duration'],
        'initiated_by': current_user.email
    })

@app.route('/api/status')
@login_required
def get_status():
    status_dict = {}
    for sync_type, sync_info in active_syncs.items():
        status_dict[sync_type] = {
            'status': sync_info.get('status', 'unknown'),
            'started': sync_info.get('started', '').isoformat() if sync_info.get('started') else '',
            'estimated_completion': sync_info.get('estimated_completion', '').isoformat() if sync_info.get('estimated_completion') else '',
            'records_processed': sync_info.get('records_processed', 0),
            'user': sync_info.get('user', 'unknown')
        }
    
    return jsonify(status_dict)

@app.route('/api/metrics')
@login_required
def get_metrics():
    return jsonify(get_current_metrics())

@app.route('/api/logs')
@login_required
def get_logs():
    filter_level = request.args.get('level')
    filter_sync_type = request.args.get('sync_type')
    
    filtered_logs = []
    for log in logs:
        if filter_level and log['level'] != filter_level:
            continue
        if filter_sync_type and log.get('sync_type') != filter_sync_type:
            continue
        filtered_logs.append(log)
    
    return jsonify(filtered_logs)

@app.route('/api/clear-logs', methods=['POST'])
@login_required
def clear_logs():
    logs.clear()
    add_log('INFO', f'Logs cleared by {current_user.email}', user_email=current_user.email)
    return jsonify({'message': 'Logs cleared successfully'})

@app.route('/api/history')
@login_required
def get_sync_history():
    return jsonify(list(sync_history))

@app.route('/events')
@login_required
def events():
    def event_stream():
        # Send initial data
        initial_data = {
            'type': 'init',
            'logs': list(logs)[-50:],  # Last 50 logs
            'status': get_status(),
            'metrics': get_current_metrics()
        }
        yield f"data: {json.dumps(initial_data)}\n\n"
        
        # Stream real-time updates
        while True:
            try:
                data = event_queue.get(timeout=30)
                yield f"data: {data}\n\n"
            except queue.Empty:
                # Send keepalive ping
                ping_data = {
                    'type': 'ping',
                    'metrics': get_current_metrics()
                }
                yield f"data: {json.dumps(ping_data)}\n\n"
    
    response = Response(event_stream(), content_type='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
    return response

def get_status():
    """Get current sync status"""
    status_dict = {}
    for sync_type, sync_info in active_syncs.items():
        status_dict[sync_type] = {
            'status': sync_info.get('status', 'unknown'),
            'started': sync_info.get('started', '').isoformat() if sync_info.get('started') else '',
            'estimated_completion': sync_info.get('estimated_completion', '').isoformat() if sync_info.get('estimated_completion') else '',
            'records_processed': sync_info.get('records_processed', 0),
            'user': sync_info.get('user', 'unknown')
        }
    return status_dict

# Health and debug endpoints
@app.route('/health')
def health():
    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'deployment': 'vercel-full',
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
        'message': 'Full-featured Flask app is running on Vercel',
        'oauth_configured': bool(client_id and client_secret),
        'sync_scripts_available': len(SYNC_SCRIPTS),
        'features': [
            'OAuth authentication',
            'Sync operations',
            'Real-time updates',
            'Static file serving',
            'API endpoints'
        ]
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
if __name__ == '__main__':
    app.run(debug=True) 