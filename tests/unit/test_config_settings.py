#!/usr/bin/env python3
"""
Tests for Configuration Management System

This module tests the enterprise configuration management system
including settings validation, environment handling, and convenience functions.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config.settings import (
    ApplicationSettings,
    DatabaseSettings,
    Environment,
    LogLevel,
    MCPSettings,
    MonitoringSettings,
    OpenAISettings,
    RedisSettings,
    SecuritySettings,
    Settings,
    get_database_url,
    get_jwt_secret,
    get_openai_api_key,
    get_redis_url,
    get_settings,
    is_development,
    is_production,
    reload_settings,
)


class TestEnvironmentEnum:
    """Test Environment enumeration."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"


class TestLogLevelEnum:
    """Test LogLevel enumeration."""

    def test_log_level_values(self):
        """Test log level enum values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"


class TestDatabaseSettings:
    """Test database configuration settings."""

    def test_default_values(self):
        """Test default database settings."""
        settings = DatabaseSettings()

        assert settings.database_host == "localhost"
        assert settings.database_port == 5432
        assert settings.database_name == "openai_agents_demo"
        assert settings.database_user == "postgres"
        assert settings.database_password == ""
        assert settings.database_pool_size == 10
        assert settings.sqlite_file == "./data/app.db"

    def test_url_assembly_with_password(self):
        """Test database URL assembly with password."""
        settings = DatabaseSettings(
            database_user="testuser",
            database_password="testpass",
            database_host="testhost",
            database_port=5433,
            database_name="testdb",
        )

        expected = "postgresql://testuser:testpass@testhost:5433/testdb"
        assert settings.database_url == expected

    def test_url_assembly_without_password(self):
        """Test database URL assembly without password."""
        settings = DatabaseSettings(
            database_user="testuser",
            database_password="",
            database_host="testhost",
            database_port=5433,
            database_name="testdb",
        )

        expected = "postgresql://testuser@testhost:5433/testdb"
        assert settings.database_url == expected

    def test_existing_url_preserved(self):
        """Test that existing database URL is preserved."""
        existing_url = "postgresql://user:pass@host:5432/db"
        settings = DatabaseSettings(database_url=existing_url)

        assert settings.database_url == existing_url


class TestRedisSettings:
    """Test Redis configuration settings."""

    def test_default_values(self):
        """Test default Redis settings."""
        settings = RedisSettings()

        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
        assert settings.redis_password is None
        assert settings.redis_pool_size == 10
        assert settings.redis_timeout == 5

    def test_url_assembly_with_password(self):
        """Test Redis URL assembly with password."""
        settings = RedisSettings(
            redis_host="testhost",
            redis_port=6380,
            redis_db=1,
            redis_password="testpass",
        )

        expected = "redis://:testpass@testhost:6380/1"
        assert settings.redis_url == expected

    def test_url_assembly_without_password(self):
        """Test Redis URL assembly without password."""
        settings = RedisSettings(redis_host="testhost", redis_port=6380, redis_db=1)

        expected = "redis://testhost:6380/1"
        assert settings.redis_url == expected

    def test_existing_url_preserved(self):
        """Test that existing Redis URL is preserved."""
        existing_url = "redis://user:pass@host:6379/0"
        settings = RedisSettings(redis_url=existing_url)

        assert settings.redis_url == existing_url


class TestSecuritySettings:
    """Test security configuration settings."""

    def test_default_values(self):
        """Test default security settings."""
        settings = SecuritySettings()

        assert len(settings.jwt_secret_key) >= 32
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_access_token_expire_minutes == 30
        assert settings.jwt_refresh_token_expire_days == 7
        assert settings.password_min_length == 8
        assert settings.enable_cors is True
        assert settings.rate_limit_enabled is True

    def test_jwt_secret_validation_success(self):
        """Test JWT secret validation with valid key."""
        long_key = "a" * 32
        settings = SecuritySettings(jwt_secret_key=long_key)
        assert settings.jwt_secret_key == long_key

    def test_jwt_secret_validation_failure(self):
        """Test JWT secret validation with short key."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            SecuritySettings(jwt_secret_key="short")

    def test_cors_origins_default(self):
        """Test default CORS origins."""
        settings = SecuritySettings()
        assert "http://localhost:3000" in settings.cors_origins


class TestOpenAISettings:
    """Test OpenAI configuration settings."""

    def test_default_values(self):
        """Test default OpenAI settings."""
        # Mock the required API key
        settings = OpenAISettings(openai_api_key="test-key")

        assert settings.openai_api_key == "test-key"
        assert settings.default_model == "gpt-4.1"
        assert settings.max_tokens == 4000
        assert settings.temperature == 0.7
        assert settings.requests_per_minute == 60
        assert settings.tokens_per_minute == 90000

    def test_custom_values(self):
        """Test custom OpenAI settings."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "custom-key"}):
            settings = OpenAISettings(
                openai_organization="org-123",
                openai_base_url="https://custom.api.com",
                default_model="gpt-3.5-turbo",
                max_tokens=2000,
                temperature=0.5,
            )

            assert settings.openai_organization == "org-123"
            assert settings.openai_base_url == "https://custom.api.com"
            assert settings.default_model == "gpt-3.5-turbo"
            assert settings.max_tokens == 2000
            assert settings.temperature == 0.5


class TestMCPSettings:
    """Test MCP configuration settings."""

    def test_default_values(self):
        """Test default MCP settings."""
        settings = MCPSettings()

        assert settings.mcp_servers_dir == Path("./generated_servers")
        assert settings.mcp_templates_dir == Path("./mcp/templates")
        assert settings.default_timeout == 30
        assert settings.default_max_retries == 3
        assert settings.default_auth_type == "none"
        assert settings.auto_cleanup_servers is True
        assert settings.max_endpoints_per_server == 50
        assert settings.max_complexity_score == 8

    def test_custom_paths(self):
        """Test custom MCP paths."""
        settings = MCPSettings(
            mcp_servers_dir=Path("/custom/servers"),
            mcp_templates_dir=Path("/custom/templates"),
            registry_file=Path("/custom/registry.json"),
        )

        assert settings.mcp_servers_dir == Path("/custom/servers")
        assert settings.mcp_templates_dir == Path("/custom/templates")
        assert settings.registry_file == Path("/custom/registry.json")


class TestMonitoringSettings:
    """Test monitoring configuration settings."""

    def test_default_values(self):
        """Test default monitoring settings."""
        settings = MonitoringSettings()

        assert settings.log_level == LogLevel.INFO
        assert settings.log_format == "json"
        assert settings.log_file is None
        assert settings.enable_metrics is True
        assert settings.metrics_port == 8001
        assert settings.enable_tracing is False
        assert settings.health_check_interval == 30

    def test_custom_values(self):
        """Test custom monitoring settings."""
        settings = MonitoringSettings(
            log_level=LogLevel.DEBUG,
            log_format="text",
            log_file=Path("/var/log/app.log"),
            enable_tracing=True,
            jaeger_endpoint="http://jaeger:14268",
        )

        assert settings.log_level == LogLevel.DEBUG
        assert settings.log_format == "text"
        assert settings.log_file == Path("/var/log/app.log")
        assert settings.enable_tracing is True
        assert settings.jaeger_endpoint == "http://jaeger:14268"


class TestApplicationSettings:
    """Test application configuration settings."""

    def test_default_values(self):
        """Test default application settings."""
        settings = ApplicationSettings()

        assert settings.app_name == "OpenAI Customer Service Agents"
        assert settings.app_version == "1.0.0"
        assert settings.environment == Environment.DEVELOPMENT
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.workers == 1

    def test_directory_creation(self):
        """Test automatic directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            temp_app_dir = Path(temp_dir) / "tmp"

            settings = ApplicationSettings(data_dir=data_dir, temp_dir=temp_app_dir)

            assert settings.data_dir.exists()
            assert settings.temp_dir.exists()

    def test_feature_flags(self):
        """Test feature flag settings."""
        settings = ApplicationSettings(
            enable_multi_tenancy=True, enable_audit_logging=True, enable_mcp_ui=False
        )

        assert settings.enable_multi_tenancy is True
        assert settings.enable_audit_logging is True
        assert settings.enable_mcp_ui is False


class TestCompleteSettings:
    """Test complete settings integration."""

    def test_default_settings(self):
        """Test default complete settings."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()

            assert isinstance(settings.app, ApplicationSettings)
            assert isinstance(settings.database, DatabaseSettings)
            assert isinstance(settings.redis, RedisSettings)
            assert isinstance(settings.security, SecuritySettings)
            assert isinstance(settings.openai, OpenAISettings)
            assert isinstance(settings.mcp, MCPSettings)
            assert isinstance(settings.monitoring, MonitoringSettings)

    def test_environment_detection(self):
        """Test environment detection methods."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Test development
            settings = Settings()
            settings.app.environment = Environment.DEVELOPMENT
            assert settings.is_development() is True
            assert settings.is_production() is False
            assert settings.is_testing() is False

            # Test production
            settings.app.environment = Environment.PRODUCTION
            assert settings.is_development() is False
            assert settings.is_production() is True
            assert settings.is_testing() is False

            # Test testing
            settings.app.environment = Environment.TESTING
            assert settings.is_development() is False
            assert settings.is_production() is False
            assert settings.is_testing() is True

    def test_database_url_methods(self):
        """Test database URL methods."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()

            # Test development (SQLite)
            settings.app.environment = Environment.DEVELOPMENT
            url = settings.get_database_url()
            assert url.startswith("sqlite:///")

            # Test production without URL - clear the database_url first
            settings.app.environment = Environment.PRODUCTION
            settings.database.database_url = None
            with pytest.raises(ValueError, match="Database URL must be configured"):
                settings.get_database_url()

            # Test with explicit URL
            settings.database.database_url = "postgresql://user:pass@host/db"
            url = settings.get_database_url()
            assert url == "postgresql://user:pass@host/db"

    def test_redis_url_methods(self):
        """Test Redis URL methods."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()

            # Test default Redis URL
            url = settings.get_redis_url()
            assert url == "redis://localhost:6379/0"

            # Test with password - password takes precedence over explicit URL
            settings.redis.redis_password = "testpass"
            url = settings.get_redis_url()
            assert url == "redis://:testpass@localhost:6379/0"

            # Test with explicit URL (without password)
            settings.redis.redis_password = None
            settings.redis.redis_url = "redis://custom:6380/1"
            url = settings.get_redis_url()
            assert url == "redis://custom:6380/1"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_settings_singleton(self):
        """Test settings singleton behavior."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2

    def test_reload_settings(self):
        """Test settings reload functionality."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings1 = get_settings()
            settings2 = reload_settings()
            assert settings1 is not settings2

    def test_convenience_functions(self):
        """Test convenience functions."""
        with patch.dict(os.environ, {"OPENAI_OPENAI_API_KEY": "test-key"}):
            # Reload settings to pick up environment variable
            reload_settings()

            # Test database URL
            url = get_database_url()
            assert url.startswith("sqlite:///")

            # Test Redis URL
            redis_url = get_redis_url()
            assert redis_url == "redis://localhost:6379/0"

            # Test environment checks
            assert is_development() is True
            assert is_production() is False

            # Test API key
            api_key = get_openai_api_key()
            assert api_key == "test-key"

            # Test JWT secret
            jwt_secret = get_jwt_secret()
            assert len(jwt_secret) >= 32


class TestEnvironmentVariables:
    """Test environment variable integration."""

    def test_database_env_vars(self):
        """Test database environment variables."""
        env_vars = {
            "DB_DATABASE_HOST": "envhost",
            "DB_DATABASE_PORT": "5433",
            "DB_DATABASE_NAME": "envdb",
            "DB_DATABASE_USER": "envuser",
            "DB_DATABASE_PASSWORD": "envpass",
        }

        with patch.dict(os.environ, env_vars):
            settings = DatabaseSettings()
            assert settings.database_host == "envhost"
            assert settings.database_port == 5433
            assert settings.database_name == "envdb"
            assert settings.database_user == "envuser"
            assert settings.database_password == "envpass"

    def test_security_env_vars(self):
        """Test security environment variables."""
        env_vars = {
            "SECURITY_JWT_SECRET_KEY": "a" * 32,
            "SECURITY_JWT_ALGORITHM": "HS512",
            "SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE": "120",
        }

        with patch.dict(os.environ, env_vars):
            settings = SecuritySettings()
            assert settings.jwt_secret_key == "a" * 32
            assert settings.jwt_algorithm == "HS512"
            assert settings.rate_limit_requests_per_minute == 120

    def test_app_env_vars(self):
        """Test application environment variables."""
        env_vars = {
            "APP_APP_NAME": "Custom App",
            "APP_ENVIRONMENT": "production",
            "APP_DEBUG": "true",
            "APP_PORT": "9000",
        }

        with patch.dict(os.environ, env_vars):
            settings = ApplicationSettings()
            assert settings.app_name == "Custom App"
            assert settings.environment == Environment.PRODUCTION
            assert settings.debug is True
            assert settings.port == 9000


if __name__ == "__main__":
    pytest.main([__file__])
