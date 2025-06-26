"""
Authentication module for enterprise security.

Provides JWT authentication, RBAC authorization, audit logging,
and middleware integration for FastAPI applications.
"""

from .jwt_auth import (
    JWTAuthenticationError,
    JWTAuthenticator,
    TokenData,
    TokenPair,
    UserCredentials,
    UserInfo,
    create_demo_user,
    get_authenticator,
)
from .middleware import (
    AuthenticationMiddleware,
    TenantContextMiddleware,
    get_current_tenant_id,
    get_current_user,
    require_permission,
    require_role,
    require_tenant_access,
    security,
)
from .rbac import (
    AccessDecision,
    PermissionAction,
    PermissionScope,
    RBACManager,
    get_rbac_manager,
)

__all__ = [
    # JWT Authentication
    "JWTAuthenticator",
    "get_authenticator",
    "TokenData",
    "TokenPair",
    "UserCredentials",
    "UserInfo",
    "JWTAuthenticationError",
    "create_demo_user",
    # RBAC Authorization
    "RBACManager",
    "get_rbac_manager",
    "PermissionScope",
    "PermissionAction",
    "AccessDecision",
    # Middleware
    "AuthenticationMiddleware",
    "TenantContextMiddleware",
    "get_current_user",
    "get_current_tenant_id",
    "require_permission",
    "require_role",
    "require_tenant_access",
    "security",
]
