"""
Tests for tenant model.
"""

from datetime import datetime, timezone

from models.tenant import Tenant, TenantInvitation, TenantPlan, TenantStatus, TenantUser


class TestTenantModel:
    """Test tenant model functionality."""

    def test_tenant_creation(self):
        """Test creating a tenant."""
        tenant = Tenant(
            name="Test Company",
            slug="test-company",
            domain="test.com",
            plan=TenantPlan.BASIC,
            contact_email="contact@test.com",
        )

        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.domain == "test.com"
        assert tenant.plan == TenantPlan.BASIC
        assert tenant.contact_email == "contact@test.com"

    def test_tenant_status_enum(self):
        """Test tenant status enumeration."""
        assert TenantStatus.ACTIVE == "active"
        assert TenantStatus.SUSPENDED == "suspended"
        assert TenantStatus.INACTIVE == "inactive"
        assert TenantStatus.PENDING == "pending"

    def test_tenant_plan_enum(self):
        """Test tenant plan enumeration."""
        assert TenantPlan.FREE == "free"
        assert TenantPlan.BASIC == "basic"
        assert TenantPlan.PROFESSIONAL == "professional"
        assert TenantPlan.ENTERPRISE == "enterprise"

    def test_tenant_plan_limits(self):
        """Test tenant plan resource limits."""
        # Free plan
        free_tenant = Tenant(
            name="Free Tenant",
            slug="free-tenant",
            plan=TenantPlan.FREE,
            contact_email="free@test.com",
            max_users=3,
            max_mcp_servers=1,
            max_agents=5,
        )
        assert free_tenant.max_users == 3
        assert free_tenant.max_mcp_servers == 1
        assert free_tenant.max_agents == 5

        # Enterprise plan
        enterprise_tenant = Tenant(
            name="Enterprise Tenant",
            slug="enterprise-tenant",
            plan=TenantPlan.ENTERPRISE,
            contact_email="enterprise@test.com",
            max_users=1000,
            max_mcp_servers=100,
            max_agents=1000,
        )
        assert enterprise_tenant.max_users == 1000
        assert enterprise_tenant.max_mcp_servers == 100
        assert enterprise_tenant.max_agents == 1000

    def test_tenant_activate(self):
        """Test activating a tenant."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            status=TenantStatus.PENDING,
        )

        tenant.activate()
        assert tenant.status == TenantStatus.ACTIVE

    def test_tenant_suspend(self):
        """Test suspending a tenant."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            status=TenantStatus.ACTIVE,
        )

        tenant.suspend()
        assert tenant.status == TenantStatus.SUSPENDED

    def test_tenant_deactivate(self):
        """Test deactivating a tenant."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            status=TenantStatus.ACTIVE,
        )

        tenant.deactivate()
        assert tenant.status == TenantStatus.INACTIVE

    def test_tenant_is_active(self):
        """Test checking if tenant is active."""
        active_tenant = Tenant(
            name="Active Tenant",
            slug="active-tenant",
            status=TenantStatus.ACTIVE,
            contact_email="active@test.com",
            is_active=True,
        )

        suspended_tenant = Tenant(
            name="Suspended Tenant",
            slug="suspended-tenant",
            status=TenantStatus.SUSPENDED,
            contact_email="suspended@test.com",
            is_active=False,
        )

        assert active_tenant.is_active is True
        assert suspended_tenant.is_active is False

    def test_tenant_can_create_user(self):
        """Test checking if tenant can create users."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            plan=TenantPlan.BASIC,
            contact_email="test@test.com",
            max_users=10,
        )

        assert tenant.can_create_user(5) is True  # 5 < 10
        assert tenant.can_create_user(10) is False  # 10 >= 10
        assert tenant.can_create_user(15) is False  # 15 > 10

    def test_tenant_can_create_mcp_server(self):
        """Test checking if tenant can create MCP servers."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            plan=TenantPlan.BASIC,
            contact_email="test@test.com",
            max_mcp_servers=5,
        )

        assert tenant.can_create_mcp_server(3) is True  # 3 < 5
        assert tenant.can_create_mcp_server(5) is False  # 5 >= 5
        assert tenant.can_create_mcp_server(10) is False  # 10 > 5

    def test_tenant_can_create_agent(self):
        """Test checking if tenant can create agents."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            plan=TenantPlan.BASIC,
            contact_email="test@test.com",
            max_agents=20,
        )

        assert tenant.can_create_agent(15) is True  # 15 < 20
        assert tenant.can_create_agent(20) is False  # 20 >= 20
        assert tenant.can_create_agent(25) is False  # 25 > 20

    def test_tenant_settings_default(self):
        """Test tenant default settings."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            contact_email="test@test.com",
            settings={},
        )

        assert tenant.settings == {}

    def test_tenant_settings_custom(self):
        """Test tenant custom settings."""
        custom_settings = {
            "theme": "dark",
            "notifications": True,
            "api_rate_limit": 1000,
        }

        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            settings=custom_settings,
        )

        assert tenant.settings == custom_settings

    def test_tenant_billing_info(self):
        """Test tenant billing information."""
        billing_start = datetime.now(timezone.utc)
        billing_end = datetime.now(timezone.utc)

        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            billing_email="billing@test.com",
            subscription_start=billing_start,
            subscription_end=billing_end,
        )

        assert tenant.billing_email == "billing@test.com"
        assert tenant.subscription_start == billing_start
        assert tenant.subscription_end == billing_end

    def test_tenant_repr(self):
        """Test tenant string representation."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
        )

        repr_str = repr(tenant)
        assert "Test Tenant" in repr_str
        assert "test-tenant" in repr_str


class TestTenantInvitation:
    """Test tenant invitation model."""

    def test_invitation_creation(self):
        """Test creating a tenant invitation."""
        expires_at = datetime.now(timezone.utc).replace(year=2030)
        invitation = TenantInvitation(
            tenant_id="tenant-123",
            email="user@example.com",
            role="user",
            token="invitation-token-123",
            invited_by="admin-123",
            expires_at=expires_at,
        )

        assert invitation.tenant_id == "tenant-123"
        assert invitation.email == "user@example.com"
        assert invitation.role == "user"
        assert invitation.token == "invitation-token-123"
        assert invitation.is_accepted is False

    def test_invitation_accept(self):
        """Test accepting an invitation."""
        expires_at = datetime.now(timezone.utc).replace(year=2030)
        invitation = TenantInvitation(
            tenant_id="tenant-123",
            email="user@example.com",
            role="user",
            token="invitation-token-123",
            invited_by="admin-123",
            expires_at=expires_at,
        )

        invitation.accept("user-456")
        assert invitation.is_accepted is True
        assert invitation.accepted_at is not None

    def test_invitation_is_expired(self):
        """Test checking if invitation is expired."""
        # Create invitation that expires in the past
        past_date = datetime.utcnow().replace(year=2020)
        invitation = TenantInvitation(
            tenant_id="tenant-123",
            email="user@example.com",
            role="user",
            token="invitation-token-123",
            invited_by="admin-123",
            expires_at=past_date,
        )

        assert invitation.is_expired is True

        # Create invitation that expires in the future
        future_date = datetime.utcnow().replace(year=2030)
        invitation.expires_at = future_date
        assert invitation.is_expired is False


class TestTenantUser:
    """Test tenant user model."""

    def test_tenant_user_creation(self):
        """Test creating a tenant user."""
        tenant_user = TenantUser(
            tenant_id="tenant-123",
            user_id="user-456",
            role="admin",
            is_primary=False,
        )

        assert tenant_user.tenant_id == "tenant-123"
        assert tenant_user.user_id == "user-456"
        assert tenant_user.role == "admin"
        assert tenant_user.is_primary is False

    def test_tenant_user_with_primary_flag(self):
        """Test creating a tenant user with primary flag."""
        tenant_user = TenantUser(
            tenant_id="tenant-123",
            user_id="user-456",
            role="admin",
            is_primary=True,
        )

        assert tenant_user.tenant_id == "tenant-123"
        assert tenant_user.user_id == "user-456"
        assert tenant_user.role == "admin"
        assert tenant_user.is_primary is True

    def test_tenant_user_repr(self):
        """Test tenant user string representation."""
        tenant_user = TenantUser(
            tenant_id="tenant-123",
            user_id="user-456",
            role="user",
        )

        repr_str = repr(tenant_user)
        assert "tenant-123" in repr_str
        assert "user-456" in repr_str
        assert "user" in repr_str
