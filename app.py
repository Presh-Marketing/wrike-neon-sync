#!/usr/bin/env python3
"""
Professional API Sync Monitor
Advanced web interface for running various sync scripts with real-time logging,
metrics tracking, and object-level reporting via SSE
"""

import os
import subprocess
import threading
import time
import json
import queue
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, Response
from collections import deque, defaultdict
import psutil

app = Flask(__name__)

# Enhanced global storage
logs = deque(maxlen=2000)  # Keep last 2000 log entries
active_syncs = {}  # Track active sync processes
sync_history = deque(maxlen=100)  # Keep sync history
metrics = {
    'jobs_today': 0,
    'jobs_completed': 0,
    'jobs_failed': 0,
    'total_records_synced': 0,
    'avg_duration': 0,
    'durations': deque(maxlen=50)
}

# Event queue for Server-Sent Events
event_queue = queue.Queue()

# Available sync scripts with enhanced metadata
SYNC_SCRIPTS = {
    'hubspot_companies': {
        'name': 'HubSpot Companies',
        'script': 'hubspot_companies_sync.py',
        'description': 'Sync companies from HubSpot to database',
        'color': 'orange',
        'category': 'HubSpot',
        'estimated_duration': 120,  # seconds
        'object_type': 'companies'
    },
    'hubspot_contacts': {
        'name': 'HubSpot Contacts',
        'script': 'hubspot_contacts_sync.py',
        'description': 'Sync contacts from HubSpot to database with comprehensive field mapping',
        'color': 'amber',
        'category': 'HubSpot',
        'estimated_duration': 180,  # seconds
        'object_type': 'contacts'
    },
    'hubspot_deals': {
        'name': 'HubSpot Deals',
        'script': 'hubspot_deals_sync.py',
        'description': 'Sync deals from HubSpot to database with comprehensive property mapping (150+ fields)',
        'color': 'emerald',
        'category': 'HubSpot',
        'estimated_duration': 240,  # seconds
        'object_type': 'deals'
    },
    'hubspot_line_items': {
        'name': 'HubSpot Line Items',
        'script': 'hubspot_line_items_sync.py',
        'description': 'Sync line items from HubSpot to database with deal associations and comprehensive pricing data',
        'color': 'purple',
        'category': 'HubSpot',
        'estimated_duration': 120,  # seconds
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

def add_log(level, message, sync_type=None, object_count=None):
    """Add a log entry with timestamp and broadcast to SSE clients."""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message,
        'sync_type': sync_type,
        'object_count': object_count
    }
    logs.append(log_entry)
    
    # Update metrics based on log
    update_metrics_from_log(log_entry)
    
    # Broadcast to SSE clients
    event_data = {
        'type': 'log',
        'data': log_entry
    }
    try:
        event_queue.put_nowait(json.dumps(event_data))
    except queue.Full:
        pass  # Skip if queue is full

def update_metrics_from_log(log_entry):
    """Update metrics based on log entries."""
    today = datetime.now().date()
    log_date = datetime.fromisoformat(log_entry['timestamp']).date()
    
    if log_date == today:
        if log_entry['level'] == 'SUCCESS' and 'completed successfully' in log_entry['message']:
            metrics['jobs_completed'] += 1
        elif log_entry['level'] == 'ERROR' and 'failed' in log_entry['message']:
            metrics['jobs_failed'] += 1
        
        # Extract object count if available
        if log_entry['object_count']:
            metrics['total_records_synced'] += log_entry['object_count']

def broadcast_status_update(sync_type, status):
    """Broadcast status update to SSE clients."""
    # Convert datetime objects to ISO strings for JSON serialization
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

def run_sync_script(sync_type, limit=None):
    """Run a sync script in a separate thread with enhanced tracking."""
    script_info = SYNC_SCRIPTS.get(sync_type)
    if not script_info:
        add_log('ERROR', f'Unknown sync type: {sync_type}')
        return

    script_name = script_info['script']
    
    # Check if script exists
    if not os.path.exists(script_name):
        add_log('ERROR', f'Script not found: {script_name}', sync_type)
        return
    
    # Add debug information
    add_log('INFO', f'Script found: {script_name}', sync_type)
    add_log('INFO', f'Current working directory: {os.getcwd()}', sync_type)

    start_time = datetime.now()
    add_log('INFO', f'Starting {script_info["name"]} sync...', sync_type)
    
    try:
        # Build command with unbuffered Python output
        cmd = ['python', '-u', script_name]  # -u for unbuffered output
        if limit:
            cmd.append(str(limit))
        
        add_log('INFO', f'Running command: {" ".join(cmd)}', sync_type)
        
        # Set sync as active with enhanced tracking
        active_syncs[sync_type] = {
            'started': start_time,
            'script': script_name,
            'status': 'running',
            'estimated_completion': start_time + timedelta(seconds=script_info['estimated_duration']),
            'object_type': script_info['object_type'],
            'records_processed': 0
        }
        
        # Broadcast status update
        broadcast_status_update(sync_type, active_syncs[sync_type])
        
        # Prepare environment variables for subprocess
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output
        
        # Run the script
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout for logging
            text=True,
            bufsize=0,  # Unbuffered
            universal_newlines=True,
            env=env
        )
        
        add_log('INFO', f'Process started with PID: {process.pid}', sync_type)
        
        records_processed = 0
        
        # Read output line by line (stdout and stderr combined)
        while True:
            # Check if process is still running
            poll_result = process.poll()
            
            # Read combined output
            output_line = process.stdout.readline()
            if output_line:
                line = output_line.strip()
                level = 'INFO'
                
                # Parse log level from Python logging format
                if ' - ERROR - ' in line:
                    level = 'ERROR'
                elif ' - WARNING - ' in line:
                    level = 'WARNING'
                elif ' - INFO - ' in line:
                    level = 'INFO'
                elif 'ERROR' in line.upper():
                    level = 'ERROR'
                elif 'WARNING' in line.upper():
                    level = 'WARNING'
                
                # Try to extract record counts from log messages
                object_count = None
                if any(keyword in line.lower() for keyword in ['processed', 'synced', 'deliverables processed', 'tasks processed', 'contacts processed', 'companies processed', 'deals processed']):
                    import re
                    # Look for patterns like "X deliverables processed" or "Summary: X contacts processed"
                    numbers = re.findall(r'(\d+)\s*(?:deliverables?|tasks?|records?|contacts?|companies?|deals?)\s*(?:processed|synced)', line.lower())
                    if not numbers:
                        numbers = re.findall(r'(?:summary|total).*?(\d+).*?(?:processed|synced|contacts|companies|deals)', line.lower())
                    if not numbers:
                        # Handle HubSpot specific patterns like "Summary: 25 contacts processed, 0 skipped"
                        numbers = re.findall(r'summary:\s*(\d+)\s*(?:contacts?|companies?|deals?)\s*processed', line.lower())
                    if numbers:
                        try:
                            object_count = int(numbers[0])
                            records_processed += object_count
                            active_syncs[sync_type]['records_processed'] = records_processed
                        except (ValueError, IndexError):
                            pass
                
                add_log(level, line, sync_type, object_count)
            
            # Break if process finished and no more output
            if poll_result is not None and not output_line:
                break
        
        # Capture any remaining output
        remaining_output, _ = process.communicate()
        if remaining_output:
            for line in remaining_output.strip().split('\n'):
                if line.strip():
                    level = 'INFO'
                    if 'ERROR' in line.upper():
                        level = 'ERROR'
                    elif 'WARNING' in line.upper():
                        level = 'WARNING'
                    add_log(level, line.strip(), sync_type)
        
        # Get return code
        return_code = process.poll()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Update sync history
        sync_record = {
            'sync_type': sync_type,
            'started': start_time.isoformat(),
            'completed': end_time.isoformat(),
            'duration': duration,
            'status': 'completed' if return_code == 0 else 'failed',
            'records_processed': records_processed,
            'return_code': return_code
        }
        sync_history.append(sync_record)
        
        # Update metrics
        metrics['durations'].append(duration)
        if len(metrics['durations']) > 0:
            metrics['avg_duration'] = sum(metrics['durations']) / len(metrics['durations'])
        
        if return_code == 0:
            add_log('SUCCESS', f'{script_info["name"]} sync completed successfully! Processed {records_processed} {script_info["object_type"]} in {duration:.1f}s', sync_type, records_processed)
            active_syncs[sync_type]['status'] = 'completed'
        else:
            add_log('ERROR', f'{script_info["name"]} sync failed with return code {return_code}', sync_type)
            active_syncs[sync_type]['status'] = 'failed'
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        add_log('ERROR', f'Error running {script_info["name"]} sync: {str(e)}', sync_type)
        add_log('ERROR', f'Full traceback: {error_details}', sync_type)
        active_syncs[sync_type]['status'] = 'failed'
        
        # Add to sync history even if failed
        sync_record = {
            'sync_type': sync_type,
            'started': start_time.isoformat(),
            'completed': datetime.now().isoformat(),
            'duration': (datetime.now() - start_time).total_seconds(),
            'status': 'failed',
            'records_processed': 0,
            'error': str(e)
        }
        sync_history.append(sync_record)
    
    finally:
        # Mark sync as completed and broadcast update
        if sync_type in active_syncs:
            active_syncs[sync_type]['completed'] = datetime.now()
            broadcast_status_update(sync_type, active_syncs[sync_type])
            broadcast_metrics_update()

def get_current_metrics():
    """Get current system and application metrics."""
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Application metrics
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

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', sync_scripts=SYNC_SCRIPTS)

@app.route('/events')
def events():
    """Server-Sent Events endpoint for real-time updates."""
    def event_stream():
        # Send initial status and recent logs
        initial_data = {
            'type': 'init', 
            'logs': list(logs)[-100:], 
            'status': get_status_dict(),
            'metrics': get_current_metrics()
        }
        yield f"data: {json.dumps(initial_data)}\n\n"
        
        # Stream new events
        while True:
            try:
                # Wait for new event with timeout
                event = event_queue.get(timeout=30)  # 30 second timeout for keep-alive
                yield f"data: {event}\n\n"
            except queue.Empty:
                # Send keep-alive ping with current metrics
                ping_data = {
                    'type': 'ping',
                    'metrics': get_current_metrics()
                }
                yield f"data: {json.dumps(ping_data)}\n\n"
    
    return Response(event_stream(), mimetype='text/event-stream')

def get_status_dict():
    """Get status dictionary for all syncs."""
    status = {}
    for sync_type, info in active_syncs.items():
        status[sync_type] = {
            'status': info.get('status', 'unknown'),
            'started': info.get('started').isoformat() if info.get('started') else None,
            'completed': info.get('completed').isoformat() if info.get('completed') else None,
            'records_processed': info.get('records_processed', 0),
            'estimated_completion': info.get('estimated_completion').isoformat() if info.get('estimated_completion') else None
        }
    return status

@app.route('/api/sync/<sync_type>')
def start_sync(sync_type):
    """Start a sync process."""
    if sync_type not in SYNC_SCRIPTS:
        return jsonify({'error': f'Unknown sync type: {sync_type}'}), 400
    
    # Check if already running
    if sync_type in active_syncs and active_syncs[sync_type].get('status') == 'running':
        return jsonify({'error': f'{SYNC_SCRIPTS[sync_type]["name"]} sync is already running'}), 400
    
    # Get optional limit parameter
    limit = request.args.get('limit', type=int)
    
    # Start sync in background thread
    thread = threading.Thread(target=run_sync_script, args=(sync_type, limit))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': f'{SYNC_SCRIPTS[sync_type]["name"]} sync started',
        'sync_type': sync_type,
        'estimated_duration': SYNC_SCRIPTS[sync_type]['estimated_duration']
    })

@app.route('/api/logs')
def get_logs():
    """Get recent logs with optional filtering."""
    limit = request.args.get('limit', 100, type=int)
    level_filter = request.args.get('level')
    sync_type_filter = request.args.get('sync_type')
    
    filtered_logs = list(logs)
    
    # Apply filters
    if level_filter:
        filtered_logs = [log for log in filtered_logs if log['level'] == level_filter]
    
    if sync_type_filter:
        filtered_logs = [log for log in filtered_logs if log.get('sync_type') == sync_type_filter]
    
    # Apply limit
    recent_logs = filtered_logs[-limit:] if filtered_logs else []
    
    return jsonify({
        'logs': recent_logs,
        'total': len(filtered_logs),
        'total_all': len(logs)
    })

@app.route('/api/status')
def get_status():
    """Get status of all sync processes."""
    return jsonify(get_status_dict())

@app.route('/api/metrics')
def get_metrics():
    """Get current system and application metrics."""
    return jsonify(get_current_metrics())

@app.route('/api/history')
def get_sync_history():
    """Get sync job history."""
    limit = request.args.get('limit', 50, type=int)
    recent_history = list(sync_history)[-limit:]
    
    return jsonify({
        'history': recent_history,
        'total': len(sync_history)
    })

@app.route('/api/clear-logs')
def clear_logs():
    """Clear all logs."""
    logs.clear()
    add_log('INFO', 'Logs cleared by user')
    return jsonify({'message': 'Logs cleared'})

@app.route('/api/system-info')
def get_system_info():
    """Get detailed system information."""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return jsonify({
            'hostname': os.uname().nodename,
            'system': f"{os.uname().sysname} {os.uname().release}",
            'python_version': f"{psutil.Process().exe()}",
            'uptime': str(uptime).split('.')[0],  # Remove microseconds
            'boot_time': boot_time.isoformat(),
            'processes': len(psutil.pids()),
            'cpu_count': psutil.cpu_count(),
            'memory_total': f"{psutil.virtual_memory().total / (1024**3):.1f} GB"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Add startup log
    add_log('INFO', 'Professional API Sync Monitor started with real-time updates')
    
    # Set WRIKE_API_TOKEN from WRIKE_TOKEN if not set (for backward compatibility)
    if not os.getenv('WRIKE_API_TOKEN') and os.getenv('WRIKE_TOKEN'):
        os.environ['WRIKE_API_TOKEN'] = os.getenv('WRIKE_TOKEN')
    elif not os.getenv('WRIKE_TOKEN') and os.getenv('WRIKE_API_TOKEN'):
        os.environ['WRIKE_TOKEN'] = os.getenv('WRIKE_API_TOKEN')
    
    # Check if required environment variables are set (after setting compatibility vars)
    required_vars = ['NEON_HOST', 'NEON_DATABASE', 'NEON_USER', 'NEON_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    # Check for at least one Wrike token
    if not os.getenv('WRIKE_TOKEN') and not os.getenv('WRIKE_API_TOKEN'):
        missing_vars.append('WRIKE_TOKEN or WRIKE_API_TOKEN')
    
    if missing_vars:
        add_log('WARNING', f'Missing environment variables: {", ".join(missing_vars)}')
    else:
        add_log('INFO', 'All required environment variables are set')
    
    # Initialize metrics
    metrics['jobs_today'] = 0
    add_log('INFO', 'Metrics tracking initialized')
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5001) 