from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import CSRFError
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
import bcrypt
import threading
import time
import os
from config import get_config, get_int_config, get_bool_config, reload_config, get_sleep_hours  # Centralized configuration
import sqlite3
from datetime import datetime, timedelta, timezone
import json
import math
from functools import lru_cache
import gc  # For memory management
import logging
import re  # For log sanitization
import secrets  # For secure random key generation
import hashlib  # For key strength validation

# Import bot modules (with error handling for missing API keys)
import database
from database import validate_table_name
import tweet_length as tweet_length_rules

# Create or migrate the schema on import: gunicorn loads app:app and never runs __main__
database.createDatabase()

# Security-aware logging system
def setup_secure_logging():
    """Setup secure logging with sanitization"""
    # os.makedirs returns None, so create the directory first instead of using it in a condition
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/security.log', mode='a', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

# Initialize secure logger
secure_logger = setup_secure_logging()

def sanitize_for_logging(data):
    """
    Sanitize sensitive data before logging
    Returns sanitized string safe for logging
    """
    if isinstance(data, dict):
        sensitive_keys = [
            'api_key', 'api_secret', 'access_token', 'access_token_secret', 
            'bearer_token', 'gemini_api_key', 'password', 'secret', 'token'
        ]
        sanitized = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                if value:
                    sanitized[key] = f"***{value[-4:] if len(str(value)) > 4 else '****'}***"
                else:
                    sanitized[key] = "***empty***"
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, (list, tuple)):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str):
        # Sanitize known sensitive patterns
        patterns = [
            (r'(api_key|secret|token|password)[=:]\s*[^\s,}]+', r'\1=***REDACTED***'),
            (r'Bearer\s+[A-Za-z0-9_%-]+', r'Bearer ***REDACTED***'),
            (r'[A-Za-z0-9_-]{20,}', lambda m: f"***{m.group()[-4:]}***" if len(m.group()) > 10 else "***REDACTED***")
        ]
        sanitized = data
        for pattern, replacement in patterns:
            if callable(replacement):
                sanitized = re.sub(pattern, replacement, sanitized)
            else:
                sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized
    else:
        return data

def secure_log(level, message, data=None):
    """
    Log messages with automatic sanitization of sensitive data
    """
    if data is not None:
        sanitized_data = sanitize_for_logging(data)
        message = f"{message}: {sanitized_data}"
    
    if level.upper() == 'DEBUG':
        secure_logger.debug(message)
    elif level.upper() == 'INFO':
        secure_logger.info(message)
    elif level.upper() == 'WARNING':
        secure_logger.warning(message)
    elif level.upper() == 'ERROR':
        secure_logger.error(message)
    elif level.upper() == 'CRITICAL':
        secure_logger.critical(message)
    else:
        secure_logger.info(message)

# Analytics memory management
_analytics_cleanup_counter = 0
_analytics_cleanup_interval = 100  # Run cleanup every 100 analytics requests

def analytics_memory_cleanup():
    """Periodic memory cleanup for analytics functions"""
    global _analytics_cleanup_counter
    _analytics_cleanup_counter += 1
    
    if _analytics_cleanup_counter >= _analytics_cleanup_interval:
        gc.collect()  # Force garbage collection
        _analytics_cleanup_counter = 0
        secure_log('info', f"Analytics memory cleanup performed (every {_analytics_cleanup_interval} requests)")

def validate_secret_key_strength(key):
    """
    Validate Flask secret key strength
    Returns: (is_strong: bool, issues: list, score: int)
    """
    issues = []
    score = 0
    
    # Length check
    if len(key) < 32:
        issues.append("Secret key should be at least 32 characters long")
    else:
        score += 2
    
    if len(key) >= 64:
        score += 1
        
    # Character variety check
    has_upper = any(c.isupper() for c in key)
    has_lower = any(c.islower() for c in key)
    has_digit = any(c.isdigit() for c in key)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in key)
    
    variety_count = sum([has_upper, has_lower, has_digit, has_special])
    
    if variety_count < 2:
        issues.append("Secret key should contain different character types (upper, lower, digits, special)")
    else:
        score += variety_count
    
    # Common/weak patterns check
    weak_patterns = [
        "secret", "password", "key", "twitter", "bot", "flask",
        "123456", "abcdef", "qwerty", "admin", "test", "default"
    ]
    
    key_lower = key.lower()
    for pattern in weak_patterns:
        if pattern in key_lower:
            issues.append(f"Secret key contains weak pattern: '{pattern}'")
            score -= 1
    
    # Entropy check (simplified)
    unique_chars = len(set(key))
    if unique_chars < len(key) * 0.5:  # Less than 50% unique characters
        issues.append("Secret key has low entropy (too many repeated characters)")
    else:
        score += 1
    
    # Classification
    is_strong = len(issues) == 0 and score >= 5
    
    return is_strong, issues, max(0, score)

def generate_secure_secret_key():
    """Generate a cryptographically secure secret key"""
    # Generate 64 random bytes and convert to URL-safe base64
    random_bytes = secrets.token_bytes(64)
    secure_key = secrets.token_urlsafe(64)
    
    # Add timestamp hash for additional uniqueness
    timestamp = str(time.time()).encode()
    timestamp_hash = hashlib.sha256(timestamp).hexdigest()[:16]
    
    # Combine for final key
    final_key = f"{secure_key}-{timestamp_hash}"
    
    return final_key

def setup_secure_flask_secret():
    """Setup Flask secret key with security validation"""
    # Get configured secret key
    configured_key = get_config("FLASK_SECRET_KEY", None)
    
    # Default weak keys that should never be used
    weak_default_keys = [
        "twitter-bot-secret-key", "default-secret-key", "secret-key", 
        "flask-secret", "your-secret-key", "change-this-key",
        "super-secret-key", "my-secret-key", "development-key"
    ]
    
    # Check if we have a configured key
    if not configured_key or configured_key in weak_default_keys:
        # Generate new secure key
        new_key = generate_secure_secret_key()
        
        # Log security warning
        secure_log('warning', "No secure Flask secret key found - generated new one")
        secure_log('warning', "IMPORTANT: Save this key to FLASK_SECRET_KEY in token.env for production use")
        secure_log('info', f"Generated key length: {len(new_key)} characters")
        
        return new_key
    
    # Validate existing key strength
    is_strong, issues, score = validate_secret_key_strength(configured_key)
    
    if not is_strong:
        secure_log('warning', f"Flask secret key has security issues (score: {score}/7)")
        for issue in issues:
            secure_log('warning', f"  - {issue}")
        
        if score < 3:  # Very weak key
            secure_log('error', "Secret key is too weak - generating new secure key")
            new_key = generate_secure_secret_key() 
            secure_log('warning', "IMPORTANT: Update FLASK_SECRET_KEY in token.env with secure key")
            return new_key
        else:
            secure_log('warning', "Using existing key but consider improving it")
    else:
        secure_log('info', f"Flask secret key security validated (score: {score}/7)")
    
    return configured_key

def get_safe_table_name():
    """
    Get validated table name for safe SQL operations.
    
    Returns:
        str: Validated table name or None if invalid
    """
    if not validate_table_name(database.tableName):
        print(f"[ERROR] Invalid table name detected: {database.tableName}")
        return None
    return database.tableName

def tweets_table():
    """
    Return the configured tweets table name for SQL, raising if it is not whitelisted.

    The name is checked against database.ALLOWED_TABLE_NAMES, so it is safe to
    interpolate into queries.
    """
    safe_table = get_safe_table_name()
    if not safe_table:
        raise ValueError("Güvenlik hatası: Geçersiz tablo adı")
    return safe_table

# Conditional imports - only import if API keys are available
reply = None
trend = None
twitter_client = None
main = None

try:
    import reply
    import trend
    import twitter_client
    import main
    API_MODULES_LOADED = True
except Exception as e:
    print(f"[WARNING] Bot modules not fully loaded: {e}")
    print("[INFO] Dashboard will run in configuration-only mode")
    API_MODULES_LOADED = False

# Load environment variables
# Configuration loaded via centralized config module

# Web server configuration
WEB_PORT = get_int_config("WEB_PORT", 5000)
WEB_HOST = get_config("WEB_HOST", "127.0.0.1")
WEB_DEBUG = get_bool_config("WEB_DEBUG", False)

# Initialize Flask app with secure secret key
app = Flask(__name__)

# SECURITY: Setup secure Flask secret key with validation
app.secret_key = setup_secure_flask_secret()

# CRITICAL: Validate single-worker deployment
# Multi-worker deployment is incompatible with bot state management
def validate_single_worker_deployment():
    """Validate that we're running with exactly 1 worker for bot functionality"""
    workers_env = get_config('WORKERS', '1')
    try:
        workers = int(workers_env)
        if workers > 1:
            print(f"[ERROR] Detected {workers} workers configured!")
            print("[ERROR] Bot functionality requires exactly 1 worker to prevent state conflicts")
            print("[ERROR] Multiple bot instances would conflict and cause unpredictable behavior")
            print("[SOLUTION] Set WORKERS=1 in environment or use --workers=1 with gunicorn")
            return False
    except ValueError:
        print(f"[WARNING] Invalid WORKERS value: {workers_env}, defaulting to 1")
    return True

# Validate deployment configuration on startup
if not validate_single_worker_deployment():
    print("[WARNING] Multi-worker configuration detected - bot functionality may be unstable")

# Initialize security extensions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmalısınız.'

csrf = CSRFProtect(app)

# SECURITY: Enhanced CSRF protection configuration
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour token lifetime
app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']  # Methods requiring CSRF
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']  # Allowed headers

# SECURITY: Add secure CSRF token generation for AJAX requests
@app.context_processor
def inject_csrf_token():
    """Inject secure CSRF token for AJAX requests without exposing in meta tags"""
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf())

# SECURITY: Secure CSRF token endpoint (instead of meta tag exposure)
@app.route('/csrf-token')
def get_csrf_token():
    """Provide CSRF token via secure API endpoint instead of meta tag"""
    try:
        from flask_wtf.csrf import generate_csrf
        token = generate_csrf()
        return jsonify({
            'csrf_token': token,
            'expires_in': app.config.get('WTF_CSRF_TIME_LIMIT', 3600)
        })
    except Exception as e:
        secure_log('error', 'Failed to generate CSRF token', str(e))
        return jsonify({'error': 'Failed to generate token'}), 500

# CSP nonce injection removed - using unsafe-inline for compatibility

# SECURITY: Enhanced security headers with CSP nonce
@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers"""
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS Protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HTTPS Strict Transport Security (if using HTTPS)
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    # Content Security Policy - Allow jQuery and other CDN sources
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "connect-src 'self' ws: wss:; "
        "img-src 'self' data: https:; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    
    
    return response

# Initialize SocketIO for real-time updates
socketio = SocketIO(app)  # Default CORS policy only accepts same-origin connections

# Global bot control variables with thread safety
bot_thread = None
bot_running = False
bot_stop_event = threading.Event()  # Event for graceful thread termination
bot_lock = threading.Lock()  # Thread safety for bot variables
connected_clients = set()  # Track connected WebSocket clients
bot_stats = {
    "last_tweet": None,
    "last_tweet_time": None,
    "daily_tweets": 0,
    "total_tweets": 0,
    "bot_start_time": None
}

# User model for authentication
class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    # Simple user system - in production use proper database
    admin_users = get_config("ADMIN_USERS", "admin").split(",")
    if user_id in admin_users:
        return User(user_id)
    return None

# Login form
class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

def is_safe_redirect_target(target):
    """Allow only same-site relative paths as post-login redirect targets."""
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return False
    from urllib.parse import urlparse
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Secure authentication with bcrypt password hashing only
        admin_password_hash = get_config("ADMIN_PASSWORD_HASH")
        admin_users = get_config("ADMIN_USERS", "admin").split(",")
        
        # SECURITY: Require proper bcrypt hash - no fallback to plain passwords
        if not admin_password_hash:
            flash('Sistem yapılandırması eksik: ADMIN_PASSWORD_HASH gerekli', 'danger')
            return redirect(url_for('login'))
        
        # Validate password strength requirement during setup
        if len(admin_password_hash) < 60:  # bcrypt hashes are ~60 characters
            flash('Geçersiz şifre hash formatı', 'danger')
            return redirect(url_for('login'))
        
        try:
            # Test password verification
            password_match = bcrypt.checkpw(password.encode('utf-8'), admin_password_hash.encode('utf-8'))
            username_match = username in admin_users
        except Exception as e:
            # Log authentication errors without exposing details
            print(f"[ERROR] Authentication error: {type(e).__name__}")
            flash('Kimlik doğrulama hatası', 'danger')
            return redirect(url_for('login'))
        
        if username_match and password_match:
            user = User(username)
            login_user(user)
            flash('Başarıyla giriş yaptınız!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if is_safe_redirect_target(next_page) else redirect(url_for('dashboard'))
        else:
            # Generic error message to prevent username enumeration
            flash('Geçersiz kimlik bilgileri', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Başarıyla çıkış yaptınız', 'info')
    return redirect(url_for('login'))

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    from flask import send_from_directory
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
@login_required
def dashboard():
    """Main dashboard page showing bot status and recent activity"""
    update_stats()
    config = get_current_config()
    return render_template('dashboard.html', stats=bot_stats, bot_running=bot_running, config=config)

@app.route('/tweets')
@login_required
def tweets_history():
    """Tweet history page with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')
    per_page = 20
    
    # Get tweets from database with filtering
    tweets, total_count = get_tweets_from_db(page, per_page, filter_type)
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('tweets.html', 
                         tweets=tweets, 
                         page=page, 
                         total_pages=total_pages,
                         filter_type=filter_type,
                         total_count=total_count)

@app.route('/manual')
@login_required
def manual_tweet():
    """Manual tweet composition page"""
    return render_template('manual.html')

@app.route('/config')
@login_required
def configuration():
    """Configuration panel for bot settings"""
    config = get_current_config()
    return render_template('config.html', config=config)

@app.route('/monitoring')
@login_required
def monitoring():
    """Real-time monitoring page"""
    trends = get_current_trends()
    return render_template('monitoring.html', trends=trends)

@app.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard page"""
    return render_template('analytics.html')

@app.route('/prompts')
@login_required
def prompts():
    """Prompt management page"""
    return render_template('prompts.html')

# API Endpoints
@app.route('/api/status')
@login_required
def api_status():
    """Get bot current status"""
    update_stats()
    return jsonify({
        "running": bot_running,
        "stats": bot_stats
    })

@app.route('/api/control', methods=['POST'])
@login_required
def api_control():
    """Start/stop bot control"""
    global bot_thread, bot_running
    
    # Check if bot modules are loaded
    if not API_MODULES_LOADED:
        return jsonify({"success": False, "message": "Bot modülleri yüklenmedi - API anahtarlarını kontrol edin"}), 400
    
    # Validate request JSON
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "JSON verisi gerekli"}), 400

    action = data.get('action')
    
    # Validate action parameter
    if not action or action not in ['start', 'stop']:
        return jsonify({"success": False, "message": "Geçersiz action: 'start' veya 'stop' olmalı"}), 400
    
    global bot_stop_event
    with bot_lock:
        if action == 'start' and not bot_running:
            try:
                # Give each run its own stop event: a previous thread that is still
                # blocked in a network call keeps its set event and exits afterwards
                bot_stop_event = threading.Event()

                print(f"[INFO] Starting bot thread...")
                bot_thread = threading.Thread(target=run_bot_thread, args=(bot_stop_event,))
                bot_thread.daemon = True
                bot_thread.start()
                bot_running = True
                bot_stats["bot_start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[SUCCESS] Bot started successfully, bot_running={bot_running}")

                # Broadcast status update via SocketIO
                socketio.emit('bot_status', {'running': True, 'message': 'Bot başlatıldı'})

                return jsonify({"success": True, "message": "Bot başlatıldı"})
            except Exception as e:
                print(f"[!] Error starting bot thread: {e}")
                return jsonify({"success": False, "message": f"Bot başlatılamadı: {str(e)}"})
            
        elif action == 'stop' and bot_running:
            try:
                print(f"[INFO] Stopping bot thread...")
                bot_running = False
                # Signal the thread; it exits at its next stop-event check. The event
                # stays set so a thread blocked in a long call still stops afterwards.
                bot_stop_event.set()

                # Clear bot start time when stopped
                bot_stats["bot_start_time"] = None

                print(f"[SUCCESS] Bot stopped successfully, bot_running={bot_running}")

                # Broadcast status update via SocketIO
                socketio.emit('bot_status', {'running': False, 'message': 'Bot durduruldu'})

                return jsonify({"success": True, "message": "Bot durduruldu"})
            except Exception as e:
                return jsonify({"success": False, "message": f"Bot durdurma hatası: {str(e)}"})
            
        return jsonify({"success": False, "message": "Geçersiz işlem"})

PERSONA_TYPES = ('tech', 'casual', 'sad')  # Persona prompt types stored with tweets

@app.route('/api/tweet', methods=['POST'])
@login_required
def api_manual_tweet():
    """Post manual tweet"""
    if not API_MODULES_LOADED or not main:
        return jsonify({"success": False, "message": "Bot modülleri yüklenmedi - API anahtarlarını kontrol edin"}), 400
    
    data = request.get_json(silent=True) or {}  # A missing or invalid JSON body means no text
    tweet_text = data.get('text')
    persona = data.get('persona', 'casual')
    
    # Validate and sanitize input
    # Tweets are plain text for Twitter and the dashboard renders them escaped,
    # so keep "<", ">" and "data:" instead of stripping them like HTML
    tweet_text = (tweet_text or "").strip()
    is_valid, error_message = validate_tweet_text(tweet_text)
    
    if not is_valid:
        return jsonify({"success": False, "message": error_message})
    
    try:
        # Post tweet using main module function
        status = main.scheduled_tweet(tweet_text)
        
        # Save to database
        database.save_tweets(tweet=tweet_text, tweet_type="manual", status=status,
                             persona=persona if persona in PERSONA_TYPES else None)
        
        # Broadcast to all clients
        broadcast_new_tweet(tweet_text, status)
        
        return jsonify({
            "success": status,
            "message": "Tweet gönderildi" if status else "Tweet gönderilemedi"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata: {str(e)}"})

@app.route('/api/enhance', methods=['POST'])
@login_required
def api_enhance_tweet():
    """Enhance tweet text using AI"""
    if not API_MODULES_LOADED or not reply:
        return jsonify({"success": False, "message": "AI modülü yüklenmedi"}), 400

    data = request.get_json(silent=True) or {}  # A missing or invalid JSON body means no text
    original_text = (data.get('text') or '').strip()
    persona = data.get('persona', 'casual')

    if not original_text:
        return jsonify({"success": False, "message": "Tweet metni gerekli"}), 400

    try:
        # Get persona prompt from database
        prompts = database.get_prompts()
        persona_prompt = prompts.get(persona, prompts.get('casual', ''))

        # Create enhancement prompt using persona from database
        enhancement_prompt = f"""
            {persona_prompt}

            Konu: {original_text}

            ÖNEMLİ KURALLAR:
            1. Oluşturacağın tweet'in karakter sayısı yukarıda yazıyor. asla aşmayacaksın!
            2. Tweet'i kesik bırakma, tam bir cümle olsun
            3. Emoji ve hashtag'ler de karakter sayısına dahil

            Sadece tweet metnini yaz, başka hiçbir açıklama ekleme."""

        # Use Gemini AI to enhance the tweet
        import google.generativeai as genai
        genai.configure(api_key=get_config("gemini_api_key"))

        model = genai.GenerativeModel(get_config("GEMINI_MODEL", "gemini-2.5-flash"))
        response = model.generate_content(enhancement_prompt)
        enhanced_text = response.text.strip()

        # Remove any quotes if AI wrapped it in quotes
        if enhanced_text.startswith('"') and enhanced_text.endswith('"'):
            enhanced_text = enhanced_text[1:-1]

        # Just validate length, don't truncate - let AI handle it properly
        if not tweet_length_rules.fits_in_tweet(enhanced_text):
            print(f"Warning: AI generated tweet longer than 280 chars: {tweet_length_rules.tweet_length(enhanced_text)}")
            # Try once more with stronger emphasis
            enhancement_prompt_retry = f"""
            HATA: Ürettiğin tweet {tweet_length_rules.tweet_length(enhanced_text)} karakter, bu çok uzun!

            {persona_prompt}

            Konu: {original_text}

            MUTLAKA 280 KARAKTERDEN KISA BİR TWEET YAZ!
            Sadece tweet metnini döndür."""

            response = model.generate_content(enhancement_prompt_retry)
            enhanced_text = response.text.strip()
            if enhanced_text.startswith('"') and enhanced_text.endswith('"'):
                enhanced_text = enhanced_text[1:-1]

        return jsonify({
            "success": True,
            "enhanced": enhanced_text,
            "original": original_text
        })

    except Exception as e:
        print(f"AI Enhancement error: {e}")
        return jsonify({
            "success": False,
            "message": f"AI iyileştirme hatası: {str(e)}"
        })

@app.route('/api/trends')
@login_required
def api_trends():
    """Get current trending topics"""
    trends = get_current_trends()
    return jsonify({"trends": trends})

@app.route('/api/retry_tweet/<int:tweet_id>', methods=['POST'])
@login_required
def api_retry_tweet(tweet_id):
    """Retry failed tweet by ID"""
    try:
        # Validate table name first
        safe_table = get_safe_table_name()
        if not safe_table:
            return jsonify({"success": False, "message": "Güvenlik hatası: Geçersiz tablo adı"})
            
        conn = database.get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Veritabanı bağlantı hatası"})

        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT tweet_text FROM {safe_table} WHERE id = ? AND sent = 0", (tweet_id,))
            tweet_data = cursor.fetchone()
        finally:
            conn.close()  # Do not hold the connection during the Twitter call

        if not tweet_data:
            return jsonify({"success": False, "message": "Tweet bulunamadı veya zaten gönderilmiş"})

        # Try to post the tweet again
        status = main.scheduled_tweet(tweet_data[0])
        if not status:
            return jsonify({"success": False, "message": "Tweet tekrar gönderilemedi"})

        # Update database to mark as sent
        conn = database.get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Tweet gönderildi ancak veritabanı güncellenemedi"})
        try:
            with conn:  # Commits on success
                conn.execute(f"UPDATE {safe_table} SET sent = 1 WHERE id = ?", (tweet_id,))
        finally:
            conn.close()
        return jsonify({"success": True, "message": "Tweet başarıyla tekrar gönderildi"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Hata: {str(e)}"})

def mark_tweet_sent(safe_table, tweet_id):
    """Set sent = 1 for one tweet in its own short transaction."""
    conn = database.get_db_connection()
    if not conn:
        raise RuntimeError("Veritabanı bağlantı hatası")
    try:
        with conn:  # Commits on success
            conn.execute(f"UPDATE {safe_table} SET sent = 1 WHERE id = ?", (tweet_id,))
    finally:
        conn.close()

@app.route('/api/bulk_retry', methods=['POST'])
@login_required
def api_bulk_retry():
    """Retry all failed tweets"""
    try:
        # Get all failed tweets with validated table name
        safe_table = get_safe_table_name()
        if not safe_table:
            return jsonify({"success": False, "message": "Güvenlik hatası: Geçersiz tablo adı"})

        conn = database.get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Veritabanı bağlantı hatası"})
        try:
            failed_tweets = conn.execute(f"SELECT id, tweet_text FROM {safe_table} WHERE sent = 0").fetchall()
        finally:
            conn.close()  # Do not hold a connection while posting

        if not failed_tweets:
            return jsonify({"success": False, "message": "Tekrar gönderilecek başarısız tweet bulunamadı"})

        success_count = 0
        for tweet_id, tweet_text in failed_tweets:
            # Try to post each failed tweet
            if main.scheduled_tweet(tweet_text):
                # Mark it sent right away in a short transaction, so a later failure
                # cannot leave a posted tweet flagged for another retry
                mark_tweet_sent(safe_table, tweet_id)
                success_count += 1

            # Small delay between tweets to avoid rate limiting
            time.sleep(2)

        return jsonify({
            "success": True,
            "message": f"{success_count}/{len(failed_tweets)} tweet başarıyla gönderildi"
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Hata: {str(e)}"})

@app.route('/api/delete_tweet/<int:tweet_id>', methods=['DELETE'])
@login_required
def api_delete_tweet(tweet_id):
    """Delete tweet from database"""
    try:
        # Delete tweet from database with validated table name
        safe_table = get_safe_table_name()
        if not safe_table:
            return jsonify({"success": False, "message": "Güvenlik hatası: Geçersiz tablo adı"})

        conn = database.get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Veritabanı bağlantı hatası"})
        try:
            with conn:  # Commits on success
                deleted = conn.execute(f"DELETE FROM {safe_table} WHERE id = ?", (tweet_id,)).rowcount
        finally:
            conn.close()

        if deleted > 0:
            return jsonify({"success": True, "message": "Tweet veritabanından silindi"})
        return jsonify({"success": False, "message": "Tweet bulunamadı"})

    except Exception as e:
        return jsonify({"success": False, "message": f"Hata: {str(e)}"})

@app.route('/api/config', methods=['GET', 'PUT']) 
@login_required  # Ensure only authenticated users can access
def api_config():
    """Get or update configuration with security validation"""
    if request.method == 'GET':
        return jsonify(get_current_config())
    
    elif request.method == 'PUT':
        try:
            # SECURITY: Check request content type and size
            if not request.is_json:
                return jsonify({
                    'success': False, 
                    'error': 'Invalid content type. JSON required.'
                }), 400
            
            new_config = request.json
            
            # SECURITY: Check for empty or oversized config
            if not new_config:
                return jsonify({
                    'success': False,
                    'error': 'Empty configuration provided'
                }), 400
                
            if len(str(new_config)) > 10000:  # Limit config size
                return jsonify({
                    'success': False,
                    'error': 'Configuration data too large'
                }), 400
            
            # SECURITY: Log configuration change attempt (with sanitization)
            secure_log('info', f"Configuration change attempt by user {current_user.id} from IP {request.remote_addr}")
            secure_log('info', "Keys to update", list(new_config.keys()))
            
            # Update token.env file with new configuration
            update_token_env(new_config)
            
            # Reload environment variables for immediate effect
            reload_config()
            
            # Broadcast configuration change to all clients
            socketio.emit('config_updated', {
                'message': 'Konfigürasyon güncellendi ve otomatik olarak uygulandı!',
                'updated_keys': list(new_config.keys()),
                'auto_applied': True
            })
            
            return jsonify({
                "success": True, 
                "message": "Konfigürasyon güncellendi (tüm değerler doğrulandı)",
                "validated_keys": list(new_config.keys()),
                "timestamp": datetime.now().isoformat()
            })
            
        except ValueError as validation_error:
            # SECURITY: Log validation failures (sanitized)
            secure_log('warning', f"Configuration validation failed for user {current_user.id}", str(validation_error))
            return jsonify({
                "success": False, 
                "error": "Configuration validation failed",
                "details": str(validation_error)
            }), 400
            
        except Exception as e:
            # SECURITY: Log unexpected errors (sanitized)
            secure_log('error', f"Configuration update failed for user {current_user.id}", str(e))
            return jsonify({
                "success": False, 
                "error": "Configuration update failed", 
                "details": "Sunucu hatası"
            }), 500

@app.route('/api/emergency_stop', methods=['POST'])
@login_required
def api_emergency_stop():
    """Emergency stop - kill all bot processes immediately"""
    global bot_running, bot_thread
    
    try:
        with bot_lock:
            bot_running = False
            # Signal the bot thread; it exits at its next stop-event check
            bot_stop_event.set()
            bot_stats["bot_start_time"] = None

        # Broadcast emergency stop to all clients
        socketio.emit('emergency_stop', {
            'message': 'ACİL DURDURMA - Tüm bot işlemleri durduruldu',
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
        
        broadcast_console_log('ERROR', 'ACİL DURDURMA YAPILDI - Bot tüm işlemleri durdurdu')
        
        return jsonify({"success": True, "message": "Acil durdurma başarıyla gerçekleştirildi"})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Acil durdurma hatası: {str(e)}"})

@app.route('/api/clear_database', methods=['POST'])
@login_required
def api_clear_database():
    """Clear all tweets from database"""
    try:
        # Validate table name before touching the database
        safe_table = get_safe_table_name()
        if not safe_table:
            return jsonify({"success": False, "message": "Güvenlik hatası: Geçersiz tablo adı"})

        conn = database.get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Veritabanı bağlantı hatası"})
        try:
            with conn:  # Commits on success
                # Clear all tweets; rowcount is the number of deleted records
                record_count = conn.execute(f"DELETE FROM {safe_table}").rowcount
        finally:
            conn.close()

        broadcast_console_log('WARN', f'Veritabanı temizlendi - {record_count} kayıt silindi')

        return jsonify({
            "success": True,
            "message": f"Veritabanı temizlendi - {record_count} kayıt silindi"
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Veritabanı temizlenemedi: {str(e)}"})

@app.route('/api/force_tweet', methods=['POST'])
@login_required
def api_force_tweet():
    """Force immediate tweet generation and posting"""
    try:
        # Get a trending topic
        trends = get_current_trends()
        if trends:
            selected_trend = trends[0]  # Use first trend
            
            # Generate tweet using AI
            tweet, persona = reply.generate_reply_with_persona(selected_trend)
            
            if tweet:
                # Post immediately
                status = main.scheduled_tweet(tweet)
                
                # Save to database
                database.save_tweets(tweet=tweet, tweet_type="forced", status=status, persona=persona)
                
                # Broadcast to all clients
                broadcast_new_tweet(tweet, status)
                broadcast_console_log('SUCCESS' if status else 'ERROR', 
                                    f'Zorla tweet {"gönderildi" if status else "gönderilemedi"}: {tweet[:50]}...')
                
                return jsonify({
                    "success": status,
                    "message": "Tweet zorla gönderildi" if status else "Tweet gönderilemedi",
                    "tweet": tweet
                })
            else:
                return jsonify({"success": False, "message": "AI tweet oluşturamadı"})
        else:
            return jsonify({"success": False, "message": "Trending topic bulunamadı"})
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Zorla tweet hatası: {str(e)}"})

# Helper Functions
def timezone_offset_hours():
    """Hours between UTC and the dashboard's local time (TIMEZONE_OFFSET, default UTC+3)."""
    return get_int_config("TIMEZONE_OFFSET", 3)

def local_now():
    """Current time in the dashboard's local timezone as a naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=timezone_offset_hours())

def sqlite_tz_modifier():
    """SQLite date modifier that shifts UTC created_at values to local time."""
    return f"{timezone_offset_hours():+d} hours"

def update_stats():
    """Update bot statistics from database"""
    global bot_stats
    safe_table = get_safe_table_name()
    if not safe_table:
        return
    conn = None
    try:
        conn = database.get_db_connection()
        if conn:
            cursor = conn.cursor()

            cursor.execute(f"SELECT tweet_text, created_at FROM {safe_table} ORDER BY created_at DESC LIMIT 1")
            last_tweet = cursor.fetchone()

            if last_tweet:
                bot_stats["last_tweet"] = last_tweet[0]
                # Convert UTC to local time for display
                try:
                    utc_time = datetime.strptime(last_tweet[1], "%Y-%m-%d %H:%M:%S")
                    local_time = utc_time + timedelta(hours=timezone_offset_hours())
                    bot_stats["last_tweet_time"] = local_time.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    bot_stats["last_tweet_time"] = last_tweet[1]
            else:
                # Table is empty (for example after clearing the database)
                bot_stats["last_tweet"] = None
                bot_stats["last_tweet_time"] = None

            # Get daily and total tweets count in single optimized query.
            # created_at is UTC, so shift it to the configured local timezone first.
            today = local_now().strftime("%Y-%m-%d")
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_tweets,
                    SUM(CASE WHEN DATE(created_at, ?) = ? THEN 1 ELSE 0 END) as daily_tweets
                FROM {safe_table}
            """, (sqlite_tz_modifier(), today))
            
            stats_result = cursor.fetchone()
            bot_stats["total_tweets"] = stats_result[0]
            bot_stats["daily_tweets"] = stats_result[1] or 0  # SUM is NULL on an empty table
    except Exception as e:
        print(f"Stats update error: {e}")
    finally:
        if conn:
            conn.close()

def get_tweets_from_db(page, per_page, filter_type='all'):
    """Get paginated tweets from database with filtering"""
    try:
        conn = database.get_db_connection()
        if conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            
            # Build WHERE clause based on filter
            where_clause = ""
            params = []
            
            if filter_type == 'success':
                where_clause = "WHERE sent = 1"
            elif filter_type == 'failed':
                where_clause = "WHERE sent = 0"
            elif filter_type == 'manual':
                where_clause = "WHERE tweet_type = 'manual'"
            elif filter_type == 'auto':
                where_clause = "WHERE tweet_type = 'tweet'"
            
            # Get total count for pagination with validated table name
            safe_table = get_safe_table_name()
            if not safe_table:
                return jsonify({"success": False, "message": "Güvenlik hatası: Geçersiz tablo adı"})
                
            # Single optimized query with window function (no separate COUNT query needed)
            params.extend([per_page, offset])
            query = f"""
                SELECT 
                    id, tweet_text, tweet_type, sent, tweet_time, tweet_date, created_at,
                    COUNT(*) OVER() as total_count
                FROM {safe_table} 
                {where_clause}
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(query, params)
            tweets = cursor.fetchall()
            
            # Extract total_count from first row (window function result)
            total_count = tweets[0][7] if tweets else 0  # 8th column (0-indexed) is total_count
            
            # Remove total_count from tweet data (keep only first 7 columns)
            tweets = [tweet[:7] for tweet in tweets]
            
            cursor.close()
            conn.close()
            return tweets, total_count
    except Exception as e:
        print(f"Database error: {e}")
    return [], 0

def get_current_config():
    """Get current bot configuration - always use environment variables for latest values"""
    # Always reload environment variables to get latest values
    reload_config()  # Force reload from centralized config
    
    # URL to country code mapping (reverse of country_urls)
    url_to_country = {
        'https://xtrends.iamrohit.in/turkey': 'turkey',
        'https://xtrends.iamrohit.in/united-states': 'usa',
        'https://xtrends.iamrohit.in/united-kingdom': 'uk',
        'https://xtrends.iamrohit.in/germany': 'germany',
        'https://xtrends.iamrohit.in/france': 'france',
        'https://xtrends.iamrohit.in/italy': 'italy',
        'https://xtrends.iamrohit.in/spain': 'spain',
        'https://xtrends.iamrohit.in/netherlands': 'netherlands',
        'https://xtrends.iamrohit.in/canada': 'canada',
        'https://xtrends.iamrohit.in/australia': 'australia',
        'https://xtrends.iamrohit.in/japan': 'japan',
        'https://xtrends.iamrohit.in/south-korea': 'korea',
        'https://xtrends.iamrohit.in/india': 'india',
        'https://xtrends.iamrohit.in/brazil': 'brazil',
        'https://xtrends.iamrohit.in/mexico': 'mexico'
    }
    
    current_url = get_config("TRENDS_URL", "https://xtrends.iamrohit.in/turkey")
    trend_country = url_to_country.get(current_url, 'turkey')
    
    # Parse SLEEP_HOURS with the same rules the bot uses
    sleep_hours = get_sleep_hours()

    return {
        "trends_limit": get_int_config("TRENDS_LIMIT", 3),
        "sleep_hours": sleep_hours,
        "cycle_duration": get_int_config("CYCLE_DURATION_MINUTES", 60),
        "trend_country": trend_country,
        "ai_temperature": float(get_config("AI_TEMPERATURE", "0.85")),
        "ai_model": get_config("GEMINI_MODEL", "gemini-2.5-flash"),
        # API Credentials
        "api_key": get_config("api_key", ""),
        "api_secret": get_config("api_secret", ""),
        "access_token": get_config("access_token", ""),
        "access_token_secret": get_config("access_token_secret", ""),
        "bearer_token": get_config("bearer_token", ""),
        "user_id": get_config("USER_ID", ""),
        "gemini_api_key": get_config("gemini_api_key", "")
    }

def get_current_trends():
    """Get current trending topics"""
    if not API_MODULES_LOADED or not trend:
        return []
    try:
        # Use trend limit from configuration
        trend_limit = get_int_config('TRENDS_LIMIT', 3)
        trends = trend.prepareTrend(trend_limit)
        return trends if trends else []
    except Exception as e:
        print(f"Trends fetch error: {e}")
        return []

def mark_bot_stopped_if_current():
    """Clear bot_running only when the calling thread is the active bot thread."""
    global bot_running
    with bot_lock:
        # A stopped thread that finishes late must not flag a newer run as stopped
        if bot_thread is threading.current_thread():
            bot_running = False

def run_bot_thread(stop_event):
    """Run bot in separate thread with proper event-based termination"""
    if not API_MODULES_LOADED or not main:
        print("[ERROR] Bot modules not loaded - cannot start bot")
        mark_bot_stopped_if_current()
        return

    try:
        # Import required modules
        import time
        import random
        from config import get_int_config

        # Initialize bot modules first
        if hasattr(main, 'initialize_bot_modules'):
            if not main.initialize_bot_modules():
                print("[ERROR] Could not initialize bot modules")
                mark_bot_stopped_if_current()
                return

        while not stop_event.is_set():
            try:
                prompt = ""
                topic = ""

                # Check if it's trending time
                if main.isTrendingTime():
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Getting Trending Topics...")
                    broadcast_console_log('INFO', 'Getting trending topics...')

                    # Get trending topics
                    topic = main.trending_tweets()
                    if not topic:
                        print("[!] No trending topics found")
                        broadcast_console_log('WARNING', 'No trending topics found')
                        # Wait before retry
                        if stop_event.wait(timeout=60):
                            break
                        continue

                    # Create prompt for AI
                    prompt += f"Bunlar tweet detayları. [format- konu, tweet sayısı, tweet URL] {topic}. Tüm bu detayları tweet bilgin için kullan, referans için değil."
                    context = "Kullanıcı tarafından ek bağlam eklenmedi. Konu detaylarını kullanarak bağlamı ve amacı anlamalısın. Tweet referansı için detayları kullan."
                    prompt += " " + context
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleep hour - using general prompt")
                    broadcast_console_log('INFO', 'Sleep hour - using general prompt')
                    prompt = "En ilgi çekici ve güncel konuda bir tweet oluştur."

                # Generate AI tweet
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating Reply...Topic: {prompt[:100]}...")
                broadcast_console_log('INFO', f'Generating AI tweet for: {str(topic)[:100] if topic else "general topic"}')

                if hasattr(main, 'reply') and main.reply:
                    tweet, persona = main.reply.generate_reply_with_persona(prompt)
                else:
                    # Fallback if reply module not available
                    import reply
                    tweet, persona = reply.generate_reply_with_persona(prompt)

                # Check if tweet is None (political topic)
                if tweet is None:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Political topic detected, skipping...")
                    broadcast_console_log('WARNING', 'Political topic detected, skipping to avoid controversy')
                    # Try again with shorter wait
                    if stop_event.wait(timeout=10):
                        break
                    continue
                elif stop_event.is_set():
                    # Stop was requested while the tweet was generated; do not post it
                    break
                elif tweet:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Tweet generated: {tweet}")
                    broadcast_console_log('SUCCESS', f'Tweet generated: {tweet}')

                    # Post tweet
                    status = main.scheduled_tweet(tweet)

                    # Save to database
                    database.save_tweets(tweet=tweet, tweet_type="tweet", status=status, persona=persona)

                    if status:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Tweet posted successfully!")
                        broadcast_console_log('SUCCESS', 'Tweet posted successfully!')
                        bot_stats["last_tweet"] = tweet[:50] + "..." if len(tweet) > 50 else tweet
                        bot_stats["last_tweet_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # Emit new tweet event
                        socketio.emit('new_tweet', {
                            'tweet': tweet,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to post tweet")
                        broadcast_console_log('ERROR', 'Failed to post tweet')
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to generate tweet")
                    broadcast_console_log('ERROR', 'Failed to generate tweet')

                # Update stats
                bot_stats["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Sleep with interruptible wait; read the cycle length each time so
                # a value saved from the settings page applies to the next cycle
                cycle_minutes = main.get_cycle_duration_minutes()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleeping for {cycle_minutes} minutes...")
                broadcast_console_log('INFO', f'Next tweet in {cycle_minutes} minutes')

                if stop_event.wait(timeout=cycle_minutes * 60):
                    break  # Event was set during wait, exit loop

            except Exception as cycle_error:
                print(f"Bot cycle error: {cycle_error}")
                broadcast_console_log('ERROR', f'Bot cycle error: {str(cycle_error)}')
                # Continue running even if one cycle fails
                if stop_event.wait(timeout=60):  # Wait 1 minute before retry
                    break

    except Exception as e:
        print(f"Bot thread error: {e}")
        broadcast_console_log('ERROR', f'Bot thread error: {str(e)}')
    finally:
        mark_bot_stopped_if_current()
        print("[INFO] Bot thread terminated gracefully")
        broadcast_console_log('INFO', 'Bot stopped')

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    from flask import request
    # Reject unauthenticated sockets; broadcasts carry tweets and console logs
    if not current_user.is_authenticated:
        return False
    client_id = request.sid
    connected_clients.add(client_id)
    print(f'[+] Client {client_id} connected to real-time updates (Total: {len(connected_clients)})')
    emit('status', {'message': 'Gerçek zamanlı güncellemeler aktif'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    from flask import request
    client_id = request.sid
    connected_clients.discard(client_id)  # Remove client safely
    print(f'[-] Client {client_id} disconnected from real-time updates (Remaining: {len(connected_clients)})')

@socketio.on('request_status')
def handle_status_request():
    """Send current bot status to client"""
    update_stats()
    emit('bot_status', {
        'running': bot_running,
        'stats': bot_stats
    })

# Real-time update functions
def broadcast_bot_status():
    """Broadcast bot status to all connected clients"""
    socketio.emit('bot_status', {
        'running': bot_running,
        'stats': bot_stats
    })

def broadcast_new_tweet(tweet_text, status):
    """Broadcast new tweet to all connected clients"""
    socketio.emit('new_tweet', {
        'tweet': tweet_text,
        'status': status,
        'timestamp': datetime.now().strftime("%H:%M:%S")
    })

def broadcast_console_log(log_type, message):
    """Broadcast console log to monitoring page"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    socketio.emit('console_log', {
        'type': log_type,
        'message': message,
        'timestamp': timestamp
    })

def validate_config_value(key, value):
    """
    Validate configuration values against expected types and constraints
    Returns: (is_valid: bool, sanitized_value: str, error_message: str)
    """
    
    # Define validation rules for each configuration key
    validation_rules = {
        'trends_limit': {
            'type': int,
            'min': 1,
            'max': 50,
            'description': 'Number of trends to fetch'
        },
        'cycle_duration': {
            'type': int, 
            'min': 1,
            'max': 1440,  # Max 24 hours
            'description': 'Cycle duration in minutes'
        },
        'ai_temperature': {
            'type': float,
            'min': 0.0,
            'max': 2.0,
            'description': 'AI creativity level'
        },
        'sleep_hours': {
            'type': list,
            'element_type': int,
            'min_elements': 0,
            'max_elements': 24,
            'element_min': 0,
            'element_max': 23,
            'description': 'Hours when bot sleeps'
        },
        'trend_country': {
            'type': str,
            'allowed_values': [
                'turkey', 'usa', 'uk', 'germany', 'france', 'italy', 
                'spain', 'netherlands', 'canada', 'australia', 'japan',
                'korea', 'india', 'brazil', 'mexico'
            ],
            'description': 'Country for trending topics'
        },
        'ai_model': {
            'type': str,
            'allowed_values': [
                'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro',
                'gemini-2.0-flash-exp', 'gemini-2.5-flash', 'gemini-2.5-pro'
            ],
            'description': 'AI model to use'
        },
        'api_key': {
            'type': str,
            'min_length': 10,
            'max_length': 200,
            'pattern': r'^[A-Za-z0-9_-]+$',
            'description': 'Twitter API key'
        },
        'api_secret': {
            'type': str,
            'min_length': 10,
            'max_length': 200,
            'pattern': r'^[A-Za-z0-9_-]+$',
            'description': 'Twitter API secret'
        },
        'access_token': {
            'type': str,
            'min_length': 10,
            'max_length': 200,
            'pattern': r'^[A-Za-z0-9_-]+$',
            'description': 'Twitter access token'
        },
        'access_token_secret': {
            'type': str,
            'min_length': 10,
            'max_length': 200,
            'pattern': r'^[A-Za-z0-9_-]+$',
            'description': 'Twitter access token secret'
        },
        'bearer_token': {
            'type': str,
            'min_length': 10,
            'max_length': 500,
            'pattern': r'^[A-Za-z0-9_%-]+$',
            'description': 'Twitter bearer token'
        },
        'user_id': {
            'type': str,
            'min_length': 1,
            'max_length': 50,
            'pattern': r'^[0-9]+$',
            'description': 'Twitter user ID (numeric)'
        },
        'gemini_api_key': {
            'type': str,
            'min_length': 10,
            'max_length': 200,
            'pattern': r'^[A-Za-z0-9_-]+$',
            'description': 'Gemini API key'
        },
        'flask_secret_key': {
            'type': str,
            'min_length': 32,
            'max_length': 500,
            'description': 'Flask secret key for session security'
        }
    }
    
    # Check if key is allowed
    if key not in validation_rules:
        return False, "", f"Configuration key '{key}' is not allowed"
    
    rule = validation_rules[key]
    
    try:
        # Type validation and conversion
        if rule['type'] == int:
            if isinstance(value, str) and not value.strip():
                return False, "", f"{rule['description']} cannot be empty"
            sanitized = int(value)
            
            # Range validation
            if 'min' in rule and sanitized < rule['min']:
                return False, "", f"{rule['description']} must be >= {rule['min']}"
            if 'max' in rule and sanitized > rule['max']:
                return False, "", f"{rule['description']} must be <= {rule['max']}"
                
        elif rule['type'] == float:
            if isinstance(value, str) and not value.strip():
                return False, "", f"{rule['description']} cannot be empty"
            sanitized = float(value)
            # NaN fails every comparison below, so reject non-finite values explicitly
            if not math.isfinite(sanitized):
                return False, "", f"{rule['description']} must be a finite number"

            # Range validation
            if 'min' in rule and sanitized < rule['min']:
                return False, "", f"{rule['description']} must be >= {rule['min']}"
            if 'max' in rule and sanitized > rule['max']:
                return False, "", f"{rule['description']} must be <= {rule['max']}"
                
        elif rule['type'] == str:
            sanitized = str(value).strip()
            
            # Length validation
            if 'min_length' in rule and len(sanitized) < rule['min_length']:
                return False, "", f"{rule['description']} must be at least {rule['min_length']} characters"
            if 'max_length' in rule and len(sanitized) > rule['max_length']:
                return False, "", f"{rule['description']} must be at most {rule['max_length']} characters"
            
            # Pattern validation
            if 'pattern' in rule:
                import re
                if not re.match(rule['pattern'], sanitized):
                    return False, "", f"{rule['description']} contains invalid characters"
                    
            # Allowed values validation
            if 'allowed_values' in rule and sanitized not in rule['allowed_values']:
                return False, "", f"{rule['description']} must be one of: {', '.join(rule['allowed_values'])}"
                
        elif rule['type'] == list:
            if isinstance(value, str):
                # Handle comma-separated string
                if not value.strip():
                    sanitized = []
                else:
                    sanitized = [item.strip() for item in value.split(',') if item.strip()]
            elif isinstance(value, list):
                sanitized = value
            else:
                return False, "", f"{rule['description']} must be a list or comma-separated string"
            
            # List size validation
            if 'min_elements' in rule and len(sanitized) < rule['min_elements']:
                return False, "", f"{rule['description']} must have at least {rule['min_elements']} elements"
            if 'max_elements' in rule and len(sanitized) > rule['max_elements']:
                return False, "", f"{rule['description']} must have at most {rule['max_elements']} elements"
            
            # Element validation
            if 'element_type' in rule:
                validated_elements = []
                for element in sanitized:
                    try:
                        if rule['element_type'] == int:
                            elem = int(element)
                            if 'element_min' in rule and elem < rule['element_min']:
                                return False, "", f"{rule['description']} elements must be >= {rule['element_min']}"
                            if 'element_max' in rule and elem > rule['element_max']:
                                return False, "", f"{rule['description']} elements must be <= {rule['element_max']}"
                            validated_elements.append(elem)
                        else:
                            validated_elements.append(element)
                    except (ValueError, TypeError):
                        return False, "", f"{rule['description']} contains invalid element: {element}"
                sanitized = validated_elements

            # Lists are stored as comma-separated values (the format get_sleep_hours reads)
            sanitized = ','.join(map(str, sanitized))

        # Special validation for Flask secret key
        if key == 'flask_secret_key':
            is_strong, issues, score = validate_secret_key_strength(sanitized)
            if not is_strong and score < 3:
                return False, "", f"Flask secret key is too weak (score: {score}/7): {'; '.join(issues)}"
            elif not is_strong:
                # Log warnings but accept the key
                secure_log('warning', f"Flask secret key has issues (score: {score}/7): {'; '.join(issues)}")
        
        return True, str(sanitized), ""
        
    except (ValueError, TypeError) as e:
        return False, "", f"Invalid {rule['description']}: {str(e)}"

TOKEN_ENV_FILE = 'token.env'
token_env_lock = threading.Lock()

# Settings keys mapped to their token.env variable names
CONFIG_ENV_KEYS = {
    'sleep_hours': 'SLEEP_HOURS',
    'trends_limit': 'TRENDS_LIMIT',
    'cycle_duration': 'CYCLE_DURATION_MINUTES',
    'trend_country': 'TRENDS_URL',
    'ai_temperature': 'AI_TEMPERATURE',
    'ai_model': 'GEMINI_MODEL',
    # API Credentials
    'api_key': 'api_key',
    'api_secret': 'api_secret',
    'access_token': 'access_token',
    'access_token_secret': 'access_token_secret',
    'bearer_token': 'bearer_token',
    'user_id': 'USER_ID',
    'gemini_api_key': 'gemini_api_key',
    'flask_secret_key': 'FLASK_SECRET_KEY'
}

# Country to URL mappings
COUNTRY_TREND_URLS = {
    'turkey': 'https://xtrends.iamrohit.in/turkey',
    'usa': 'https://xtrends.iamrohit.in/united-states',
    'uk': 'https://xtrends.iamrohit.in/united-kingdom',
    'germany': 'https://xtrends.iamrohit.in/germany',
    'france': 'https://xtrends.iamrohit.in/france',
    'italy': 'https://xtrends.iamrohit.in/italy',
    'spain': 'https://xtrends.iamrohit.in/spain',
    'netherlands': 'https://xtrends.iamrohit.in/netherlands',
    'canada': 'https://xtrends.iamrohit.in/canada',
    'australia': 'https://xtrends.iamrohit.in/australia',
    'japan': 'https://xtrends.iamrohit.in/japan',
    'korea': 'https://xtrends.iamrohit.in/south-korea',
    'india': 'https://xtrends.iamrohit.in/india',
    'brazil': 'https://xtrends.iamrohit.in/brazil',
    'mexico': 'https://xtrends.iamrohit.in/mexico'
}

def token_env_line(config_key, value):
    """Build one token.env line for a validated setting."""
    if config_key == 'trend_country':
        # Convert country code to URL (already validated)
        value = COUNTRY_TREND_URLS.get(value, COUNTRY_TREND_URLS['turkey'])
    # SECURITY: Remove characters that could inject extra lines into the env file
    sanitized_value = str(value).replace('\n', '').replace('\r', '').replace('\0', '')
    return f"{CONFIG_ENV_KEYS[config_key]}={sanitized_value}\n"

def render_token_env_lines(lines, validated_config):
    """Replace existing lines for validated settings and append the ones missing from the file."""
    env_to_config = {env_key: config_key for config_key, env_key in CONFIG_ENV_KEYS.items()}
    written = set()
    updated_lines = []
    for line in lines:
        config_key = env_to_config.get(line.split('=', 1)[0]) if '=' in line else None
        if config_key in validated_config:
            updated_lines.append(token_env_line(config_key, validated_config[config_key]))
            written.add(config_key)
        else:
            updated_lines.append(line)

    missing = [key for key in validated_config if key not in written]
    if missing and updated_lines and not updated_lines[-1].endswith('\n'):
        updated_lines[-1] += '\n'
    updated_lines.extend(token_env_line(key, validated_config[key]) for key in missing)
    return updated_lines

def write_file_atomic(path, lines):
    """Write lines to a temp file and rename it over path, so a crash cannot truncate path."""
    directory = os.path.dirname(os.path.abspath(path))
    import tempfile
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix='.token.env.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            os.chmod(temp_path, os.stat(path).st_mode & 0o777)
        os.replace(temp_path, path)
    except BaseException:
        os.unlink(temp_path)
        raise

def update_token_env(new_config):
    """Update token.env file with validated configuration values"""
    try:
        # SECURITY: Validate all input values before processing
        validated_config = {}
        validation_errors = []
        
        for key, value in new_config.items():
            is_valid, sanitized_value, error_msg = validate_config_value(key, value)
            if not is_valid:
                validation_errors.append(f"{key}: {error_msg}")
                secure_log('warning', f"Validation failed for {key}", error_msg)
            else:
                validated_config[key] = sanitized_value
                secure_log('debug', f"Validated {key}", sanitized_value)
        
        # If there are validation errors, reject the entire update
        if validation_errors:
            error_summary = "; ".join(validation_errors)
            raise ValueError(f"Configuration validation failed: {error_summary}")
        
        secure_log('info', f"All {len(validated_config)} configuration values validated successfully")

        # Serialize read-modify-write so concurrent saves cannot drop each other's changes
        with token_env_lock:
            with open(TOKEN_ENV_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            updated_lines = render_token_env_lines(lines, validated_config)

            # SECURITY: Create backup before modifying file
            try:
                with open(TOKEN_ENV_FILE + '.backup', 'w', encoding='utf-8') as backup:
                    backup.writelines(lines)
            except OSError as backup_error:
                print(f"[WARNING] Could not create backup: {backup_error}")

            write_file_atomic(TOKEN_ENV_FILE, updated_lines)

        # Log security event (sanitized)
        secure_log('info', f"Configuration updated in token.env with {len(validated_config)} validated values")
        secure_log('info', "Updated keys", list(validated_config.keys()))
        
        # Force reload of centralized configuration
        reload_config()
        
    except Exception as e:
        secure_log('error', "Error updating token.env", str(e))
        raise

# Analytics API endpoints
@app.route('/api/analytics/success_rate')
@login_required
def api_analytics_success_rate():
    """Get tweet success rate data for charts"""
    try:
        analytics_memory_cleanup()  # Periodic memory cleanup
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()
        
        # Get success rate data by day for last 30 days
        cursor.execute(f"""
            SELECT
                DATE(created_at, :tz) as date,
                COUNT(*) as total_tweets,
                SUM(CASE WHEN sent = 1 THEN 1 ELSE 0 END) as successful_tweets,
                ROUND(
                    (SUM(CASE WHEN sent = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2
                ) as success_rate
            FROM {tweets_table()}
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at, :tz)
            ORDER BY date DESC
        """, {"tz": sqlite_tz_modifier()})
        
        results = cursor.fetchall()
        conn.close()
        
        # Format data for Chart.js
        data = {
            'labels': [row[0] for row in reversed(results)],
            'datasets': [{
                'label': 'Başarı Oranı (%)',
                'data': [row[3] for row in reversed(results)],
                'backgroundColor': 'rgba(29, 161, 242, 0.2)',
                'borderColor': 'rgba(29, 161, 242, 1)',
                'borderWidth': 2,
                'fill': True
            }]
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'total_days': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Analytics error: {str(e)}'
        }), 500

@app.route('/api/analytics/personas')
@login_required
def api_analytics_personas():
    """Get persona usage statistics"""
    try:
        analytics_memory_cleanup()  # Periodic memory cleanup
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()
        
        # Get persona usage counts; the percentage uses the same 30-day window as the counts
        cursor.execute(f"""
            SELECT
                persona,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM {tweets_table()}
            WHERE created_at >= datetime('now', '-30 days')
            AND persona IS NOT NULL
            GROUP BY persona
            ORDER BY count DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # Persona display names
        persona_names = {
            'tech': 'Teknik',
            'casual': 'Gündelik',
            'sad': 'Üzgün',
            'default': 'Varsayılan'
        }
        
        # Format data for Chart.js pie chart
        data = {
            'labels': [persona_names.get(row[0], row[0]) for row in results],
            'datasets': [{
                'data': [row[1] for row in results],
                'backgroundColor': [
                    'rgba(29, 161, 242, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)',
                    'rgba(108, 117, 125, 0.8)'
                ],
                'borderColor': [
                    'rgba(29, 161, 242, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)',
                    'rgba(108, 117, 125, 1)'
                ],
                'borderWidth': 1
            }]
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'statistics': [
                {
                    'persona': persona_names.get(row[0], row[0]),
                    'count': row[1],
                    'percentage': row[2]
                } for row in results
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Analytics error: {str(e)}'
        }), 500

@app.route('/api/analytics/hourly_activity')
@login_required
def api_analytics_hourly_activity():
    """Get hourly posting activity data"""
    try:
        analytics_memory_cleanup()  # Periodic memory cleanup
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()
        
        # Get tweet counts by local hour for last 7 days (created_at is UTC)
        cursor.execute(f"""
            SELECT
                CAST(strftime('%H', created_at, ?) AS INTEGER) as hour,
                COUNT(*) as tweet_count
            FROM {tweets_table()}
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY hour
            ORDER BY hour
        """, (sqlite_tz_modifier(),))
        
        results = cursor.fetchall()
        conn.close()
        
        # Create 24-hour data array (0-23)
        hourly_data = [0] * 24
        for hour, count in results:
            hourly_data[hour] = count
        
        # Scale colors by the busiest hour; use 1 when there are no tweets to avoid dividing by zero
        max_count = max(hourly_data) or 1

        # Format data for Chart.js heatmap/bar chart
        data = {
            'labels': [f"{i:02d}:00" for i in range(24)],
            'datasets': [{
                'label': 'Tweet Sayısı',
                'data': hourly_data,
                'backgroundColor': [
                    f'rgba(29, 161, 242, {min(0.1 + (count / max_count) * 0.9, 1)})'
                    for count in hourly_data
                ],
                'borderColor': 'rgba(29, 161, 242, 1)',
                'borderWidth': 1
            }]
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'peak_hour': hourly_data.index(max(hourly_data)) if hourly_data else 0,
            'total_tweets': sum(hourly_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Analytics error: {str(e)}'
        }), 500

@app.route('/api/analytics/trending_topics')
@login_required
def api_analytics_trending_topics():
    """Get popular trending topics data with memory leak protection"""
    try:
        # Call periodic memory cleanup
        analytics_memory_cleanup()
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()
        
        # Get recent sent tweets; word frequencies are counted below. (An aggregate
        # without GROUP BY returned a single arbitrary row.)
        cursor.execute(f"""
            SELECT tweet_text
            FROM {tweets_table()}
            WHERE created_at >= datetime('now', '-30 days')
            AND sent = 1
            ORDER BY created_at DESC
            LIMIT 500
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # Simple word extraction with memory leak protection
        word_frequency = {}
        max_unique_words = 1000  # Limit to prevent unbounded memory growth
        
        for (content,) in results:
            if content and len(word_frequency) < max_unique_words:
                # Basic word extraction
                words = content.lower().split()
                for word in words:
                    # Clean word (remove punctuation)
                    import re
                    clean_word = re.sub(r'[^\w\sğüşıöçĞÜŞİÖÇ]', '', word)
                    if len(clean_word) > 3 and not clean_word.startswith('http'):
                        word_frequency[clean_word] = word_frequency.get(clean_word, 0) + 1
                        
                        # Additional protection: stop if dictionary gets too large
                        if len(word_frequency) >= max_unique_words:
                            print(f"[WARNING] Word frequency dictionary reached limit ({max_unique_words} words)")
                            break
        
        # Get top 15 words and clear large dictionary immediately
        sorted_words = sorted(word_frequency.items(), key=lambda x: x[1], reverse=True)[:15]
        word_frequency.clear()  # Explicit cleanup to prevent memory retention
        
        # Format for word cloud visualization
        data = {
            'labels': [word for word, freq in sorted_words],
            'datasets': [{
                'label': 'Kullanım Sıklığı',
                'data': [freq for word, freq in sorted_words],
                'backgroundColor': [
                    f'rgba({29 + i*10}, {161 - i*5}, {242 - i*8}, 0.7)' 
                    for i in range(len(sorted_words))
                ],
                'borderColor': 'rgba(29, 161, 242, 1)',
                'borderWidth': 1
            }]
        }
        
        # Memory cleanup and monitoring
        gc.collect()  # Force garbage collection to free memory
        
        return jsonify({
            'success': True,
            'data': data,
            'word_cloud_data': [
                {'text': word, 'size': freq} 
                for word, freq in sorted_words
            ],
            'memory_stats': {
                'words_processed': len(sorted_words),
                'memory_cleaned': True
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Analytics error: {str(e)}'
        }), 500

# Data Export/Import API endpoints
@app.route('/api/export/database', methods=['GET'])
@login_required
def api_export_database():
    """Export complete database to JSON"""
    try:
        table = tweets_table()
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()

        # Export tweets table
        cursor.execute(f"SELECT * FROM {table}")
        tweets = cursor.fetchall()

        # Get column names
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        conn.close()
        
        # Convert to list of dictionaries
        tweets_data = []
        for tweet in tweets:
            tweet_dict = dict(zip(columns, tweet))
            tweets_data.append(tweet_dict)
        
        # Create export data structure
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'total_tweets': len(tweets_data)
            },
            'tweets': tweets_data,
            'configuration': {
                'database_file': database.dbName,
                'table_name': table
            }
        }
        
        return jsonify({
            'success': True,
            'data': export_data,
            'filename': f"twitter_bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Export error: {str(e)}'
        }), 500

def import_tweet_rows(conn, tweets):
    """
    Insert backup rows that are not already present.

    IDs from another database say nothing about local rows, so duplicates are
    detected by (tweet_text, created_at) instead.

    Returns:
        tuple: (imported_count, skipped_count)
    """
    table = tweets_table()
    existing = set(conn.execute(f"SELECT tweet_text, created_at FROM {table}").fetchall())
    # Match the UTC "YYYY-MM-DD HH:MM:SS" format SQLite's CURRENT_TIMESTAMP produces
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    imported_count = 0
    skipped_count = 0
    for tweet_data in tweets:
        text = tweet_data.get('tweet_text', tweet_data.get('content', ''))
        created_at = tweet_data.get('created_at') or now_utc
        if (text, created_at) in existing:
            skipped_count += 1
            continue
        sent = tweet_data.get('sent', tweet_data.get('status'))
        conn.execute(f"""
            INSERT INTO {table} (tweet_text, tweet_type, sent, created_at, persona)
            VALUES (?, ?, ?, ?, ?)
        """, (
            text,
            tweet_data.get('tweet_type', 'imported'),
            1 if sent in (1, True, 'success') else 0,
            created_at,
            tweet_data.get('persona')
        ))
        existing.add((text, created_at))
        imported_count += 1
    return imported_count, skipped_count

def csv_safe_cell(value):
    """Prefix cells that spreadsheets would run as formulas (CSV injection)."""
    text = '' if value is None else str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text

@app.route('/api/export/tweets', methods=['GET'])
@login_required
def api_export_tweets():
    """Export tweet history as a CSV download"""
    import csv
    import io
    from flask import Response

    columns = ['id', 'tweet_text', 'tweet_type', 'sent', 'persona', 'tweet_date', 'tweet_time', 'created_at']
    conn = sqlite3.connect(database.dbName)
    try:
        rows = conn.execute(f"SELECT {', '.join(columns)} FROM {tweets_table()} ORDER BY created_at DESC").fetchall()
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    writer.writerows([csv_safe_cell(value) for value in row] for row in rows)

    filename = f"tweets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    # UTF-8 BOM so spreadsheet apps show Turkish characters correctly
    return Response('﻿' + output.getvalue(), content_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@app.route('/api/import/database', methods=['POST'])
@login_required
def api_import_database():
    """Import database from JSON backup"""
    try:
        import_data = request.get_json(silent=True)
        
        if not import_data or 'tweets' not in import_data:
            return jsonify({
                'success': False,
                'message': 'Geçersiz import verisi'
            }), 400
        
        conn = sqlite3.connect(database.dbName)
        try:
            with conn:  # Commit all rows together, roll back on error
                imported_count, skipped_count = import_tweet_rows(conn, import_data['tweets'])
        finally:
            conn.close()

        return jsonify({
            'success': True,
            'message': f'Import tamamlandı: {imported_count} tweet eklendi, {skipped_count} tweet atlandı',
            'imported': imported_count,
            'skipped': skipped_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Import error: {str(e)}'
        }), 500

# API Status Check Endpoint
@app.route('/api/check_status')
@login_required
def api_check_status():
    """Check real-time status of all APIs"""
    try:
        import check_api_status
        status = check_api_status.get_all_api_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Prompt Management API endpoints
@app.route('/api/prompts', methods=['GET'])
@login_required
def api_get_prompts():
    """Get all AI persona prompts"""
    try:
        prompts = database.get_all_prompts()
        prompt_list = []
        for prompt in prompts:
            prompt_list.append({
                'id': prompt[0],
                'prompt_type': prompt[1],
                'prompt_text': prompt[2],
                'description': prompt[3],
                'is_active': bool(prompt[4]),
                'updated_at': prompt[5]
            })
        
        return jsonify({
            'success': True,
            'prompts': prompt_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Prompts retrieval error: {str(e)}'
        }), 500

@app.route('/api/prompts/<prompt_type>', methods=['PUT'])
@login_required
def api_update_prompt(prompt_type):
    """Update a specific prompt"""
    try:
        data = request.get_json(silent=True) or {}
        prompt_text = sanitize_input(data.get('prompt_text'))
        description = sanitize_input(data.get('description', ''))
        
        if not prompt_text:
            return jsonify({
                'success': False,
                'message': 'Prompt metni gerekli'
            }), 400

        template_error = database.validate_prompt_template(prompt_text, database.get_persona_settings().keys())
        if template_error:
            return jsonify({
                'success': False,
                'message': template_error
            }), 400

        success = database.update_prompt(prompt_type, prompt_text, description)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{prompt_type} prompt güncellendi'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Prompt güncelleme başarısız'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Prompt update error: {str(e)}'
        }), 500

@app.route('/api/prompts/<prompt_type>/toggle', methods=['POST'])
@login_required
def api_toggle_prompt(prompt_type):
    """Toggle prompt active status"""
    try:
        success = database.toggle_prompt_status(prompt_type)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{prompt_type} prompt durumu değiştirildi'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Prompt durumu değiştirilemedi'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Toggle error: {str(e)}'
        }), 500

@app.route('/api/prompts/<prompt_type>/active', methods=['PUT'])
@login_required
def api_set_prompt_active(prompt_type):
    """Set prompt active status to an explicit value"""
    data = request.get_json(silent=True) or {}
    is_active = data.get('active')
    if not isinstance(is_active, bool):
        return jsonify({
            'success': False,
            'message': "'active' alanı true veya false olmalı"
        }), 400

    if database.set_prompt_active(prompt_type, is_active):
        return jsonify({
            'success': True,
            'message': f'{prompt_type} prompt durumu güncellendi'
        })
    return jsonify({
        'success': False,
        'message': 'Prompt durumu güncellenemedi'
    }), 404

@app.route('/api/persona-settings', methods=['GET'])
@login_required
def api_get_persona_settings():
    """Get all persona settings"""
    try:
        settings = database.get_persona_settings()
        
        # Format settings for frontend
        formatted_settings = []
        setting_descriptions = {
            'persona_name': 'Persona karakterinin ismi',
            'persona_age': 'Persona karakterinin yaşı',
            'persona_location': 'Yaşadığı şehir',
            'persona_personality': 'Temel kişilik özellikleri',
            'persona_language': 'Temel tweet dili',
            'max_tweet_length': 'Maksimum tweet karakter sayısı',
            'interaction_style': 'Etkileşim tarzı'
        }
        
        # Turkish display names
        display_names = {
            'persona_name': 'İsim',
            'persona_age': 'Yaş', 
            'persona_location': 'Konum',
            'persona_personality': 'Kişilik',
            'persona_language': 'Dil',
            'max_tweet_length': 'Maksimum Tweet Uzunluğu',
            'interaction_style': 'Etkileşim Tarzı'
        }
        
        for key, value in settings.items():
            formatted_settings.append({
                'setting_key': key,
                'setting_value': value,
                'description': setting_descriptions.get(key, ''),
                'display_name': display_names.get(key, key.replace('persona_', '').replace('_', ' ').title())
            })
        
        return jsonify({
            'success': True,
            'settings': formatted_settings
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Settings retrieval error: {str(e)}'
        }), 500

@app.route('/api/persona-settings/<setting_key>', methods=['PUT'])
@login_required
def api_update_persona_setting(setting_key):
    """Update a specific persona setting"""
    try:
        data = request.get_json(silent=True) or {}
        setting_value = sanitize_input(data.get('setting_value'))
        
        if not setting_value:
            return jsonify({
                'success': False,
                'message': 'Ayar değeri gerekli'
            }), 400
        
        success = database.update_persona_setting(setting_key, setting_value)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{setting_key} ayarı güncellendi'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ayar güncelleme başarısız'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Setting update error: {str(e)}'
        }), 500

@app.route('/api/realtime_stats')
@login_required
def get_realtime_stats():
    """Get real-time statistics for monitoring page"""
    try:
        import sqlite3
        from datetime import datetime, timedelta

        stats = {}
        table = tweets_table()

        # Get success rate from database
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()

        # Calculate success rate from last 100 tweets
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN sent = 1 THEN 1 ELSE 0 END) as successful
            FROM (
                SELECT sent FROM {table}
                ORDER BY created_at DESC
                LIMIT 100
            )
        """)
        result = cursor.fetchone()
        if result and result[0] > 0:
            stats['success_rate'] = round((result[1] / result[0]) * 100, 1)
        else:
            stats['success_rate'] = 100.0

        # Count API calls today in the configured local timezone (created_at is UTC
        # text "YYYY-MM-DD HH:MM:SS", so compare dates, not ISO strings with a "T")
        cursor.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE DATE(created_at, ?) = ?
        """, (sqlite_tz_modifier(), local_now().strftime("%Y-%m-%d")))
        stats['api_calls'] = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Calculate bot uptime (bot_start_time is server local time from datetime.now())
        start_time_text = bot_stats.get("bot_start_time")
        is_running = bot_running and bool(start_time_text)
        if is_running:
            start_time = datetime.strptime(start_time_text, "%Y-%m-%d %H:%M:%S")
            uptime_seconds = int((datetime.now() - start_time).total_seconds())
            stats['bot_uptime'] = uptime_seconds
        else:
            stats['bot_uptime'] = 0

        # Calculate next tweet time
        if is_running:
            cycle_minutes = get_int_config("CYCLE_DURATION_MINUTES", 60)

            # Find last tweet time
            conn = sqlite3.connect(database.dbName)
            cursor = conn.cursor()
            cursor.execute(f"SELECT created_at FROM {table} WHERE sent = 1 ORDER BY created_at DESC LIMIT 1")
            last_tweet = cursor.fetchone()
            cursor.close()
            conn.close()

            if last_tweet:
                # created_at is UTC, so compare it with the current UTC time
                last_tweet_time = datetime.fromisoformat(last_tweet[0].replace(' ', 'T'))
                next_run = last_tweet_time + timedelta(minutes=cycle_minutes)
                utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
                time_remaining = (next_run - utc_now).total_seconds()

                if time_remaining > 0:
                    minutes = int(time_remaining // 60)
                    seconds = int(time_remaining % 60)
                    stats['next_tweet_time'] = f"{minutes:02d}:{seconds:02d}"
                else:
                    stats['next_tweet_time'] = "Yakında"
            else:
                stats['next_tweet_time'] = "Bekleniyor"
        else:
            stats['next_tweet_time'] = "--:--"

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'stats': {
                'success_rate': 100.0,
                'api_calls': 0,
                'next_tweet_time': '--:--',
                'bot_uptime': 0
            }
        })

@app.route('/api/activity', methods=['GET'])
@login_required
def get_recent_activity():
    """Get recent bot activity logs"""
    try:
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()
        
        # Get last 5 tweets with their details
        cursor.execute(f"""
            SELECT tweet_text, tweet_type, sent, created_at, tweet_time
            FROM {tweets_table()}
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        tweets = cursor.fetchall()
        conn.close()
        
        activities = []
        
        if tweets:
            for tweet in tweets:
                text, tweet_type, success, created_at, time = tweet
                
                # Generate activity entry based on tweet data
                if success:
                    activity = {
                        'time': time or created_at,
                        'icon': 'fas fa-paper-plane',
                        'message': f'Tweet gönderildi: "{text[:50]}{"..." if len(text) > 50 else ""}"',
                        'type': 'success'
                    }
                else:
                    activity = {
                        'time': time or created_at,
                        'icon': 'fas fa-exclamation-triangle',
                        'message': f'Tweet gönderilemeđi: "{text[:50]}{"..." if len(text) > 50 else ""}"',
                        'type': 'error'
                    }
                
                activities.append(activity)
        
        # Add some simulated bot activities if no tweets
        if not activities:
            from datetime import datetime
            current_time = datetime.now().strftime('%H:%M')
            activities = [
                {
                    'time': current_time,
                    'icon': 'fas fa-robot',
                    'message': 'Bot izleme sistemi aktif',
                    'type': 'info'
                },
                {
                    'time': '14:30',
                    'icon': 'fas fa-chart-line',
                    'message': 'Sistem durumu kontrol edildi',
                    'type': 'info'
                }
            ]
        
        return jsonify({
            'success': True,
            'activities': activities[:5]  # Max 5 activity
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Aktivite verileri alınamadı: {str(e)}'
        }), 500

@app.route('/api/database/stats', methods=['GET'])
@login_required
def get_database_stats():
    """Get database file size and record count"""
    try:
        import os
        
        # Get database file size
        db_path = database.dbName
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            
            # Format size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = "0 KB"
        
        # Get total tweet count
        conn = sqlite3.connect(database.dbName)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {tweets_table()}")
        total_tweets = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'success': True,
            'size': size_str,
            'total_tweets': f"{total_tweets:,}".replace(',', '.')  # Turkish number format
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Database stats error: {str(e)}'
        }), 500

# Error handlers
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF token errors"""
    return jsonify({
        'success': False,
        'message': 'CSRF token hatası. Sayfayı yenileyip tekrar deneyin.',
        'error_type': 'csrf_error'
    }), 400

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Sayfa bulunamadı"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Sunucu hatası"), 500

# Input validation utilities
def calculate_twitter_length(text):
    """
    Calculate the actual length of a tweet accounting for Twitter's URL shortening.
    
    Twitter automatically shortens URLs to t.co links:
    - HTTP URLs: 23 characters
    - HTTPS URLs: 23 characters  
    - Media URLs: 23 characters (additional)
    
    Returns:
        int: Calculated tweet length according to Twitter's counting rules
    """
    import re

    # Find all URLs in the text
    urls = tweet_length_rules.URL_PATTERN.findall(text)

    # Find mentions and hashtags for reporting
    mentions = re.findall(r'@\w+', text)
    hashtags = re.findall(r'#\w+', text)

    return {
        # Weighted count: emoji and CJK count as 2, each URL as a 23-character t.co link
        'length': tweet_length_rules.tweet_length(text),
        'url_count': len(urls),
        'mention_count': len(mentions),
        'hashtag_count': len(hashtags),
        'urls': urls,
        'mentions': mentions,
        'hashtags': hashtags
    }

def validate_tweet_text(text):
    """Validate tweet text input with proper Twitter length calculation"""
    if not text or not text.strip():
        return False, "Tweet metni boş olamaz"
    
    # Use Twitter's actual character counting rules
    twitter_metrics = calculate_twitter_length(text)
    twitter_length = twitter_metrics['length']
    
    if twitter_length > 280:
        return False, f"Tweet {twitter_length} karakter (280 limit, URL'ler t.co olarak sayılır)"
    
    # Check for extremely long tweets (probably an error)
    if len(text) > 2000:
        return False, "Tweet çok uzun (muhtemelen hata)"

    # Create detailed validation message
    message = f"Geçerli ({twitter_length}/280 karakter)"
    if twitter_metrics['url_count'] > 0:
        message += f", {twitter_metrics['url_count']} URL"
    if twitter_metrics['mention_count'] > 0:
        message += f", {twitter_metrics['mention_count']} mention"
    if twitter_metrics['hashtag_count'] > 0:
        message += f", {twitter_metrics['hashtag_count']} hashtag"
    
    return True, message

def test_twitter_length_calculation():
    """Test Twitter length calculation with various content types"""
    test_cases = [
        ("Hello world!", 12),
        ("Check this out: https://example.com/very-long-url-that-will-be-shortened", 23 + 17),  # URL shortened to 23
        ("@username how are you?", 20),  # Mention counts as full
        ("#hashtag #trending now", 19),  # Hashtags count as full  
        ("Visit https://example.com and https://test.com", 23 + 5 + 23),  # Two URLs
        ("Hello @user1 @user2 #tech https://example.com", len("Hello @user1 @user2 #tech ") + 23),
    ]
    
    print("[INFO] Testing Twitter length calculation:")
    for text, expected in test_cases:
        result = calculate_twitter_length(text)
        actual = result['length']
        status = "✓" if actual == expected else "✗"
        print(f"  {status} '{text}' -> {actual} chars (expected: {expected})")
        if result['url_count'] > 0:
            print(f"    URLs: {result['urls']}")
        if result['mention_count'] > 0:
            print(f"    Mentions: {result['mentions']}")
        if result['hashtag_count'] > 0:
            print(f"    Hashtags: {result['hashtags']}")
    
    return True

def sanitize_input(text):
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove HTML tags and scripts; repeat until stable so nested payloads
    # such as "jajavascript:vascript:" cannot reassemble after one pass
    import re
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'data:', '', text, flags=re.IGNORECASE)

    return text.strip()

if __name__ == '__main__':
    print(f"Starting AI-TwitterPersona Web Dashboard...")
    print(f"Dashboard will be available at: http://{WEB_HOST}:{WEB_PORT}")
    print(f"Real-time updates enabled via WebSocket")
    
    # Run Flask-SocketIO development server
    socketio.run(app, host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG)