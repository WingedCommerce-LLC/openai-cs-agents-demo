"""
OpenTelemetry Integration

Provides comprehensive observability with metrics, traces, and logs
for enterprise production monitoring.
"""

import logging
import time
from contextlib import contextmanager
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Metric(BaseModel):
    """Metric data structure."""

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    metric_type: MetricType = Field(..., description="Type of metric")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metric labels")
    timestamp: float = Field(default_factory=time.time, description="Metric timestamp")
    help_text: Optional[str] = Field(None, description="Metric description")


class TraceSpan(BaseModel):
    """Trace span data structure."""

    trace_id: str = Field(..., description="Trace identifier")
    span_id: str = Field(..., description="Span identifier")
    parent_span_id: Optional[str] = Field(None, description="Parent span ID")
    operation_name: str = Field(..., description="Operation name")
    start_time: float = Field(..., description="Span start time")
    end_time: Optional[float] = Field(None, description="Span end time")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Span tags")
    logs: List[Dict[str, Any]] = Field(default_factory=list, description="Span logs")
    status: str = Field(default="ok", description="Span status")


class TelemetryManager:
    """
    Comprehensive telemetry and observability manager.

    Features:
    - Metrics collection and export
    - Distributed tracing
    - Structured logging
    - Performance monitoring
    - Custom instrumentation
    """

    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.active_spans: Dict[str, TraceSpan] = {}
        self.completed_spans: List[TraceSpan] = []
        self.enabled = True

    def enable(self) -> None:
        """Enable telemetry collection."""
        self.enabled = True
        logger.info("Telemetry collection enabled")

    def disable(self) -> None:
        """Disable telemetry collection."""
        self.enabled = False
        logger.info("Telemetry collection disabled")

    def record_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """
        Record a counter metric.

        Args:
            name: Metric name
            value: Counter increment value
            labels: Metric labels
            help_text: Metric description
        """
        if not self.enabled:
            return

        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels or {},
            help_text=help_text,
        )

        # Aggregate counter values
        if name in self.metrics:
            existing = self.metrics[name]
            if existing.metric_type == MetricType.COUNTER:
                existing.value += value
                existing.timestamp = time.time()
            else:
                logger.warning(f"Metric {name} type mismatch")
        else:
            self.metrics[name] = metric

    def record_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """
        Record a gauge metric.

        Args:
            name: Metric name
            value: Gauge value
            labels: Metric labels
            help_text: Metric description
        """
        if not self.enabled:
            return

        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {},
            help_text=help_text,
        )

        self.metrics[name] = metric

    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """
        Record a histogram metric.

        Args:
            name: Metric name
            value: Observed value
            labels: Metric labels
            help_text: Metric description
        """
        if not self.enabled:
            return

        # For simplicity, store as gauge for now
        # In production, this would use proper histogram buckets
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {},
            help_text=help_text,
        )

        self.metrics[f"{name}_latest"] = metric

    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start a new trace span.

        Args:
            operation_name: Name of the operation
            parent_span_id: Parent span identifier
            tags: Initial span tags

        Returns:
            Span identifier
        """
        if not self.enabled:
            return "disabled"

        import uuid

        span_id = str(uuid.uuid4())
        trace_id = parent_span_id or str(uuid.uuid4())

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {},
        )

        self.active_spans[span_id] = span
        return span_id

    def finish_span(
        self,
        span_id: str,
        status: str = "ok",
        tags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Finish a trace span.

        Args:
            span_id: Span identifier
            status: Span completion status
            tags: Additional tags to add
        """
        if not self.enabled or span_id == "disabled":
            return

        if span_id not in self.active_spans:
            logger.warning(f"Span {span_id} not found in active spans")
            return

        span = self.active_spans.pop(span_id)
        span.end_time = time.time()
        span.status = status

        if tags:
            span.tags.update(tags)

        self.completed_spans.append(span)

        # Keep only recent spans to prevent memory growth
        if len(self.completed_spans) > 1000:
            self.completed_spans = self.completed_spans[-500:]

    def add_span_tag(self, span_id: str, key: str, value: Any) -> None:
        """
        Add a tag to an active span.

        Args:
            span_id: Span identifier
            key: Tag key
            value: Tag value
        """
        if not self.enabled or span_id == "disabled":
            return

        if span_id in self.active_spans:
            self.active_spans[span_id].tags[key] = value

    def add_span_log(self, span_id: str, message: str, level: str = "info") -> None:
        """
        Add a log entry to an active span.

        Args:
            span_id: Span identifier
            message: Log message
            level: Log level
        """
        if not self.enabled or span_id == "disabled":
            return

        if span_id in self.active_spans:
            log_entry = {
                "timestamp": time.time(),
                "level": level,
                "message": message,
            }
            self.active_spans[span_id].logs.append(log_entry)

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing operations.

        Args:
            operation_name: Name of the operation
            tags: Initial span tags

        Yields:
            Span identifier
        """
        span_id = self.start_span(operation_name, tags=tags)
        try:
            yield span_id
            self.finish_span(span_id, status="ok")
        except Exception as e:
            self.add_span_tag(span_id, "error", True)
            self.add_span_tag(span_id, "error.message", str(e))
            self.add_span_tag(span_id, "error.type", type(e).__name__)
            self.finish_span(span_id, status="error")
            raise

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        if not self.metrics:
            return {"total_metrics": 0, "metrics": {}}

        metrics_by_type = {}
        for metric in self.metrics.values():
            metric_type = metric.metric_type
            if metric_type not in metrics_by_type:
                metrics_by_type[metric_type] = []
            metrics_by_type[metric_type].append(
                {
                    "name": metric.name,
                    "value": metric.value,
                    "labels": metric.labels,
                    "timestamp": metric.timestamp,
                }
            )

        return {
            "total_metrics": len(self.metrics),
            "metrics_by_type": metrics_by_type,
            "last_updated": max(
                (m.timestamp for m in self.metrics.values()), default=0
            ),
        }

    def get_traces_summary(self) -> Dict[str, Any]:
        """Get summary of collected traces."""
        active_count = len(self.active_spans)
        completed_count = len(self.completed_spans)

        if completed_count == 0:
            return {
                "active_spans": active_count,
                "completed_spans": 0,
                "total_spans": active_count,
            }

        # Calculate trace statistics
        durations = []
        error_count = 0
        operations = {}

        for span in self.completed_spans:
            if span.end_time:
                duration = span.end_time - span.start_time
                durations.append(duration)

            if span.status == "error":
                error_count += 1

            op_name = span.operation_name
            operations[op_name] = operations.get(op_name, 0) + 1

        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0

        return {
            "active_spans": active_count,
            "completed_spans": completed_count,
            "total_spans": active_count + completed_count,
            "error_rate": error_count / completed_count if completed_count > 0 else 0,
            "average_duration_ms": round(avg_duration * 1000, 2),
            "max_duration_ms": round(max_duration * 1000, 2),
            "min_duration_ms": round(min_duration * 1000, 2),
            "operations": operations,
        }

    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        if not self.metrics:
            return "# No metrics available\n"

        lines = ["# Prometheus metrics export"]

        for metric in self.metrics.values():
            # Add help text
            if metric.help_text:
                lines.append(f"# HELP {metric.name} {metric.help_text}")

            # Add type
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")

            # Add metric with labels
            if metric.labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                lines.append(f"{metric.name}{{{label_str}}} {metric.value}")
            else:
                lines.append(f"{metric.name} {metric.value}")

        return "\n".join(lines) + "\n"

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()
        logger.info("Metrics cleared")

    def clear_traces(self) -> None:
        """Clear all trace data."""
        self.active_spans.clear()
        self.completed_spans.clear()
        logger.info("Traces cleared")


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager() -> TelemetryManager:
    """Get the global telemetry manager instance."""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager


# Convenience functions for common operations
def record_request_duration(duration_ms: float, endpoint: str, method: str) -> None:
    """Record HTTP request duration."""
    telemetry = get_telemetry_manager()
    telemetry.record_histogram(
        "http_request_duration_ms",
        duration_ms,
        labels={"endpoint": endpoint, "method": method},
        help_text="HTTP request duration in milliseconds",
    )


def record_request_count(endpoint: str, method: str, status_code: int) -> None:
    """Record HTTP request count."""
    telemetry = get_telemetry_manager()
    telemetry.record_counter(
        "http_requests_total",
        labels={
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code),
        },
        help_text="Total HTTP requests",
    )


def record_agent_execution(agent_name: str, duration_ms: float, success: bool) -> None:
    """Record agent execution metrics."""
    telemetry = get_telemetry_manager()

    # Record execution count
    telemetry.record_counter(
        "agent_executions_total",
        labels={"agent": agent_name, "success": str(success).lower()},
        help_text="Total agent executions",
    )

    # Record execution duration
    telemetry.record_histogram(
        "agent_execution_duration_ms",
        duration_ms,
        labels={"agent": agent_name},
        help_text="Agent execution duration in milliseconds",
    )


def record_database_operation(
    operation: str, duration_ms: float, success: bool
) -> None:
    """Record database operation metrics."""
    telemetry = get_telemetry_manager()

    telemetry.record_counter(
        "database_operations_total",
        labels={"operation": operation, "success": str(success).lower()},
        help_text="Total database operations",
    )

    telemetry.record_histogram(
        "database_operation_duration_ms",
        duration_ms,
        labels={"operation": operation},
        help_text="Database operation duration in milliseconds",
    )
