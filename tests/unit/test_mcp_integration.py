#!/usr/bin/env python3
"""
Tests for MCP Integration Module

This module tests the OpenAPI analyzer, server generator, and registry components
of the MCP integration system.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from mcp.openapi_analyzer import HTTPMethod, OpenAPIAnalyzer, ParameterLocation
from mcp.registry import MCPServerInfo, MCPServerRegistry, ServerStatus
from mcp.server_generator import (
    GeneratedFile,
    MCPServerGenerator,
    ServerGenerationConfig,
)


class TestOpenAPIAnalyzer:
    """Test OpenAPI specification analyzer."""

    @pytest.fixture
    def sample_openapi_spec(self):
        """Sample OpenAPI specification for testing."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A test API for MCP integration",
            },
            "servers": [{"url": "https://api.test.com"}],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "summary": "Get all users",
                        "description": "Retrieve a list of all users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer"},
                                "description": "Maximum number of users to return",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "object"},
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/users/{id}": {
                    "get": {
                        "operationId": "getUserById",
                        "summary": "Get user by ID",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                                "description": "User ID",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "User found",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            }
                        },
                    }
                },
            },
        }

    @pytest.fixture
    def analyzer(self):
        """OpenAPI analyzer instance."""
        return OpenAPIAnalyzer()

    def test_parse_spec_dict(self, analyzer, sample_openapi_spec):
        """Test parsing OpenAPI spec from dictionary."""
        result = analyzer.parse_spec(sample_openapi_spec)
        assert result == sample_openapi_spec
        assert analyzer.spec == sample_openapi_spec

    def test_parse_spec_yaml_string(self, analyzer, sample_openapi_spec):
        """Test parsing OpenAPI spec from YAML string."""
        yaml_content = yaml.dump(sample_openapi_spec)
        result = analyzer.parse_spec(yaml_content)
        assert result == sample_openapi_spec

    def test_parse_spec_json_string(self, analyzer, sample_openapi_spec):
        """Test parsing OpenAPI spec from JSON string."""
        json_content = json.dumps(sample_openapi_spec)
        result = analyzer.parse_spec(json_content)
        assert result == sample_openapi_spec

    def test_parse_spec_invalid(self, analyzer):
        """Test parsing invalid OpenAPI spec."""
        with pytest.raises(ValueError):
            analyzer.parse_spec("invalid: content: [")

    def test_analyze_spec(self, analyzer, sample_openapi_spec):
        """Test complete OpenAPI spec analysis."""
        result = analyzer.analyze_spec(sample_openapi_spec)

        assert result.total_endpoints == 2
        assert len(result.endpoints) == 2
        assert result.spec_info["title"] == "Test API"
        assert result.spec_info["version"] == "1.0.0"

        # Check endpoints
        endpoints = {ep.operation_id: ep for ep in result.endpoints}
        assert "getUsers" in endpoints
        assert "getUserById" in endpoints

        # Check endpoint details
        get_users = endpoints["getUsers"]
        assert get_users.method == HTTPMethod.GET
        assert get_users.path == "/users"
        assert len(get_users.parameters) == 1
        assert get_users.parameters[0].name == "limit"
        assert get_users.parameters[0].location == ParameterLocation.QUERY

        get_user_by_id = endpoints["getUserById"]
        assert get_user_by_id.method == HTTPMethod.GET
        assert get_user_by_id.path == "/users/{id}"
        assert len(get_user_by_id.parameters) == 1
        assert get_user_by_id.parameters[0].name == "id"
        assert get_user_by_id.parameters[0].location == ParameterLocation.PATH
        assert get_user_by_id.parameters[0].required is True

    def test_complexity_scoring(self, analyzer, sample_openapi_spec):
        """Test endpoint complexity scoring."""
        result = analyzer.analyze_spec(sample_openapi_spec)

        for endpoint in result.endpoints:
            assert 1 <= endpoint.complexity_score <= 10
            assert isinstance(endpoint.complexity_score, int)

    def test_functionality_groups(self, analyzer, sample_openapi_spec):
        """Test functionality grouping."""
        result = analyzer.analyze_spec(sample_openapi_spec)

        assert len(result.functionality_groups) > 0
        for group in result.functionality_groups:
            assert group.name
            assert len(group.endpoints) > 0
            assert group.total_complexity > 0

    def test_recommended_endpoints(self, analyzer, sample_openapi_spec):
        """Test endpoint recommendations."""
        result = analyzer.analyze_spec(sample_openapi_spec)

        assert len(result.recommended_endpoints) > 0
        for endpoint in result.recommended_endpoints:
            assert endpoint.complexity_score <= analyzer.max_complexity_threshold
            assert not endpoint.deprecated


class TestServerGenerationConfig:
    """Test server generation configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ServerGenerationConfig(
            server_name="Test Server", package_name="test_server"
        )

        assert config.server_name == "Test Server"
        assert config.package_name == "test_server"
        assert config.version == "1.0.0"
        assert config.include_async is True
        assert config.include_error_handling is True
        assert config.auth_type == "none"
        assert config.max_endpoints == 20
        assert config.max_complexity == 8

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ServerGenerationConfig(
            server_name="Custom Server",
            package_name="custom_server",
            version="2.0.0",
            base_url="https://custom.api.com",
            auth_type="bearer",
            max_endpoints=10,
            include_logging=False,
        )

        assert config.server_name == "Custom Server"
        assert config.version == "2.0.0"
        assert config.base_url == "https://custom.api.com"
        assert config.auth_type == "bearer"
        assert config.max_endpoints == 10
        assert config.include_logging is False


class TestMCPServerGenerator:
    """Test MCP server generator."""

    @pytest.fixture
    def config(self):
        """Test server generation configuration."""
        return ServerGenerationConfig(
            server_name="Test MCP Server",
            package_name="test_mcp_server",
            server_description="A test MCP server",
            base_url="https://api.test.com",
        )

    @pytest.fixture
    def sample_openapi_spec(self):
        """Simple OpenAPI spec for testing."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "getTest",
                        "summary": "Test endpoint",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = MCPServerGenerator()
        assert generator.template_dir
        assert generator.jinja_env

    def test_template_directory_setup(self):
        """Test template directory setup."""
        generator = MCPServerGenerator()
        template_dir = Path(generator.template_dir)
        assert template_dir.exists()
        assert (template_dir / "server_main.py.j2").exists()

    def test_jinja_filters(self):
        """Test custom Jinja2 filters."""
        generator = MCPServerGenerator()

        # Test snake_case filter
        assert generator._to_snake_case("TestName") == "test_name"
        assert generator._to_snake_case("test-name") == "test_name"
        assert generator._to_snake_case("TestAPIName") == "test_api_name"

        # Test camel_case filter
        assert generator._to_camel_case("test_name") == "testName"
        assert generator._to_camel_case("test-name") == "testName"

        # Test pascal_case filter
        assert generator._to_pascal_case("test_name") == "TestName"
        assert generator._to_pascal_case("test-name") == "TestName"

        # Test python_type filter
        assert generator._to_python_type("string") == "str"
        assert generator._to_python_type("integer") == "int"
        assert generator._to_python_type("boolean") == "bool"
        assert generator._to_python_type("unknown") == "Any"

    def test_generate_server_success(self, config, sample_openapi_spec):
        """Test successful server generation."""
        generator = MCPServerGenerator()
        result = generator.generate_server(sample_openapi_spec, config)

        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.generated_files) > 0
        assert len(result.selected_endpoints) > 0

        # Check that main server file is generated
        server_files = [f for f in result.generated_files if f.file_type == "python"]
        assert len(server_files) > 0

        # Check generation summary
        assert result.generation_summary["total_files"] > 0
        assert result.generation_summary["selected_endpoints"] > 0

    def test_generate_requirements_file(self, config):
        """Test requirements.txt generation."""
        generator = MCPServerGenerator()
        requirements_file = generator._generate_requirements_file(config)

        assert requirements_file.path == "requirements.txt"
        assert requirements_file.file_type == "text"
        assert "mcp>=1.0.0" in requirements_file.content
        assert "httpx>=0.25.0" in requirements_file.content
        assert "pydantic>=2.0.0" in requirements_file.content

    def test_generate_dockerfile(self, config):
        """Test Dockerfile generation."""
        generator = MCPServerGenerator()
        dockerfile = generator._generate_dockerfile(config)

        assert dockerfile.path == "Dockerfile"
        assert dockerfile.file_type == "dockerfile"
        assert "FROM python:" in dockerfile.content
        assert config.package_name in dockerfile.content

    def test_endpoint_selection(self, config, sample_openapi_spec):
        """Test endpoint selection logic."""
        generator = MCPServerGenerator()

        # Mock analyzer result
        mock_analyzer = MagicMock()
        mock_endpoint = MagicMock()
        mock_endpoint.complexity_score = 5
        mock_endpoint.deprecated = False
        mock_analyzer.analyze_spec.return_value.recommended_endpoints = [mock_endpoint]
        mock_analyzer.analyze_spec.return_value.endpoints = [mock_endpoint]

        with patch("mcp.server_generator.OpenAPIAnalyzer", return_value=mock_analyzer):
            result = generator.generate_server(sample_openapi_spec, config)
            assert len(result.selected_endpoints) == 1

    def test_write_server_to_disk(self, config, sample_openapi_spec):
        """Test writing generated server to disk."""
        generator = MCPServerGenerator()
        result = generator.generate_server(sample_openapi_spec, config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = generator.write_server_to_disk(result, temp_dir)
            output_dir = Path(output_path)

            assert output_dir.exists()
            assert (output_dir / "requirements.txt").exists()
            assert (output_dir / "Dockerfile").exists()
            assert (output_dir / config.package_name / "server.py").exists()


class TestMCPServerRegistry:
    """Test MCP server registry."""

    @pytest.fixture
    def registry(self):
        """Test registry with temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield MCPServerRegistry(temp_dir)

    @pytest.fixture
    def config(self):
        """Test server configuration."""
        return ServerGenerationConfig(
            server_name="Test Server", package_name="test_server"
        )

    @pytest.fixture
    def sample_spec(self):
        """Sample OpenAPI spec."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "getTest",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert registry.registry_dir.exists()
        assert isinstance(registry.servers, dict)
        assert isinstance(registry.processes, dict)
        assert registry.generator

    @pytest.mark.asyncio
    async def test_register_server(self, registry, config, sample_spec):
        """Test server registration."""
        server_info = await registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_spec,
            config=config,
            description="A test server",
            tags=["test"],
            auto_generate=False,  # Skip generation for this test
        )

        assert server_info.id == "test-server"
        assert server_info.name == "Test Server"
        assert server_info.description == "A test server"
        assert "test" in server_info.tags
        assert server_info.status == ServerStatus.CREATED

        # Check registry state
        assert "test-server" in registry.servers
        assert registry.get_server("test-server") == server_info

    @pytest.mark.asyncio
    async def test_register_duplicate_server(self, registry, config, sample_spec):
        """Test registering duplicate server ID."""
        await registry.register_server(
            "test-server", "Test", sample_spec, config, auto_generate=False
        )

        with pytest.raises(ValueError, match="already exists"):
            await registry.register_server(
                "test-server", "Test2", sample_spec, config, auto_generate=False
            )

    def test_list_servers(self, registry):
        """Test listing servers."""
        servers = registry.list_servers()
        assert isinstance(servers, list)

        # Test filtering by status
        servers_by_status = registry.list_servers(status=ServerStatus.CREATED)
        assert isinstance(servers_by_status, list)

    @pytest.mark.asyncio
    async def test_health_check_nonexistent(self, registry):
        """Test health check for non-existent server."""
        result = await registry.health_check("nonexistent")
        assert result["status"] == "not_found"

    def test_registry_stats(self, registry):
        """Test registry statistics."""
        stats = registry.get_registry_stats()

        assert "total_servers" in stats
        assert "status_distribution" in stats
        assert "running_servers" in stats
        assert "total_endpoints" in stats
        assert "total_tools" in stats
        assert "average_complexity" in stats
        assert "registry_path" in stats

        assert isinstance(stats["total_servers"], int)
        assert isinstance(stats["status_distribution"], dict)

    def test_registry_persistence(self):
        """Test registry persistence across instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first registry and add a server
            registry1 = MCPServerRegistry(temp_dir)
            server_info = MCPServerInfo(
                id="test-server",
                name="Test Server",
                generation_config=ServerGenerationConfig(
                    server_name="Test", package_name="test"
                ),
            )
            registry1.servers["test-server"] = server_info
            registry1._save_registry()

            # Create second registry and check if server is loaded
            registry2 = MCPServerRegistry(temp_dir)
            assert "test-server" in registry2.servers
            assert registry2.servers["test-server"].name == "Test Server"


class TestGeneratedFile:
    """Test generated file model."""

    def test_generated_file_creation(self):
        """Test creating a generated file."""
        file_info = GeneratedFile(
            path="test.py",
            content="print('hello')",
            description="Test file",
            file_type="python",
        )

        assert file_info.path == "test.py"
        assert file_info.content == "print('hello')"
        assert file_info.description == "Test file"
        assert file_info.file_type == "python"


class TestMCPServerInfo:
    """Test MCP server info model."""

    def test_server_info_creation(self):
        """Test creating server info."""
        config = ServerGenerationConfig(
            server_name="Test Server", package_name="test_server"
        )

        server_info = MCPServerInfo(
            id="test-server",
            name="Test Server",
            description="A test server",
            generation_config=config,
        )

        assert server_info.id == "test-server"
        assert server_info.name == "Test Server"
        assert server_info.description == "A test server"
        assert server_info.status == ServerStatus.CREATED
        assert server_info.endpoint_count == 0
        assert server_info.tool_count == 0
        assert server_info.complexity_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
