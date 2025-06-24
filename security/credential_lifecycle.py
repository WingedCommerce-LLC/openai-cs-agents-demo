"""
Credential lifecycle management for automatic rotation and monitoring.

This module provides:
- Automatic credential rotation scheduling
- Expiration monitoring and alerts
- Rotation policy enforcement
- Audit logging for credential lifecycle events
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
import logging
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
    
    async def check_expiring_credentials(self, tenant_id: str) -> List[CredentialMetadata]:
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
    
    async def schedule_rotation(self, credential_id: str, tenant_id: str, rotation_date: datetime):
        """Schedule automatic credential rotation."""
        # In a real implementation, this would integrate with a task queue like Celery
        logger.info(f"Scheduled rotation for credential {credential_id} on {rotation_date}")
        # Implementation would depend on your task queue system
        pass
    
    async def rotate_credential_if_needed(self, credential_id: str, tenant_id: str, new_value: str) -> bool:
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
            "healthy": 0
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
