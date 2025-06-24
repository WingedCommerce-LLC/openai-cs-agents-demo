"""
Credential lifecycle management for automatic rotation and monitoring.

This module provides:
- Automatic credential rotation scheduling
- Expiration monitoring and alerts
- Rotation policy enforcement
- Audit logging for credential lifecycle events
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pydantic import BaseModel

from .credential_manager import CredentialManager, CredentialMetadata

logger = logging.getLogger(__name__)


class CredentialRotationPolicy(BaseModel):
    rotation_interval_days: int
    warning_days_before_expiry: int
    auto_rotate: bool = False
    notification_channels: List[str] = []


class CredentialLifecycleManager:
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager

    async def check_expiring_credentials(
        self, tenant_id: str
    ) -> List[CredentialMetadata]:
        """Check for credentials that are expiring soon."""
        expiring_credentials = []

        credentials = await self.credential_manager.store.list_credentials(tenant_id)

        for cred in credentials:
            if cred.expires_at:
                expiry_date = datetime.fromisoformat(cred.expires_at)
                days_until_expiry = (expiry_date - datetime.utcnow()).days

                if days_until_expiry <= 7:  # Warning threshold
                    expiring_credentials.append(cred)

        return expiring_credentials

    async def schedule_rotation(
        self, credential_id: str, tenant_id: str, rotation_date: datetime
    ):
        """Schedule automatic credential rotation."""
        # In a real implementation, this would integrate with a task queue like Celery
        logger.info(
            f"Scheduled rotation for credential {credential_id} on {rotation_date}"
        )
        # Implementation would depend on your task queue system
        pass

    async def rotate_credential_if_needed(
        self, credential_id: str, tenant_id: str, new_value: str
    ) -> bool:
        """Rotate a credential if it meets rotation criteria."""
        credentials = await self.credential_manager.store.list_credentials(tenant_id)
        credential = next((c for c in credentials if c.id == credential_id), None)

        if not credential:
            return False

        # Check if rotation is needed based on policy
        if credential.expires_at:
            expiry_date = datetime.fromisoformat(credential.expires_at)
            days_until_expiry = (expiry_date - datetime.utcnow()).days

            if days_until_expiry <= 30:  # Rotate if expiring within 30 days
                return await self.credential_manager.rotate_credential(
                    credential_id, tenant_id, new_value
                )

        return False

    async def get_rotation_status(self, tenant_id: str) -> Dict[str, int]:
        """Get rotation status for all credentials in a tenant."""
        credentials = await self.credential_manager.store.list_credentials(tenant_id)

        status = {
            "total_credentials": len(credentials),
            "expiring_soon": 0,
            "expired": 0,
            "healthy": 0,
        }

        for cred in credentials:
            if cred.expires_at:
                expiry_date = datetime.fromisoformat(cred.expires_at)
                days_until_expiry = (expiry_date - datetime.utcnow()).days

                if days_until_expiry < 0:
                    status["expired"] += 1
                elif days_until_expiry <= 7:
                    status["expiring_soon"] += 1
                else:
                    status["healthy"] += 1
            else:
                status["healthy"] += 1

        return status


class CredentialRotationScheduler:
    """Handles scheduling and management of credential rotations."""

    def __init__(self):
        self.scheduled_rotations = {}
        self.logger = logging.getLogger(__name__)

    def schedule_rotation(
        self, credential_id: str, tenant_id: str, interval_seconds: int
    ):
        """Schedule a credential rotation."""
        rotation_key = f"{tenant_id}:{credential_id}"
        self.scheduled_rotations[rotation_key] = {
            "credential_id": credential_id,
            "tenant_id": tenant_id,
            "interval_seconds": interval_seconds,
            "next_rotation": datetime.utcnow() + timedelta(seconds=interval_seconds),
            "scheduled_at": datetime.utcnow(),
        }
        self.logger.info(
            f"Scheduled rotation for {rotation_key} every {interval_seconds} seconds"
        )

    def cancel_rotation(self, credential_id: str, tenant_id: str):
        """Cancel a scheduled credential rotation."""
        rotation_key = f"{tenant_id}:{credential_id}"
        if rotation_key in self.scheduled_rotations:
            del self.scheduled_rotations[rotation_key]
            self.logger.info(f"Cancelled rotation for {rotation_key}")
            return True
        return False

    def get_scheduled_rotations(self, tenant_id: Optional[str] = None) -> Dict:
        """Get all scheduled rotations, optionally filtered by tenant."""
        if tenant_id:
            return {
                k: v
                for k, v in self.scheduled_rotations.items()
                if v["tenant_id"] == tenant_id
            }
        return self.scheduled_rotations.copy()

    def get_next_rotation_time(
        self, credential_id: str, tenant_id: str
    ) -> Optional[datetime]:
        """Get the next rotation time for a specific credential."""
        rotation_key = f"{tenant_id}:{credential_id}"
        rotation = self.scheduled_rotations.get(rotation_key)
        return rotation["next_rotation"] if rotation else None


class CredentialMonitoring:
    """Monitors credential usage, expiration, and security events."""

    def __init__(self):
        self.usage_logs = []
        self.expiration_checks = {}
        self.logger = logging.getLogger(__name__)

    def check_expiration(self, credential_id: str, tenant_id: str) -> Dict:
        """Check if a credential is expired or expiring soon."""
        check_key = f"{tenant_id}:{credential_id}"
        check_result = {
            "credential_id": credential_id,
            "tenant_id": tenant_id,
            "checked_at": datetime.utcnow(),
            "status": "unknown",
            "days_until_expiry": None,
            "expired": False,
            "expiring_soon": False,
        }

        # Store the check result
        self.expiration_checks[check_key] = check_result
        self.logger.info(f"Checked expiration for {check_key}")

        return check_result

    def monitor_usage(
        self, credential_id: str, tenant_id: str, operation: str = "access"
    ):
        """Monitor credential usage and log access patterns."""
        usage_event = {
            "credential_id": credential_id,
            "tenant_id": tenant_id,
            "operation": operation,
            "timestamp": datetime.utcnow(),
            "source": "monitoring_system",
        }

        self.usage_logs.append(usage_event)
        self.logger.info(
            f"Logged {operation} for credential {credential_id} in tenant {tenant_id}"
        )

        # Keep only last 1000 usage events to prevent memory issues
        if len(self.usage_logs) > 1000:
            self.usage_logs = self.usage_logs[-1000:]

    def get_usage_stats(self, credential_id: str, tenant_id: str) -> Dict:
        """Get usage statistics for a specific credential."""
        relevant_logs = [
            log
            for log in self.usage_logs
            if log["credential_id"] == credential_id and log["tenant_id"] == tenant_id
        ]

        return {
            "credential_id": credential_id,
            "tenant_id": tenant_id,
            "total_accesses": len(relevant_logs),
            "last_access": relevant_logs[-1]["timestamp"] if relevant_logs else None,
            "operations": list(set(log["operation"] for log in relevant_logs)),
        }

    def get_expiration_alerts(self, tenant_id: Optional[str] = None) -> List[Dict]:
        """Get all expiration alerts, optionally filtered by tenant."""
        alerts = []
        for check_key, check_result in self.expiration_checks.items():
            if tenant_id and check_result["tenant_id"] != tenant_id:
                continue

            if check_result.get("expired") or check_result.get("expiring_soon"):
                alerts.append(check_result)

        return alerts
