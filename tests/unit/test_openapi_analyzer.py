"""
Tests for OpenAPI Specification Analyzer

This module tests the comprehensive OpenAPI analysis functionality including
endpoint detection, complexity scoring, and MCP optimization features.
"""

import json
from unittest.mock import mock_open, patch

import pytest
import yaml

from mcp.openapi_analyzer import (
    EndpointInfo,
    EndpointParameter,
    FunctionalityGroup,
    HTTPMethod,
    OpenAPIAnalyzer,
    ParameterLocation,
    RequestBodyInfo,
    ResponseInfo,
    analyze_openapi_file,
    analyze_openapi_url,
)


class TestOpenAPIAnalyzer:
    """Test the OpenAPIAnalyzer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = OpenAPIAnalyzer()
        self.sample_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A test API for unit testing",
            },
            "servers": [{"url": "https://api.example.com/v1"}],
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "summary": "Get all users",
                        "description": "Retrieve a list of all users",
                        "tags": ["users"],
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "integer", "default": 10},
                                "description": "Number of users to return",
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/User"
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    },
                    "post": {
                        "operationId": "createUser",
                        "summary": "Create a new user",
                        "tags": ["users"],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "responses": {
                            "201": {"description": "User created"},
                            "400": {"description": "Invalid input"},
                        },
                    },
                },
                "/users/{id}": {
                    "get": {
                        "operationId": "getUserById",
                        "summary": "Get user by ID",
                        "tags": ["users"],
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {
                            "200": {"description": "User found"},
                            "404": {"description": "User not found"},
                        },
                    }
                },
                "/admin/settings": {
                    "put": {
                        "operationId": "updateSettings",
                        "summary": "Update admin settings",
                        "tags": ["admin"],
                        "deprecated": True,
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "setting1": {"type": "string"},
                                            "setting2": {"type": "boolean"},
                                            "setting3": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {"description": "Settings updated"},
                            "401": {"description": "Unauthorized"},
                            "403": {"description": "Forbidden"},
                        },
                    }
                },
            },
            "components": {
                "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
            },
        }

    def test_parse_spec_dict(self):
        """Test parsing OpenAPI spec from dictionary."""
        result = self.analyzer.parse_spec(self.sample_spec)
        assert result == self.sample_spec
        assert self.analyzer.spec == self.sample_spec

    def test_parse_spec_yaml_string(self):
        """Test parsing OpenAPI spec from YAML string."""
        yaml_content = yaml.dump(self.sample_spec)
        result = self.analyzer.parse_spec(yaml_content)
        assert result["info"]["title"] == "Test API"

    def test_parse_spec_json_string(self):
        """Test parsing OpenAPI spec from JSON string."""
        json_content = json.dumps(self.sample_spec)
        result = self.analyzer.parse_spec(json_content)
        assert result["info"]["title"] == "Test API"

    def test_parse_spec_invalid_format(self):
        """Test parsing invalid spec format raises error."""
        with pytest.raises(ValueError, match="Invalid OpenAPI specification format"):
            self.analyzer.parse_spec("invalid: content: [unclosed")

    def test_analyze_spec_complete(self):
        """Test complete spec analysis."""
        result = self.analyzer.analyze_spec(self.sample_spec)

        assert result.total_endpoints == 4
        assert len(result.endpoints) == 4
        assert len(result.functionality_groups) == 2  # users, admin
        assert result.spec_info["title"] == "Test API"
        assert result.spec_info["base_url"] == "https://api.example.com/v1"

    def test_extract_spec_info(self):
        """Test spec info extraction."""
        self.analyzer.spec = self.sample_spec
        info = self.analyzer._extract_spec_info()

        assert info["title"] == "Test API"
        assert info["version"] == "1.0.0"
        assert info["description"] == "A test API for unit testing"
        assert info["openapi_version"] == "3.0.0"
        assert info["base_url"] == "https://api.example.com/v1"
        assert "bearerAuth" in info["security_schemes"]

    def test_extract_base_url(self):
        """Test base URL extraction."""
        self.analyzer.spec = self.sample_spec
        base_url = self.analyzer._extract_base_url()
        assert base_url == "https://api.example.com/v1"

    def test_extract_base_url_empty(self):
        """Test base URL extraction with no servers."""
        self.analyzer.spec = {"servers": []}
        base_url = self.analyzer._extract_base_url()
        assert base_url == ""

    def test_analyze_endpoints(self):
        """Test endpoint analysis."""
        self.analyzer.spec = self.sample_spec
        endpoints = self.analyzer._analyze_endpoints()

        assert len(endpoints) == 4

        # Check GET /users endpoint
        get_users = next(ep for ep in endpoints if ep.operation_id == "getUsers")
        assert get_users.method == HTTPMethod.GET
        assert get_users.path == "/users"
        assert get_users.summary == "Get all users"
        assert "users" in get_users.tags
        assert len(get_users.parameters) == 1
        assert get_users.parameters[0].name == "limit"
        assert get_users.parameters[0].location == ParameterLocation.QUERY
        assert not get_users.deprecated

    def test_analyze_single_endpoint_with_request_body(self):
        """Test analyzing endpoint with request body."""
        operation = self.sample_spec["paths"]["/users"]["post"]
        endpoint = self.analyzer._analyze_single_endpoint("/users", "POST", operation)

        assert endpoint is not None
        assert endpoint.operation_id == "createUser"
        assert endpoint.method == HTTPMethod.POST
        assert endpoint.request_body is not None
        assert endpoint.request_body.required is True
        assert endpoint.request_body.content_type == "application/json"

    def test_analyze_single_endpoint_deprecated(self):
        """Test analyzing deprecated endpoint."""
        operation = self.sample_spec["paths"]["/admin/settings"]["put"]
        endpoint = self.analyzer._analyze_single_endpoint(
            "/admin/settings", "PUT", operation
        )

        assert endpoint is not None
        assert endpoint.deprecated is True
        assert len(endpoint.security_requirements) == 1
        assert (
            endpoint.complexity_score > 1
        )  # Should be higher due to deprecation and security

    def test_path_to_operation_id(self):
        """Test path to operation ID conversion."""
        assert self.analyzer._path_to_operation_id("/users") == "users"
        assert self.analyzer._path_to_operation_id("/users/{id}") == "users_by_id"
        assert (
            self.analyzer._path_to_operation_id("/admin/settings") == "admin_settings"
        )
        assert (
            self.analyzer._path_to_operation_id("/api/v1/complex-path")
            == "api_v1_complex_path"
        )

    def test_parse_parameters(self):
        """Test parameter parsing."""
        params = [
            {
                "name": "limit",
                "in": "query",
                "required": False,
                "schema": {"type": "integer", "default": 10},
                "description": "Number of items",
            },
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            },
        ]

        parsed = self.analyzer._parse_parameters(params)

        assert len(parsed) == 2
        assert parsed[0].name == "limit"
        assert parsed[0].type == "integer"
        assert parsed[0].required is False
        assert parsed[0].location == ParameterLocation.QUERY
        assert parsed[0].default_value == 10

        assert parsed[1].name == "id"
        assert parsed[1].required is True
        assert parsed[1].location == ParameterLocation.PATH

    def test_parse_request_body(self):
        """Test request body parsing."""
        request_body = {
            "required": True,
            "description": "User data",
            "content": {
                "application/json": {
                    "schema": {"type": "object"},
                    "examples": {"example1": {"value": {"name": "John"}}},
                }
            },
        }

        parsed = self.analyzer._parse_request_body(request_body)

        assert parsed is not None
        assert parsed.required is True
        assert parsed.description == "User data"
        assert parsed.content_type == "application/json"
        assert "example1" in parsed.examples

    def test_parse_request_body_none(self):
        """Test parsing None request body."""
        assert self.analyzer._parse_request_body(None) is None
        assert self.analyzer._parse_request_body({}) is None

    def test_parse_responses(self):
        """Test response parsing."""
        responses = {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"},
                        "examples": {"success": {"value": {"status": "ok"}}},
                    }
                },
            },
            "404": {"description": "Not found"},
        }

        parsed = self.analyzer._parse_responses(responses)

        assert len(parsed) == 2
        assert parsed[0].status_code == "200"
        assert parsed[0].description == "Success"
        assert parsed[0].content_type == "application/json"
        assert "success" in parsed[0].examples

        assert parsed[1].status_code == "404"
        assert parsed[1].description == "Not found"

    def test_calculate_complexity_score(self):
        """Test complexity score calculation."""
        operation = {"deprecated": False}
        parameters = [
            EndpointParameter(
                name="id", required=True, location=ParameterLocation.PATH
            ),
            EndpointParameter(
                name="limit", required=False, location=ParameterLocation.QUERY
            ),
        ]
        request_body = RequestBodyInfo(
            required=True,
            schema_info={"properties": {"name": {}, "email": {}, "age": {}}},
        )
        responses = [ResponseInfo(status_code="200"), ResponseInfo(status_code="400")]

        score = self.analyzer._calculate_complexity_score(
            operation, parameters, request_body, responses
        )

        # Base(1) + params(1.0) + required_params(0.3) + request_body(2) +
        # required_body(1) + properties(0.6) + responses(0.6) + path_params(0.4) = ~6.9
        assert 6 <= score <= 8

    def test_calculate_complexity_score_deprecated(self):
        """Test complexity score for deprecated endpoint."""
        operation = {"deprecated": True}
        score = self.analyzer._calculate_complexity_score(operation, [], None, [])
        assert score >= 3  # Base(1) + deprecated(2)

    def test_generate_mcp_tool_name(self):
        """Test MCP tool name generation."""
        assert (
            self.analyzer._generate_mcp_tool_name("getUsers", "GET", "/users")
            == "getusers"
        )
        assert (
            self.analyzer._generate_mcp_tool_name("create-user", "POST", "/users")
            == "create_user"
        )
        assert (
            self.analyzer._generate_mcp_tool_name("123invalid", "GET", "/test")
            == "api_123invalid"
        )
        assert (
            self.analyzer._generate_mcp_tool_name("", "GET", "/test") == "get_endpoint"
        )

    def test_generate_mcp_description(self):
        """Test MCP description generation."""
        assert (
            self.analyzer._generate_mcp_description("Get users", "", "GET", "/users")
            == "Get users"
        )
        assert (
            self.analyzer._generate_mcp_description(
                "", "Get all users from database.", "GET", "/users"
            )
            == "Get all users from database"
        )
        assert (
            self.analyzer._generate_mcp_description("", "", "GET", "/users")
            == "GET /users"
        )

    def test_estimate_token_usage(self):
        """Test token usage estimation."""
        operation = {"description": "This is a test endpoint with some description"}
        parameters = [EndpointParameter(name="test1"), EndpointParameter(name="test2")]
        request_body = RequestBodyInfo(
            schema_info={"properties": {"field1": {}, "field2": {}}}
        )

        tokens = self.analyzer._estimate_token_usage(
            operation, parameters, request_body
        )

        # Base(50) + params(20) + request_body(30) + properties(10)
        # + description(~10) = ~120
        assert 100 <= tokens <= 150

    def test_create_functionality_groups(self):
        """Test functionality group creation."""
        endpoints = [
            EndpointInfo(
                path="/users",
                method=HTTPMethod.GET,
                operation_id="getUsers",
                tags=["users"],
                complexity_score=2,
            ),
            EndpointInfo(
                path="/users",
                method=HTTPMethod.POST,
                operation_id="createUser",
                tags=["users"],
                complexity_score=3,
            ),
            EndpointInfo(
                path="/admin/settings",
                method=HTTPMethod.PUT,
                operation_id="updateSettings",
                tags=["admin"],
                complexity_score=5,
            ),
        ]

        groups = self.analyzer._create_functionality_groups(endpoints)

        assert len(groups) == 2
        users_group = next(g for g in groups if g.name == "Users")
        admin_group = next(g for g in groups if g.name == "Admin")

        assert len(users_group.endpoints) == 2
        assert users_group.total_complexity == 5
        assert len(admin_group.endpoints) == 1
        assert admin_group.total_complexity == 5

    def test_determine_group_name(self):
        """Test group name determination."""
        endpoint_with_tag = EndpointInfo(
            path="/test", method=HTTPMethod.GET, operation_id="test", tags=["users"]
        )
        assert self.analyzer._determine_group_name(endpoint_with_tag) == "Users"

        endpoint_with_path = EndpointInfo(
            path="/admin/settings", method=HTTPMethod.GET, operation_id="test", tags=[]
        )
        assert self.analyzer._determine_group_name(endpoint_with_path) == "Admin"

        endpoint_default = EndpointInfo(
            path="/", method=HTTPMethod.GET, operation_id="test", tags=[]
        )
        assert self.analyzer._determine_group_name(endpoint_default) == "Default"

    def test_get_recommended_endpoints(self):
        """Test recommended endpoints filtering."""
        endpoints = [
            EndpointInfo(
                path="/simple",
                method=HTTPMethod.GET,
                operation_id="simple",
                complexity_score=3,
                deprecated=False,
            ),
            EndpointInfo(
                path="/complex",
                method=HTTPMethod.GET,
                operation_id="complex",
                complexity_score=10,
                deprecated=False,
            ),
            EndpointInfo(
                path="/deprecated",
                method=HTTPMethod.GET,
                operation_id="deprecated",
                complexity_score=2,
                deprecated=True,
            ),
            EndpointInfo(
                path="/unsupported",
                method=HTTPMethod.HEAD,
                operation_id="unsupported",
                complexity_score=2,
                deprecated=False,
            ),
        ]

        recommended = self.analyzer._get_recommended_endpoints(endpoints)

        assert len(recommended) == 1
        assert recommended[0].operation_id == "simple"

    def test_get_high_value_groups(self):
        """Test high value groups filtering."""
        groups = [
            FunctionalityGroup(
                name="HighValue",
                endpoints=[
                    EndpointInfo(
                        path="/test1",
                        method=HTTPMethod.GET,
                        operation_id="test1",
                        complexity_score=2,
                    ),
                    EndpointInfo(
                        path="/test2",
                        method=HTTPMethod.GET,
                        operation_id="test2",
                        complexity_score=3,
                    ),
                ],
                total_complexity=5,
                recommended_for_mcp=True,
            ),
            FunctionalityGroup(
                name="TooComplex",
                endpoints=[
                    EndpointInfo(
                        path="/test3",
                        method=HTTPMethod.GET,
                        operation_id="test3",
                        complexity_score=10,
                    )
                ],
                total_complexity=20,
                recommended_for_mcp=False,
            ),
            FunctionalityGroup(
                name="TooFew",
                endpoints=[
                    EndpointInfo(
                        path="/test4",
                        method=HTTPMethod.GET,
                        operation_id="test4",
                        complexity_score=1,
                    )
                ],
                total_complexity=1,
                recommended_for_mcp=True,
            ),
        ]

        high_value = self.analyzer._get_high_value_groups(groups)

        assert len(high_value) == 1
        assert high_value[0].name == "HighValue"

    def test_calculate_complexity_distribution(self):
        """Test complexity distribution calculation."""
        endpoints = [
            EndpointInfo(
                path="/simple1",
                method=HTTPMethod.GET,
                operation_id="simple1",
                complexity_score=2,
            ),
            EndpointInfo(
                path="/simple2",
                method=HTTPMethod.GET,
                operation_id="simple2",
                complexity_score=3,
            ),
            EndpointInfo(
                path="/moderate",
                method=HTTPMethod.GET,
                operation_id="moderate",
                complexity_score=5,
            ),
            EndpointInfo(
                path="/complex",
                method=HTTPMethod.GET,
                operation_id="complex",
                complexity_score=8,
            ),
            EndpointInfo(
                path="/very_complex",
                method=HTTPMethod.GET,
                operation_id="very_complex",
                complexity_score=10,
            ),
        ]

        distribution = self.analyzer._calculate_complexity_distribution(endpoints)

        assert distribution["simple"] == 2
        assert distribution["moderate"] == 1
        assert distribution["complex"] == 1
        assert distribution["very_complex"] == 1

    def test_get_endpoints_by_tag(self):
        """Test filtering endpoints by tag."""
        self.analyzer.analyze_spec(self.sample_spec)
        users_endpoints = self.analyzer.get_endpoints_by_tag("users")

        assert len(users_endpoints) == 3  # GET /users, POST /users, GET /users/{id}
        assert all("users" in ep.tags for ep in users_endpoints)

    def test_get_endpoints_by_complexity(self):
        """Test filtering endpoints by complexity."""
        self.analyzer.analyze_spec(self.sample_spec)
        simple_endpoints = self.analyzer.get_endpoints_by_complexity(5)

        assert len(simple_endpoints) >= 1
        assert all(ep.complexity_score <= 5 for ep in simple_endpoints)

    def test_export_analysis_summary(self):
        """Test analysis summary export."""
        self.analyzer.analyze_spec(self.sample_spec)
        summary = self.analyzer.export_analysis_summary()

        assert summary["spec_title"] == "Test API"
        assert summary["total_endpoints"] == 4
        assert "recommended_endpoints" in summary
        assert "functionality_groups" in summary
        assert "complexity_distribution" in summary
        assert "average_complexity" in summary
        assert "estimated_total_tokens" in summary

    def test_export_analysis_summary_no_result(self):
        """Test export summary with no analysis result."""
        summary = self.analyzer.export_analysis_summary()
        assert summary == {}


class TestConvenienceFunctions:
    """Test convenience functions for file and URL analysis."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"openapi": "3.0.0", "info": {"title": "Test"}, "paths": {}}',
    )
    def test_analyze_openapi_file(self, mock_file):
        """Test analyzing OpenAPI file."""
        result = analyze_openapi_file("test.json")

        assert result.spec_info["title"] == "Test"
        mock_file.assert_called_once_with("test.json", "r", encoding="utf-8")

    @patch("httpx.Client")
    def test_analyze_openapi_url(self, mock_client):
        """Test analyzing OpenAPI from URL."""
        mock_response = mock_client.return_value.__enter__.return_value.get.return_value
        mock_response.text = (
            '{"openapi": "3.0.0", "info": {"title": "Remote API"}, "paths": {}}'
        )
        mock_response.raise_for_status.return_value = None

        result = analyze_openapi_url("https://api.example.com/openapi.json")

        assert result.spec_info["title"] == "Remote API"
        mock_client.return_value.__enter__.return_value.get.assert_called_once_with(
            "https://api.example.com/openapi.json"
        )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_spec(self):
        """Test analyzing empty spec."""
        analyzer = OpenAPIAnalyzer()
        result = analyzer.analyze_spec({})

        assert result.total_endpoints == 0
        assert len(result.endpoints) == 0
        assert len(result.functionality_groups) == 0

    def test_malformed_paths(self):
        """Test handling malformed paths."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {
                "/valid": {
                    "get": {
                        "operationId": "valid",
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/invalid": "not_an_object",
                "/missing_method": {"invalid_method": {"operationId": "invalid"}},
            },
        }

        analyzer = OpenAPIAnalyzer()
        result = analyzer.analyze_spec(spec)

        assert result.total_endpoints == 1  # Only valid endpoint counted

    def test_missing_operation_id(self):
        """Test handling missing operation ID."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}},
        }

        analyzer = OpenAPIAnalyzer()
        result = analyzer.analyze_spec(spec)

        assert len(result.endpoints) == 1
        assert result.endpoints[0].operation_id == "get_test"

    def test_complex_parameter_schemas(self):
        """Test handling complex parameter schemas."""
        params = [
            {
                "name": "complex_param",
                "in": "query",
                "schema": {
                    "type": "object",
                    "properties": {"nested": {"type": "string"}},
                },
            },
            {
                "name": "enum_param",
                "in": "query",
                "schema": {"type": "string", "enum": ["option1", "option2", "option3"]},
            },
        ]

        analyzer = OpenAPIAnalyzer()
        parsed = analyzer._parse_parameters(params)

        assert len(parsed) == 2
        assert parsed[0].type == "object"
        assert parsed[1].enum_values == ["option1", "option2", "option3"]

    def test_analyzer_with_custom_thresholds(self):
        """Test analyzer with custom complexity thresholds."""
        analyzer = OpenAPIAnalyzer(
            max_complexity_threshold=5, max_endpoints_per_group=3
        )

        assert analyzer.max_complexity_threshold == 5
        assert analyzer.max_endpoints_per_group == 3

        # Test that thresholds affect recommendations
        endpoints = [
            EndpointInfo(
                path="/test",
                method=HTTPMethod.GET,
                operation_id="test",
                complexity_score=6,
            )
        ]
        recommended = analyzer._get_recommended_endpoints(endpoints)
        assert len(recommended) == 0  # Should be filtered out due to lower threshold


if __name__ == "__main__":
    pytest.main([__file__])
