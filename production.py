import os
import multiprocessing
from config import get_config, get_int_config, get_bool_config  # Centralized configuration

# Production configuration
DEBUG = False
WEB_HOST = get_config("WEB_HOST", "0.0.0.0")
WEB_PORT = get_int_config("WEB_PORT", 8080)
# CRITICAL: Bot state management requires exactly 1 worker
# Multiple workers would create multiple bot instances leading to conflicts
WORKERS = 1
workers_env = get_config("WORKERS")
if workers_env and int(workers_env) != 1:
    print(f"[WARNING] WORKERS environment variable set to {workers_env}, but forcing to 1 for bot state management")
    print("[WARNING] Multi-worker deployment is not supported with bot functionality")

def create_production_app():
    """Create production-ready Flask app"""
    from app import app, socketio
    
    # Disable debug mode
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Security headers
    @app.after_request
    def security_headers(response):
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Strict Transport Security (HTTPS only)
        if app.config.get('HTTPS_ONLY', False):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "connect-src 'self' ws: wss:;"
        )
        
        return response
    
    return app, socketio

def setup_logging():
    """Setup production logging"""
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory (thread-safe for multi-worker startup)
    try:
        os.makedirs('logs', exist_ok=True)
    except OSError as e:
        print(f"[WARNING] Could not create logs directory: {e}")
        # Continue anyway - logging will work in current directory if needed
    
    # Setup rotating file handler
    file_handler = RotatingFileHandler(
        'logs/twitter_bot.log', 
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Setup logger
    app, _ = create_production_app()
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Twitter Bot Dashboard startup')

if __name__ == '__main__':
    print("Starting Twitter Bot Dashboard in PRODUCTION mode...")
    print(f"Host: {WEB_HOST}:{WEB_PORT}")
    print(f"Workers: {WORKERS}")
    print("For production use: gunicorn --config gunicorn.conf.py app:app")
    
    # Setup logging
    setup_logging()
    
    # Create production app
    app, socketio = create_production_app()
    
    # Run with SocketIO support
    socketio.run(
        app,
        host=WEB_HOST,
        port=WEB_PORT,
        debug=False,
        use_reloader=False
    )