#!/usr/bin/env python3
"""
Secure Professional API Sync Monitor with Google OAuth
Advanced web interface with authentication, rate limiting, and comprehensive security
"""

import os
import json
import logging
import secrets
import functools
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, Response, redirect, url_for, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
import redis
import subprocess
import threading
import queue
from collections import deque, defaultdict
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'secure_sync:'
app.config['SESSION_REDIS'] = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JS access to cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Google OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['GOOGLE_DISCOVERY_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'
app.config['ALLOWED_DOMAIN'] = 'preshmarketingsolutions.com'

# Validate required environment variables
if not app.config['GOOGLE_CLIENT_ID'] or not app.config['GOOGLE_CLIENT_SECRET']:
    logger.error("Missing required Google OAuth credentials")
    raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables")

# Initialize extensions
Session(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'redis://localhost:6379')
)

# Security headers with Talisman
talisman = Talisman(
    app,
    force_https=True,
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,
    session_cookie_secure=True,
    session_cookie_http_only=True,
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", 'https://accounts.google.com', 'https://cdn.jsdelivr.net'],
        'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com', 'https://cdn.jsdelivr.net'],
        'font-src': ["'self'", 'https://fonts.gstatic.com'],
        'img-src': ["'self'", 'data:', 'https://*.googleusercontent.com'],
        'connect-src': ["'self'", 'https://accounts.google.com']
    }
)

# Enhanced global storage
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

# Available sync scripts (same as before)
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
    # In production, load from database
    # For now, load from session
    user_data = session.get('user_data')
    if user_data and user_data.get('id') == user_id:
        return User(
            user_id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            picture=user_data.get('picture')
        )
    return None

# Google OAuth setup
def get_google_oauth_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": app.config['GOOGLE_CLIENT_ID'],
                "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "userinfo_uri": "https://openidconnect.googleapis.com/v1/userinfo",
                "issuer": "https://accounts.google.com",
                "redirect_uris": [url_for('oauth2callback', _external=True)]
            }
        },
        scopes=[
            'openid',
            'email',
            'profile'
        ]
    )

# Authentication routes
@app.route('/login')
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    flow = get_google_oauth_flow()
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='select_account',
        hd=app.config['ALLOWED_DOMAIN']  # Domain hint for Google
    )
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
@limiter.limit("10 per minute")
def oauth2callback():
    if 'error' in request.args:
        logger.error(f"OAuth error: {request.args.get('error')}")
        return render_template('error.html', error='Authentication failed'), 401
    
    if 'state' not in session:
        return redirect(url_for('login'))
    
    flow = get_google_oauth_flow()
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    try:
        flow.fetch_token(authorization_response=request.url)
        
        # Verify the token
        credentials = flow.credentials
        request_session = google_requests.Request()
        
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_session,
            app.config['GOOGLE_CLIENT_ID']
        )
        
        # Verify domain restriction
        email = id_info.get('email')
        if not email or not email.endswith(f"@{app.config['ALLOWED_DOMAIN']}"):
            logger.warning(f"Unauthorized domain access attempt: {email}")
            return render_template('error.html', 
                error=f'Access restricted to @{app.config["ALLOWED_DOMAIN"]} emails only'), 403
        
        # Create user object
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
        
        # Log the user in
        login_user(user, remember=True)
        logger.info(f"User logged in: {user.email}")
        
        # Redirect to original page or index
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

# Security decorator for admin functions
def admin_required(f):
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Add additional admin checks here if needed
        # For now, all authenticated users from the domain are considered admins
        return f(*args, **kwargs)
    return decorated_function

# Main application routes (protected)
@app.route('/')
@login_required
def index():
    return render_template('index_secure.html', 
        sync_scripts=SYNC_SCRIPTS,
        user=current_user)

@app.route('/api/sync/<sync_type>')
@login_required
@limiter.limit("30 per hour")
def start_sync(sync_type):
    if sync_type not in SYNC_SCRIPTS:
        return jsonify({'error': f'Unknown sync type: {sync_type}'}), 400
    
    if sync_type in active_syncs and active_syncs[sync_type].get('status') == 'running':
        return jsonify({'error': f'{SYNC_SCRIPTS[sync_type]["name"]} sync is already running'}), 400
    
    limit = request.args.get('limit', type=int)
    
    # Log sync initiation
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

# Keep all the existing helper functions (add_log, update_metrics_from_log, etc.)
# but add user tracking to logs
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
        import traceback
        error_details = traceback.format_exc()
        add_log('ERROR', f'Error running {script_info["name"]} sync: {str(e)}', 
            sync_type, user_email=user_email)
        add_log('ERROR', f'Full traceback: {error_details}', sync_type, user_email=user_email)
        active_syncs[sync_type]['status'] = 'failed'
    
    finally:
        if sync_type in active_syncs:
            active_syncs[sync_type]['completed'] = datetime.now()
            broadcast_status_update(sync_type, active_syncs[sync_type])
            broadcast_metrics_update()

# Keep all other existing functions (broadcast_status_update, get_current_metrics, etc.)
def broadcast_status_update(sync_type, status):
    """Broadcast status update to SSE clients."""
    serializable_status = {}
    for key, value in status.items():
        if isinstance(value, datetime):
            serializable_status[key] = value.isoformat()
        else:
            serializable_status[key] = value
    
    event_data = {
        'type': 'status',
        'sync_type': sync_type,
        'data': serializable_status
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

def update_metrics_from_log(log_entry):
    """Update metrics based on log entries."""
    today = datetime.now().date()
    log_date = datetime.fromisoformat(log_entry['timestamp']).date()
    
    if log_date == today:
        if log_entry['level'] == 'SUCCESS' and 'completed successfully' in log_entry['message']:
            metrics['jobs_completed'] += 1
        elif log_entry['level'] == 'ERROR' and 'failed' in log_entry['message']:
            metrics['jobs_failed'] += 1
        
        if log_entry['object_count']:
            metrics['total_records_synced'] += log_entry['object_count']

def get_current_metrics():
    """Get current system and application metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    active_jobs = len([sync for sync in active_syncs.values() if sync.get('status') == 'running'])
    
    today = datetime.now().date()
    today_logs = [log for log in logs if datetime.fromisoformat(log['timestamp']).date() == today]
    completed_today = len([log for log in today_logs if log['level'] == 'SUCCESS' and 'completed successfully' in log['message']])
    failed_today = len([log for log in today_logs if log['level'] == 'ERROR' and 'failed' in log['message']])
    
    return {
        'active_jobs': active_jobs,
        'completed_today': completed_today,
        'failed_today': failed_today,
        'total_records_synced': metrics['total_records_synced'],
        'avg_duration': f"{metrics['avg_duration']:.1f}s" if metrics['avg_duration'] > 0 else '--',
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent
        }
    }

def get_status_dict():
    """Get status dictionary for all syncs."""
    status = {}
    for sync_type, info in active_syncs.items():
        status[sync_type] = {
            'status': info.get('status', 'unknown'),
            'started': info.get('started').isoformat() if info.get('started') else None,
            'completed': info.get('completed').isoformat() if info.get('completed') else None,
            'records_processed': info.get('records_processed', 0),
            'estimated_completion': info.get('estimated_completion').isoformat() if info.get('estimated_completion') else None,
            'user': info.get('user')
        }
    return status

# Protected API endpoints
@app.route('/events')
@login_required
def events():
    """Server-Sent Events endpoint for real-time updates."""
    def event_stream():
        initial_data = {
            'type': 'init', 
            'logs': list(logs)[-100:], 
            'status': get_status_dict(),
            'metrics': get_current_metrics()
        }
        yield f"data: {json.dumps(initial_data)}\n\n"
        
        while True:
            try:
                event = event_queue.get(timeout=30)
                yield f"data: {event}\n\n"
            except queue.Empty:
                ping_data = {
                    'type': 'ping',
                    'metrics': get_current_metrics()
                }
                yield f"data: {json.dumps(ping_data)}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/logs')
@login_required
@limiter.limit("100 per hour")
def get_logs():
    """Get recent logs with optional filtering."""
    limit = request.args.get('limit', 100, type=int)
    level_filter = request.args.get('level')
    sync_type_filter = request.args.get('sync_type')
    
    filtered_logs = list(logs)
    
    if level_filter:
        filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
    
    if sync_type_filter:
        filtered_logs = [log for log in filtered_logs if log.get('sync_type') == sync_type_filter]
    
    recent_logs = filtered_logs[-limit:] if filtered_logs else []
    
    return jsonify({
        'logs': recent_logs,
        'total': len(filtered_logs),
        'total_all': len(logs)
    })

@app.route('/api/status')
@login_required
def get_status():
    """Get status of all sync processes."""
    return jsonify(get_status_dict())

@app.route('/api/metrics')
@login_required
def get_metrics():
    """Get current system and application metrics."""
    return jsonify(get_current_metrics())

@app.route('/api/history')
@login_required
@limiter.limit("50 per hour")
def get_sync_history():
    """Get sync history."""
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        'history': list(sync_history)[-limit:],
        'total': len(sync_history)
    })

@app.route('/api/clear-logs', methods=['POST'])
@login_required
@admin_required
@limiter.limit("5 per hour")
def clear_logs():
    """Clear all logs (admin only)."""
    logs.clear()
    logger.warning(f"Logs cleared by {current_user.email}")
    return jsonify({'message': 'Logs cleared successfully'})

@app.route('/api/system-info')
@login_required
def get_system_info():
    """Get system information."""
    import flask
    return jsonify({
        'platform': os.name,
        'python_version': subprocess.check_output(['python', '--version']).decode().strip(),
        'flask_version': flask.__version__,
        'uptime': datetime.now().isoformat(),
        'environment': os.environ.get('FLASK_ENV', 'production')
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

# Health check endpoint (no auth required for monitoring)
@app.route('/health')
@limiter.exempt
def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check Redis connection
        app.config['SESSION_REDIS'].ping()
        redis_status = 'healthy'
    except:
        redis_status = 'unhealthy'
    
    return jsonify({
        'status': 'healthy' if redis_status == 'healthy' else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'redis': redis_status,
            'app': 'healthy'
        }
    })

if __name__ == '__main__':
    # In production, use a proper WSGI server like Gunicorn
    # This is only for development
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True, ssl_context='adhoc', host='127.0.0.1', port=5001)
    else:
        logger.info("Running in production mode with WSGI server")

# For Vercel deployment - expose the WSGI app
application = app 