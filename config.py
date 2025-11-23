"""
Centralized configuration management for AI-TwitterPersona
Loads environment variables once and provides cached access
"""

import os
import threading
import time
from dotenv import load_dotenv

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
                    self._load_config()
                    self._initialized = True
    
    def _load_config(self):
        """Load environment variables from token.env"""
        try:
            # Use override=True to force reload of changed values
            load_dotenv("token.env", override=True)
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
        value = self.get(key, '').lower()
        return value in ('true', '1', 'yes', 'on')
    
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