#!/usr/bin/env python3
"""
Enterprise Configuration Management System

This module provides centralized configuration management using Pydantic settings
with environment variable support, validation, and multi-environment capabilities.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    # Database connection
    database_url: Optional[str] = Field(
        default=None,
        description="Database URL"
    )
    database_host: str = Field(
        default="localhost",
        description="Database host"
    )
    database_port: int = Field(
        default=5432,
        description="Database port"
    )
    database_name: str = Field(
        default="openai_agents_demo",
        description="Database name"
    )
    database_user: str = Field(
        default="postgres",
        description="Database user"
    )
    database_password: str = Field(
        default="",
        description="Database password"
    )

    # Connection pool settings
    database_pool_size: int = Field(
        default=10,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20,
        description="Database connection pool max overflow"
    )
    database_pool_timeout: int = Field(
        default=30,
        description="Database connection pool timeout in seconds"
    )

    # SQLite fallback for development
    sqlite_file: str = Field(
        default="./data/app.db",
        description="SQLite database file path for development"
    )

    def __init__(self, **data):
        """Initialize database settings with URL assembly."""
        super().__init__(**data)
        if not self.database_url:
            # Build PostgreSQL URL from components
            user = self.database_user
            password = self.database_password
            host = self.database_host
            port = self.database_port
            name = self.database_name

            if password:
                url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
                self.database_url = url
            else:
                self.database_url = f"postgresql://{user}@{host}:{port}/{name}"

    class Config:
        env_prefix = "DB_"
        case_sensitive = False


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    redis_host: str = Field(
        default="localhost",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        description="Redis port"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password"
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number"
    )

    # Connection settings
    redis_pool_size: int = Field(
        default=10,
        description="Redis connection pool size"
    )
    redis_timeout: int = Field(
        default=5,
        description="Redis connection timeout in seconds"
    )

    def __init__(self, **data):
        """Initialize Redis settings with URL assembly."""
        super().__init__(**data)
        if not self.redis_url:
            # Build Redis URL from components
            host = self.redis_host
            port = self.redis_port
            db = self.redis_db
            password = self.redis_password

            if password:
                self.redis_url = f"redis://:{password}@{host}:{port}/{db}"
            else:
                self.redis_url = f"redis://{host}:{port}/{db}"

    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    # JWT settings
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production-must-be-32-chars",
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        description="JWT access token expiration in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="JWT refresh token expiration in days"
    )

    # Password settings
    password_min_length: int = Field(
        default=8,
        description="Minimum password length"
    )
    password_require_uppercase: bool = Field(
        default=True,
        description="Require uppercase letters in passwords"
    )
    password_require_lowercase: bool = Field(
        default=True,
        description="Require lowercase letters in passwords"
    )
    password_require_numbers: bool = Field(
        default=True,
        description="Require numbers in passwords"
    )
    password_require_special: bool = Field(
        default=True,
        description="Require special characters in passwords"
    )

    # Security headers
    enable_cors: bool = Field(
        default=True,
        description="Enable CORS middleware"
    )
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Rate limit requests per minute"
    )

    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key strength."""
        if len(v) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 characters long"
            )
        return v

    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class OpenAISettings(BaseSettings):
    """OpenAI API configuration settings."""

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key"
    )
    openai_organization: Optional[str] = Field(
        default=None,
        description="OpenAI organization ID"
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        description="OpenAI API base URL (for custom endpoints)"
    )

    # Model settings
    default_model: str = Field(
        default="gpt-4.1",
        description="Default OpenAI model"
    )
    max_tokens: int = Field(
        default=4000,
        description="Maximum tokens per request"
    )
    temperature: float = Field(
        default=0.7,
        description="Model temperature"
    )

    # Rate limiting
    requests_per_minute: int = Field(
        default=60,
        description="OpenAI API requests per minute limit"
    )
    tokens_per_minute: int = Field(
        default=90000,
        description="OpenAI API tokens per minute limit"
    )

    class Config:
        env_prefix = "OPENAI_"
        case_sensitive = False


class MCPSettings(BaseSettings):
    """MCP (Model Context Protocol) configuration settings."""

    # Server generation settings
    mcp_servers_dir: Path = Field(
        default=Path("./generated_servers"),
        description="Directory for generated MCP servers"
    )
    mcp_templates_dir: Path = Field(
        default=Path("./mcp/templates"),
        description="Directory for MCP server templates"
    )

    # Default server configuration
    default_timeout: int = Field(
        default=30,
        description="Default timeout for MCP server requests"
    )
    default_max_retries: int = Field(
        default=3,
        description="Default maximum retries for failed requests"
    )
    default_auth_type: str = Field(
        default="none",
        description="Default authentication type for generated servers"
    )

    # Registry settings
    registry_file: Path = Field(
        default=Path("./data/mcp_registry.json"),
        description="MCP server registry file path"
    )
    auto_cleanup_servers: bool = Field(
        default=True,
        description="Automatically cleanup stopped servers"
    )

    # Generation limits
    max_endpoints_per_server: int = Field(
        default=50,
        description="Maximum endpoints per generated server"
    )
    max_complexity_score: int = Field(
        default=8,
        description="Maximum complexity score for endpoint inclusion"
    )

    class Config:
        env_prefix = "MCP_"
        case_sensitive = False


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration settings."""

    # Logging
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Application log level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Log file path (if file logging enabled)"
    )

    # Metrics
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    metrics_port: int = Field(
        default=8001,
        description="Metrics server port"
    )

    # Tracing
    enable_tracing: bool = Field(
        default=False,
        description="Enable distributed tracing"
    )
    jaeger_endpoint: Optional[str] = Field(
        default=None,
        description="Jaeger tracing endpoint"
    )

    # Health checks
    health_check_interval: int = Field(
        default=30,
        description="Health check interval in seconds"
    )

    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = False


class ApplicationSettings(BaseSettings):
    """Main application configuration settings."""

    # Application metadata
    app_name: str = Field(
        default="OpenAI Customer Service Agents",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    app_description: str = Field(
        default="Enterprise-ready customer service agents platform",
        description="Application description"
    )

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )

    # Server settings
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        description="Server port"
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes"
    )

    # Data directories
    data_dir: Path = Field(
        default=Path("./data"),
        description="Data directory path"
    )
    temp_dir: Path = Field(
        default=Path("./tmp"),
        description="Temporary files directory"
    )

    # Feature flags
    enable_multi_tenancy: bool = Field(
        default=False,
        description="Enable multi-tenancy features"
    )
    enable_audit_logging: bool = Field(
        default=False,
        description="Enable audit logging"
    )
    enable_mcp_ui: bool = Field(
        default=True,
        description="Enable MCP management UI"
    )

    @validator("data_dir", "temp_dir", pre=True)
    def create_directories(cls, v: Union[str, Path]) -> Path:
        """Create directories if they don't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_prefix = "APP_"
        case_sensitive = False


class Settings(BaseSettings):
    """Complete application settings combining all configuration sections."""

    # Core application settings
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)

    # Database configuration
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Redis configuration
    redis: RedisSettings = Field(default_factory=RedisSettings)

    # Security configuration
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # OpenAI configuration
    openai: OpenAISettings = Field(default_factory=OpenAISettings)

    # MCP configuration
    mcp: MCPSettings = Field(default_factory=MCPSettings)

    # Monitoring configuration
    monitoring: MonitoringSettings = Field(
        default_factory=MonitoringSettings
    )

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app.environment == Environment.TESTING

    def get_database_url(self) -> str:
        """Get the appropriate database URL for the current environment."""
        if self.is_development() or self.is_testing():
            # Use SQLite for development/testing
            return f"sqlite:///{self.database.sqlite_file}"
        elif self.database.database_url:
            return str(self.database.database_url)
        else:
            raise ValueError(
                "Database URL must be configured for production environment"
            )

    def get_redis_url(self) -> str:
        """Get the Redis connection URL."""
        # Build URL from current settings - password takes precedence
        host = self.redis.redis_host
        port = self.redis.redis_port
        db = self.redis.redis_db
        password = self.redis.redis_password

        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        elif self.redis.redis_url:
            return str(self.redis.redis_url)
        else:
            return f"redis://{host}:{port}/{db}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings()
    return _settings


# Convenience functions for common settings
def get_database_url() -> str:
    """Get the database URL."""
    return get_settings().get_database_url()


def get_redis_url() -> str:
    """Get the Redis URL."""
    return get_settings().get_redis_url()


def is_development() -> bool:
    """Check if running in development mode."""
    return get_settings().is_development()


def is_production() -> bool:
    """Check if running in production mode."""
    return get_settings().is_production()


def get_openai_api_key() -> str:
    """Get the OpenAI API key."""
    return get_settings().openai.openai_api_key


def get_jwt_secret() -> str:
    """Get the JWT secret key."""
    return get_settings().security.jwt_secret_key


if __name__ == "__main__":
    # Example usage and validation
    settings = get_settings()
    print(f"App: {settings.app.app_name} v{settings.app.app_version}")
    print(f"Environment: {settings.app.environment}")
    print(f"Database URL: {settings.get_database_url()}")
    print(f"Redis URL: {settings.get_redis_url()}")
    print(f"Debug mode: {settings.app.debug}")
