"""
MCP Server Registry

This module provides dynamic MCP server management capabilities including
server registration, lifecycle management, and runtime configuration.
"""

import json
import logging
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from .server_generator import (
    MCPServerGenerator,
    ServerGenerationConfig,
    ServerGenerationResult,
)

logger = logging.getLogger(__name__)


class ServerStatus(str, Enum):
    """MCP server status enumeration."""

    CREATED = "created"
    GENERATING = "generating"
    GENERATED = "generated"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DELETED = "deleted"


class MCPServerInfo(BaseModel):
    """Information about a registered MCP server."""

    id: str = Field(..., description="Unique server identifier")
    name: str = Field(..., description="Human-readable server name")
    description: str = Field(default="", description="Server description")

    # Generation info
    openapi_spec: Dict[str, Any] = Field(
        default_factory=dict, description="Original OpenAPI spec"
    )
    generation_config: ServerGenerationConfig = Field(
        ..., description="Generation configuration"
    )
    generation_result: Optional[ServerGenerationResult] = Field(
        default=None, description="Generation result"
    )

    # Runtime info
    status: ServerStatus = Field(
        default=ServerStatus.CREATED, description="Current server status"
    )
    server_path: Optional[str] = Field(
        default=None, description="Path to generated server"
    )
    process_id: Optional[int] = Field(default=None, description="Running process ID")

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    tags: List[str] = Field(default_factory=list, description="Server tags")

    # Statistics
    endpoint_count: int = Field(default=0, description="Number of endpoints")
    tool_count: int = Field(default=0, description="Number of MCP tools")
    complexity_score: float = Field(default=0.0, description="Average complexity score")


class MCPServerRegistry:
    """
    Registry for managing MCP servers dynamically.

    Features:
    - Server registration and lifecycle management
    - Dynamic server generation from OpenAPI specs
    - Process management for running servers
    - Configuration and metadata storage
    - Health monitoring and status tracking
    """

    def __init__(self, registry_dir: Optional[str] = None):
        self.registry_dir = Path(registry_dir or "./mcp_registry")
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        self.servers: Dict[str, MCPServerInfo] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.generator = MCPServerGenerator()

        # Load existing servers
        self._load_registry()

    def _load_registry(self):
        """Load existing servers from registry directory."""
        registry_file = self.registry_dir / "registry.json"

        if registry_file.exists():
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for server_data in data.get("servers", []):
                    server_info = MCPServerInfo(**server_data)
                    self.servers[server_info.id] = server_info

                logger.info(f"Loaded {len(self.servers)} servers from registry")

            except Exception as e:
                logger.error(f"Failed to load registry: {e}")

    def _save_registry(self):
        """Save current registry state to disk."""
        registry_file = self.registry_dir / "registry.json"

        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "servers": [server.dict() for server in self.servers.values()],
            }

            with open(registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            logger.debug("Registry saved successfully")

        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    async def register_server(
        self,
        server_id: str,
        name: str,
        openapi_spec: Union[str, Dict],
        config: ServerGenerationConfig,
        description: str = "",
        tags: List[str] = None,
        auto_generate: bool = True,
    ) -> MCPServerInfo:
        """Register a new MCP server."""
        if server_id in self.servers:
            raise ValueError(f"Server with ID '{server_id}' already exists")

        # Parse OpenAPI spec if it's a string
        if isinstance(openapi_spec, str):
            try:
                openapi_spec = json.loads(openapi_spec)
            except json.JSONDecodeError:
                import yaml

                openapi_spec = yaml.safe_load(openapi_spec)

        # Create server info
        server_info = MCPServerInfo(
            id=server_id,
            name=name,
            description=description,
            openapi_spec=openapi_spec,
            generation_config=config,
            tags=tags or [],
            status=ServerStatus.CREATED,
        )

        # Register server
        self.servers[server_id] = server_info
        self._save_registry()

        logger.info(f"Registered server: {server_id}")

        # Auto-generate if requested
        if auto_generate:
            await self.generate_server(server_id)

        return server_info

    async def generate_server(self, server_id: str) -> ServerGenerationResult:
        """Generate MCP server code from OpenAPI specification."""
        if server_id not in self.servers:
            raise ValueError(f"Server '{server_id}' not found")

        server_info = self.servers[server_id]
        server_info.status = ServerStatus.GENERATING
        server_info.updated_at = datetime.now()
        self._save_registry()

        try:
            # Generate server
            result = self.generator.generate_server(
                server_info.openapi_spec, server_info.generation_config
            )

            if result.success:
                # Write server to disk
                server_path = self.registry_dir / server_id
                output_path = self.generator.write_server_to_disk(
                    result, str(server_path)
                )

                # Update server info
                server_info.generation_result = result
                server_info.server_path = output_path
                server_info.status = ServerStatus.GENERATED
                server_info.endpoint_count = len(result.selected_endpoints)
                server_info.tool_count = len(result.selected_endpoints)

                # Calculate average complexity
                if result.selected_endpoints:
                    total_complexity = sum(
                        ep.complexity_score for ep in result.selected_endpoints
                    )
                    server_info.complexity_score = total_complexity / len(
                        result.selected_endpoints
                    )

                logger.info(f"Generated server: {server_id} at {output_path}")

            else:
                server_info.status = ServerStatus.ERROR
                logger.error(f"Failed to generate server {server_id}: {result.errors}")

            server_info.updated_at = datetime.now()
            self._save_registry()

            return result

        except Exception as e:
            server_info.status = ServerStatus.ERROR
            server_info.updated_at = datetime.now()
            self._save_registry()

            logger.error(f"Server generation failed for {server_id}: {e}")
            raise

    async def start_server(self, server_id: str) -> bool:
        """Start a generated MCP server."""
        if server_id not in self.servers:
            raise ValueError(f"Server '{server_id}' not found")

        server_info = self.servers[server_id]

        if server_info.status != ServerStatus.GENERATED:
            raise ValueError(
                f"Server '{server_id}' is not ready to start "
                f"(status: {server_info.status})"
            )

        if server_id in self.processes:
            logger.warning(f"Server '{server_id}' is already running")
            return True

        try:
            server_info.status = ServerStatus.STARTING
            self._save_registry()

            # Start server process
            server_script = (
                Path(server_info.server_path)
                / server_info.generation_config.package_name
                / "server.py"
            )

            if not server_script.exists():
                raise FileNotFoundError(f"Server script not found: {server_script}")

            process = subprocess.Popen(
                ["python", str(server_script)],
                cwd=server_info.server_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Store process
            self.processes[server_id] = process
            server_info.process_id = process.pid
            server_info.status = ServerStatus.RUNNING
            server_info.updated_at = datetime.now()
            self._save_registry()

            logger.info(f"Started server: {server_id} (PID: {process.pid})")
            return True

        except Exception as e:
            server_info.status = ServerStatus.ERROR
            server_info.updated_at = datetime.now()
            self._save_registry()

            logger.error(f"Failed to start server {server_id}: {e}")
            return False

    async def stop_server(self, server_id: str) -> bool:
        """Stop a running MCP server."""
        if server_id not in self.servers:
            raise ValueError(f"Server '{server_id}' not found")

        server_info = self.servers[server_id]

        if server_id not in self.processes:
            logger.warning(f"Server '{server_id}' is not running")
            server_info.status = ServerStatus.STOPPED
            server_info.process_id = None
            self._save_registry()
            return True

        try:
            process = self.processes[server_id]
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing server {server_id}")
                process.kill()
                process.wait()

            # Clean up
            del self.processes[server_id]
            server_info.status = ServerStatus.STOPPED
            server_info.process_id = None
            server_info.updated_at = datetime.now()
            self._save_registry()

            logger.info(f"Stopped server: {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop server {server_id}: {e}")
            return False

    async def delete_server(self, server_id: str, cleanup_files: bool = True) -> bool:
        """Delete a registered MCP server."""
        if server_id not in self.servers:
            raise ValueError(f"Server '{server_id}' not found")

        try:
            # Stop server if running
            if server_id in self.processes:
                await self.stop_server(server_id)

            server_info = self.servers[server_id]

            # Clean up files if requested
            if cleanup_files and server_info.server_path:
                import shutil

                server_path = Path(server_info.server_path)
                if server_path.exists():
                    shutil.rmtree(server_path)
                    logger.info(f"Cleaned up server files: {server_path}")

            # Remove from registry
            del self.servers[server_id]
            self._save_registry()

            logger.info(f"Deleted server: {server_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete server {server_id}: {e}")
            return False

    def get_server(self, server_id: str) -> Optional[MCPServerInfo]:
        """Get server information by ID."""
        return self.servers.get(server_id)

    def list_servers(
        self,
        status: Optional[ServerStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> List[MCPServerInfo]:
        """List registered servers with optional filtering."""
        servers = list(self.servers.values())

        if status:
            servers = [s for s in servers if s.status == status]

        if tags:
            servers = [s for s in servers if any(tag in s.tags for tag in tags)]

        return sorted(servers, key=lambda s: s.created_at, reverse=True)

    async def health_check(self, server_id: str) -> Dict[str, Any]:
        """Check health status of a server."""
        if server_id not in self.servers:
            return {"status": "not_found", "error": f"Server '{server_id}' not found"}

        server_info = self.servers[server_id]

        if server_id not in self.processes:
            return {
                "status": "stopped",
                "server_status": server_info.status.value,
                "process_id": None,
            }

        process = self.processes[server_id]

        # Check if process is still running
        if process.poll() is not None:
            # Process has terminated
            del self.processes[server_id]
            server_info.status = ServerStatus.STOPPED
            server_info.process_id = None
            server_info.updated_at = datetime.now()
            self._save_registry()

            return {
                "status": "terminated",
                "server_status": server_info.status.value,
                "exit_code": process.returncode,
            }

        return {
            "status": "running",
            "server_status": server_info.status.value,
            "process_id": process.pid,
            "uptime": (datetime.now() - server_info.updated_at).total_seconds(),
        }

    async def get_server_logs(self, server_id: str, lines: int = 100) -> List[str]:
        """Get recent logs from a server."""
        if server_id not in self.processes:
            return []

        try:
            process = self.processes[server_id]

            # Read stderr (where most logs go)
            if process.stderr:
                # This is a simplified implementation
                # In production, you'd want proper log file handling
                return ["Log retrieval not implemented in this demo"]

            return []

        except Exception as e:
            logger.error(f"Failed to get logs for server {server_id}: {e}")
            return [f"Error retrieving logs: {e}"]

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        servers = list(self.servers.values())

        status_counts = {}
        for status in ServerStatus:
            status_counts[status.value] = len(
                [s for s in servers if s.status == status]
            )

        total_endpoints = sum(s.endpoint_count for s in servers)
        total_tools = sum(s.tool_count for s in servers)
        avg_complexity = (
            sum(s.complexity_score for s in servers) / len(servers) if servers else 0
        )

        return {
            "total_servers": len(servers),
            "status_distribution": status_counts,
            "running_servers": len(self.processes),
            "total_endpoints": total_endpoints,
            "total_tools": total_tools,
            "average_complexity": round(avg_complexity, 2),
            "registry_path": str(self.registry_dir),
        }

    async def cleanup(self):
        """Clean up registry resources."""
        # Stop all running servers
        for server_id in list(self.processes.keys()):
            await self.stop_server(server_id)

        logger.info("Registry cleanup completed")


# Global registry instance
_registry: Optional[MCPServerRegistry] = None


def get_registry(registry_dir: Optional[str] = None) -> MCPServerRegistry:
    """Get the global MCP server registry instance."""
    global _registry

    if _registry is None:
        _registry = MCPServerRegistry(registry_dir)

    return _registry


async def register_server_from_url(
    server_id: str,
    name: str,
    openapi_url: str,
    config: ServerGenerationConfig,
    description: str = "",
    tags: List[str] = None,
) -> MCPServerInfo:
    """Convenience function to register server from OpenAPI URL."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(openapi_url)
        response.raise_for_status()
        openapi_spec = response.text

    registry = get_registry()
    return await registry.register_server(
        server_id=server_id,
        name=name,
        openapi_spec=openapi_spec,
        config=config,
        description=description,
        tags=tags,
    )


async def register_server_from_file(
    server_id: str,
    name: str,
    openapi_file: str,
    config: ServerGenerationConfig,
    description: str = "",
    tags: List[str] = None,
) -> MCPServerInfo:
    """Convenience function to register server from OpenAPI file."""
    with open(openapi_file, "r", encoding="utf-8") as f:
        openapi_spec = f.read()

    registry = get_registry()
    return await registry.register_server(
        server_id=server_id,
        name=name,
        openapi_spec=openapi_spec,
        config=config,
        description=description,
        tags=tags,
    )
