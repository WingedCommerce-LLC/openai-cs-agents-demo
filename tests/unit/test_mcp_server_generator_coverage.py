#!/usr/bin/env python3
"""
Comprehensive tests for MCP Server Generator to improve coverage

This module provides extensive test coverage for the MCP server generator
including template rendering, file generation, and error scenarios.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp.openapi_analyzer import OpenAPIAnalysisResult
from mcp.server_generator import (
    GeneratedFile,
    MCPServerGenerator,
    ServerGenerationConfig,
    ServerGenerationResult,
    generate_mcp_server_from_file,
    generate_mcp_server_from_url,
)


class TestMCPServerGeneratorComprehensive:
    """Comprehensive tests for MCP server generator."""

    @pytest.fixture
    def generator(self):
        """Create a server generator instance."""
        return MCPServerGenerator()

    @pytest.fixture
    def config(self):
        """Sample server generation configuration."""
        return ServerGenerationConfig(
            server_name="Test MCP Server",
            package_name="test_mcp_server",
            server_description="A test MCP server",
            base_url="https://api.test.com",
            auth_type="bearer",
            auth_header="Authorization",
            include_logging=True,
            include_rate_limiting=True,
            include_caching=True,
            create_dockerfile=True,
            create_requirements=True,
            create_readme=True,
            create_tests=True,
        )

    @pytest.fixture
    def simple_openapi_spec(self):
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

    @pytest.fixture
    def complex_openapi_spec(self):
        """Complex OpenAPI spec for testing."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Complex API",
                "version": "2.0.0",
                "description": "A complex API for testing",
            },
            "servers": [{"url": "https://api.complex.com"}],
            "paths": {
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
                            },
                            {
                                "name": "include",
                                "in": "query",
                                "schema": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "description": "Fields to include",
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "User found",
                                "content": {
                                    "application/json": {"schema": {"type": "object"}}
                                },
                            },
                            "404": {"description": "User not found"},
                        },
                    },
                    "post": {
                        "operationId": "createUser",
                        "summary": "Create user",
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
                                        "required": ["name", "email"],
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {"description": "User created"},
                            "400": {"description": "Invalid input"},
                        },
                    },
                },
                "/health": {
                    "get": {
                        "operationId": "getHealth",
                        "summary": "Health check",
                        "deprecated": True,
                        "responses": {"200": {"description": "Healthy"}},
                    }
                },
            },
        }

    def test_generator_initialization_with_custom_template_dir(self):
        """Test generator initialization with custom template directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = MCPServerGenerator(template_dir=temp_dir)
            assert generator.template_dir == temp_dir

    def test_jinja_environment_setup(self, generator):
        """Test Jinja2 environment setup with filters and globals."""
        env = generator.jinja_env

        # Test filters
        assert "snake_case" in env.filters
        assert "camel_case" in env.filters
        assert "pascal_case" in env.filters
        assert "python_type" in env.filters
        assert "json_schema" in env.filters
        assert "escape_quotes" in env.filters
        assert "indent_lines" in env.filters

        # Test globals
        assert "generate_tool_name" in env.globals
        assert "generate_parameter_validation" in env.globals
        assert "generate_request_body" in env.globals
        assert "generate_response_handling" in env.globals

    def test_jinja_filters(self, generator):
        """Test custom Jinja2 filters."""
        # Test snake_case filter
        assert generator._to_snake_case("TestAPIName") == "test_api_name"
        assert generator._to_snake_case("HTTPSConnection") == "https_connection"
        assert generator._to_snake_case("simple") == "simple"
        assert generator._to_snake_case("test-name") == "test_name"
        assert generator._to_snake_case("test.name") == "test_name"

        # Test camel_case filter
        assert generator._to_camel_case("test_name") == "testName"
        assert generator._to_camel_case("test-name") == "testName"
        assert generator._to_camel_case("simple") == "simple"

        # Test pascal_case filter
        assert generator._to_pascal_case("test_name") == "TestName"
        assert generator._to_pascal_case("test-name") == "TestName"
        assert generator._to_pascal_case("simple") == "Simple"

        # Test python_type filter
        assert generator._to_python_type("string") == "str"
        assert generator._to_python_type("integer") == "int"
        assert generator._to_python_type("number") == "float"
        assert generator._to_python_type("boolean") == "bool"
        assert generator._to_python_type("array") == "List[Any]"
        assert generator._to_python_type("object") == "Dict[str, Any]"
        assert generator._to_python_type("unknown") == "Any"

        # Test json_schema filter
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = generator._to_json_schema(schema)
        assert json.loads(result) == schema

        # Test escape_quotes filter
        assert generator._escape_quotes('test "quote"') == 'test \\"quote\\"'
        assert generator._escape_quotes("test 'quote'") == "test \\'quote\\'"

        # Test indent_lines filter
        text = "line1\nline2\nline3"
        indented = generator._indent_lines(text, 2)
        lines = indented.split("\n")
        assert lines[0] == "  line1"
        assert lines[1] == "  line2"
        assert lines[2] == "  line3"

    def test_jinja_global_functions(self, generator):
        """Test custom Jinja2 global functions."""
        # Mock endpoint for testing
        mock_endpoint = MagicMock()
        mock_endpoint.mcp_tool_name = None
        mock_endpoint.method.lower.return_value = "get"
        mock_endpoint.operation_id = "getTest"
        mock_endpoint.parameters = []
        mock_endpoint.request_body = None
        mock_endpoint.responses = []

        # Test generate_tool_name
        tool_name = generator._generate_tool_name(mock_endpoint)
        assert tool_name == "get_getTest"

        mock_endpoint.mcp_tool_name = "custom_tool"
        tool_name = generator._generate_tool_name(mock_endpoint)
        assert tool_name == "custom_tool"

        # Test generate_parameter_validation
        mock_param = MagicMock()
        mock_param.name = "test_param"
        mock_param.required = True
        mock_endpoint.parameters = [mock_param]

        validation = generator._generate_parameter_validation(mock_endpoint)
        assert "test_param" in validation
        assert "ValueError" in validation

        # Test generate_request_body
        mock_endpoint.request_body = None
        body_code = generator._generate_request_body(mock_endpoint)
        assert body_code == "data = None"

        mock_request_body = MagicMock()
        mock_request_body.content_type = "application/json"
        mock_endpoint.request_body = mock_request_body
        body_code = generator._generate_request_body(mock_endpoint)
        assert "json.dumps" in body_code

        # Test generate_response_handling
        mock_endpoint.responses = []
        response_code = generator._generate_response_handling(mock_endpoint)
        assert "response.json()" in response_code

        mock_response = MagicMock()
        mock_response.status_code = "200"
        mock_response.content_type = "application/json"
        mock_endpoint.responses = [mock_response]
        response_code = generator._generate_response_handling(mock_endpoint)
        assert "response.json()" in response_code

    def test_generate_requirements_file_with_all_options(self, generator):
        """Test requirements file generation with all options enabled."""
        config = ServerGenerationConfig(
            server_name="Test Server",
            package_name="test_server",
            include_logging=True,
            include_rate_limiting=True,
            include_caching=True,
        )

        requirements_file = generator._generate_requirements_file(config)

        assert requirements_file.path == "requirements.txt"
        assert requirements_file.file_type == "text"
        assert "mcp>=1.0.0" in requirements_file.content
        assert "httpx>=0.25.0" in requirements_file.content
        assert "pydantic>=2.0.0" in requirements_file.content
        assert "structlog>=23.0.0" in requirements_file.content
        assert "aiohttp-ratelimiter>=1.0.0" in requirements_file.content
        assert "aiocache>=0.12.0" in requirements_file.content

    def test_generate_requirements_file_minimal(self, generator):
        """Test requirements file generation with minimal options."""
        config = ServerGenerationConfig(
            server_name="Test Server",
            package_name="test_server",
            include_logging=False,
            include_rate_limiting=False,
            include_caching=False,
        )

        requirements_file = generator._generate_requirements_file(config)

        assert "mcp>=1.0.0" in requirements_file.content
        assert "httpx>=0.25.0" in requirements_file.content
        assert "pydantic>=2.0.0" in requirements_file.content
        assert "structlog" not in requirements_file.content
        assert "aiohttp-ratelimiter" not in requirements_file.content
        assert "aiocache" not in requirements_file.content

    def test_generate_config_files_with_auth(self, generator):
        """Test configuration file generation with authentication."""
        config = ServerGenerationConfig(
            server_name="Auth Server",
            package_name="auth_server",
            version="2.0.0",
            base_url="https://api.auth.com",
            auth_type="bearer",
            auth_header="X-API-Key",
        )

        config_files = generator._generate_config_files(config)

        # Check __init__.py
        init_file = next(f for f in config_files if f.path.endswith("__init__.py"))
        assert "Auth Server" in init_file.content
        assert "2.0.0" in init_file.content

        # Check .env.example
        env_file = next(f for f in config_files if f.path == ".env.example")
        assert "Auth Server Configuration" in env_file.content
        assert "https://api.auth.com" in env_file.content
        assert "X_API_KEY_TOKEN=your_token_here" in env_file.content

    def test_generate_config_files_no_auth(self, generator):
        """Test configuration file generation without authentication."""
        config = ServerGenerationConfig(
            server_name="No Auth Server",
            package_name="no_auth_server",
            auth_type="none",
        )

        config_files = generator._generate_config_files(config)

        # Check .env.example
        env_file = next(f for f in config_files if f.path == ".env.example")
        assert "TOKEN" not in env_file.content

    def test_calculate_complexity_distribution(self, generator):
        """Test complexity distribution calculation."""
        # Mock endpoints with different complexity scores
        endpoints = []
        for score in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            mock_endpoint = MagicMock()
            mock_endpoint.complexity_score = score
            endpoints.append(mock_endpoint)

        distribution = generator._calculate_selected_complexity_distribution(endpoints)

        assert distribution["simple"] == 3  # scores 1-3
        assert distribution["moderate"] == 3  # scores 4-6
        assert distribution["complex"] == 2  # scores 7-8
        assert distribution["very_complex"] == 2  # scores 9-10

    def test_select_endpoints_with_filters(self, generator):
        """Test endpoint selection with various filters."""
        # Mock analysis result
        mock_analysis = MagicMock()

        # Create mock endpoints
        endpoints = []
        for i in range(5):
            endpoint = MagicMock()
            endpoint.complexity_score = i + 1
            endpoint.deprecated = i == 4  # Last one is deprecated
            endpoints.append(endpoint)

        mock_analysis.recommended_endpoints = endpoints

        # Test with default config
        config = ServerGenerationConfig(
            server_name="Test",
            package_name="test",
            max_complexity=3,
            max_endpoints=2,
            include_deprecated=False,
        )

        selected = generator._select_endpoints(mock_analysis, config)

        # Should select first 2 non-deprecated endpoints with complexity <= 3
        assert len(selected) == 2
        assert all(ep.complexity_score <= 3 for ep in selected)
        assert all(not ep.deprecated for ep in selected)

    def test_select_endpoints_include_deprecated(self, generator):
        """Test endpoint selection including deprecated endpoints."""
        mock_analysis = MagicMock()

        # Create mock endpoints
        endpoints = []
        for i in range(3):
            endpoint = MagicMock()
            endpoint.complexity_score = i + 1
            endpoint.deprecated = i == 2  # Last one is deprecated
            endpoints.append(endpoint)

        mock_analysis.recommended_endpoints = endpoints

        config = ServerGenerationConfig(
            server_name="Test",
            package_name="test",
            max_complexity=5,
            max_endpoints=5,
            include_deprecated=True,
        )

        selected = generator._select_endpoints(mock_analysis, config)

        # Should include all endpoints including deprecated
        assert len(selected) == 3

    def test_write_server_to_disk_success(self, generator):
        """Test writing server files to disk successfully."""
        config = ServerGenerationConfig(
            server_name="Test Server",
            package_name="test_server",
        )

        # Create mock generation result
        result = ServerGenerationResult(
            config=config,
            analysis_result=OpenAPIAnalysisResult(),
            generated_files=[
                GeneratedFile(
                    path="test_file.py",
                    content="# Test content",
                    description="Test file",
                    file_type="python",
                ),
                GeneratedFile(
                    path="subdir/another_file.txt",
                    content="Another test",
                    description="Another file",
                    file_type="text",
                ),
            ],
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = generator.write_server_to_disk(result, temp_dir)

            # Check that files were created
            assert Path(output_path).exists()
            assert (Path(output_path) / "test_file.py").exists()
            assert (Path(output_path) / "subdir" / "another_file.txt").exists()

            # Check file contents
            with open(Path(output_path) / "test_file.py") as f:
                assert f.read() == "# Test content"

    def test_write_server_to_disk_default_output_dir(self, generator):
        """Test writing server files using default output directory."""
        config = ServerGenerationConfig(
            server_name="Test Server",
            package_name="test_server",
            output_dir="./test_output",
        )

        result = ServerGenerationResult(
            config=config,
            analysis_result=OpenAPIAnalysisResult(),
            generated_files=[
                GeneratedFile(
                    path="test.py",
                    content="test",
                    description="Test",
                    file_type="python",
                )
            ],
            success=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory to avoid creating files in project
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                output_path = generator.write_server_to_disk(result)
                assert "test_output" in output_path
            finally:
                os.chdir(old_cwd)


class TestConvenienceFunctions:
    """Test convenience functions for server generation."""

    @pytest.fixture
    def config(self):
        """Sample configuration."""
        return ServerGenerationConfig(
            server_name="Convenience Test",
            package_name="convenience_test",
        )

    def test_generate_mcp_server_from_file(self, config):
        """Test generating server from OpenAPI file."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "File API", "version": "1.0.0"},
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "getTest",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(openapi_spec, f)
            temp_file = f.name

        try:
            with patch(
                "mcp.server_generator.MCPServerGenerator"
            ) as mock_generator_class:
                mock_generator = MagicMock()
                mock_generator_class.return_value = mock_generator

                mock_result = MagicMock()
                mock_result.success = True
                mock_generator.generate_server.return_value = mock_result

                result = generate_mcp_server_from_file(temp_file, config)

                assert mock_generator.generate_server.called
                assert result == mock_result
        finally:
            Path(temp_file).unlink()

    def test_generate_mcp_server_from_file_with_output_dir(self, config):
        """Test generating server from file with output directory."""
        openapi_spec = {"openapi": "3.0.0", "info": {"title": "Test"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(openapi_spec, f)
            temp_file = f.name

        try:
            with tempfile.TemporaryDirectory() as output_dir, patch(
                "mcp.server_generator.MCPServerGenerator"
            ) as mock_generator_class:
                mock_generator = MagicMock()
                mock_generator_class.return_value = mock_generator

                mock_result = MagicMock()
                mock_result.success = True
                mock_generator.generate_server.return_value = mock_result

                generate_mcp_server_from_file(temp_file, config, output_dir)

                # Should call write_server_to_disk
                # when success=True and output_dir provided
                mock_generator.write_server_to_disk.assert_called_once_with(
                    mock_result, output_dir
                )
        finally:
            Path(temp_file).unlink()

    def test_generate_mcp_server_from_url(self, config):
        """Test generating server from OpenAPI URL."""
        mock_response = MagicMock()
        mock_response.text = '{"openapi": "3.0.0", "info": {"title": "URL API"}}'

        with patch("httpx.Client") as mock_client_class, patch(
            "mcp.server_generator.MCPServerGenerator"
        ) as mock_generator_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            mock_generator = MagicMock()
            mock_generator_class.return_value = mock_generator

            mock_result = MagicMock()
            mock_result.success = True
            mock_generator.generate_server.return_value = mock_result

            result = generate_mcp_server_from_url(
                "https://api.example.com/openapi.json", config
            )

            mock_client.get.assert_called_once_with(
                "https://api.example.com/openapi.json"
            )
            mock_response.raise_for_status.assert_called_once()
            mock_generator.generate_server.assert_called_once()
            assert result == mock_result

    def test_generate_mcp_server_from_url_with_output_dir(self, config):
        """Test generating server from URL with output directory."""
        mock_response = MagicMock()
        mock_response.text = '{"openapi": "3.0.0"}'

        with tempfile.TemporaryDirectory() as output_dir, patch(
            "httpx.Client"
        ) as mock_client_class, patch(
            "mcp.server_generator.MCPServerGenerator"
        ) as mock_generator_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response

            mock_generator = MagicMock()
            mock_generator_class.return_value = mock_generator

            mock_result = MagicMock()
            mock_result.success = True
            mock_generator.generate_server.return_value = mock_result

            generate_mcp_server_from_url(
                "https://api.example.com/openapi.json", config, output_dir
            )

            # Should call write_server_to_disk when success=True and output_dir provided
            mock_generator.write_server_to_disk.assert_called_once_with(
                mock_result, output_dir
            )


class TestServerGenerationModels:
    """Test server generation data models."""

    def test_server_generation_config_defaults(self):
        """Test default values in ServerGenerationConfig."""
        config = ServerGenerationConfig(
            server_name="Test Server",
            package_name="test_server",
        )

        assert config.server_name == "Test Server"
        assert config.package_name == "test_server"
        assert config.version == "1.0.0"
        assert config.author == "Auto-generated"
        assert config.include_async is True
        assert config.include_error_handling is True
        assert config.include_logging is True
        assert config.include_validation is True
        assert config.include_rate_limiting is False
        assert config.include_caching is False
        assert config.auth_type == "none"
        assert config.auth_header == "Authorization"
        assert config.timeout == 30
        assert config.max_endpoints == 20
        assert config.max_complexity == 8
        assert config.include_deprecated is False
        assert config.output_dir == "./generated_server"
        assert config.create_dockerfile is True
        assert config.create_requirements is True
        assert config.create_readme is True
        assert config.create_tests is True

    def test_generated_file_model(self):
        """Test GeneratedFile model."""
        file_info = GeneratedFile(
            path="test/file.py",
            content="print('hello')",
            description="Test Python file",
            file_type="python",
        )

        assert file_info.path == "test/file.py"
        assert file_info.content == "print('hello')"
        assert file_info.description == "Test Python file"
        assert file_info.file_type == "python"

    def test_server_generation_result_defaults(self):
        """Test default values in ServerGenerationResult."""
        config = ServerGenerationConfig(server_name="Test", package_name="test")

        result = ServerGenerationResult(
            config=config,
            analysis_result=OpenAPIAnalysisResult(),
        )

        assert result.config == config
        assert result.generated_files == []
        assert result.selected_endpoints == []
        assert result.generation_summary == {}
        assert result.success is True
        assert result.errors == []
        assert result.warnings == []


if __name__ == "__main__":
    pytest.main([__file__])
