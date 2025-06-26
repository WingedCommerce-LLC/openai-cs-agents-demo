"""
Tenant repository implementation.

Provides specialized operations for tenant management.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.tenant import Tenant, TenantPlan, TenantStatus

from .base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """
    Repository for tenant operations.

    Provides specialized methods for tenant management beyond basic CRUD.
    """

    def __init__(self, session: Session):
        super().__init__(session, Tenant)

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        query = select(Tenant).where(Tenant.slug == slug)
        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by domain."""
        query = select(Tenant).where(Tenant.domain == domain)
        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_active_tenants(self) -> List[Tenant]:
        """Get all active tenants."""
        return self.get_all(filters={"status": TenantStatus.ACTIVE})

    def get_by_status(self, status: TenantStatus) -> List[Tenant]:
        """Get tenants by status."""
        return self.get_all(filters={"status": status})

    def get_by_plan(self, plan: TenantPlan) -> List[Tenant]:
        """Get tenants by plan."""
        return self.get_all(filters={"plan": plan})

    def search_tenants(self, query: str) -> List[Tenant]:
        """Search tenants by name or slug."""
        stmt = select(Tenant).where(
            (Tenant.name.ilike(f"%{query}%")) | (Tenant.slug.ilike(f"%{query}%"))
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a tenant."""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            tenant.activate()
            self.session.commit()
            return True
        return False

    def suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend a tenant."""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            tenant.suspend()
            self.session.commit()
            return True
        return False

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate a tenant."""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            tenant.deactivate()
            self.session.commit()
            return True
        return False

    def update_tenant_settings(self, tenant_id: str, settings: dict) -> bool:
        """Update tenant settings."""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            if not tenant.settings:
                tenant.settings = {}
            tenant.settings.update(settings)
            self.session.commit()
            return True
        return False

    def get_tenant_statistics(self) -> dict:
        """Get tenant statistics."""
        total_tenants = self.count()
        active_tenants = self.count(filters={"status": TenantStatus.ACTIVE})
        suspended_tenants = self.count(filters={"status": TenantStatus.SUSPENDED})

        # Count by plan
        plan_counts = {}
        for plan in TenantPlan:
            plan_counts[plan.value] = self.count(filters={"plan": plan})

        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "suspended_tenants": suspended_tenants,
            "plan_distribution": plan_counts,
        }
