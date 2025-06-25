#!/usr/bin/env python3
"""
Comprehensive tests for MCP Registry to improve coverage

This module provides extensive test coverage for the MCP registry functionality
including server lifecycle management, process handling, and error scenarios.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.registry import (
    MCPServerInfo,
    MCPServerRegistry,
    ServerStatus,
    get_registry,
    register_server_from_file,
    register_server_from_url,
)
from mcp.server_generator import ServerGenerationConfig


class TestMCPServerRegistryComprehensive:
    """Comprehensive tests for MCP server registry."""

    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield MCPServerRegistry(temp_dir)

    @pytest.fixture
    def sample_config(self):
        """Sample server generation configuration."""
        return ServerGenerationConfig(
            server_name="Test Server",
            package_name="test_server",
            base_url="https://api.test.com",
        )

    @pytest.fixture
    def sample_openapi_spec(self):
        """Sample OpenAPI specification."""
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

    def test_registry_initialization_with_existing_data(self):
        """Test registry initialization with existing registry data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_file = Path(temp_dir) / "registry.json"

            # Create existing registry data
            existing_data = {
                "version": "1.0",
                "updated_at": "2023-01-01T00:00:00",
                "servers": [
                    {
                        "id": "existing-server",
                        "name": "Existing Server",
                        "description": "Pre-existing server",
                        "openapi_spec": {},
                        "generation_config": {
                            "server_name": "Existing",
                            "package_name": "existing",
                        },
                        "status": "created",
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                        "tags": [],
                        "endpoint_count": 0,
                        "tool_count": 0,
                        "complexity_score": 0.0,
                    }
                ],
            }

            with open(registry_file, "w") as f:
                json.dump(existing_data, f)

            # Initialize registry
            registry = MCPServerRegistry(temp_dir)

            # Verify existing server was loaded
            assert "existing-server" in registry.servers
            assert registry.servers["existing-server"].name == "Existing Server"

    def test_registry_initialization_with_invalid_data(self):
        """Test registry initialization with invalid JSON data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_file = Path(temp_dir) / "registry.json"

            # Create invalid JSON
            with open(registry_file, "w") as f:
                f.write("invalid json content")

            # Should handle gracefully
            registry = MCPServerRegistry(temp_dir)
            assert len(registry.servers) == 0

    @pytest.mark.asyncio
    async def test_register_server_with_yaml_spec(self, temp_registry, sample_config):
        """Test registering server with YAML OpenAPI spec."""
        yaml_spec = """
openapi: 3.0.0
info:
  title: YAML API
  version: 1.0.0
paths:
  /yaml:
    get:
      operationId: getYaml
      responses:
        '200':
          description: Success
"""

        with patch.object(temp_registry.generator, "generate_server") as mock_gen:
            mock_gen.return_value.success = True
            mock_gen.return_value.selected_endpoints = []

            server_info = await temp_registry.register_server(
                server_id="yaml-server",
                name="YAML Server",
                openapi_spec=yaml_spec,
                config=sample_config,
                auto_generate=False,
            )

            assert server_info.id == "yaml-server"
            assert server_info.name == "YAML Server"

    @pytest.mark.asyncio
    async def test_register_server_with_json_string(self, temp_registry, sample_config):
        """Test registering server with JSON string OpenAPI spec."""
        json_spec = json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "JSON API", "version": "1.0.0"},
                "paths": {
                    "/json": {
                        "get": {
                            "operationId": "getJson",
                            "responses": {"200": {"description": "Success"}},
                        }
                    }
                },
            }
        )

        with patch.object(temp_registry.generator, "generate_server") as mock_gen:
            mock_gen.return_value.success = True
            mock_gen.return_value.selected_endpoints = []

            server_info = await temp_registry.register_server(
                server_id="json-server",
                name="JSON Server",
                openapi_spec=json_spec,
                config=sample_config,
                auto_generate=False,
            )

            assert server_info.id == "json-server"
            assert server_info.name == "JSON Server"

    @pytest.mark.asyncio
    async def test_generate_server_success(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test successful server generation."""
        # Register server first
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        # Mock successful generation
        with patch.object(
            temp_registry.generator, "generate_server"
        ) as mock_gen, patch.object(
            temp_registry.generator, "write_server_to_disk"
        ) as mock_write:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.selected_endpoints = [MagicMock(complexity_score=3)]
            mock_gen.return_value = mock_result
            mock_write.return_value = "/fake/path"

            result = await temp_registry.generate_server("test-server")

            assert result.success is True
            assert temp_registry.servers["test-server"].status == ServerStatus.GENERATED
            assert temp_registry.servers["test-server"].server_path == "/fake/path"

    @pytest.mark.asyncio
    async def test_generate_server_failure(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test server generation failure."""
        # Register server first
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        # Mock failed generation
        with patch.object(temp_registry.generator, "generate_server") as mock_gen:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.errors = ["Generation failed"]
            mock_gen.return_value = mock_result

            result = await temp_registry.generate_server("test-server")

            assert result.success is False
            assert temp_registry.servers["test-server"].status == ServerStatus.ERROR

    @pytest.mark.asyncio
    async def test_generate_server_exception(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test server generation with exception."""
        # Register server first
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        # Mock exception during generation
        with patch.object(temp_registry.generator, "generate_server") as mock_gen:
            mock_gen.side_effect = Exception("Generation error")

            with pytest.raises(Exception):
                await temp_registry.generate_server("test-server")

            assert temp_registry.servers["test-server"].status == ServerStatus.ERROR

    @pytest.mark.asyncio
    async def test_start_server_success(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test successful server startup."""
        # Register and generate server
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        # Set server as generated
        temp_registry.servers["test-server"].status = ServerStatus.GENERATED
        temp_registry.servers["test-server"].server_path = "/fake/path"

        # Mock subprocess and file existence
        mock_process = MagicMock()
        mock_process.pid = 12345

        with patch("subprocess.Popen", return_value=mock_process), patch(
            "pathlib.Path.exists", return_value=True
        ):
            result = await temp_registry.start_server("test-server")

            assert result is True
            assert temp_registry.servers["test-server"].status == ServerStatus.RUNNING
            assert temp_registry.servers["test-server"].process_id == 12345
            assert "test-server" in temp_registry.processes

    @pytest.mark.asyncio
    async def test_start_server_not_ready(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test starting server that's not ready."""
        # Register server but don't generate
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        with pytest.raises(ValueError, match="not ready to start"):
            await temp_registry.start_server("test-server")

    @pytest.mark.asyncio
    async def test_start_server_already_running(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test starting server that's already running."""
        # Register and set up server
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        temp_registry.servers["test-server"].status = ServerStatus.GENERATED
        temp_registry.processes["test-server"] = MagicMock()

        result = await temp_registry.start_server("test-server")
        assert result is True

    @pytest.mark.asyncio
    async def test_start_server_missing_script(
        self, temp_registry, sample_config, sample_openapi_spec
    ):
        """Test starting server with missing script file."""
        # Register and generate server
        await temp_registry.register_server(
            server_id="test-server",
            name="Test Server",
            openapi_spec=sample_openapi_spec,
            config=sample_config,
            auto_generate=False,
        )

        temp_registry.servers["test-server"].status = ServerStatus.GENERATED
        temp_registry.servers["test-server"].server_path = "/fake/path"

        with patch("pathlib.Path.exists", return_value=False):
            result = await temp_registry.start_server("test-server")
            assert result is False
            assert temp_registry.servers["test-server"].status == ServerStatus.ERROR

    @pytest.mark.asyncio
    async def test_stop_server_success(self, temp_registry):
        """Test successful server stop."""
        # Set up running server
        mock_process = MagicMock()
        mock_process.wait.return_value = None
        temp_registry.processes["test-server"] = mock_process
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
            status=ServerStatus.RUNNING,
            process_id=12345,
        )

        result = await temp_registry.stop_server("test-server")

        assert result is True
        assert temp_registry.servers["test-server"].status == ServerStatus.STOPPED
        assert temp_registry.servers["test-server"].process_id is None
        assert "test-server" not in temp_registry.processes

    @pytest.mark.asyncio
    async def test_stop_server_force_kill(self, temp_registry):
        """Test server stop with force kill."""
        # Set up running server
        mock_process = MagicMock()
        mock_process.wait.side_effect = [
            TimeoutError(),
            None,
        ]  # First timeout, then success
        temp_registry.processes["test-server"] = mock_process
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
            status=ServerStatus.RUNNING,
        )

        with patch("subprocess.TimeoutExpired", TimeoutError):
            result = await temp_registry.stop_server("test-server")

            assert result is True
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_server_not_running(self, temp_registry):
        """Test stopping server that's not running."""
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
        )

        result = await temp_registry.stop_server("test-server")
        assert result is True
        assert temp_registry.servers["test-server"].status == ServerStatus.STOPPED

    @pytest.mark.asyncio
    async def test_delete_server_with_cleanup(self, temp_registry):
        """Test deleting server with file cleanup."""
        # Set up server with running process
        mock_process = MagicMock()
        temp_registry.processes["test-server"] = mock_process
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
            server_path="/fake/path",
        )

        with patch("shutil.rmtree") as mock_rmtree, patch(
            "pathlib.Path.exists", return_value=True
        ):
            result = await temp_registry.delete_server(
                "test-server", cleanup_files=True
            )

            assert result is True
            assert "test-server" not in temp_registry.servers
            mock_rmtree.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_server_without_cleanup(self, temp_registry):
        """Test deleting server without file cleanup."""
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
        )

        result = await temp_registry.delete_server("test-server", cleanup_files=False)

        assert result is True
        assert "test-server" not in temp_registry.servers

    def test_list_servers_with_filters(self, temp_registry):
        """Test listing servers with status and tag filters."""
        # Add multiple servers
        temp_registry.servers["server1"] = MCPServerInfo(
            id="server1",
            name="Server 1",
            generation_config=ServerGenerationConfig(
                server_name="Server1", package_name="server1"
            ),
            status=ServerStatus.RUNNING,
            tags=["api", "test"],
        )
        temp_registry.servers["server2"] = MCPServerInfo(
            id="server2",
            name="Server 2",
            generation_config=ServerGenerationConfig(
                server_name="Server2", package_name="server2"
            ),
            status=ServerStatus.STOPPED,
            tags=["web", "test"],
        )
        temp_registry.servers["server3"] = MCPServerInfo(
            id="server3",
            name="Server 3",
            generation_config=ServerGenerationConfig(
                server_name="Server3", package_name="server3"
            ),
            status=ServerStatus.RUNNING,
            tags=["api"],
        )

        # Test status filter
        running_servers = temp_registry.list_servers(status=ServerStatus.RUNNING)
        assert len(running_servers) == 2
        assert all(s.status == ServerStatus.RUNNING for s in running_servers)

        # Test tag filter
        api_servers = temp_registry.list_servers(tags=["api"])
        assert len(api_servers) == 2
        assert all("api" in s.tags for s in api_servers)

        # Test combined filters
        test_servers = temp_registry.list_servers(tags=["test"])
        assert len(test_servers) == 2

    @pytest.mark.asyncio
    async def test_health_check_running_server(self, temp_registry):
        """Test health check for running server."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.pid = 12345

        temp_registry.processes["test-server"] = mock_process
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
            status=ServerStatus.RUNNING,
        )

        result = await temp_registry.health_check("test-server")

        assert result["status"] == "running"
        assert result["process_id"] == 12345

    @pytest.mark.asyncio
    async def test_health_check_terminated_server(self, temp_registry):
        """Test health check for terminated server."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Process terminated
        mock_process.returncode = 0

        temp_registry.processes["test-server"] = mock_process
        temp_registry.servers["test-server"] = MCPServerInfo(
            id="test-server",
            name="Test Server",
            generation_config=ServerGenerationConfig(
                server_name="Test", package_name="test"
            ),
            status=ServerStatus.RUNNING,
        )

        result = await temp_registry.health_check("test-server")

        assert result["status"] == "terminated"
        assert result["exit_code"] == 0
        assert "test-server" not in temp_registry.processes

    @pytest.mark.asyncio
    async def test_get_server_logs(self, temp_registry):
        """Test getting server logs."""
        mock_process = MagicMock()
        temp_registry.processes["test-server"] = mock_process

        logs = await temp_registry.get_server_logs("test-server")

        # Should return placeholder message
        assert len(logs) == 1
        assert "not implemented" in logs[0].lower()

    @pytest.mark.asyncio
    async def test_get_server_logs_no_process(self, temp_registry):
        """Test getting logs for non-running server."""
        logs = await temp_registry.get_server_logs("test-server")
        assert logs == []

    def test_get_registry_stats(self, temp_registry):
        """Test getting registry statistics."""
        # Add servers with different statuses
        temp_registry.servers["server1"] = MCPServerInfo(
            id="server1",
            name="Server 1",
            generation_config=ServerGenerationConfig(
                server_name="Server1", package_name="server1"
            ),
            status=ServerStatus.RUNNING,
            endpoint_count=5,
            tool_count=5,
            complexity_score=3.5,
        )
        temp_registry.servers["server2"] = MCPServerInfo(
            id="server2",
            name="Server 2",
            generation_config=ServerGenerationConfig(
                server_name="Server2", package_name="server2"
            ),
            status=ServerStatus.STOPPED,
            endpoint_count=3,
            tool_count=3,
            complexity_score=2.0,
        )

        temp_registry.processes["server1"] = MagicMock()

        stats = temp_registry.get_registry_stats()

        assert stats["total_servers"] == 2
        assert stats["running_servers"] == 1
        assert stats["total_endpoints"] == 8
        assert stats["total_tools"] == 8
        assert stats["average_complexity"] == 2.75
        assert "status_distribution" in stats

    @pytest.mark.asyncio
    async def test_cleanup(self, temp_registry):
        """Test registry cleanup."""
        # Add running servers
        mock_process1 = MagicMock()
        mock_process2 = MagicMock()
        temp_registry.processes["server1"] = mock_process1
        temp_registry.processes["server2"] = mock_process2

        temp_registry.servers["server1"] = MCPServerInfo(
            id="server1",
            name="Server 1",
            generation_config=ServerGenerationConfig(
                server_name="Server1", package_name="server1"
            ),
        )
        temp_registry.servers["server2"] = MCPServerInfo(
            id="server2",
            name="Server 2",
            generation_config=ServerGenerationConfig(
                server_name="Server2", package_name="server2"
            ),
        )

        await temp_registry.cleanup()

        # All processes should be stopped
        assert len(temp_registry.processes) == 0


class TestRegistryGlobalFunctions:
    """Test global registry functions."""

    def test_get_registry_singleton(self):
        """Test global registry singleton behavior."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry1 = get_registry(temp_dir)
            registry2 = get_registry(temp_dir)

            # Should return the same instance
            assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_register_server_from_url(self):
        """Test registering server from URL."""
        config = ServerGenerationConfig(
            server_name="URL Server", package_name="url_server"
        )

        mock_response = MagicMock()
        mock_response.text = '{"openapi": "3.0.0", "info": {"title": "URL API"}}'

        with patch("httpx.AsyncClient") as mock_client, patch(
            "mcp.registry.get_registry"
        ) as mock_get_registry:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )
            mock_registry = MagicMock()
            mock_get_registry.return_value = mock_registry
            mock_registry.register_server = AsyncMock()

            await register_server_from_url(
                server_id="url-server",
                name="URL Server",
                openapi_url="https://api.example.com/openapi.json",
                config=config,
            )

            mock_registry.register_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_server_from_file(self):
        """Test registering server from file."""
        config = ServerGenerationConfig(
            server_name="File Server", package_name="file_server"
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"openapi": "3.0.0", "info": {"title": "File API"}}, f)
            temp_file = f.name

        try:
            with patch("mcp.registry.get_registry") as mock_get_registry:
                mock_registry = MagicMock()
                mock_get_registry.return_value = mock_registry
                mock_registry.register_server = AsyncMock()

                await register_server_from_file(
                    server_id="file-server",
                    name="File Server",
                    openapi_file=temp_file,
                    config=config,
                )

                mock_registry.register_server.assert_called_once()
        finally:
            Path(temp_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__])
