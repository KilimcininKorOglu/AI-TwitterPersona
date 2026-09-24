"""
Centralized configuration management for AI-TwitterPersona
Loads environment variables once and provides cached access
"""

import os
import threading
import time
from dotenv import dotenv_values

class ConfigManager:
    """Thread-safe centralized configuration manager"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global config access"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager once"""
        if not getattr(self, '_initialized', False):
            with self._lock:
                if not self._initialized:
                    self._config_cache = {}
                    self._last_reload = 0
                    self._reload_interval = 300  # 5 minutes
                    # Variables set by the process environment (Docker, systemd) take
                    # precedence over token.env and are never overwritten by reloads
                    self._process_env_keys = set(os.environ)
                    self._load_config()
                    self._initialized = True

    def _load_config(self):
        """Load environment variables from token.env"""
        try:
            # Apply every token.env value on each reload so dashboard edits take effect,
            # except keys the process environment already defined
            for key, value in dotenv_values("token.env").items():
                if value is not None and key not in self._process_env_keys:
                    os.environ[key] = value
            self._last_reload = time.time()
            print("[CONFIG] Environment variables reloaded successfully")
        except Exception as e:
            print(f"[CONFIG ERROR] Failed to load environment: {e}")
    
    def get(self, key, default=None, force_reload=False):
        """Get configuration value with optional caching"""
        current_time = time.time()
        
        # Check if reload is needed
        if force_reload or (current_time - self._last_reload > self._reload_interval):
            with self._lock:
                if force_reload or (current_time - self._last_reload > self._reload_interval):
                    self._load_config()
        
        return os.getenv(key, default)
    
    def get_int(self, key, default=0):
        """Get integer configuration value with error handling"""
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key, default=0.0):
        """Get float configuration value with error handling"""
        try:
            return float(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key, default=False):
        """Get boolean configuration value"""
        value = self.get(key)
        if value is None or not value.strip():
            return default
        return value.strip().lower() in ('true', '1', 'yes', 'on')
    
    def get_list(self, key, default=None, separator=','):
        """Get list configuration value by splitting string"""
        if default is None:
            default = []
        value = self.get(key, '')
        if not value:
            return default
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def reload(self):
        """Force reload configuration from file"""
        return self.get('dummy', force_reload=True)
    
    def is_loaded(self):
        """Check if configuration has been loaded"""
        return self._last_reload > 0

# Global singleton instance
config = ConfigManager()

# Convenience functions for backward compatibility
def get_config(key, default=None):
    """Get configuration value"""
    return config.get(key, default)

def get_int_config(key, default=0):
    """Get integer configuration value"""
    return config.get_int(key, default)

def get_float_config(key, default=0.0):
    """Get float configuration value"""
    return config.get_float(key, default)

def get_bool_config(key, default=False):
    """Get boolean configuration value"""
    return config.get_bool(key, default)

def get_list_config(key, default=None, separator=','):
    """Get list configuration value"""
    return config.get_list(key, default, separator)

def reload_config():
    """Force reload configuration"""
    return config.reload()

DEFAULT_SLEEP_HOURS = [1, 3, 9, 10]

def get_sleep_hours():
    """
    Parse SLEEP_HOURS into a list of hours (0-23).

    Accepts "1,3,9" and the legacy bracketed "[1, 3, 9]" format. An unset key
    returns the default hours; an explicitly empty value means no sleep hours.
    Invalid or out-of-range values fall back to the default hours.
    """
    raw = config.get("SLEEP_HOURS")
    if raw is None:
        return list(DEFAULT_SLEEP_HOURS)
    raw = raw.strip().strip('[]').strip()
    if not raw:
        return []
    try:
        hours = [int(item.strip()) for item in raw.split(',') if item.strip()]
    except ValueError:
        print(f"[!] Warning: Invalid SLEEP_HOURS format '{raw}', using default: {DEFAULT_SLEEP_HOURS}")
        return list(DEFAULT_SLEEP_HOURS)
    if any(not 0 <= hour <= 23 for hour in hours):
        print(f"[!] Warning: SLEEP_HOURS values must be 0-23, using default: {DEFAULT_SLEEP_HOURS}")
        return list(DEFAULT_SLEEP_HOURS)
    return hours