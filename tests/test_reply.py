import sys
from unittest.mock import MagicMock

# Mocking external modules that are not installed in the test environment.
# This is necessary because the environment lacks many project dependencies
# and we are only testing the safe_float_config function in reply.py.
# sys.modules hacks are used here to avoid ModuleNotFoundError during import.
mock_modules = [
    'google',
    'google.generativeai',
    'google.api_core',
    'google.api_core.exceptions',
    'database',
    'dotenv',
    'requests',
    'flask',
    'flask_socketio',
    'flask_login',
    'flask_wtf',
    'bcrypt',
    'eventlet',
    'tweepy',
    'bs4'
]

for module_name in mock_modules:
    sys.modules[module_name] = MagicMock()

import pytest
from unittest.mock import patch
import os

# Import the function to be tested
from reply import safe_float_config

def test_safe_float_config_valid(capsys):
    """Test safe_float_config with a valid float within range."""
    with patch('reply.get_float_config') as mock_get_float:
        mock_get_float.return_value = 1.5
        result = safe_float_config("AI_TEMPERATURE", 1.0, 0.0, 2.0)
        assert result == 1.5
        out, err = capsys.readouterr()
        assert out == ""

def test_safe_float_config_below_min(capsys):
    """Test safe_float_config with a value below the minimum."""
    with patch('reply.get_float_config') as mock_get_float:
        mock_get_float.return_value = -1.0
        result = safe_float_config("AI_TEMPERATURE", 1.0, 0.0, 2.0)
        assert result == 0.0
        out, err = capsys.readouterr()
        assert "[WARNING] AI_TEMPERATURE=-1.0 is below minimum 0.0, using 0.0" in out

def test_safe_float_config_above_max(capsys):
    """Test safe_float_config with a value above the maximum."""
    with patch('reply.get_float_config') as mock_get_float:
        mock_get_float.return_value = 3.0
        result = safe_float_config("AI_TEMPERATURE", 1.0, 0.0, 2.0)
        assert result == 2.0
        out, err = capsys.readouterr()
        assert "[WARNING] AI_TEMPERATURE=3.0 is above maximum 2.0, using 2.0" in out

def test_safe_float_config_at_min(capsys):
    """Test safe_float_config with a value exactly at the minimum."""
    with patch('reply.get_float_config') as mock_get_float:
        mock_get_float.return_value = 0.0
        result = safe_float_config("AI_TEMPERATURE", 1.0, 0.0, 2.0)
        assert result == 0.0
        out, err = capsys.readouterr()
        assert out == ""

def test_safe_float_config_at_max(capsys):
    """Test safe_float_config with a value exactly at the maximum."""
    with patch('reply.get_float_config') as mock_get_float:
        mock_get_float.return_value = 2.0
        result = safe_float_config("AI_TEMPERATURE", 1.0, 0.0, 2.0)
        assert result == 2.0
        out, err = capsys.readouterr()
        assert out == ""

def test_safe_float_config_no_min_max(capsys):
    """Test safe_float_config when no min/max are provided."""
    with patch('reply.get_float_config') as mock_get_float:
        mock_get_float.return_value = 100.0
        result = safe_float_config("AI_TEMPERATURE", 1.0)
        assert result == 100.0
        out, err = capsys.readouterr()
        assert out == ""

def test_safe_float_config_value_error(capsys):
    """Test safe_float_config handling of ValueError from get_float_config."""
    with patch('reply.get_float_config') as mock_get_float, \
         patch('os.getenv') as mock_getenv:
        mock_get_float.side_effect = ValueError("Invalid float")
        mock_getenv.return_value = "invalid_string"
        result = safe_float_config("AI_TEMPERATURE", 1.0)
        assert result == 1.0
        out, err = capsys.readouterr()
        assert "[ERROR] Invalid AI_TEMPERATURE value 'invalid_string': Invalid float. Using default: 1.0" in out

def test_safe_float_config_type_error(capsys):
    """Test safe_float_config handling of TypeError from get_float_config."""
    with patch('reply.get_float_config') as mock_get_float, \
         patch('os.getenv') as mock_getenv:
        mock_get_float.side_effect = TypeError("Type error")
        mock_getenv.return_value = None
        result = safe_float_config("AI_TEMPERATURE", 1.0)
        assert result == 1.0
        out, err = capsys.readouterr()
        assert "[ERROR] Invalid AI_TEMPERATURE value 'None': Type error. Using default: 1.0" in out
