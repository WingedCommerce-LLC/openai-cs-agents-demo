"""
Multi-tenancy models for enterprise platform.

Provides tenant isolation and management for the enterprise platform,
enabling multiple organizations to use the same system with data isolation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TenantStatus(str, Enum):
    """Tenant status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    PENDING = "pending"


class TenantPlan(str, Enum):
    """Tenant subscription plan enumeration."""

    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    """
    Tenant model for multi-tenancy support.

    Each tenant represents an organization or customer
    with isolated data and configuration.
    """

    __tablename__ = "tenants"

    # Basic tenant information
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Tenant organization name"
    )

    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, doc="URL-friendly tenant identifier"
    )

    domain: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, doc="Custom domain for tenant"
    )

    # Contact information
    contact_email: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Primary contact email"
    )

    contact_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Primary contact name"
    )

    # Status and plan
    status: Mapped[TenantStatus] = mapped_column(
        String(20),
        default=TenantStatus.PENDING,
        nullable=False,
        doc="Current tenant status",
    )

    plan: Mapped[TenantPlan] = mapped_column(
        String(20), default=TenantPlan.FREE, nullable=False, doc="Subscription plan"
    )

    # Configuration
    settings: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, doc="Tenant-specific configuration settings"
    )

    # Limits and quotas
    max_users: Mapped[int] = mapped_column(
        default=10, nullable=False, doc="Maximum number of users allowed"
    )

    max_mcp_servers: Mapped[int] = mapped_column(
        default=5, nullable=False, doc="Maximum number of MCP servers allowed"
    )

    max_agents: Mapped[int] = mapped_column(
        default=10, nullable=False, doc="Maximum number of agents allowed"
    )

    # Billing information
    billing_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, doc="Billing contact email"
    )

    subscription_start: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, doc="Subscription start date"
    )

    subscription_end: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, doc="Subscription end date"
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Tenant description"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, doc="Whether tenant is active"
    )

    # Relationships (to be defined when other models are created)
    # users: Mapped[List["User"]] = relationship("User", back_populates="tenant")
    # mcp_servers: Mapped[List["MCPServer"]] = relationship(
    #     "MCPServer", back_populates="tenant"
    # )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def is_enterprise(self) -> bool:
        """Check if tenant is on enterprise plan."""
        return self.plan == TenantPlan.ENTERPRISE

    @property
    def is_suspended(self) -> bool:
        """Check if tenant is suspended."""
        return self.status == TenantStatus.SUSPENDED

    def can_create_user(self, current_user_count: int) -> bool:
        """Check if tenant can create another user."""
        return current_user_count < self.max_users

    def can_create_mcp_server(self, current_server_count: int) -> bool:
        """Check if tenant can create another MCP server."""
        return current_server_count < self.max_mcp_servers

    def can_create_agent(self, current_agent_count: int) -> bool:
        """Check if tenant can create another agent."""
        return current_agent_count < self.max_agents

    def get_setting(self, key: str, default=None):
        """Get a tenant-specific setting."""
        if not self.settings:
            return default
        return self.settings.get(key, default)

    def set_setting(self, key: str, value) -> None:
        """Set a tenant-specific setting."""
        if not self.settings:
            self.settings = {}
        self.settings[key] = value

    def activate(self) -> None:
        """Activate the tenant."""
        self.status = TenantStatus.ACTIVE
        self.is_active = True

    def suspend(self) -> None:
        """Suspend the tenant."""
        self.status = TenantStatus.SUSPENDED
        self.is_active = False

    def deactivate(self) -> None:
        """Deactivate the tenant."""
        self.status = TenantStatus.INACTIVE
        self.is_active = False


class TenantMixin:
    """
    Mixin for models that belong to a tenant.

    Add this to any model that should be tenant-isolated.
    """

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        doc="ID of the tenant this record belongs to",
    )

    # tenant: Mapped["Tenant"] = relationship("Tenant")

    # Note: for_tenant method will be implemented in repository pattern
    pass


class TenantUser(Base):
    """
    Association model for tenant users with roles.

    Manages user membership in tenants with specific roles.
    """

    __tablename__ = "tenant_users"

    tenant_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, doc="Tenant ID"
    )

    user_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, doc="User ID"
    )

    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user", doc="User role within the tenant"
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the user's primary tenant",
    )

    joined_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, doc="When the user joined the tenant"
    )

    # Relationships
    # tenant: Mapped["Tenant"] = relationship("Tenant")
    # user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<TenantUser(tenant_id={self.tenant_id}, "
            f"user_id={self.user_id}, role={self.role})>"
        )


class TenantInvitation(Base):
    """
    Model for tenant invitations.

    Manages invitations for users to join tenants.
    """

    __tablename__ = "tenant_invitations"

    tenant_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, doc="Tenant ID"
    )

    email: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Email address of invited user"
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        doc="Role to assign when invitation is accepted",
    )

    invited_by: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        doc="ID of user who sent the invitation",
    )

    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, doc="Unique invitation token"
    )

    expires_at: Mapped[datetime] = mapped_column(
        nullable=False, doc="When the invitation expires"
    )

    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, doc="When the invitation was accepted"
    )

    accepted_by: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, doc="ID of user who accepted the invitation"
    )

    # Relationships
    # tenant: Mapped["Tenant"] = relationship("Tenant")

    def __repr__(self) -> str:
        return (
            f"<TenantInvitation(id={self.id}, email={self.email}, "
            f"tenant_id={self.tenant_id})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        """Check if invitation has been accepted."""
        return self.accepted_at is not None

    def accept(self, user_id: str) -> None:
        """Mark invitation as accepted."""
        self.accepted_at = datetime.utcnow()
        self.accepted_by = user_id
