"""
Comprehensive tests for the CLI agent_cli module.

Tests all CLI commands including agent creation, MCP server management,
development environment commands, and project initialization.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

# Import the CLI module
from cli.agent_cli import cli


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_main_command(self):
        """Test the main CLI command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "OpenAI Agents Enterprise CLI" in result.output
        assert "Manage agents, MCP servers, and enterprise deployments" in result.output

    def test_cli_version(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_agent_group_help(self):
        """Test agent command group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["agent", "--help"])
        assert result.exit_code == 0
        assert "Agent management commands" in result.output

    def test_mcp_group_help(self):
        """Test MCP command group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP server management commands" in result.output

    def test_dev_group_help(self):
        """Test dev command group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "--help"])
        assert result.exit_code == 0
        assert "Development environment commands" in result.output

    def test_deploy_group_help(self):
        """Test deploy command group help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "Deployment commands" in result.output


class TestAgentCommands:
    """Test agent management commands."""

    def test_agent_create_basic(self):
        """Test basic agent creation."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                cli, ["agent", "create", "TestAgent", "--output-dir", temp_dir]
            )

            assert result.exit_code == 0
            assert "Creating agent 'TestAgent'" in result.output
            assert "Agent 'TestAgent' created" in result.output

            # Check if agent file was created
            agent_dir = Path(temp_dir) / "testagent"
            agent_file = agent_dir / "testagent_agent.py"
            assert agent_file.exists()

            # Check file content
            content = agent_file.read_text()
            assert "TestAgent Agent" in content
            assert "class TestAgentContext" in content
            assert "testagent_agent = Agent" in content

    def test_agent_create_with_description(self):
        """Test agent creation with description."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                cli,
                [
                    "agent",
                    "create",
                    "CustomAgent",
                    "--description",
                    "A custom test agent",
                    "--output-dir",
                    temp_dir,
                ],
            )

            assert result.exit_code == 0
            assert "Creating agent 'CustomAgent'" in result.output

    def test_agent_create_with_tools_and_guardrails(self):
        """Test agent creation with tools and guardrails."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                cli,
                [
                    "agent",
                    "create",
                    "AdvancedAgent",
                    "--tools",
                    "tool1",
                    "--tools",
                    "tool2",
                    "--guardrails",
                    "guard1",
                    "--output-dir",
                    temp_dir,
                ],
            )

            assert result.exit_code == 0
            assert "Creating agent 'AdvancedAgent'" in result.output

    def test_agent_create_with_spaces_in_name(self):
        """Test agent creation with spaces in name."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                cli, ["agent", "create", "My Test Agent", "--output-dir", temp_dir]
            )

            assert result.exit_code == 0

            # Check if directory and file names are properly formatted
            agent_dir = Path(temp_dir) / "my_test_agent"
            agent_file = agent_dir / "my_test_agent_agent.py"
            assert agent_file.exists()

            content = agent_file.read_text()
            assert "My Test Agent Agent" in content
            assert "class MyTestAgentContext" in content


class TestMCPCommands:
    """Test MCP server management commands."""

    @patch("mcp.server_generator.MCPServerGenerator")
    @patch("mcp.registry.MCPServerRegistry")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"openapi": "3.0.0"}')
    def test_mcp_create_server_success(
        self, mock_file, mock_exists, mock_registry, mock_generator
    ):
        """Test successful MCP server creation."""
        # Setup mocks
        mock_exists.return_value = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.generation_summary = {
            "total_files": 5,
            "selected_endpoints": 3,
            "complexity_distribution": {"simple": 2, "moderate": 1, "complex": 0},
        }

        mock_gen_instance = mock_generator.return_value
        mock_gen_instance.generate_server.return_value = mock_result
        mock_gen_instance.write_server_to_disk.return_value = "/path/to/server"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp",
                "create",
                "TestServer",
                "openapi.yaml",
                "--base-url",
                "https://api.example.com",
            ],
        )

        assert result.exit_code == 0
        assert "Creating MCP server 'TestServer'" in result.output
        assert "MCP server 'TestServer' created successfully!" in result.output
        assert "Generated 5 files" in result.output
        assert "Included 3 endpoints" in result.output

    @patch("os.path.exists")
    def test_mcp_create_server_file_not_found(self, mock_exists):
        """Test MCP server creation with missing OpenAPI file."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp",
                "create",
                "TestServer",
                "missing.yaml",
                "--base-url",
                "https://api.example.com",
            ],
        )

        assert result.exit_code == 0
        assert "OpenAPI spec file not found" in result.output

    @patch("mcp.server_generator.MCPServerGenerator")
    @patch("os.path.exists")
    def test_mcp_create_server_generation_failure(self, mock_exists, mock_generator):
        """Test MCP server creation with generation failure."""
        mock_exists.return_value = True

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Test error 1", "Test error 2"]

        mock_gen_instance = mock_generator.return_value
        mock_gen_instance.generate_server.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp",
                "create",
                "TestServer",
                "openapi.yaml",
                "--base-url",
                "https://api.example.com",
            ],
        )

        assert result.exit_code == 0
        assert "Server generation failed:" in result.output
        assert "Test error 1" in result.output
        assert "Test error 2" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_list_servers_empty(self, mock_registry):
        """Test listing MCP servers when none exist."""
        mock_reg_instance = mock_registry.return_value
        mock_reg_instance.list_servers.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "list"])

        assert result.exit_code == 0
        assert "No MCP servers registered" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_list_servers_with_data(self, mock_registry):
        """Test listing MCP servers with data."""
        from datetime import datetime

        mock_server = MagicMock()
        mock_server.name = "TestServer"
        mock_server.id = "test_server"
        mock_server.status.value = "generated"
        mock_server.endpoint_count = 5
        mock_server.created_at = datetime(2023, 1, 1, 12, 0)
        mock_server.server_path = "/path/to/server"

        mock_reg_instance = mock_registry.return_value
        mock_reg_instance.list_servers.return_value = [mock_server]

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "list"])

        assert result.exit_code == 0
        assert "Found 1 MCP servers:" in result.output
        assert "TestServer (test_server)" in result.output
        assert "Status: generated" in result.output
        assert "Endpoints: 5" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    @patch("asyncio.run")
    def test_mcp_start_server_success(self, mock_asyncio_run, mock_registry):
        """Test starting MCP server successfully."""
        mock_asyncio_run.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "start", "test_server"])

        assert result.exit_code == 0
        assert "Starting MCP server 'test_server'" in result.output
        assert "Server 'test_server' started successfully!" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    @patch("asyncio.run")
    def test_mcp_start_server_failure(self, mock_asyncio_run, mock_registry):
        """Test starting MCP server with failure."""
        mock_asyncio_run.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "start", "test_server"])

        assert result.exit_code == 0
        assert "Starting MCP server 'test_server'" in result.output
        assert "Failed to start server 'test_server'" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    @patch("asyncio.run")
    def test_mcp_stop_server_success(self, mock_asyncio_run, mock_registry):
        """Test stopping MCP server successfully."""
        mock_asyncio_run.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "stop", "test_server"])

        assert result.exit_code == 0
        assert "Stopping MCP server 'test_server'" in result.output
        assert "Server 'test_server' stopped successfully!" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    @patch("asyncio.run")
    def test_mcp_server_status(self, mock_asyncio_run, mock_registry):
        """Test getting MCP server status."""
        from datetime import datetime

        mock_server = MagicMock()
        mock_server.name = "TestServer"
        mock_server.status.value = "running"
        mock_server.endpoint_count = 5
        mock_server.tool_count = 5
        mock_server.complexity_score = 3.5
        mock_server.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_server.updated_at = datetime(2023, 1, 1, 12, 30, 0)
        mock_server.server_path = "/path/to/server"

        mock_health = {"status": "running", "process_id": 12345, "uptime": 1800}

        mock_reg_instance = mock_registry.return_value
        mock_reg_instance.get_server.return_value = mock_server
        mock_asyncio_run.return_value = mock_health

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "status", "test_server"])

        assert result.exit_code == 0
        assert "Status for MCP server 'TestServer'" in result.output
        assert "Server Status: running" in result.output
        assert "Health Status: running" in result.output
        assert "Process ID: 12345" in result.output
        assert "Uptime: 1800 seconds" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_server_status_not_found(self, mock_registry):
        """Test getting status for non-existent server."""
        mock_reg_instance = mock_registry.return_value
        mock_reg_instance.get_server.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "status", "nonexistent"])

        assert result.exit_code == 0
        assert "Server 'nonexistent' not found" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    @patch("asyncio.run")
    @patch("click.confirm")
    def test_mcp_delete_server_confirmed(
        self, mock_confirm, mock_asyncio_run, mock_registry
    ):
        """Test deleting MCP server with confirmation."""
        mock_confirm.return_value = True
        mock_asyncio_run.return_value = True

        mock_server = MagicMock()
        mock_server.name = "TestServer"

        mock_reg_instance = mock_registry.return_value
        mock_reg_instance.get_server.return_value = mock_server

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "delete", "test_server"])

        assert result.exit_code == 0
        assert "Deleting MCP server 'test_server'" in result.output
        assert "Server 'test_server' deleted completely" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    @patch("click.confirm")
    def test_mcp_delete_server_cancelled(self, mock_confirm, mock_registry):
        """Test deleting MCP server with cancellation."""
        mock_confirm.return_value = False

        mock_server = MagicMock()
        mock_server.name = "TestServer"

        mock_reg_instance = mock_registry.return_value
        mock_reg_instance.get_server.return_value = mock_server

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "delete", "test_server"])

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output


class TestDevCommands:
    """Test development environment commands."""

    @patch("os.path.exists")
    @patch("os.system")
    def test_dev_start_with_compose_file(self, mock_system, mock_exists):
        """Test starting dev environment with docker-compose file."""
        mock_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "start"])

        assert result.exit_code == 0
        assert "Starting development environment" in result.output
        mock_system.assert_called_once_with(
            "docker-compose -f docker-compose.dev.yml up --build"
        )

    @patch("os.path.exists")
    def test_dev_start_without_compose_file(self, mock_exists):
        """Test starting dev environment without docker-compose file."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "start"])

        assert result.exit_code == 0
        assert "Starting development environment" in result.output
        assert "docker-compose.dev.yml not found" in result.output

    @patch("os.path.exists")
    @patch("os.system")
    def test_dev_stop_with_compose_file(self, mock_system, mock_exists):
        """Test stopping dev environment with docker-compose file."""
        mock_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "stop"])

        assert result.exit_code == 0
        assert "Stopping development environment" in result.output
        mock_system.assert_called_once_with(
            "docker-compose -f docker-compose.dev.yml down"
        )

    @patch("os.path.exists")
    def test_dev_stop_without_compose_file(self, mock_exists):
        """Test stopping dev environment without docker-compose file."""
        mock_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "stop"])

        assert result.exit_code == 0
        assert "Stopping development environment" in result.output
        assert "docker-compose.dev.yml not found" in result.output


class TestDeployCommands:
    """Test deployment commands."""

    def test_deploy_k8s_development(self):
        """Test Kubernetes deployment to development."""
        runner = CliRunner()
        result = runner.invoke(cli, ["deploy", "k8s", "--environment", "development"])

        assert result.exit_code == 0
        assert "Deploying to development" in result.output
        assert "Would deploy to development environment" in result.output

    def test_deploy_k8s_staging(self):
        """Test Kubernetes deployment to staging."""
        runner = CliRunner()
        result = runner.invoke(cli, ["deploy", "k8s", "--environment", "staging"])

        assert result.exit_code == 0
        assert "Deploying to staging" in result.output
        assert "Would deploy to staging environment" in result.output

    @patch("click.confirm")
    def test_deploy_k8s_production_confirmed(self, mock_confirm):
        """Test Kubernetes deployment to production with confirmation."""
        mock_confirm.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli, ["deploy", "k8s", "--environment", "production"])

        assert result.exit_code == 0
        assert "Deploying to production" in result.output
        assert "Would deploy to production environment" in result.output

    @patch("click.confirm")
    def test_deploy_k8s_production_cancelled(self, mock_confirm):
        """Test Kubernetes deployment to production with cancellation."""
        mock_confirm.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli, ["deploy", "k8s", "--environment", "production"])

        assert result.exit_code == 0
        assert "Deploying to production" in result.output
        # Should exit early without deployment message


class TestInitCommand:
    """Test project initialization command."""

    def test_init_command(self):
        """Test project initialization."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                result = runner.invoke(cli, ["init"])

                assert result.exit_code == 0
                assert "Initializing OpenAI Agents Enterprise project" in result.output
                assert "Project initialized successfully!" in result.output

                # Check if directories were created
                expected_dirs = [
                    "agents",
                    "mcp_servers",
                    "config",
                    "security",
                    "models",
                    "repositories",
                    "auth",
                    "audit",
                    "monitoring",
                    "tests",
                    "docs",
                ]

                for directory in expected_dirs:
                    assert Path(directory).exists()
                    assert f"Created directory: {directory}" in result.output

                # Check if .env.example was created
                env_file = Path(".env.example")
                assert env_file.exists()

                content = env_file.read_text()
                assert "ENVIRONMENT=development" in content
                assert "OPENAI_API_KEY=your-api-key-here" in content

                # Check next steps instructions
                assert "Next steps:" in result.output
                assert "Copy .env.example to .env" in result.output

            finally:
                os.chdir(original_cwd)


class TestErrorHandling:
    """Test error handling in CLI commands."""

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_list_servers_exception(self, mock_registry):
        """Test exception handling in list servers command."""
        mock_registry.side_effect = Exception("Test exception")

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "list"])

        assert result.exit_code == 0
        assert "Failed to list servers: Test exception" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_start_server_exception(self, mock_registry):
        """Test exception handling in start server command."""
        mock_registry.side_effect = Exception("Test exception")

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "start", "test_server"])

        assert result.exit_code == 0
        assert "Failed to start server: Test exception" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_stop_server_exception(self, mock_registry):
        """Test exception handling in stop server command."""
        mock_registry.side_effect = Exception("Test exception")

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "stop", "test_server"])

        assert result.exit_code == 0
        assert "Failed to stop server: Test exception" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_server_status_exception(self, mock_registry):
        """Test exception handling in server status command."""
        mock_registry.side_effect = Exception("Test exception")

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "status", "test_server"])

        assert result.exit_code == 0
        assert "Failed to get server status: Test exception" in result.output

    @patch("mcp.registry.MCPServerRegistry")
    def test_mcp_delete_server_exception(self, mock_registry):
        """Test exception handling in delete server command."""
        mock_registry.side_effect = Exception("Test exception")

        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "delete", "test_server"])

        assert result.exit_code == 0
        assert "Failed to delete server: Test exception" in result.output


class TestMCPCreateServerOptions:
    """Test MCP create server command with various options."""

    @patch("mcp.server_generator.MCPServerGenerator")
    @patch("mcp.registry.MCPServerRegistry")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"openapi": "3.0.0"}')
    def test_mcp_create_server_with_all_options(
        self, mock_file, mock_exists, mock_registry, mock_generator
    ):
        """Test MCP server creation with all options."""
        mock_exists.return_value = True

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.generation_summary = {
            "total_files": 8,
            "selected_endpoints": 5,
            "complexity_distribution": {"simple": 3, "moderate": 2, "complex": 0},
        }

        mock_gen_instance = mock_generator.return_value
        mock_gen_instance.generate_server.return_value = mock_result
        mock_gen_instance.write_server_to_disk.return_value = "/custom/path"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp",
                "create",
                "AdvancedServer",
                "openapi.yaml",
                "--base-url",
                "https://api.advanced.com",
                "--output-dir",
                "/custom/output",
                "--max-endpoints",
                "15",
                "--max-complexity",
                "6",
                "--auth-type",
                "bearer",
                "--include-tests",
                "--include-docker",
            ],
        )

        assert result.exit_code == 0
        assert "Creating MCP server 'AdvancedServer'" in result.output
        assert "Base URL: https://api.advanced.com" in result.output

    @patch("mcp.server_generator.MCPServerGenerator")
    @patch("mcp.registry.MCPServerRegistry")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"openapi": "3.0.0"}')
    @patch("asyncio.run")
    def test_mcp_create_server_with_auto_deploy(
        self, mock_asyncio_run, mock_file, mock_exists, mock_registry, mock_generator
    ):
        """Test MCP server creation with auto-deploy."""
        mock_exists.return_value = True
        mock_asyncio_run.return_value = None  # Successful registration

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.generation_summary = {
            "total_files": 5,
            "selected_endpoints": 3,
            "complexity_distribution": {"simple": 2, "moderate": 1, "complex": 0},
        }

        mock_gen_instance = mock_generator.return_value
        mock_gen_instance.generate_server.return_value = mock_result
        mock_gen_instance.write_server_to_disk.return_value = "/path/to/server"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp",
                "create",
                "AutoDeployServer",
                "openapi.yaml",
                "--base-url",
                "https://api.example.com",
                "--auto-deploy",
            ],
        )

        assert result.exit_code == 0
        assert "Auto-deploying server..." in result.output
        assert "Server registered and deployed!" in result.output

    @patch("mcp.server_generator.MCPServerGenerator")
    @patch("mcp.registry.MCPServerRegistry")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b'{"openapi": "3.0.0"}')
    @patch("asyncio.run")
    def test_mcp_create_server_auto_deploy_failure(
        self, mock_asyncio_run, mock_file, mock_exists, mock_registry, mock_generator
    ):
        """Test MCP server creation with auto-deploy failure."""
        mock_exists.return_value = True
        mock_asyncio_run.side_effect = Exception("Deployment failed")

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.generation_summary = {
            "total_files": 5,
            "selected_endpoints": 3,
            "complexity_distribution": {"simple": 2, "moderate": 1, "complex": 0},
        }

        mock_gen_instance = mock_generator.return_value
        mock_gen_instance.generate_server.return_value = mock_result
        mock_gen_instance.write_server_to_disk.return_value = "/path/to/server"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp",
                "create",
                "FailDeployServer",
                "openapi.yaml",
                "--base-url",
                "https://api.example.com",
                "--auto-deploy",
            ],
        )

        assert result.exit_code == 0
        assert "Auto-deploying server..." in result.output
        assert (
            "Server created but deployment failed: Deployment failed" in result.output
        )


if __name__ == "__main__":
    pytest.main([__file__])
