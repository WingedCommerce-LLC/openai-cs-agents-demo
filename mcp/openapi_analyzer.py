"""
OpenAPI Specification Analyzer for MCP Server Generation

This module provides comprehensive analysis of OpenAPI specifications to enable
intelligent MCP server generation with endpoint classification and complexity scoring.
"""

import json
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocation(str, Enum):
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"


class EndpointParameter(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    location: ParameterLocation = ParameterLocation.QUERY
    enum_values: Optional[List[str]] = None
    default_value: Optional[Any] = None
    example: Optional[Any] = None


class RequestBodyInfo(BaseModel):
    content_type: str = "application/json"
    schema_info: Dict[str, Any] = Field(default_factory=dict)
    required: bool = False
    description: str = ""
    examples: Dict[str, Any] = Field(default_factory=dict)


class ResponseInfo(BaseModel):
    status_code: str
    description: str = ""
    content_type: str = "application/json"
    schema_info: Dict[str, Any] = Field(default_factory=dict)
    examples: Dict[str, Any] = Field(default_factory=dict)


class EndpointInfo(BaseModel):
    path: str
    method: HTTPMethod
    operation_id: str
    summary: str = ""
    description: str = ""
    parameters: List[EndpointParameter] = Field(default_factory=list)
    request_body: Optional[RequestBodyInfo] = None
    responses: List[ResponseInfo] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    complexity_score: int = 1
    security_requirements: List[Dict[str, List[str]]] = Field(default_factory=list)
    deprecated: bool = False

    # MCP-specific metadata
    mcp_tool_name: str = ""
    mcp_description: str = ""
    estimated_tokens: int = 0


class FunctionalityGroup(BaseModel):
    name: str
    description: str = ""
    endpoints: List[EndpointInfo] = Field(default_factory=list)
    total_complexity: int = 0
    recommended_for_mcp: bool = True


class OpenAPIAnalysisResult(BaseModel):
    spec_info: Dict[str, Any] = Field(default_factory=dict)
    endpoints: List[EndpointInfo] = Field(default_factory=list)
    functionality_groups: List[FunctionalityGroup] = Field(default_factory=list)
    total_endpoints: int = 0
    complexity_distribution: Dict[str, int] = Field(default_factory=dict)
    recommended_endpoints: List[EndpointInfo] = Field(default_factory=list)
    high_value_groups: List[FunctionalityGroup] = Field(default_factory=list)


class OpenAPIAnalyzer:
    """
    Comprehensive OpenAPI specification analyzer for MCP server generation.

    Features:
    - Parse YAML/JSON OpenAPI specifications
    - Extract and classify endpoints
    - Calculate complexity scores for MCP suitability
    - Group endpoints by functionality
    - Recommend optimal endpoint selections
    - Generate MCP tool metadata
    """

    def __init__(
        self, max_complexity_threshold: int = 8, max_endpoints_per_group: int = 10
    ):
        self.max_complexity_threshold = max_complexity_threshold
        self.max_endpoints_per_group = max_endpoints_per_group
        self.spec: Dict[str, Any] = {}
        self.analysis_result: Optional[OpenAPIAnalysisResult] = None

    def parse_spec(self, content: Union[str, Dict]) -> Dict[str, Any]:
        """Parse OpenAPI specification from string or dict."""
        if isinstance(content, dict):
            self.spec = content
            return self.spec

        try:
            # Try YAML first
            self.spec = yaml.safe_load(content)
            logger.info("Successfully parsed OpenAPI spec as YAML")
        except yaml.YAMLError:
            try:
                # Fall back to JSON
                self.spec = json.loads(content)
                logger.info("Successfully parsed OpenAPI spec as JSON")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAPI spec: {e}")
                raise ValueError(f"Invalid OpenAPI specification format: {e}")

        return self.spec

    def analyze_spec(self, spec_content: Union[str, Dict]) -> OpenAPIAnalysisResult:
        """Perform comprehensive analysis of OpenAPI specification."""
        self.parse_spec(spec_content)

        # Extract basic spec information
        spec_info = self._extract_spec_info()

        # Analyze all endpoints
        endpoints = self._analyze_endpoints()

        # Group endpoints by functionality
        functionality_groups = self._create_functionality_groups(endpoints)

        # Calculate recommendations
        recommended_endpoints = self._get_recommended_endpoints(endpoints)
        high_value_groups = self._get_high_value_groups(functionality_groups)

        # Calculate complexity distribution
        complexity_distribution = self._calculate_complexity_distribution(endpoints)

        self.analysis_result = OpenAPIAnalysisResult(
            spec_info=spec_info,
            endpoints=endpoints,
            functionality_groups=functionality_groups,
            total_endpoints=len(endpoints),
            complexity_distribution=complexity_distribution,
            recommended_endpoints=recommended_endpoints,
            high_value_groups=high_value_groups,
        )

        logger.info(
            f"Analysis complete: {len(endpoints)} endpoints, "
            f"{len(functionality_groups)} groups"
        )
        return self.analysis_result

    def _extract_spec_info(self) -> Dict[str, Any]:
        """Extract basic information from OpenAPI specification."""
        info = self.spec.get("info", {})
        return {
            "title": info.get("title", "Unknown API"),
            "version": info.get("version", "1.0.0"),
            "description": info.get("description", ""),
            "openapi_version": self.spec.get("openapi", "3.0.0"),
            "servers": self.spec.get("servers", []),
            "base_url": self._extract_base_url(),
            "security_schemes": self.spec.get("components", {}).get(
                "securitySchemes", {}
            ),
            "tags": self.spec.get("tags", []),
        }

    def _extract_base_url(self) -> str:
        """Extract base URL from servers section."""
        servers = self.spec.get("servers", [])
        if servers and isinstance(servers[0], dict):
            return servers[0].get("url", "")
        return ""

    def _analyze_endpoints(self) -> List[EndpointInfo]:
        """Analyze all endpoints in the OpenAPI specification."""
        endpoints = []
        paths = self.spec.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if method.upper() not in [m.value for m in HTTPMethod]:
                    continue

                if not isinstance(operation, dict):
                    continue

                endpoint = self._analyze_single_endpoint(
                    path, method.upper(), operation
                )
                if endpoint:
                    endpoints.append(endpoint)

        return endpoints

    def _analyze_single_endpoint(
        self, path: str, method: str, operation: Dict
    ) -> Optional[EndpointInfo]:
        """Analyze a single endpoint operation."""
        try:
            # Basic endpoint information
            operation_id = operation.get(
                "operationId", f"{method.lower()}_{self._path_to_operation_id(path)}"
            )
            summary = operation.get("summary", "")
            description = operation.get("description", "")
            tags = operation.get("tags", [])
            deprecated = operation.get("deprecated", False)

            # Parse parameters
            parameters = self._parse_parameters(operation.get("parameters", []))

            # Parse request body
            request_body = self._parse_request_body(operation.get("requestBody"))

            # Parse responses
            responses = self._parse_responses(operation.get("responses", {}))

            # Parse security requirements
            security_requirements = operation.get("security", [])

            # Calculate complexity score
            complexity_score = self._calculate_complexity_score(
                operation, parameters, request_body, responses
            )

            # Generate MCP metadata
            mcp_tool_name = self._generate_mcp_tool_name(operation_id, method, path)
            mcp_description = self._generate_mcp_description(
                summary, description, method, path
            )
            estimated_tokens = self._estimate_token_usage(
                operation, parameters, request_body
            )

            return EndpointInfo(
                path=path,
                method=HTTPMethod(method),
                operation_id=operation_id,
                summary=summary,
                description=description,
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                tags=tags,
                complexity_score=complexity_score,
                security_requirements=security_requirements,
                deprecated=deprecated,
                mcp_tool_name=mcp_tool_name,
                mcp_description=mcp_description,
                estimated_tokens=estimated_tokens,
            )

        except Exception as e:
            logger.warning(f"Failed to analyze endpoint {method} {path}: {e}")
            return None

    def _path_to_operation_id(self, path: str) -> str:
        """Convert path to operation ID format."""
        # Remove path parameters and convert to snake_case
        clean_path = re.sub(r"\{[^}]+\}", "by_id", path)
        clean_path = re.sub(r"[^a-zA-Z0-9_]", "_", clean_path)
        clean_path = re.sub(r"_+", "_", clean_path).strip("_")
        return clean_path

    def _parse_parameters(self, parameters: List[Dict]) -> List[EndpointParameter]:
        """Parse endpoint parameters."""
        parsed_params = []

        for param in parameters:
            if not isinstance(param, dict):
                continue

            schema = param.get("schema", {})
            param_type = schema.get("type", "string")

            parsed_param = EndpointParameter(
                name=param.get("name", ""),
                type=param_type,
                required=param.get("required", False),
                description=param.get("description", ""),
                location=ParameterLocation(param.get("in", "query")),
                enum_values=schema.get("enum"),
                default_value=schema.get("default"),
                example=param.get("example") or schema.get("example"),
            )
            parsed_params.append(parsed_param)

        return parsed_params

    def _parse_request_body(
        self, request_body: Optional[Dict]
    ) -> Optional[RequestBodyInfo]:
        """Parse request body information."""
        if not request_body or not isinstance(request_body, dict):
            return None

        content = request_body.get("content", {})
        if not content:
            return None

        # Get the first content type (usually application/json)
        content_type = next(iter(content.keys()))
        content_info = content[content_type]

        return RequestBodyInfo(
            content_type=content_type,
            schema_info=content_info.get("schema", {}),
            required=request_body.get("required", False),
            description=request_body.get("description", ""),
            examples=content_info.get("examples", {}),
        )

    def _parse_responses(self, responses: Dict) -> List[ResponseInfo]:
        """Parse response information."""
        parsed_responses = []

        for status_code, response in responses.items():
            if not isinstance(response, dict):
                continue

            content = response.get("content", {})
            content_type = "application/json"
            schema = {}
            examples = {}

            if content:
                content_type = next(iter(content.keys()))
                content_info = content[content_type]
                schema = content_info.get("schema", {})
                examples = content_info.get("examples", {})

            parsed_response = ResponseInfo(
                status_code=str(status_code),
                description=response.get("description", ""),
                content_type=content_type,
                schema_info=schema,
                examples=examples,
            )
            parsed_responses.append(parsed_response)

        return parsed_responses

    def _calculate_complexity_score(
        self,
        operation: Dict,
        parameters: List[EndpointParameter],
        request_body: Optional[RequestBodyInfo],
        responses: List[ResponseInfo],
    ) -> int:
        """Calculate complexity score for MCP suitability (1-10 scale)."""
        score = 1  # Base score

        # Parameter complexity
        score += len(parameters) * 0.5
        required_params = sum(1 for p in parameters if p.required)
        score += required_params * 0.3

        # Request body complexity
        if request_body:
            score += 2
            if request_body.required:
                score += 1
            # Check schema complexity
            schema = request_body.schema_info
            if schema and isinstance(schema, dict):
                properties = schema.get("properties", {})
                score += len(properties) * 0.2

        # Response complexity
        score += len(responses) * 0.3

        # Security requirements
        security = operation.get("security", [])
        if security:
            score += len(security) * 0.5

        # Path parameter complexity
        path_params = [p for p in parameters if p.location == ParameterLocation.PATH]
        score += len(path_params) * 0.4

        # Deprecated endpoints are less suitable
        if operation.get("deprecated", False):
            score += 2

        return min(int(score), 10)  # Cap at 10

    def _generate_mcp_tool_name(self, operation_id: str, method: str, path: str) -> str:
        """Generate appropriate MCP tool name."""
        # Clean operation ID for MCP tool naming
        tool_name = operation_id.lower()
        tool_name = re.sub(r"[^a-z0-9_]", "_", tool_name)
        tool_name = re.sub(r"_+", "_", tool_name).strip("_")

        # Ensure it starts with a letter
        if tool_name and not tool_name[0].isalpha():
            tool_name = f"api_{tool_name}"

        return tool_name or f"{method.lower()}_endpoint"

    def _generate_mcp_description(
        self, summary: str, description: str, method: str, path: str
    ) -> str:
        """Generate MCP tool description."""
        if summary:
            return summary
        elif description:
            # Use first sentence of description
            first_sentence = description.split(".")[0].strip()
            return first_sentence if first_sentence else description[:100]
        else:
            return f"{method} {path}"

    def _estimate_token_usage(
        self,
        operation: Dict,
        parameters: List[EndpointParameter],
        request_body: Optional[RequestBodyInfo],
    ) -> int:
        """Estimate token usage for this endpoint."""
        tokens = 50  # Base tokens for tool definition

        # Add tokens for parameters
        tokens += len(parameters) * 10

        # Add tokens for request body
        if request_body:
            tokens += 30
            schema = request_body.schema_info
            if schema and isinstance(schema, dict):
                properties = schema.get("properties", {})
                tokens += len(properties) * 5

        # Add tokens for description
        description = operation.get("description", "")
        tokens += len(description.split()) * 1.3  # Rough token estimation

        return int(tokens)

    def _create_functionality_groups(
        self, endpoints: List[EndpointInfo]
    ) -> List[FunctionalityGroup]:
        """Group endpoints by functionality using tags and path analysis."""
        groups_dict: Dict[str, FunctionalityGroup] = {}

        for endpoint in endpoints:
            # Determine group name
            group_name = self._determine_group_name(endpoint)

            if group_name not in groups_dict:
                groups_dict[group_name] = FunctionalityGroup(
                    name=group_name,
                    description=f"Operations related to {group_name.lower()}",
                    endpoints=[],
                    total_complexity=0,
                    recommended_for_mcp=True,
                )

            groups_dict[group_name].endpoints.append(endpoint)
            groups_dict[group_name].total_complexity += endpoint.complexity_score

        # Convert to list and sort by complexity
        groups = list(groups_dict.values())
        groups.sort(key=lambda g: g.total_complexity)

        # Mark groups as not recommended if too complex or too many endpoints
        for group in groups:
            if (
                group.total_complexity > self.max_complexity_threshold * 3
                or len(group.endpoints) > self.max_endpoints_per_group
            ):
                group.recommended_for_mcp = False

        return groups

    def _determine_group_name(self, endpoint: EndpointInfo) -> str:
        """Determine the functional group name for an endpoint."""
        # Use first tag if available
        if endpoint.tags:
            return endpoint.tags[0].title()

        # Extract from path
        path_parts = [
            part
            for part in endpoint.path.split("/")
            if part and not part.startswith("{")
        ]
        if path_parts:
            return path_parts[0].title()

        return "Default"

    def _get_recommended_endpoints(
        self, endpoints: List[EndpointInfo]
    ) -> List[EndpointInfo]:
        """Get endpoints recommended for MCP server generation."""
        recommended = []

        for endpoint in endpoints:
            if (
                endpoint.complexity_score <= self.max_complexity_threshold
                and not endpoint.deprecated
                and endpoint.method
                in [HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.DELETE]
            ):
                recommended.append(endpoint)

        # Sort by complexity (simpler first)
        recommended.sort(key=lambda e: e.complexity_score)

        return recommended

    def _get_high_value_groups(
        self, groups: List[FunctionalityGroup]
    ) -> List[FunctionalityGroup]:
        """Get functionality groups with high value for MCP integration."""
        high_value = []

        for group in groups:
            if (
                group.recommended_for_mcp
                and group.total_complexity <= self.max_complexity_threshold * 2
                and len(group.endpoints) >= 2
            ):  # At least 2 endpoints to be valuable
                high_value.append(group)

        # Sort by value (more endpoints with lower complexity = higher value)
        high_value.sort(
            key=lambda g: (len(g.endpoints), -g.total_complexity), reverse=True
        )

        return high_value

    def _calculate_complexity_distribution(
        self, endpoints: List[EndpointInfo]
    ) -> Dict[str, int]:
        """Calculate distribution of complexity scores."""
        distribution = {
            "simple": 0,  # 1-3
            "moderate": 0,  # 4-6
            "complex": 0,  # 7-8
            "very_complex": 0,  # 9-10
        }

        for endpoint in endpoints:
            score = endpoint.complexity_score
            if score <= 3:
                distribution["simple"] += 1
            elif score <= 6:
                distribution["moderate"] += 1
            elif score <= 8:
                distribution["complex"] += 1
            else:
                distribution["very_complex"] += 1

        return distribution

    def get_endpoints_by_tag(self, tag: str) -> List[EndpointInfo]:
        """Get all endpoints with a specific tag."""
        if not self.analysis_result:
            return []

        return [ep for ep in self.analysis_result.endpoints if tag in ep.tags]

    def get_endpoints_by_complexity(self, max_complexity: int) -> List[EndpointInfo]:
        """Get endpoints with complexity score <= max_complexity."""
        if not self.analysis_result:
            return []

        return [
            ep
            for ep in self.analysis_result.endpoints
            if ep.complexity_score <= max_complexity
        ]

    def export_analysis_summary(self) -> Dict[str, Any]:
        """Export a summary of the analysis results."""
        if not self.analysis_result:
            return {}

        return {
            "spec_title": self.analysis_result.spec_info.get("title", "Unknown"),
            "total_endpoints": self.analysis_result.total_endpoints,
            "recommended_endpoints": len(self.analysis_result.recommended_endpoints),
            "functionality_groups": len(self.analysis_result.functionality_groups),
            "high_value_groups": len(self.analysis_result.high_value_groups),
            "complexity_distribution": self.analysis_result.complexity_distribution,
            "average_complexity": sum(
                ep.complexity_score for ep in self.analysis_result.endpoints
            )
            / max(len(self.analysis_result.endpoints), 1),
            "estimated_total_tokens": sum(
                ep.estimated_tokens for ep in self.analysis_result.endpoints
            ),
        }


def analyze_openapi_file(file_path: str, **kwargs) -> OpenAPIAnalysisResult:
    """Convenience function to analyze OpenAPI file."""
    analyzer = OpenAPIAnalyzer(**kwargs)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return analyzer.analyze_spec(content)


def analyze_openapi_url(url: str, **kwargs) -> OpenAPIAnalysisResult:
    """Convenience function to analyze OpenAPI spec from URL."""
    import httpx

    analyzer = OpenAPIAnalyzer(**kwargs)

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.text

    return analyzer.analyze_spec(content)
