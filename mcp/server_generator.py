"""
MCP Server Generator

This module generates complete MCP servers from OpenAPI specifications using
Jinja2 templates. It creates production-ready MCP servers with proper error
handling, type safety, and comprehensive tool implementations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jinja2
from pydantic import BaseModel, Field

from .openapi_analyzer import EndpointInfo, OpenAPIAnalysisResult, OpenAPIAnalyzer

logger = logging.getLogger(__name__)


class ServerGenerationConfig(BaseModel):
    """Configuration for MCP server generation."""

    server_name: str = Field(..., description="Name of the MCP server")
    server_description: str = Field(default="", description="Description of the server")
    package_name: str = Field(..., description="Python package name for the server")
    author: str = Field(default="Auto-generated", description="Author name")
    version: str = Field(default="1.0.0", description="Server version")

    # Generation options
    include_async: bool = Field(default=True, description="Generate async tools")
    include_error_handling: bool = Field(
        default=True, description="Include comprehensive error handling"
    )
    include_logging: bool = Field(default=True, description="Include logging")
    include_validation: bool = Field(
        default=True, description="Include input validation"
    )
    include_rate_limiting: bool = Field(
        default=False, description="Include rate limiting"
    )
    include_caching: bool = Field(default=False, description="Include response caching")

    # API configuration
    base_url: str = Field(default="", description="Base URL for the API")
    auth_type: str = Field(
        default="none", description="Authentication type (none, bearer, api_key)"
    )
    auth_header: str = Field(
        default="Authorization", description="Authentication header name"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # Endpoint selection
    max_endpoints: int = Field(
        default=20, description="Maximum number of endpoints to include"
    )
    max_complexity: int = Field(
        default=8, description="Maximum complexity score for endpoints"
    )
    include_deprecated: bool = Field(
        default=False, description="Include deprecated endpoints"
    )

    # Output options
    output_dir: str = Field(
        default="./generated_server", description="Output directory"
    )
    create_dockerfile: bool = Field(default=True, description="Create Dockerfile")
    create_requirements: bool = Field(
        default=True, description="Create requirements.txt"
    )
    create_readme: bool = Field(default=True, description="Create README.md")
    create_tests: bool = Field(default=True, description="Create test files")


class GeneratedFile(BaseModel):
    """Information about a generated file."""

    path: str
    content: str
    description: str
    file_type: str  # python, dockerfile, markdown, etc.


class ServerGenerationResult(BaseModel):
    """Result of server generation."""

    config: ServerGenerationConfig
    analysis_result: OpenAPIAnalysisResult
    generated_files: List[GeneratedFile] = Field(default_factory=list)
    selected_endpoints: List[EndpointInfo] = Field(default_factory=list)
    generation_summary: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MCPServerGenerator:
    """
    Generates complete MCP servers from OpenAPI specifications.

    Features:
    - Jinja2 template-based generation
    - Configurable server options
    - Production-ready code generation
    - Comprehensive error handling
    - Type-safe implementations
    - Docker support
    - Test generation
    """

    def __init__(self, template_dir: Optional[str] = None):
        self.template_dir = template_dir or self._get_default_template_dir()
        self.jinja_env = self._setup_jinja_environment()

    def _get_default_template_dir(self) -> str:
        """Get the default template directory."""
        current_dir = Path(__file__).parent
        template_dir = current_dir / "templates"
        return str(template_dir)

    def _setup_jinja_environment(self) -> jinja2.Environment:
        """Set up Jinja2 environment with custom filters and functions."""
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(
                enabled_extensions=("html", "xml"),
                default_for_string=False,
            ),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        env.filters.update(
            {
                "snake_case": self._to_snake_case,
                "camel_case": self._to_camel_case,
                "pascal_case": self._to_pascal_case,
                "python_type": self._to_python_type,
                "json_schema": self._to_json_schema,
                "escape_quotes": self._escape_quotes,
                "indent_lines": self._indent_lines,
            }
        )

        # Add custom functions
        env.globals.update(
            {
                "generate_tool_name": self._generate_tool_name,
                "generate_parameter_validation": self._generate_parameter_validation,
                "generate_request_body": self._generate_request_body,
                "generate_response_handling": self._generate_response_handling,
            }
        )

        return env

    def generate_server(
        self, openapi_spec: Union[str, Dict], config: ServerGenerationConfig
    ) -> ServerGenerationResult:
        """Generate a complete MCP server from OpenAPI specification."""
        try:
            # Analyze the OpenAPI specification
            analyzer = OpenAPIAnalyzer(
                max_complexity_threshold=config.max_complexity,
                max_endpoints_per_group=config.max_endpoints,
            )
            analysis_result = analyzer.analyze_spec(openapi_spec)

            # Select endpoints to include
            selected_endpoints = self._select_endpoints(analysis_result, config)

            # Generate all files
            generated_files = []

            # Generate main server file
            server_file = self._generate_server_file(
                selected_endpoints, config, analysis_result
            )
            generated_files.append(server_file)

            # Generate requirements.txt
            if config.create_requirements:
                requirements_file = self._generate_requirements_file(config)
                generated_files.append(requirements_file)

            # Generate Dockerfile
            if config.create_dockerfile:
                dockerfile = self._generate_dockerfile(config)
                generated_files.append(dockerfile)

            # Generate README.md
            if config.create_readme:
                readme_file = self._generate_readme_file(
                    config, analysis_result, selected_endpoints
                )
                generated_files.append(readme_file)

            # Generate test files
            if config.create_tests:
                test_files = self._generate_test_files(selected_endpoints, config)
                generated_files.extend(test_files)

            # Generate configuration files
            config_files = self._generate_config_files(config)
            generated_files.extend(config_files)

            # Create generation summary
            generation_summary = {
                "total_files": len(generated_files),
                "selected_endpoints": len(selected_endpoints),
                "total_available_endpoints": len(analysis_result.endpoints),
                "functionality_groups": len(analysis_result.functionality_groups),
                "estimated_tokens": sum(
                    ep.estimated_tokens for ep in selected_endpoints
                ),
                "complexity_distribution": (
                    self._calculate_selected_complexity_distribution(selected_endpoints)
                ),
            }

            return ServerGenerationResult(
                config=config,
                analysis_result=analysis_result,
                generated_files=generated_files,
                selected_endpoints=selected_endpoints,
                generation_summary=generation_summary,
                success=True,
            )

        except Exception as e:
            logger.error(f"Server generation failed: {e}")
            return ServerGenerationResult(
                config=config,
                analysis_result=OpenAPIAnalysisResult(),
                success=False,
                errors=[str(e)],
            )

    def write_server_to_disk(
        self,
        generation_result: ServerGenerationResult,
        output_dir: Optional[str] = None,
    ) -> str:
        """Write generated server files to disk."""
        output_path = output_dir or generation_result.config.output_dir
        output_path = Path(output_path).resolve()

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Write all generated files
        for file_info in generation_result.generated_files:
            file_path = output_path / file_info.path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_info.content)

            logger.info(f"Generated {file_info.description}: {file_path}")

        logger.info(f"MCP server generated successfully in: {output_path}")
        return str(output_path)

    def _select_endpoints(
        self, analysis_result: OpenAPIAnalysisResult, config: ServerGenerationConfig
    ) -> List[EndpointInfo]:
        """Select endpoints to include in the generated server."""
        candidates = []

        # Start with recommended endpoints
        for endpoint in analysis_result.recommended_endpoints:
            if endpoint.complexity_score <= config.max_complexity and (
                config.include_deprecated or not endpoint.deprecated
            ):
                candidates.append(endpoint)

        # Sort by complexity (simpler first) and limit count
        candidates.sort(key=lambda ep: (ep.complexity_score, ep.path))
        selected = candidates[: config.max_endpoints]

        logger.info(
            f"Selected {len(selected)} endpoints out of "
            f"{len(analysis_result.endpoints)} available"
        )
        return selected

    def _generate_server_file(
        self,
        endpoints: List[EndpointInfo],
        config: ServerGenerationConfig,
        analysis_result: OpenAPIAnalysisResult,
    ) -> GeneratedFile:
        """Generate the main MCP server Python file."""
        template = self.jinja_env.get_template("server_main.py.j2")

        content = template.render(
            config=config,
            endpoints=endpoints,
            analysis_result=analysis_result,
            spec_info=analysis_result.spec_info,
        )

        return GeneratedFile(
            path=f"{config.package_name}/server.py",
            content=content,
            description="Main MCP server implementation",
            file_type="python",
        )

    def _generate_requirements_file(
        self, config: ServerGenerationConfig
    ) -> GeneratedFile:
        """Generate requirements.txt file."""
        requirements = [
            "mcp>=1.0.0",
            "httpx>=0.25.0",
            "pydantic>=2.0.0",
            "typing-extensions>=4.0.0",
        ]

        if config.include_logging:
            requirements.append("structlog>=23.0.0")

        if config.include_rate_limiting:
            requirements.append("aiohttp-ratelimiter>=1.0.0")

        if config.include_caching:
            requirements.append("aiocache>=0.12.0")

        content = "\n".join(sorted(requirements)) + "\n"

        return GeneratedFile(
            path="requirements.txt",
            content=content,
            description="Python dependencies",
            file_type="text",
        )

    def _generate_dockerfile(self, config: ServerGenerationConfig) -> GeneratedFile:
        """Generate Dockerfile."""
        template = self.jinja_env.get_template("Dockerfile.j2")

        content = template.render(config=config)

        return GeneratedFile(
            path="Dockerfile",
            content=content,
            description="Docker container configuration",
            file_type="dockerfile",
        )

    def _generate_readme_file(
        self,
        config: ServerGenerationConfig,
        analysis_result: OpenAPIAnalysisResult,
        endpoints: List[EndpointInfo],
    ) -> GeneratedFile:
        """Generate README.md file."""
        template = self.jinja_env.get_template("README.md.j2")

        content = template.render(
            config=config,
            analysis_result=analysis_result,
            endpoints=endpoints,
            spec_info=analysis_result.spec_info,
        )

        return GeneratedFile(
            path="README.md",
            content=content,
            description="Server documentation",
            file_type="markdown",
        )

    def _generate_test_files(
        self, endpoints: List[EndpointInfo], config: ServerGenerationConfig
    ) -> List[GeneratedFile]:
        """Generate test files."""
        files = []

        # Generate main test file
        template = self.jinja_env.get_template("test_server.py.j2")
        content = template.render(
            config=config,
            endpoints=endpoints,
        )

        files.append(
            GeneratedFile(
                path="tests/test_server.py",
                content=content,
                description="Server unit tests",
                file_type="python",
            )
        )

        # Generate test configuration
        test_config = {
            "test_base_url": "https://api.example.com",
            "mock_responses": True,
            "timeout": 10,
        }

        files.append(
            GeneratedFile(
                path="tests/conftest.py",
                content=(
                    f"# Test configuration\n"
                    f"TEST_CONFIG = {json.dumps(test_config, indent=2)}\n"
                ),
                description="Test configuration",
                file_type="python",
            )
        )

        return files

    def _generate_config_files(
        self, config: ServerGenerationConfig
    ) -> List[GeneratedFile]:
        """Generate configuration files."""
        files = []

        # Generate __init__.py
        init_content = (
            f'"""MCP Server: {config.server_name}"""\n\n'
            f'__version__ = "{config.version}"\n'
        )
        files.append(
            GeneratedFile(
                path=f"{config.package_name}/__init__.py",
                content=init_content,
                description="Package initialization",
                file_type="python",
            )
        )

        # Generate setup.py
        template = self.jinja_env.get_template("setup.py.j2")
        setup_content = template.render(config=config)
        files.append(
            GeneratedFile(
                path="setup.py",
                content=setup_content,
                description="Package setup configuration",
                file_type="python",
            )
        )

        # Generate .env.example
        env_example = f"""# {config.server_name} Configuration
API_BASE_URL={config.base_url}
API_TIMEOUT={config.timeout}
LOG_LEVEL=INFO
"""

        if config.auth_type != "none":
            token_var = f"{config.auth_header.upper().replace('-', '_')}_TOKEN"
            env_example += f"{token_var}=your_token_here\n"

        files.append(
            GeneratedFile(
                path=".env.example",
                content=env_example,
                description="Environment variables example",
                file_type="text",
            )
        )

        return files

    def _calculate_selected_complexity_distribution(
        self, endpoints: List[EndpointInfo]
    ) -> Dict[str, int]:
        """Calculate complexity distribution for selected endpoints."""
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

    # Jinja2 filter functions
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        import re

        text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
        text = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", text)
        text = re.sub(r"[^a-zA-Z0-9_]", "_", text)
        return text.lower().strip("_")

    def _to_camel_case(self, text: str) -> str:
        """Convert text to camelCase."""
        components = text.replace("-", "_").split("_")
        return components[0].lower() + "".join(
            word.capitalize() for word in components[1:]
        )

    def _to_pascal_case(self, text: str) -> str:
        """Convert text to PascalCase."""
        components = text.replace("-", "_").split("_")
        return "".join(word.capitalize() for word in components)

    def _to_python_type(self, openapi_type: str) -> str:
        """Convert OpenAPI type to Python type annotation."""
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "List[Any]",
            "object": "Dict[str, Any]",
        }
        return type_mapping.get(openapi_type, "Any")

    def _to_json_schema(self, schema: Dict[str, Any]) -> str:
        """Convert schema to JSON string."""
        return json.dumps(schema, indent=2)

    def _escape_quotes(self, text: str) -> str:
        """Escape quotes in text."""
        return text.replace('"', '\\"').replace("'", "\\'")

    def _indent_lines(self, text: str, spaces: int = 4) -> str:
        """Indent all lines in text."""
        indent = " " * spaces
        return "\n".join(
            indent + line if line.strip() else line for line in text.split("\n")
        )

    # Jinja2 global functions
    def _generate_tool_name(self, endpoint: EndpointInfo) -> str:
        """Generate MCP tool name for endpoint."""
        return (
            endpoint.mcp_tool_name
            or f"{endpoint.method.lower()}_{endpoint.operation_id}"
        )

    def _generate_parameter_validation(self, endpoint: EndpointInfo) -> str:
        """Generate parameter validation code."""
        validations = []

        for param in endpoint.parameters:
            if param.required:
                error_msg = f"Parameter {param.name} is required"
                validations.append(
                    f'if not {param.name}: raise ValueError("{error_msg}")'
                )

        return "\n    ".join(validations)

    def _generate_request_body(self, endpoint: EndpointInfo) -> str:
        """Generate request body handling code."""
        if not endpoint.request_body:
            return "data = None"

        if endpoint.request_body.content_type == "application/json":
            return "data = json.dumps(request_data) if request_data else None"
        else:
            return "data = request_data"

    def _generate_response_handling(self, endpoint: EndpointInfo) -> str:
        """Generate response handling code."""
        if not endpoint.responses:
            return "return response.json() if response.content else None"

        # Find success response (2xx)
        success_responses = [
            r for r in endpoint.responses if r.status_code.startswith("2")
        ]

        if (
            success_responses
            and success_responses[0].content_type == "application/json"
        ):
            return "return response.json()"
        else:
            return "return response.text"


def generate_mcp_server_from_file(
    openapi_file: str, config: ServerGenerationConfig, output_dir: Optional[str] = None
) -> ServerGenerationResult:
    """Convenience function to generate MCP server from OpenAPI file."""
    generator = MCPServerGenerator()

    with open(openapi_file, "r", encoding="utf-8") as f:
        spec_content = f.read()

    result = generator.generate_server(spec_content, config)

    if result.success and output_dir:
        generator.write_server_to_disk(result, output_dir)

    return result


def generate_mcp_server_from_url(
    openapi_url: str, config: ServerGenerationConfig, output_dir: Optional[str] = None
) -> ServerGenerationResult:
    """Convenience function to generate MCP server from OpenAPI URL."""
    import httpx

    generator = MCPServerGenerator()

    with httpx.Client() as client:
        response = client.get(openapi_url)
        response.raise_for_status()
        spec_content = response.text

    result = generator.generate_server(spec_content, config)

    if result.success and output_dir:
        generator.write_server_to_disk(result, output_dir)

    return result
