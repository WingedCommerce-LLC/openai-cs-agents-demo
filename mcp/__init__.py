"""
MCP (Model Context Protocol) Integration Module

This module provides comprehensive MCP server generation and management capabilities
for the OpenAI Customer Service Agents Demo enterprise upgrade.
"""

from .openapi_analyzer import (
    EndpointInfo,
    FunctionalityGroup,
    OpenAPIAnalysisResult,
    OpenAPIAnalyzer,
    analyze_openapi_file,
    analyze_openapi_url,
)
from .registry import (
    MCPServerInfo,
    MCPServerRegistry,
    ServerStatus,
    get_registry,
    register_server_from_file,
    register_server_from_url,
)
from .server_generator import (
    GeneratedFile,
    MCPServerGenerator,
    ServerGenerationConfig,
    ServerGenerationResult,
    generate_mcp_server_from_file,
    generate_mcp_server_from_url,
)

__version__ = "1.0.0"
__author__ = "OpenAI Customer Service Agents Demo"

__all__ = [
    # OpenAPI Analysis
    "OpenAPIAnalyzer",
    "OpenAPIAnalysisResult",
    "EndpointInfo",
    "FunctionalityGroup",
    "analyze_openapi_file",
    "analyze_openapi_url",
    # Server Generation
    "MCPServerGenerator",
    "ServerGenerationConfig",
    "ServerGenerationResult",
    "GeneratedFile",
    "generate_mcp_server_from_file",
    "generate_mcp_server_from_url",
    # Server Registry
    "MCPServerRegistry",
    "MCPServerInfo",
    "ServerStatus",
    "get_registry",
    "register_server_from_url",
    "register_server_from_file",
]
