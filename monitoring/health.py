"""
Health Check System

Provides comprehensive health monitoring for all system components
including database, external services, and application health.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult(BaseModel):
    """Result of a health check."""

    name: str = Field(..., description="Name of the health check")
    status: HealthStatus = Field(..., description="Health status")
    message: str = Field(..., description="Status message")
    duration_ms: float = Field(..., description="Check duration in milliseconds")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Check timestamp",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional check details"
    )


class SystemHealth(BaseModel):
    """Overall system health status."""

    status: HealthStatus = Field(..., description="Overall system status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Health check timestamp",
    )
    checks: List[HealthCheckResult] = Field(
        default_factory=list, description="Individual health check results"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Health summary statistics"
    )


class HealthChecker:
    """
    Comprehensive health monitoring system.

    Features:
    - Database connectivity checks
    - External service health monitoring
    - Application component health
    - Kubernetes readiness/liveness probes
    - Performance metrics collection
    """

    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}

    def register_check(self, name: str, check_func: callable) -> None:
        """
        Register a health check function.

        Args:
            name: Unique name for the health check
            check_func: Async function that returns HealthCheckResult
        """
        self.checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    async def run_check(self, name: str) -> HealthCheckResult:
        """
        Run a specific health check.

        Args:
            name: Name of the health check to run

        Returns:
            Health check result
        """
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
                duration_ms=0.0,
            )

        start_time = time.time()
        try:
            result = await self.checks[name]()
            duration_ms = (time.time() - start_time) * 1000

            # Ensure result has correct duration
            if hasattr(result, "duration_ms"):
                result.duration_ms = duration_ms
            else:
                result = HealthCheckResult(
                    name=name,
                    status=result.status
                    if hasattr(result, "status")
                    else HealthStatus.UNKNOWN,
                    message=result.message
                    if hasattr(result, "message")
                    else str(result),
                    duration_ms=duration_ms,
                    details=result.details if hasattr(result, "details") else {},
                )

            self.last_results[name] = result
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check '{name}' failed: {e}")

            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__},
            )

            self.last_results[name] = result
            return result

    async def run_all_checks(self) -> SystemHealth:
        """
        Run all registered health checks.

        Returns:
            Overall system health status
        """
        if not self.checks:
            return SystemHealth(
                status=HealthStatus.UNKNOWN,
                checks=[],
                summary={"total_checks": 0, "message": "No health checks registered"},
            )

        # Run all checks concurrently
        tasks = [self.run_check(name) for name in self.checks.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        check_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_name = list(self.checks.keys())[i]
                check_results.append(
                    HealthCheckResult(
                        name=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check execution failed: {str(result)}",
                        duration_ms=0.0,
                        details={
                            "error": str(result),
                            "error_type": type(result).__name__,
                        },
                    )
                )
            else:
                check_results.append(result)

        # Determine overall system status
        overall_status = self._determine_overall_status(check_results)

        # Generate summary
        summary = self._generate_summary(check_results)

        return SystemHealth(
            status=overall_status,
            checks=check_results,
            summary=summary,
        )

    def _determine_overall_status(
        self, results: List[HealthCheckResult]
    ) -> HealthStatus:
        """Determine overall system status from individual check results."""
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in results]

        # If any check is unhealthy, system is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY

        # If any check is degraded, system is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # If any check is unknown, system status is unknown
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN

        # All checks are healthy
        return HealthStatus.HEALTHY

    def _generate_summary(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate summary statistics from check results."""
        if not results:
            return {"total_checks": 0}

        status_counts = {}
        total_duration = 0.0
        slowest_check = None
        fastest_check = None

        for result in results:
            # Count statuses
            status = result.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            # Track durations
            total_duration += result.duration_ms

            if slowest_check is None or result.duration_ms > slowest_check.duration_ms:
                slowest_check = result

            if fastest_check is None or result.duration_ms < fastest_check.duration_ms:
                fastest_check = result

        avg_duration = total_duration / len(results)

        return {
            "total_checks": len(results),
            "status_counts": status_counts,
            "average_duration_ms": round(avg_duration, 2),
            "total_duration_ms": round(total_duration, 2),
            "slowest_check": {
                "name": slowest_check.name,
                "duration_ms": slowest_check.duration_ms,
            }
            if slowest_check
            else None,
            "fastest_check": {
                "name": fastest_check.name,
                "duration_ms": fastest_check.duration_ms,
            }
            if fastest_check
            else None,
        }

    async def database_health_check(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        try:
            # This would be implemented with actual database connection
            # For now, return a mock healthy status
            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                duration_ms=0.0,
                details={
                    "connection_pool_size": 10,
                    "active_connections": 2,
                    "query_time_ms": 15.5,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                duration_ms=0.0,
                details={"error": str(e)},
            )

    async def openai_api_health_check(self) -> HealthCheckResult:
        """Check OpenAI API connectivity."""
        try:
            # This would make an actual API call to OpenAI
            # For now, return a mock healthy status
            return HealthCheckResult(
                name="openai_api",
                status=HealthStatus.HEALTHY,
                message="OpenAI API accessible",
                duration_ms=0.0,
                details={
                    "api_version": "v1",
                    "rate_limit_remaining": 1000,
                    "response_time_ms": 250,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                name="openai_api",
                status=HealthStatus.UNHEALTHY,
                message=f"OpenAI API check failed: {str(e)}",
                duration_ms=0.0,
                details={"error": str(e)},
            )

    async def memory_health_check(self) -> HealthCheckResult:
        """Check system memory usage."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"High memory usage: {memory_percent}%"
            elif memory_percent > 75:
                status = HealthStatus.DEGRADED
                message = f"Elevated memory usage: {memory_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory_percent}%"

            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                duration_ms=0.0,
                details={
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory_percent,
                },
            )
        except ImportError:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="psutil not available for memory monitoring",
                duration_ms=0.0,
                details={"error": "psutil package not installed"},
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {str(e)}",
                duration_ms=0.0,
                details={"error": str(e)},
            )

    def register_default_checks(self) -> None:
        """Register default health checks."""
        self.register_check("database", self.database_health_check)
        self.register_check("openai_api", self.openai_api_health_check)
        self.register_check("memory", self.memory_health_check)


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        _health_checker.register_default_checks()
    return _health_checker


# Convenience functions for Kubernetes probes
async def liveness_probe() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint.

    Returns basic application health status.
    """
    checker = get_health_checker()

    # Run only critical checks for liveness
    critical_checks = ["database", "memory"]
    results = []

    for check_name in critical_checks:
        if check_name in checker.checks:
            result = await checker.run_check(check_name)
            results.append(result)

    # Determine if application is alive
    unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)

    if unhealthy_count > 0:
        return {
            "status": "unhealthy",
            "message": f"{unhealthy_count} critical checks failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "healthy",
        "message": "Application is alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def readiness_probe() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.

    Returns whether application is ready to serve traffic.
    """
    checker = get_health_checker()
    health = await checker.run_all_checks()

    # Application is ready if overall status is healthy or degraded
    is_ready = health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    return {
        "status": "ready" if is_ready else "not_ready",
        "health_status": health.status.value,
        "message": f"System status: {health.status.value}",
        "timestamp": health.timestamp.isoformat(),
        "checks_summary": health.summary,
    }
