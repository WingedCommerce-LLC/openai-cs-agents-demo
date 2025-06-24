"""
Pytest configuration and fixtures for OpenAI Agents Enterprise Template.

This module provides shared fixtures and configuration for all test suites,
ensuring consistent test environments and utilities across unit, integration,
and end-to-end tests.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base

# Import our application modules
from security.credential_manager import CredentialManager, InMemoryCredentialStore
from security.env_sanitizer import EnvironmentSanitizer

# Test database URL - use in-memory SQLite for speed
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Clean up
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def credential_manager():
    """Create a test credential manager with in-memory store."""
    store = InMemoryCredentialStore()
    manager = CredentialManager(store, encryption_key="test-key-for-testing-only")
    return manager


@pytest.fixture
def env_sanitizer():
    """Create an environment sanitizer for testing."""
    return EnvironmentSanitizer()


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for testing."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for testing."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    return mock_redis


@pytest.fixture
def test_tenant_id():
    """Provide a consistent test tenant ID."""
    return "test-tenant-123"


@pytest.fixture
def test_user_id():
    """Provide a consistent test user ID."""
    return "test-user-456"


@pytest.fixture
def sample_openapi_spec():
    """Provide a sample OpenAPI specification for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "list_users",
                    "summary": "List users",
                    "tags": ["users"],
                    "responses": {"200": {"description": "Success"}},
                },
                "post": {
                    "operationId": "create_user",
                    "summary": "Create user",
                    "tags": ["users"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
    }


@pytest.fixture
def test_environment_vars():
    """Provide test environment variables."""
    return {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379",
        "OPENAI_API_KEY": "sk-test-key-1234567890",
        "SECRET_KEY": "test-secret-key",
        "DEBUG": "true",
        "ENVIRONMENT": "test",
    }


@pytest.fixture
def sensitive_environment_vars():
    """Provide environment variables with sensitive data for testing sanitization."""
    return {
        "API_KEY": "sk-1234567890abcdef",
        "SECRET_TOKEN": "secret-token-value",
        "DATABASE_PASSWORD": "super-secret-password",
        "OAUTH_CLIENT_SECRET": "oauth-secret-123",
        "NORMAL_VAR": "this-is-safe",
        "DEBUG": "true",
    }


# Coverage configuration
pytest_plugins = ["pytest_cov"]


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security-related")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Add security marker for security-related tests
        if "security" in str(item.fspath) or "auth" in str(item.fspath):
            item.add_marker(pytest.mark.security)


# Async test support
@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"
