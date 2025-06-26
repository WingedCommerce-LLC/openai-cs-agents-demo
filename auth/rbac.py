"""
Role-Based Access Control (RBAC) System

This module provides comprehensive RBAC functionality for the enterprise platform,
including permission management, role hierarchies, and access control decorators.
"""

import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PermissionScope(str, Enum):
    """Permission scopes for different system areas."""

    USER = "user"
    MCP = "mcp"
    AGENT = "agent"
    CHAT = "chat"
    SYSTEM = "system"
    AUDIT = "audit"


class PermissionAction(str, Enum):
    """Permission actions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class AccessDecision(BaseModel):
    """Result of an access control decision."""

    allowed: bool = Field(..., description="Whether access is allowed")
    reason: str = Field(..., description="Reason for the decision")
    permissions_checked: List[str] = Field(
        default_factory=list, description="Permissions evaluated"
    )


class RBACManager:
    """
    Role-Based Access Control Manager.

    Features:
    - Permission-based access control
    - Role hierarchies and inheritance
    - Resource-specific permissions
    - Access decision logging
    - Dynamic permission evaluation
    """

    def __init__(self):
        from .jwt_auth import get_authenticator

        self.authenticator = get_authenticator()
        self.permission_cache: Dict[str, Set[str]] = {}
        self.role_hierarchies = {
            "admin": ["developer", "user"],
            "developer": ["user"],
            "user": [],
        }

    def get_effective_permissions(self, user) -> Set[str]:
        """Get all effective permissions for a user, including inherited ones."""
        cache_key = f"{user.id}:{':'.join(sorted(user.roles))}"

        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]

        permissions = set()
        processed_roles = set()

        def collect_permissions(role_name: str):
            if role_name in processed_roles:
                return
            processed_roles.add(role_name)

            # Get direct permissions from role
            if hasattr(self.authenticator, "roles"):
                role = self.authenticator.roles.get(role_name)
                if role:
                    permissions.update(role.permissions)

            # Get inherited permissions
            inherited_roles = self.role_hierarchies.get(role_name, [])
            for parent_role in inherited_roles:
                collect_permissions(parent_role)

        # Collect permissions for all user roles
        for role_name in user.roles:
            collect_permissions(role_name)

        # Cache the result
        self.permission_cache[cache_key] = permissions
        return permissions

    def check_permission(
        self, user, permission: str, resource: Optional[str] = None
    ) -> AccessDecision:
        """Check if user has a specific permission."""
        # Get user's effective permissions
        user_permissions = self.get_effective_permissions(user)

        # Check exact permission match
        if permission in user_permissions:
            return AccessDecision(
                allowed=True,
                reason=f"User has direct permission: {permission}",
                permissions_checked=[permission],
            )

        # Check resource-specific permission
        if resource:
            resource_permission = f"{permission}:{resource}"
            if resource_permission in user_permissions:
                return AccessDecision(
                    allowed=True,
                    reason=f"User has resource permission: {resource_permission}",
                    permissions_checked=[resource_permission],
                )

        # Check admin permissions
        scope = permission.split(":")[0] if ":" in permission else permission
        admin_permission = f"{scope}:admin"
        if admin_permission in user_permissions:
            return AccessDecision(
                allowed=True,
                reason=f"User has admin permission: {admin_permission}",
                permissions_checked=[admin_permission],
            )

        # Check system admin
        if "system:admin" in user_permissions:
            return AccessDecision(
                allowed=True,
                reason="User has system admin permission",
                permissions_checked=["system:admin"],
            )

        return AccessDecision(
            allowed=False,
            reason=f"User lacks required permission: {permission}",
            permissions_checked=[permission],
        )

    def require_permission(self, permission: str, resource: Optional[str] = None):
        """Decorator to require specific permission for a function."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from function arguments or kwargs
                user = None

                # Look for user in kwargs
                if "user" in kwargs:
                    user = kwargs["user"]
                elif "current_user" in kwargs:
                    user = kwargs["current_user"]

                # Look for user in args
                for arg in args:
                    if hasattr(arg, "username") and hasattr(arg, "roles"):
                        user = arg
                        break

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Check permission
                decision = self.check_permission(user, permission, resource)
                if not decision.allowed:
                    logger.warning(
                        f"Access denied for user {user.username}: {decision.reason}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions: {decision.reason}",
                    )

                logger.info(
                    f"Access granted for user {user.username}: {decision.reason}"
                )
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def require_any_permission(
        self, permissions: List[str], resource: Optional[str] = None
    ):
        """Decorator to require any of the specified permissions."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from function arguments or kwargs
                user = None

                if "user" in kwargs:
                    user = kwargs["user"]
                elif "current_user" in kwargs:
                    user = kwargs["current_user"]

                for arg in args:
                    if hasattr(arg, "username") and hasattr(arg, "roles"):
                        user = arg
                        break

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Check if user has any of the required permissions
                for permission in permissions:
                    decision = self.check_permission(user, permission, resource)
                    if decision.allowed:
                        logger.info(
                            f"Access granted for user {user.username}: "
                            f"{decision.reason}"
                        )
                        return await func(*args, **kwargs)

                logger.warning(
                    f"Access denied for user {user.username}: "
                    f"lacks any of {permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: requires one of {permissions}",
                )

            return wrapper

        return decorator

    def require_role(self, role: str):
        """Decorator to require specific role."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from function arguments or kwargs
                user = None

                if "user" in kwargs:
                    user = kwargs["user"]
                elif "current_user" in kwargs:
                    user = kwargs["current_user"]

                for arg in args:
                    if hasattr(arg, "username") and hasattr(arg, "roles"):
                        user = arg
                        break

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Check if user has the required role or inherits it
                effective_roles = self._get_effective_roles(user)
                if role not in effective_roles:
                    logger.warning(
                        f"Access denied for user {user.username}: lacks role {role}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions: requires role {role}",
                    )

                logger.info(f"Access granted for user {user.username}: has role {role}")
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def _get_effective_roles(self, user) -> Set[str]:
        """Get all effective roles for a user, including inherited ones."""
        effective_roles = set(user.roles)

        for role in user.roles:
            inherited_roles = self.role_hierarchies.get(role, [])
            effective_roles.update(inherited_roles)

        return effective_roles

    def invalidate_permission_cache(self, user_id: Optional[str] = None):
        """Invalidate permission cache for a user or all users."""
        if user_id:
            # Remove cache entries for specific user
            keys_to_remove = [
                key
                for key in self.permission_cache.keys()
                if key.startswith(f"{user_id}:")
            ]
            for key in keys_to_remove:
                del self.permission_cache[key]
        else:
            # Clear entire cache
            self.permission_cache.clear()

        logger.info(f"Permission cache invalidated for user: {user_id or 'all users'}")

    def get_user_permissions_summary(self, user) -> Dict[str, Any]:
        """Get a summary of user's permissions and roles."""
        effective_permissions = self.get_effective_permissions(user)
        effective_roles = self._get_effective_roles(user)

        # Group permissions by scope
        permissions_by_scope = {}
        for permission in effective_permissions:
            scope = permission.split(":")[0]
            if scope not in permissions_by_scope:
                permissions_by_scope[scope] = []
            permissions_by_scope[scope].append(permission)

        return {
            "user_id": user.id,
            "username": user.username,
            "direct_roles": user.roles,
            "effective_roles": list(effective_roles),
            "total_permissions": len(effective_permissions),
            "permissions_by_scope": permissions_by_scope,
            "is_admin": "system:admin" in effective_permissions,
        }


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get the global RBAC manager instance."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


# Convenience decorators
def require_permission(permission: str, resource: Optional[str] = None):
    """Convenience decorator for requiring permissions."""
    return get_rbac_manager().require_permission(permission, resource)


def require_any_permission(permissions: List[str], resource: Optional[str] = None):
    """Convenience decorator for requiring any of multiple permissions."""
    return get_rbac_manager().require_any_permission(permissions, resource)


def require_role(role: str):
    """Convenience decorator for requiring roles."""
    return get_rbac_manager().require_role(role)


def require_admin():
    """Convenience decorator for requiring admin access."""
    return require_permission("system:admin")
