"""
Zero-Credential-Leakage Architecture

This module implements a comprehensive system to prevent credential leakage through
logs, error messages, environment variables, and any other potential exposure vectors.
It provides secure credential handling with automatic sanitization and monitoring.
"""

import hashlib
import json
import logging
import os
import re
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CredentialType(str, Enum):
    """Types of credentials that need protection."""

    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    SECRET = "secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    DATABASE_URL = "database_url"
    CONNECTION_STRING = "connection_string"


@dataclass
class CredentialPattern:
    """Pattern definition for detecting credentials."""

    name: str
    pattern: re.Pattern
    credential_type: CredentialType
    min_length: int = 8
    max_length: int = 512
    description: str = ""


class CredentialDetector:
    """Detects potential credentials in text using pattern matching."""

    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.whitelist_patterns = self._initialize_whitelist_patterns()

    def _initialize_patterns(self) -> List[CredentialPattern]:
        """Initialize credential detection patterns."""
        return [
            # API Keys
            CredentialPattern(
                name="generic_api_key",
                pattern=re.compile(
                    r'(?i)(?:api[_-]?key|apikey)\s*[:=]\s*["\']?'
                    r'([a-zA-Z0-9_-]{20,})["\']?'
                ),
                credential_type=CredentialType.API_KEY,
                min_length=20,
                description="Generic API key pattern",
            ),
            CredentialPattern(
                name="openai_api_key",
                pattern=re.compile(r"sk-[a-zA-Z0-9]{48,}"),
                credential_type=CredentialType.API_KEY,
                min_length=51,
                description="OpenAI API key",
            ),
            CredentialPattern(
                name="aws_access_key",
                pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
                credential_type=CredentialType.API_KEY,
                min_length=20,
                description="AWS Access Key ID",
            ),
            CredentialPattern(
                name="aws_secret_key",
                pattern=re.compile(
                    r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']?'
                    r'([a-zA-Z0-9/+=]{40})["\']?'
                ),
                credential_type=CredentialType.SECRET,
                min_length=40,
                description="AWS Secret Access Key",
            ),
            # Tokens
            CredentialPattern(
                name="bearer_token",
                pattern=re.compile(r"(?i)bearer\s+([a-zA-Z0-9_.-]{20,})"),
                credential_type=CredentialType.TOKEN,
                min_length=20,
                description="Bearer token",
            ),
            CredentialPattern(
                name="jwt_token",
                pattern=re.compile(
                    r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_.-]+\.[a-zA-Z0-9_.-]+"
                ),
                credential_type=CredentialType.TOKEN,
                min_length=50,
                description="JWT token",
            ),
            CredentialPattern(
                name="github_token",
                pattern=re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),
                credential_type=CredentialType.TOKEN,
                min_length=40,
                description="GitHub token",
            ),
            # Passwords
            CredentialPattern(
                name="password_field",
                pattern=re.compile(
                    r'(?i)(?:password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?'
                ),
                credential_type=CredentialType.PASSWORD,
                min_length=8,
                description="Password field",
            ),
            # Database URLs
            CredentialPattern(
                name="postgresql_url",
                pattern=re.compile(r"postgresql://[^:]+:([^@]+)@[^/]+/[^?\s]+"),
                credential_type=CredentialType.DATABASE_URL,
                min_length=8,
                description="PostgreSQL connection URL",
            ),
            CredentialPattern(
                name="mysql_url",
                pattern=re.compile(r"mysql://[^:]+:([^@]+)@[^/]+/[^?\s]+"),
                credential_type=CredentialType.DATABASE_URL,
                min_length=8,
                description="MySQL connection URL",
            ),
            CredentialPattern(
                name="redis_url",
                pattern=re.compile(r"redis://[^:]*:([^@]+)@[^/]+"),
                credential_type=CredentialType.DATABASE_URL,
                min_length=8,
                description="Redis connection URL",
            ),
            # Private Keys
            CredentialPattern(
                name="private_key",
                pattern=re.compile(
                    r"-----BEGIN[A-Z\s]*PRIVATE KEY-----[\s\S]*?"
                    r"-----END[A-Z\s]*PRIVATE KEY-----"
                ),
                credential_type=CredentialType.PRIVATE_KEY,
                min_length=100,
                max_length=2048,  # Increased to accommodate real private keys
                description="Private key (PEM format)",
            ),
            # Generic secrets (but not whitelisted ones)
            CredentialPattern(
                name="generic_secret",
                pattern=re.compile(
                    r'(?i)(?:secret|token)\s*[:=]\s*["\']?([a-zA-Z0-9_.-]{16,})["\']?'
                ),
                credential_type=CredentialType.SECRET,
                min_length=16,
                description="Generic secret pattern",
            ),
        ]

    def _initialize_whitelist_patterns(self) -> List[re.Pattern]:
        """Initialize patterns for known safe values that shouldn't be flagged."""
        return [
            re.compile(
                r"(?i)example|sample|test|demo|placeholder|your[_-]?key[_-]?here"
            ),
            re.compile(r"(?i)fake|mock|dummy|null|none|empty"),
            re.compile(r"(?i)xxx+|aaa+|111+|000+"),
            re.compile(r"(?i)sk-[x]{48,}"),  # Placeholder OpenAI keys
            re.compile(r"(?i)AKIA[X]{16}"),  # Placeholder AWS keys
        ]

    def detect_credentials(self, text: str) -> List[Dict[str, Any]]:
        """Detect potential credentials in text."""
        detections = []

        for pattern_def in self.patterns:
            matches = pattern_def.pattern.finditer(text)

            for match in matches:
                # Extract the credential value (usually in group 1, or full match)
                credential_value = match.group(1) if match.groups() else match.group(0)

                # Skip if too short or too long
                if (
                    len(credential_value) < pattern_def.min_length
                    or len(credential_value) > pattern_def.max_length
                ):
                    continue

                # Skip if matches whitelist patterns (check both value and context)
                if self._is_whitelisted(credential_value, text):
                    continue

                detections.append(
                    {
                        "pattern_name": pattern_def.name,
                        "credential_type": pattern_def.credential_type.value,
                        "description": pattern_def.description,
                        "start_pos": match.start(),
                        "end_pos": match.end(),
                        "full_match": match.group(0),
                        "credential_value": credential_value,
                        "confidence": self._calculate_confidence(
                            credential_value, pattern_def
                        ),
                        "hash": self._hash_credential(credential_value),
                    }
                )

        return detections

    def _is_whitelisted(self, value: str, context: str = "") -> bool:
        """Check if a value matches whitelist patterns."""
        # Check if the value itself is whitelisted
        for pattern in self.whitelist_patterns:
            if pattern.search(value):
                return True
            # Also check the context for test markers
            if context and pattern.search(context):
                return True
        return False

    def _calculate_confidence(
        self, value: str, pattern_def: CredentialPattern
    ) -> float:
        """Calculate confidence score for credential detection."""
        confidence = 0.5  # Base confidence

        # Length-based confidence
        if len(value) >= pattern_def.min_length * 2:
            confidence += 0.2

        # Entropy-based confidence (higher entropy = more likely to be a credential)
        entropy = self._calculate_entropy(value)
        if entropy > 4.0:
            confidence += 0.2
        elif entropy > 3.0:
            confidence += 0.1

        # Pattern-specific confidence adjustments
        if pattern_def.credential_type == CredentialType.API_KEY:
            if any(char.isdigit() for char in value) and any(
                char.isalpha() for char in value
            ):
                confidence += 0.1

        return min(confidence, 1.0)

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0

        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        import math

        entropy = 0.0
        text_len = len(text)
        for count in char_counts.values():
            probability = count / text_len
            if probability > 0:
                entropy -= probability * math.log2(probability)

        return entropy

    def _hash_credential(self, credential: str) -> str:
        """Create a hash of the credential for tracking without storing the value."""
        return hashlib.sha256(credential.encode()).hexdigest()[:16]


class CredentialSanitizer:
    """Sanitizes text by removing or masking detected credentials."""

    def __init__(self, detector: Optional[CredentialDetector] = None):
        self.detector = detector or CredentialDetector()
        self.sanitization_log = []

    def sanitize_text(
        self, text: str, mask_char: str = "*", preserve_length: bool = False
    ) -> str:
        """Sanitize text by masking detected credentials."""
        if not text:
            return text

        detections = self.detector.detect_credentials(text)
        if not detections:
            return text

        # Sort detections by position (reverse order to avoid position shifts)
        detections.sort(key=lambda x: x["start_pos"], reverse=True)

        sanitized_text = text
        for detection in detections:
            start_pos = detection["start_pos"]
            end_pos = detection["end_pos"]
            credential_value = detection["credential_value"]

            # Create mask
            if preserve_length:
                mask = self._create_preserving_mask(credential_value, mask_char)
            else:
                mask = f"[{detection['credential_type'].upper()}_REDACTED]"

            # Replace in text
            sanitized_text = (
                sanitized_text[:start_pos] + mask + sanitized_text[end_pos:]
            )

            # Log sanitization
            self.sanitization_log.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "pattern": detection["pattern_name"],
                    "type": detection["credential_type"],
                    "hash": detection["hash"],
                    "confidence": detection["confidence"],
                }
            )

        return sanitized_text

    def _create_preserving_mask(self, credential: str, mask_char: str) -> str:
        """Create a mask that preserves some structure of the original credential."""
        if len(credential) <= 8:
            return mask_char * len(credential)

        # Show first 2 and last 2 characters, mask the middle
        return credential[:2] + mask_char * (len(credential) - 4) + credential[-2:]

    def sanitize_dict(
        self, data: Dict[str, Any], recursive: bool = True
    ) -> Dict[str, Any]:
        """Sanitize dictionary values recursively."""
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_text(value)
            elif isinstance(value, dict) and recursive:
                sanitized[key] = self.sanitize_dict(value, recursive)
            elif isinstance(value, list) and recursive:
                sanitized[key] = self.sanitize_list(value, recursive)
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_list(self, data: List[Any], recursive: bool = True) -> List[Any]:
        """Sanitize list values recursively."""
        sanitized = []

        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_text(item))
            elif isinstance(item, dict) and recursive:
                sanitized.append(self.sanitize_dict(item, recursive))
            elif isinstance(item, list) and recursive:
                sanitized.append(self.sanitize_list(item, recursive))
            else:
                sanitized.append(item)

        return sanitized

    def get_sanitization_summary(self) -> Dict[str, Any]:
        """Get summary of sanitization activities."""
        if not self.sanitization_log:
            return {"total_sanitizations": 0}

        summary = {
            "total_sanitizations": len(self.sanitization_log),
            "by_type": {},
            "by_pattern": {},
            "high_confidence_count": 0,
            "latest_sanitization": self.sanitization_log[-1]["timestamp"],
        }

        for entry in self.sanitization_log:
            # Count by type
            cred_type = entry["type"]
            summary["by_type"][cred_type] = summary["by_type"].get(cred_type, 0) + 1

            # Count by pattern
            pattern = entry["pattern"]
            summary["by_pattern"][pattern] = summary["by_pattern"].get(pattern, 0) + 1

            # Count high confidence detections
            if entry["confidence"] > 0.8:
                summary["high_confidence_count"] += 1

        return summary


class SecureLoggingHandler(logging.Handler):
    """Custom logging handler that automatically sanitizes log messages."""

    def __init__(
        self,
        base_handler: logging.Handler,
        sanitizer: Optional[CredentialSanitizer] = None,
    ):
        super().__init__()
        self.base_handler = base_handler
        self.sanitizer = sanitizer or CredentialSanitizer()
        self.setLevel(base_handler.level)
        self.setFormatter(base_handler.formatter)

    def emit(self, record: logging.LogRecord):
        """Emit a log record after sanitizing it."""
        try:
            # Sanitize the message
            if hasattr(record, "msg") and isinstance(record.msg, str):
                record.msg = self.sanitizer.sanitize_text(record.msg)

            # Sanitize arguments
            if hasattr(record, "args") and record.args:
                sanitized_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        sanitized_args.append(self.sanitizer.sanitize_text(arg))
                    elif isinstance(arg, dict):
                        sanitized_args.append(self.sanitizer.sanitize_dict(arg))
                    else:
                        sanitized_args.append(arg)
                record.args = tuple(sanitized_args)

            # Sanitize exception info
            if record.exc_info:
                exc_text = self.format_exception(record.exc_info)
                record.exc_text = self.sanitizer.sanitize_text(exc_text)

            # Pass to base handler
            self.base_handler.emit(record)

        except Exception:
            self.handleError(record)

    def format_exception(self, exc_info) -> str:
        """Format exception information."""
        return "".join(traceback.format_exception(*exc_info))


class EnvironmentSanitizer:
    """Sanitizes environment variables to prevent credential exposure."""

    def __init__(self, sanitizer: Optional[CredentialSanitizer] = None):
        self.sanitizer = sanitizer or CredentialSanitizer()
        self.sensitive_env_patterns = [
            re.compile(r"(?i).*key.*"),
            re.compile(r"(?i).*secret.*"),
            re.compile(r"(?i).*token.*"),
            re.compile(r"(?i).*password.*"),
            re.compile(r"(?i).*credential.*"),
            re.compile(r"(?i).*auth.*"),
            re.compile(r"(?i).*api.*"),
            re.compile(r"(?i).*database.*url.*"),
            re.compile(r"(?i).*connection.*string.*"),
        ]

    def get_safe_environment(self) -> Dict[str, str]:
        """Get environment variables with sensitive values sanitized."""
        safe_env = {}

        for key, value in os.environ.items():
            if self._is_sensitive_key(key):
                safe_env[key] = self.sanitizer.sanitize_text(value)
            else:
                safe_env[key] = value

        return safe_env

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if environment variable key is potentially sensitive."""
        return any(pattern.match(key) for pattern in self.sensitive_env_patterns)

    def validate_environment_safety(self) -> Dict[str, Any]:
        """Validate that environment doesn't contain exposed credentials."""
        issues = []

        for key, value in os.environ.items():
            if not self._is_sensitive_key(key):
                # Check if non-sensitive env vars contain credentials
                detections = self.sanitizer.detector.detect_credentials(value)
                if detections:
                    issues.append(
                        {
                            "env_var": key,
                            "issue": "credential_in_non_sensitive_var",
                            "detections": len(detections),
                            "types": list(
                                set(d["credential_type"] for d in detections)
                            ),
                        }
                    )

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "total_env_vars": len(os.environ),
            "sensitive_env_vars": sum(
                1 for key in os.environ.keys() if self._is_sensitive_key(key)
            ),
        }


@contextmanager
def secure_context():
    """Context manager that ensures no credentials leak during execution."""
    original_handlers = logging.root.handlers[:]
    sanitizer = CredentialSanitizer()

    try:
        # Replace all logging handlers with secure versions
        for handler in logging.root.handlers:
            secure_handler = SecureLoggingHandler(handler, sanitizer)
            logging.root.removeHandler(handler)
            logging.root.addHandler(secure_handler)

        yield sanitizer

    finally:
        # Restore original handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        for handler in original_handlers:
            logging.root.addHandler(handler)


def secure_function(func):
    """Decorator that ensures function execution doesn't leak credentials."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with secure_context() as sanitizer:
            try:
                result = func(*args, **kwargs)

                # Sanitize return value if it's a string or dict
                if isinstance(result, str):
                    return sanitizer.sanitize_text(result)
                elif isinstance(result, dict):
                    return sanitizer.sanitize_dict(result)
                else:
                    return result

            except Exception as e:
                # Sanitize exception message
                sanitized_message = sanitizer.sanitize_text(str(e))
                raise type(e)(sanitized_message) from e

    return wrapper


class CredentialLeakageMonitor:
    """Monitors for potential credential leakage across the application."""

    def __init__(self):
        self.detector = CredentialDetector()
        self.sanitizer = CredentialSanitizer(self.detector)
        self.alerts = []

    def monitor_log_output(
        self, log_message: str, logger_name: str = "unknown"
    ) -> bool:
        """Monitor log output for credential leakage."""
        detections = self.detector.detect_credentials(log_message)

        if detections:
            alert = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "log_leakage",
                "logger": logger_name,
                "detections": len(detections),
                "credential_types": list(set(d["credential_type"] for d in detections)),
                "high_confidence": sum(1 for d in detections if d["confidence"] > 0.8),
            }
            self.alerts.append(alert)

            # Log the alert (but sanitized)
            sanitized_message = self.sanitizer.sanitize_text(log_message)
            logger.warning(
                f"Credential leakage detected in logs from {logger_name}. "
                f"Sanitized message: {sanitized_message[:100]}..."
            )

            return True

        return False

    def monitor_api_response(
        self, response_data: Any, endpoint: str = "unknown"
    ) -> bool:
        """Monitor API responses for credential leakage."""
        response_text = (
            json.dumps(response_data)
            if not isinstance(response_data, str)
            else response_data
        )
        detections = self.detector.detect_credentials(response_text)

        if detections:
            alert = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "api_response_leakage",
                "endpoint": endpoint,
                "detections": len(detections),
                "credential_types": list(set(d["credential_type"] for d in detections)),
                "high_confidence": sum(1 for d in detections if d["confidence"] > 0.8),
            }
            self.alerts.append(alert)

            logger.error(
                f"Credential leakage detected in API response from {endpoint}. "
                f"Response contains {len(detections)} potential credentials."
            )

            return True

        return False

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all credential leakage alerts."""
        if not self.alerts:
            return {"total_alerts": 0}

        summary = {
            "total_alerts": len(self.alerts),
            "by_type": {},
            "recent_alerts": self.alerts[-5:],  # Last 5 alerts
            "high_confidence_alerts": sum(
                1 for alert in self.alerts if alert.get("high_confidence", 0) > 0
            ),
        }

        for alert in self.alerts:
            alert_type = alert["type"]
            summary["by_type"][alert_type] = summary["by_type"].get(alert_type, 0) + 1

        return summary


# Global monitor instance
_global_monitor = CredentialLeakageMonitor()


def get_global_monitor() -> CredentialLeakageMonitor:
    """Get the global credential leakage monitor."""
    return _global_monitor


def setup_secure_logging():
    """Set up secure logging for the entire application."""
    sanitizer = CredentialSanitizer()

    # Get all existing handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]

    # Replace with secure handlers
    for handler in original_handlers:
        secure_handler = SecureLoggingHandler(handler, sanitizer)
        root_logger.removeHandler(handler)
        root_logger.addHandler(secure_handler)

    logger.info("Secure logging initialized - all log output will be sanitized")


def validate_system_security() -> Dict[str, Any]:
    """Validate overall system security against credential leakage."""
    env_sanitizer = EnvironmentSanitizer()
    monitor = get_global_monitor()

    # Check environment variables
    env_validation = env_sanitizer.validate_environment_safety()

    # Check recent alerts
    alert_summary = monitor.get_alert_summary()

    # Overall security score
    security_score = 100
    if not env_validation["safe"]:
        security_score -= 30
    if alert_summary["total_alerts"] > 0:
        security_score -= min(alert_summary["total_alerts"] * 5, 50)

    return {
        "security_score": max(security_score, 0),
        "environment_safety": env_validation,
        "leakage_alerts": alert_summary,
        "recommendations": _generate_security_recommendations(
            env_validation, alert_summary
        ),
    }


def _generate_security_recommendations(
    env_validation: Dict, alert_summary: Dict
) -> List[str]:
    """Generate security recommendations based on validation results."""
    recommendations = []

    if not env_validation["safe"]:
        recommendations.append(
            "Review environment variables - credentials detected in "
            "non-sensitive variables"
        )

    if alert_summary["total_alerts"] > 0:
        recommendations.append("Investigate recent credential leakage alerts")
        recommendations.append("Consider implementing additional input sanitization")

    if env_validation["sensitive_env_vars"] == 0:
        recommendations.append(
            "Consider using environment variables for credential management"
        )

    if not recommendations:
        recommendations.append("Security posture is good - continue monitoring")

    return recommendations
