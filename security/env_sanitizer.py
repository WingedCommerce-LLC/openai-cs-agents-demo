"""
Environment variable sanitization to prevent credential leakage.

This module ensures no credentials leak through environment variables, 
logs, or error messages by automatically detecting and masking sensitive data.
"""

import re
from typing import Dict, List, Set

class EnvironmentSanitizer:
    """Ensures no credentials leak through environment variables, logs, or error messages."""
    
    SENSITIVE_PATTERNS = [
        r'api[_-]?key',
        r'secret[_-]?key',
        r'password',
        r'token',
        r'credential',
        r'auth[_-]?token',
        r'bearer[_-]?token',
        r'access[_-]?token',
        r'refresh[_-]?token',
        r'private[_-]?key',
        r'cert[_-]?key',
        r'database[_-]?url',
        r'connection[_-]?string'
    ]
    
    def __init__(self):
        self.sensitive_keys = self._compile_patterns()
    
    def _compile_patterns(self) -> List[re.Pattern]:
        return [re.compile(pattern, re.IGNORECASE) for pattern in self.SENSITIVE_PATTERNS]
    
    def sanitize_environment(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Remove or mask sensitive environment variables."""
        sanitized = {}
        
        for key, value in env_vars.items():
            if self._is_sensitive_key(key):
                sanitized[key] = self._mask_value(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if environment variable key contains sensitive information."""
        return any(pattern.search(key) for pattern in self.sensitive_keys)
    
    def _mask_value(self, value: str) -> str:
        """Mask sensitive values for logging/display."""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    
    def sanitize_logs(self, log_message: str) -> str:
        """Remove potential credentials from log messages."""
        # Pattern to match potential API keys, tokens, etc.
        patterns = [
            r'["\']?[a-zA-Z0-9_-]*[aA][pP][iI][_-]?[kK][eE][yY]["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            r'["\']?[tT][oO][kK][eE][nN]["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_.-]{20,})["\']?',
            r'["\']?[bB][eE][aA][rR][eE][rR]\s+([a-zA-Z0-9_.-]{20,})["\']?',
            r'postgresql://[^:]+:([^@]+)@',  # Database passwords
            r'mysql://[^:]+:([^@]+)@',
            r'redis://[^:]*:([^@]+)@'
        ]
        
        sanitized = log_message
        for pattern in patterns:
            sanitized = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), "*" * 8), sanitized)
        
        return sanitized
    
    def sanitize_dict_for_logging(self, data: Dict) -> Dict:
        """Recursively sanitize a dictionary for safe logging."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_dict_for_logging(value)
            elif isinstance(value, str):
                if self._is_sensitive_key(key):
                    sanitized[key] = self._mask_value(value)
                else:
                    sanitized[key] = self.sanitize_logs(value)
            else:
                sanitized[key] = value
        
        return sanitized
