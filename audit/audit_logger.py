"""
Audit Logging System

This module provides comprehensive audit logging for the enterprise platform,
including security events, user actions, system changes, and compliance tracking.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"

    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"

    # MCP server events
    MCP_SERVER_CREATED = "mcp_server_created"
    MCP_SERVER_UPDATED = "mcp_server_updated"
    MCP_SERVER_DELETED = "mcp_server_deleted"
    MCP_SERVER_STARTED = "mcp_server_started"
    MCP_SERVER_STOPPED = "mcp_server_stopped"

    # Agent events
    AGENT_CREATED = "agent_created"
    AGENT_UPDATED = "agent_updated"
    AGENT_DELETED = "agent_deleted"
    AGENT_EXECUTED = "agent_executed"

    # Chat events
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_ENDED = "conversation_ended"
    MESSAGE_SENT = "message_sent"

    # System events
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    SYSTEM_BACKUP_CREATED = "system_backup_created"
    SYSTEM_MAINTENANCE = "system_maintenance"

    # Security events
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Audit event model."""

    id: str = Field(..., description="Unique event identifier")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    severity: AuditSeverity = Field(
        default=AuditSeverity.MEDIUM, description="Event severity"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Event timestamp"
    )
    # User information
    user_id: Optional[str] = Field(
        default=None, description="User ID who performed the action"
    )
    username: Optional[str] = Field(
        default=None, description="Username who performed the action"
    )
    user_ip: Optional[str] = Field(default=None, description="User IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    # Action details
    action: str = Field(..., description="Action performed")
    resource: Optional[str] = Field(default=None, description="Resource affected")
    resource_id: Optional[str] = Field(default=None, description="Resource identifier")
    # Context and metadata
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event details"
    )
    before_state: Optional[Dict[str, Any]] = Field(
        default=None, description="State before change"
    )
    after_state: Optional[Dict[str, Any]] = Field(
        default=None, description="State after change"
    )
    # Request information
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    # Result information
    success: bool = Field(default=True, description="Whether the action was successful")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    # Compliance and retention
    retention_period: int = Field(
        default=2555, description="Retention period in days (7 years default)"
    )
    compliance_tags: List[str] = Field(
        default_factory=list, description="Compliance tags"
    )


class AuditLogger:
    """
    Comprehensive audit logging system for enterprise compliance.

    Features:
    - Structured audit event logging
    - Multiple output formats (JSON, structured logs)
    - Configurable retention policies
    - Compliance tagging
    - Real-time event streaming
    - Query and search capabilities
    """

    def __init__(self):
        self.events: List[AuditEvent] = []  # In-memory storage for demo
        self.logger = logging.getLogger("audit")
        self._setup_audit_logger()

    def _setup_audit_logger(self):
        """Set up dedicated audit logger with appropriate formatting."""
        # Create audit-specific formatter
        formatter = logging.Formatter(
            "%(asctime)s - AUDIT - %(levelname)s - %(message)s"
        )
        # Create file handler for audit logs
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None,
    ) -> AuditEvent:
        """Log an audit event."""

        # Generate unique event ID
        event_id = f"audit_{int(datetime.now().timestamp() * 1000000)}"

        # Create audit event
        event = AuditEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            user_ip=user_ip,
            user_agent=user_agent,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details or {},
            before_state=before_state,
            after_state=after_state,
            request_id=request_id,
            session_id=session_id,
            success=success,
            error_message=error_message,
            compliance_tags=compliance_tags or [],
        )

        # Store event
        self.events.append(event)

        # Log to structured logger
        self._log_to_structured_logger(event)

        return event

    def _log_to_structured_logger(self, event: AuditEvent):
        """Log event to structured logger."""
        log_data = {
            "event_id": event.id,
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "username": event.username,
            "action": event.action,
            "resource": event.resource,
            "resource_id": event.resource_id,
            "success": event.success,
            "details": event.details,
        }

        # Add error information if present
        if event.error_message:
            log_data["error_message"] = event.error_message

        # Log at appropriate level based on severity
        log_message = json.dumps(log_data, default=str)

        if event.severity == AuditSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif event.severity == AuditSeverity.HIGH:
            self.logger.error(log_message)
        elif event.severity == AuditSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def log_authentication_event(
        self,
        event_type: AuditEventType,
        username: str,
        user_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log authentication-related events."""
        severity = AuditSeverity.HIGH if not success else AuditSeverity.MEDIUM

        return self.log_event(
            event_type=event_type,
            action=f"Authentication: {event_type.value}",
            user_id=user_id,
            username=username,
            severity=severity,
            success=success,
            error_message=error_message,
            user_ip=user_ip,
            user_agent=user_agent,
            details=details,
            compliance_tags=["authentication", "security"],
        )

    def log_permission_denied(
        self,
        username: str,
        action: str,
        resource: Optional[str] = None,
        required_permission: Optional[str] = None,
        user_id: Optional[str] = None,
        user_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log permission denied events."""
        event_details = details or {}
        if required_permission:
            event_details["required_permission"] = required_permission

        return self.log_event(
            event_type=AuditEventType.PERMISSION_DENIED,
            action=f"Permission denied: {action}",
            user_id=user_id,
            username=username,
            resource=resource,
            severity=AuditSeverity.HIGH,
            success=False,
            user_ip=user_ip,
            details=event_details,
            compliance_tags=["security", "access_control"],
        )

    def log_data_change(
        self,
        event_type: AuditEventType,
        action: str,
        resource: str,
        resource_id: str,
        username: str,
        user_id: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Log data change events with before/after states."""
        return self.log_event(
            event_type=event_type,
            action=action,
            user_id=user_id,
            username=username,
            resource=resource,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            details=details,
            compliance_tags=["data_change", "compliance"],
        )

    def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events with filters."""
        filtered_events = self.events

        # Apply filters
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if username:
            filtered_events = [e for e in filtered_events if e.username == username]

        if resource:
            filtered_events = [e for e in filtered_events if e.resource == resource]

        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]

        if success is not None:
            filtered_events = [e for e in filtered_events if e.success == success]

        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]

    def get_event_statistics(self) -> Dict[str, Any]:
        """Get audit event statistics."""
        total_events = len(self.events)

        if total_events == 0:
            return {
                "total_events": 0,
                "event_types": {},
                "severity_distribution": {},
                "success_rate": 0.0,
                "recent_events": 0,
            }

        # Count by event type
        event_type_counts = {}
        for event in self.events:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        # Count by severity
        severity_counts = {}
        for event in self.events:
            severity = event.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Calculate success rate
        successful_events = sum(1 for event in self.events if event.success)
        success_rate = (successful_events / total_events) * 100

        # Count recent events (last 24 hours)
        recent_cutoff = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        recent_events = sum(
            1 for event in self.events if event.timestamp >= recent_cutoff
        )

        return {
            "total_events": total_events,
            "event_types": event_type_counts,
            "severity_distribution": severity_counts,
            "success_rate": round(success_rate, 2),
            "recent_events": recent_events,
        }

    def export_events(
        self,
        format_type: str = "json",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """Export audit events in specified format."""
        events = self.query_events(
            start_time=start_time, end_time=end_time, limit=10000
        )

        if format_type.lower() == "json":
            return json.dumps([event.dict() for event in events], default=str, indent=2)
        elif format_type.lower() == "csv":
            # Simple CSV export
            if not events:
                return "No events to export"

            headers = [
                "id",
                "event_type",
                "severity",
                "timestamp",
                "username",
                "action",
                "resource",
                "success",
                "error_message",
            ]

            lines = [",".join(headers)]
            for event in events:
                row = [
                    event.id,
                    event.event_type.value,
                    event.severity.value,
                    event.timestamp.isoformat(),
                    event.username or "",
                    event.action,
                    event.resource or "",
                    str(event.success),
                    event.error_message or "",
                ]
                lines.append(",".join(f'"{field}"' for field in row))

            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions
def log_audit_event(event_type: AuditEventType, action: str, **kwargs) -> AuditEvent:
    """Convenience function to log an audit event."""
    return get_audit_logger().log_event(event_type, action, **kwargs)


def log_authentication(
    event_type: AuditEventType, username: str, **kwargs
) -> AuditEvent:
    """Convenience function to log authentication events."""
    return get_audit_logger().log_authentication_event(event_type, username, **kwargs)


def log_permission_denied(username: str, action: str, **kwargs) -> AuditEvent:
    """Convenience function to log permission denied events."""
    return get_audit_logger().log_permission_denied(username, action, **kwargs)


def log_data_change(
    event_type: AuditEventType,
    action: str,
    resource: str,
    resource_id: str,
    username: str,
    **kwargs,
) -> AuditEvent:
    """Convenience function to log data change events."""
    return get_audit_logger().log_data_change(
        event_type, action, resource, resource_id, username, **kwargs
    )
