"""
Tests for MCP API endpoints functionality.
"""

# Import the modules to test
from mcp.server_generator import ServerGenerationConfig


def test_server_generation_config_basic():
    """Test basic ServerGenerationConfig functionality."""
    # Test minimal config
    config = ServerGenerationConfig(
        server_name="test-server", package_name="test_package"
    )
    assert config.server_name == "test-server"
    assert config.package_name == "test_package"
    assert config.author == "Auto-generated"
    assert config.version == "1.0.0"


def test_server_generation_config_full():
    """Test ServerGenerationConfig with all parameters."""
    config = ServerGenerationConfig(
        server_name="full-test-server",
        package_name="full_test_package",
        author="Test Author",
        version="2.0.0",
        base_url="https://api.test.com",
        include_async=False,
        include_error_handling=False,
        max_endpoints=10,
        max_complexity=5,
    )
    assert config.server_name == "full-test-server"
    assert config.package_name == "full_test_package"
    assert config.author == "Test Author"
    assert config.version == "2.0.0"
    assert config.base_url == "https://api.test.com"
    assert config.include_async is False
    assert config.include_error_handling is False
    assert config.max_endpoints == 10
    assert config.max_complexity == 5


def test_mcp_server_generator_import():
    """Test that MCP server generator can be imported."""
    from mcp.server_generator import MCPServerGenerator

    generator = MCPServerGenerator()
    assert generator is not None
    assert hasattr(generator, "generate_server")
    assert hasattr(generator, "write_server_to_disk")


def test_mcp_registry_import():
    """Test that MCP registry can be imported."""
    from mcp.registry import MCPServerRegistry, get_registry

    registry = MCPServerRegistry()
    assert registry is not None
    assert hasattr(registry, "register_server")
    assert hasattr(registry, "list_servers")
    assert hasattr(registry, "get_server")

    # Test global registry function
    global_registry = get_registry()
    assert global_registry is not None


def test_mcp_openapi_analyzer_import():
    """Test that OpenAPI analyzer can be imported."""
    from mcp.openapi_analyzer import OpenAPIAnalyzer

    analyzer = OpenAPIAnalyzer()
    assert analyzer is not None
    assert hasattr(analyzer, "analyze_spec")
