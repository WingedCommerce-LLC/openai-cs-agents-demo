"""
Tests for monitoring modules.
"""

from unittest.mock import MagicMock, patch

import pytest

from monitoring.health import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    get_health_checker,
    liveness_probe,
    readiness_probe,
)
from monitoring.telemetry import (
    MetricType,
    TelemetryManager,
    get_telemetry_manager,
    record_agent_execution,
    record_database_operation,
    record_request_count,
    record_request_duration,
)


class TestHealthChecker:
    """Test health checker functionality."""

    def test_health_checker_init(self):
        """Test health checker initialization."""
        checker = HealthChecker()
        assert checker.checks == {}
        assert checker.last_results == {}

    def test_register_check(self):
        """Test registering health checks."""
        checker = HealthChecker()

        async def dummy_check():
            return HealthCheckResult(
                name="test",
                status=HealthStatus.HEALTHY,
                message="OK",
                duration_ms=10.0,
            )

        checker.register_check("test", dummy_check)
        assert "test" in checker.checks
        assert checker.checks["test"] == dummy_check

    @pytest.mark.asyncio
    async def test_run_check_success(self):
        """Test running a successful health check."""
        checker = HealthChecker()

        async def healthy_check():
            return HealthCheckResult(
                name="test",
                status=HealthStatus.HEALTHY,
                message="All good",
                duration_ms=5.0,
            )

        checker.register_check("test", healthy_check)
        result = await checker.run_check("test")

        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_check_failure(self):
        """Test running a failing health check."""
        checker = HealthChecker()

        async def failing_check():
            raise Exception("Check failed")

        checker.register_check("test", failing_check)
        result = await checker.run_check("test")

        assert result.name == "test"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Check failed" in result.message
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_check_not_found(self):
        """Test running a non-existent health check."""
        checker = HealthChecker()
        result = await checker.run_check("nonexistent")

        assert result.name == "nonexistent"
        assert result.status == HealthStatus.UNKNOWN
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_run_all_checks_empty(self):
        """Test running all checks when none are registered."""
        checker = HealthChecker()
        health = await checker.run_all_checks()

        assert health.status == HealthStatus.UNKNOWN
        assert health.checks == []
        assert health.summary["total_checks"] == 0

    @pytest.mark.asyncio
    async def test_run_all_checks_mixed(self):
        """Test running all checks with mixed results."""
        checker = HealthChecker()

        async def healthy_check():
            return HealthCheckResult(
                name="healthy",
                status=HealthStatus.HEALTHY,
                message="OK",
                duration_ms=5.0,
            )

        async def degraded_check():
            return HealthCheckResult(
                name="degraded",
                status=HealthStatus.DEGRADED,
                message="Slow",
                duration_ms=100.0,
            )

        checker.register_check("healthy", healthy_check)
        checker.register_check("degraded", degraded_check)

        health = await checker.run_all_checks()

        assert health.status == HealthStatus.DEGRADED
        assert len(health.checks) == 2
        assert health.summary["total_checks"] == 2

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check."""
        checker = HealthChecker()
        result = await checker.database_health_check()

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert "connection successful" in result.message.lower()

    @pytest.mark.asyncio
    async def test_openai_api_health_check(self):
        """Test OpenAI API health check."""
        checker = HealthChecker()
        result = await checker.openai_api_health_check()

        assert result.name == "openai_api"
        assert result.status == HealthStatus.HEALTHY
        assert "accessible" in result.message.lower()

    @pytest.mark.asyncio
    async def test_memory_health_check_no_psutil(self):
        """Test memory health check without psutil."""
        checker = HealthChecker()

        with patch("builtins.__import__", side_effect=ImportError):
            result = await checker.memory_health_check()

        assert result.name == "memory"
        assert result.status == HealthStatus.UNKNOWN
        assert "psutil not available" in result.message

    @pytest.mark.asyncio
    async def test_memory_health_check_with_psutil(self):
        """Test memory health check with psutil."""
        pytest.importorskip("psutil")

        checker = HealthChecker()

        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.total = 8 * 1024**3  # 8GB
        mock_memory.available = 4 * 1024**3  # 4GB

        with patch("psutil.virtual_memory", return_value=mock_memory):
            result = await checker.memory_health_check()

        assert result.name == "memory"
        assert result.status == HealthStatus.HEALTHY
        assert "normal" in result.message.lower()

    def test_register_default_checks(self):
        """Test registering default health checks."""
        checker = HealthChecker()
        checker.register_default_checks()

        assert "database" in checker.checks
        assert "openai_api" in checker.checks
        assert "memory" in checker.checks

    @pytest.mark.asyncio
    async def test_liveness_probe(self):
        """Test Kubernetes liveness probe."""
        result = await liveness_probe()

        assert "status" in result
        assert "message" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_readiness_probe(self):
        """Test Kubernetes readiness probe."""
        result = await readiness_probe()

        assert "status" in result
        assert "health_status" in result
        assert "message" in result
        assert "timestamp" in result


class TestTelemetryManager:
    """Test telemetry manager functionality."""

    def test_telemetry_manager_init(self):
        """Test telemetry manager initialization."""
        manager = TelemetryManager()
        assert manager.metrics == {}
        assert manager.active_spans == {}
        assert manager.completed_spans == []
        assert manager.enabled is True

    def test_enable_disable(self):
        """Test enabling and disabling telemetry."""
        manager = TelemetryManager()

        manager.disable()
        assert manager.enabled is False

        manager.enable()
        assert manager.enabled is True

    def test_record_counter(self):
        """Test recording counter metrics."""
        manager = TelemetryManager()

        manager.record_counter("test_counter", 5.0, {"label": "value"})

        assert "test_counter" in manager.metrics
        metric = manager.metrics["test_counter"]
        assert metric.name == "test_counter"
        assert metric.value == 5.0
        assert metric.metric_type == MetricType.COUNTER
        assert metric.labels == {"label": "value"}

    def test_record_counter_aggregation(self):
        """Test counter metric aggregation."""
        manager = TelemetryManager()

        manager.record_counter("test_counter", 3.0)
        manager.record_counter("test_counter", 2.0)

        metric = manager.metrics["test_counter"]
        assert metric.value == 5.0

    def test_record_gauge(self):
        """Test recording gauge metrics."""
        manager = TelemetryManager()

        manager.record_gauge("test_gauge", 42.0, {"env": "test"})

        assert "test_gauge" in manager.metrics
        metric = manager.metrics["test_gauge"]
        assert metric.name == "test_gauge"
        assert metric.value == 42.0
        assert metric.metric_type == MetricType.GAUGE

    def test_record_histogram(self):
        """Test recording histogram metrics."""
        manager = TelemetryManager()

        manager.record_histogram("test_histogram", 100.0)

        assert "test_histogram_latest" in manager.metrics
        metric = manager.metrics["test_histogram_latest"]
        assert metric.value == 100.0
        assert metric.metric_type == MetricType.HISTOGRAM

    def test_start_finish_span(self):
        """Test starting and finishing spans."""
        manager = TelemetryManager()

        span_id = manager.start_span("test_operation", tags={"key": "value"})

        assert span_id in manager.active_spans
        span = manager.active_spans[span_id]
        assert span.operation_name == "test_operation"
        assert span.tags == {"key": "value"}

        manager.finish_span(span_id, status="ok", tags={"result": "success"})

        assert span_id not in manager.active_spans
        assert len(manager.completed_spans) == 1
        completed_span = manager.completed_spans[0]
        assert completed_span.status == "ok"
        assert completed_span.tags["result"] == "success"

    def test_add_span_tag(self):
        """Test adding tags to spans."""
        manager = TelemetryManager()

        span_id = manager.start_span("test_operation")
        manager.add_span_tag(span_id, "new_tag", "new_value")

        span = manager.active_spans[span_id]
        assert span.tags["new_tag"] == "new_value"

    def test_add_span_log(self):
        """Test adding logs to spans."""
        manager = TelemetryManager()

        span_id = manager.start_span("test_operation")
        manager.add_span_log(span_id, "Test message", "info")

        span = manager.active_spans[span_id]
        assert len(span.logs) == 1
        assert span.logs[0]["message"] == "Test message"
        assert span.logs[0]["level"] == "info"

    def test_trace_operation_context_manager(self):
        """Test trace operation context manager."""
        manager = TelemetryManager()

        with manager.trace_operation("test_op") as span_id:
            assert span_id in manager.active_spans

        assert span_id not in manager.active_spans
        assert len(manager.completed_spans) == 1

    def test_trace_operation_with_exception(self):
        """Test trace operation context manager with exception."""
        manager = TelemetryManager()

        with pytest.raises(ValueError):
            with manager.trace_operation("test_op") as _:
                raise ValueError("Test error")

        assert len(manager.completed_spans) == 1
        span = manager.completed_spans[0]
        assert span.status == "error"
        assert span.tags["error"] is True

    def test_get_metrics_summary_empty(self):
        """Test metrics summary with no metrics."""
        manager = TelemetryManager()
        summary = manager.get_metrics_summary()

        assert summary["total_metrics"] == 0
        assert summary["metrics"] == {}

    def test_get_metrics_summary_with_data(self):
        """Test metrics summary with data."""
        manager = TelemetryManager()

        manager.record_counter("counter1", 5.0)
        manager.record_gauge("gauge1", 10.0)

        summary = manager.get_metrics_summary()

        assert summary["total_metrics"] == 2
        assert "counter" in summary["metrics_by_type"]
        assert "gauge" in summary["metrics_by_type"]

    def test_get_traces_summary_empty(self):
        """Test traces summary with no traces."""
        manager = TelemetryManager()
        summary = manager.get_traces_summary()

        assert summary["active_spans"] == 0
        assert summary["completed_spans"] == 0

    def test_export_metrics_prometheus_empty(self):
        """Test Prometheus export with no metrics."""
        manager = TelemetryManager()
        export = manager.export_metrics_prometheus()

        assert "No metrics available" in export

    def test_export_metrics_prometheus_with_data(self):
        """Test Prometheus export with metrics."""
        manager = TelemetryManager()

        manager.record_counter("test_counter", 5.0, {"env": "test"})
        export = manager.export_metrics_prometheus()

        assert "test_counter" in export
        assert "counter" in export
        assert 'env="test"' in export

    def test_clear_metrics(self):
        """Test clearing metrics."""
        manager = TelemetryManager()

        manager.record_counter("test", 1.0)
        assert len(manager.metrics) == 1

        manager.clear_metrics()
        assert len(manager.metrics) == 0

    def test_clear_traces(self):
        """Test clearing traces."""
        manager = TelemetryManager()

        span_id = manager.start_span("test")
        manager.finish_span(span_id)

        assert len(manager.completed_spans) == 1

        manager.clear_traces()
        assert len(manager.active_spans) == 0
        assert len(manager.completed_spans) == 0

    def test_disabled_operations(self):
        """Test operations when telemetry is disabled."""
        manager = TelemetryManager()
        manager.disable()

        # These should not create any data
        manager.record_counter("test", 1.0)
        span_id = manager.start_span("test")
        manager.add_span_tag(span_id, "key", "value")

        assert len(manager.metrics) == 0
        assert span_id == "disabled"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_record_request_duration(self):
        """Test recording request duration."""
        manager = get_telemetry_manager()
        manager.clear_metrics()

        record_request_duration(150.0, "/api/test", "GET")

        assert "http_request_duration_ms_latest" in manager.metrics

    def test_record_request_count(self):
        """Test recording request count."""
        manager = get_telemetry_manager()
        manager.clear_metrics()

        record_request_count("/api/test", "POST", 200)

        assert "http_requests_total" in manager.metrics

    def test_record_agent_execution(self):
        """Test recording agent execution."""
        manager = get_telemetry_manager()
        manager.clear_metrics()

        record_agent_execution("test_agent", 500.0, True)

        assert "agent_executions_total" in manager.metrics
        assert "agent_execution_duration_ms_latest" in manager.metrics

    def test_record_database_operation(self):
        """Test recording database operation."""
        manager = get_telemetry_manager()
        manager.clear_metrics()

        record_database_operation("SELECT", 25.0, True)

        assert "database_operations_total" in manager.metrics
        assert "database_operation_duration_ms_latest" in manager.metrics


class TestGlobalInstances:
    """Test global instance functions."""

    def test_get_health_checker(self):
        """Test getting global health checker."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()

        assert checker1 is checker2  # Should be singleton

    def test_get_telemetry_manager(self):
        """Test getting global telemetry manager."""
        manager1 = get_telemetry_manager()
        manager2 = get_telemetry_manager()

        assert manager1 is manager2  # Should be singleton
