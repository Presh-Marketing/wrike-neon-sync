import os
import sys
import traceback
from flask import Flask, jsonify

# Create a simple debug app
app = Flask(__name__)

@app.route('/')
def index():
    try:
        # Test imports
        import_status = {}
        
        # Test each import separately
        try:
            import redis
            import_status['redis'] = 'OK'
        except Exception as e:
            import_status['redis'] = str(e)
            
        try:
            from google.auth.transport import requests as google_requests
            import_status['google_auth'] = 'OK'
        except Exception as e:
            import_status['google_auth'] = str(e)
            
        try:
            from flask_login import LoginManager
            import_status['flask_login'] = 'OK'
        except Exception as e:
            import_status['flask_login'] = str(e)
            
        try:
            from flask_session import Session
            import_status['flask_session'] = 'OK'
        except Exception as e:
            import_status['flask_session'] = str(e)
            
        try:
            from flask_wtf.csrf import CSRFProtect
            import_status['flask_wtf'] = 'OK'
        except Exception as e:
            import_status['flask_wtf'] = str(e)
            
        try:
            from flask_limiter import Limiter
            import_status['flask_limiter'] = 'OK'
        except Exception as e:
            import_status['flask_limiter'] = str(e)
        
        # Test environment variables
        env_vars = {
            'GOOGLE_CLIENT_ID': 'SET' if os.environ.get('GOOGLE_CLIENT_ID') else 'MISSING',
            'GOOGLE_CLIENT_SECRET': 'SET' if os.environ.get('GOOGLE_CLIENT_SECRET') else 'MISSING',
            'SECRET_KEY': 'SET' if os.environ.get('SECRET_KEY') else 'MISSING',
            'REDIS_URL': 'SET' if os.environ.get('REDIS_URL') else 'MISSING',
            'FLASK_ENV': os.environ.get('FLASK_ENV', 'NOT SET'),
        }
        
        # Test Redis connection
        redis_status = 'Not tested'
        if os.environ.get('REDIS_URL'):
            try:
                import redis
                r = redis.from_url(os.environ.get('REDIS_URL'))
                r.ping()
                redis_status = 'Connected'
            except Exception as e:
                redis_status = f'Failed: {str(e)}'
        
        return jsonify({
            'status': 'Debug endpoint working',
            'python_version': sys.version,
            'imports': import_status,
            'environment_variables': env_vars,
            'redis_connection': redis_status
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'type': type(e).__name__
        }), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# For Vercel
app = app 