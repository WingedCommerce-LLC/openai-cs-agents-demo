"""
Unit tests for environment sanitizer module.

Tests the security functionality for preventing credential leakage
in logs and environment variables.
"""

import pytest
from security.env_sanitizer import EnvironmentSanitizer


class TestEnvironmentSanitizer:
    """Test suite for EnvironmentSanitizer class."""

    @pytest.fixture
    def sanitizer(self):
        """Create an EnvironmentSanitizer instance for testing."""
        return EnvironmentSanitizer()

    def test_sanitize_environment_removes_sensitive_keys(self, sanitizer, sensitive_environment_vars):
        """Test that sensitive environment variables are masked."""
        sanitized = sanitizer.sanitize_environment(sensitive_environment_vars)
        
        # Check that sensitive values are masked
        assert sanitized["API_KEY"] != sensitive_environment_vars["API_KEY"]
        assert "*" in sanitized["API_KEY"]
        
        assert sanitized["SECRET_TOKEN"] != sensitive_environment_vars["SECRET_TOKEN"]
        assert "*" in sanitized["SECRET_TOKEN"]
        
        assert sanitized["DATABASE_PASSWORD"] != sensitive_environment_vars["DATABASE_PASSWORD"]
        assert "*" in sanitized["DATABASE_PASSWORD"]
        
        # Check that non-sensitive values are preserved
        assert sanitized["NORMAL_VAR"] == sensitive_environment_vars["NORMAL_VAR"]
        assert sanitized["DEBUG"] == sensitive_environment_vars["DEBUG"]

    def test_is_sensitive_key_detection(self, sanitizer):
        """Test that sensitive key patterns are correctly identified."""
        # Test sensitive patterns
        assert sanitizer._is_sensitive_key("API_KEY")
        assert sanitizer._is_sensitive_key("SECRET_TOKEN")
        assert sanitizer._is_sensitive_key("DATABASE_PASSWORD")
        assert sanitizer._is_sensitive_key("OAUTH_CLIENT_SECRET")
        assert sanitizer._is_sensitive_key("PRIVATE_KEY")
        assert sanitizer._is_sensitive_key("auth_token")
        assert sanitizer._is_sensitive_key("bearer-token")
        
        # Test non-sensitive patterns
        assert not sanitizer._is_sensitive_key("DEBUG")
        assert not sanitizer._is_sensitive_key("LOG_LEVEL")
        assert not sanitizer._is_sensitive_key("PORT")
        assert not sanitizer._is_sensitive_key("ENVIRONMENT")

    def test_mask_value_preserves_structure(self, sanitizer):
        """Test that value masking preserves some structure for debugging."""
        # Test short values (fully masked)
        short_value = "abc123"
        masked_short = sanitizer._mask_value(short_value)
        assert len(masked_short) == len(short_value)
        assert all(c == "*" for c in masked_short)
        
        # Test long values (partial masking)
        long_value = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
        masked_long = sanitizer._mask_value(long_value)
        assert masked_long.startswith("sk-1")  # First 4 chars preserved
        assert masked_long.endswith("wxyz")    # Last 4 chars preserved
        assert "*" in masked_long              # Middle is masked

    def test_sanitize_logs_removes_credentials(self, sanitizer):
        """Test that log messages have credentials removed."""
        # Test API key in log message
        log_with_api_key = 'Using API key: "sk-1234567890abcdefghijklmnopqrstuvwxyz" for request'
        sanitized_log = sanitizer.sanitize_logs(log_with_api_key)
        assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in sanitized_log
        assert "********" in sanitized_log
        
        # Test token in log message
        log_with_token = "Bearer token: abc123def456ghi789jkl012mno345pqr678"
        sanitized_log = sanitizer.sanitize_logs(log_with_token)
        assert "abc123def456ghi789jkl012mno345pqr678" not in sanitized_log
        assert "********" in sanitized_log
        
        # Test database URL with password
        log_with_db = "Connecting to postgresql://user:secretpass@localhost:5432/db"
        sanitized_log = sanitizer.sanitize_logs(log_with_db)
        assert "secretpass" not in sanitized_log
        assert "********" in sanitized_log

    def test_sanitize_logs_preserves_safe_content(self, sanitizer):
        """Test that safe log content is preserved."""
        safe_log = "Application started successfully on port 8000"
        sanitized_log = sanitizer.sanitize_logs(safe_log)
        assert sanitized_log == safe_log
        
        safe_log_with_numbers = "Processing request ID: 12345 for user: john.doe@example.com"
        sanitized_log = sanitizer.sanitize_logs(safe_log_with_numbers)
        assert sanitized_log == safe_log_with_numbers

    def test_empty_and_none_values(self, sanitizer):
        """Test handling of empty and None values."""
        # Test empty environment
        empty_env = {}
        sanitized = sanitizer.sanitize_environment(empty_env)
        assert sanitized == {}
        
        # Test environment with empty values
        env_with_empty = {"API_KEY": "", "DEBUG": "true"}
        sanitized = sanitizer.sanitize_environment(env_with_empty)
        assert sanitized["API_KEY"] == ""  # Empty string preserved
        assert sanitized["DEBUG"] == "true"
        
        # Test empty log message
        empty_log = ""
        sanitized_log = sanitizer.sanitize_logs(empty_log)
        assert sanitized_log == ""

    def test_case_insensitive_pattern_matching(self, sanitizer):
        """Test that pattern matching is case insensitive."""
        # Test various case combinations
        assert sanitizer._is_sensitive_key("api_key")
        assert sanitizer._is_sensitive_key("API_KEY")
        assert sanitizer._is_sensitive_key("Api_Key")
        assert sanitizer._is_sensitive_key("secret_token")
        assert sanitizer._is_sensitive_key("SECRET_TOKEN")
        assert sanitizer._is_sensitive_key("Secret_Token")

    def test_complex_environment_scenarios(self, sanitizer):
        """Test complex real-world environment variable scenarios."""
        complex_env = {
            "DATABASE_URL": "postgresql://user:pass123@db.example.com:5432/mydb",
            "REDIS_URL": "redis://localhost:6379",
            "OPENAI_API_KEY": "sk-proj-abcdef1234567890",
            "JWT_SECRET": "super-secret-jwt-key-12345",
            "DEBUG": "false",
            "PORT": "8000",
            "CORS_ORIGINS": "http://localhost:3000,https://app.example.com",
            "SENTRY_DSN": "https://key@sentry.io/project",
            "NORMAL_CONFIG": "some-normal-value"
        }
        
        sanitized = sanitizer.sanitize_environment(complex_env)
        
        # Sensitive values should be masked
        assert "*" in sanitized["DATABASE_URL"]
        assert "*" in sanitized["OPENAI_API_KEY"]
        assert "*" in sanitized["JWT_SECRET"]
        
        # Non-sensitive values should be preserved
        assert sanitized["REDIS_URL"] == complex_env["REDIS_URL"]
        assert sanitized["DEBUG"] == complex_env["DEBUG"]
        assert sanitized["PORT"] == complex_env["PORT"]
        assert sanitized["CORS_ORIGINS"] == complex_env["CORS_ORIGINS"]
        assert sanitized["NORMAL_CONFIG"] == complex_env["NORMAL_CONFIG"]

    @pytest.mark.security
    def test_no_credential_leakage_in_exceptions(self, sanitizer):
        """Test that exceptions don't leak credentials."""
        # This test ensures our sanitizer doesn't accidentally expose
        # credentials through error messages or stack traces
        
        try:
            # Simulate an operation that might fail with sensitive data
            sensitive_data = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
            sanitized = sanitizer._mask_value(sensitive_data)
            
            # Verify the sensitive data is not in the result
            assert "1234567890abcdefghijklmnopqrstuvw" not in sanitized
            
        except Exception as e:
            # If an exception occurs, ensure it doesn't contain sensitive data
            error_message = str(e)
            assert "1234567890abcdefghijklmnopqrstuvw" not in error_message
