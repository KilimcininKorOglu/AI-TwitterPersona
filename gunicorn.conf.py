import os
import multiprocessing
from config import get_config, get_int_config  # Centralized configuration

# Server Socket
bind = f"{get_config('WEB_HOST', '0.0.0.0')}:{get_config('WEB_PORT', '8080')}"
backlog = 2048

# Worker Processes - CRITICAL: Must be 1 for bot state management
# Multiple workers would cause multiple bot instances and state conflicts
workers = 1
workers_env = get_config('WORKERS')
if workers_env:
    requested_workers = int(workers_env)
    if requested_workers != 1:
        print(f"[ERROR] Requested {requested_workers} workers, but bot functionality requires exactly 1 worker")
        print("[ERROR] Multi-worker deployment conflicts with bot state management")
        workers = 1  # Force to 1 regardless of environment variable
worker_class = 'eventlet'  # Support for WebSocket
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Process naming
proc_name = 'twitter_bot_dashboard'

# User and group
user = get_config('RUN_USER', None)
group = get_config('RUN_GROUP', None)

# Logging - ensure logs directory exists (thread-safe)
try:
    os.makedirs('logs', exist_ok=True)
except OSError as e:
    # Handle race condition gracefully
    if e.errno != 17:  # Not "File exists" error
        print(f"[WARNING] Could not create logs directory: {e}")
        # Fallback to current directory logging
        errorlog = 'gunicorn_error.log'
        accesslog = 'gunicorn_access.log'
    else:
        # Directory exists, continue normally
        errorlog = 'logs/gunicorn_error.log'
        accesslog = 'logs/gunicorn_access.log'
else:
    # Directory created successfully
    errorlog = 'logs/gunicorn_error.log'
    accesslog = 'logs/gunicorn_access.log'

# Default values are set in the try/except block above
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Preload application for better performance
preload_app = True

# SSL (uncomment if using HTTPS)
# keyfile = '/path/to/private.key'
# certfile = '/path/to/certificate.crt'
# ssl_version = 2

def when_ready(server):
    """Called when server is ready to accept connections"""
    server.log.info("Twitter Bot Dashboard is ready to accept connections")

def worker_int(worker):
    """Called when worker receives INT/QUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called before worker is forked"""
    # Ensure logs directory exists before worker starts
    try:
        os.makedirs('logs', exist_ok=True)
    except OSError:
        pass  # Ignore errors, already handled above
    server.log.info(f"Worker {worker.pid} forked")

def post_fork(server, worker):
    """Called after worker is forked"""
    server.log.info(f"Worker {worker.pid} booted")

def pre_exec(server):
    """Called before new master process is forked"""
    server.log.info("Forked child, re-executing.")


def worker_abort(worker):
    """Called when worker process is aborted"""
    worker.log.info(f"Worker {worker.pid} aborted")

def on_exit(server):
    """Called when server exits"""
    server.log.info("Twitter Bot Dashboard shutting down")

def on_reload(server):
    """Called when server reloads configuration"""
    server.log.info("Twitter Bot Dashboard reloading configuration")