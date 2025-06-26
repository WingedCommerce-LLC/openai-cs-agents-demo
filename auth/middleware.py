"""
Authentication Middleware

FastAPI middleware for JWT authentication, RBAC authorization,
and tenant context management.
"""

import logging
from typing import Callable, List, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config.settings import get_settings

from .jwt_auth import JWTAuthenticationError, TokenData, get_authenticator
from .rbac import get_rbac_manager

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI documentation
security = HTTPBearer()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication and RBAC Authorization Middleware.

    Features:
    - JWT token validation
    - Role-based access control
    - Tenant context injection
    - Route-based authentication requirements
    - Audit logging integration
    """

    def __init__(
        self,
        app,
        excluded_paths: Optional[List[str]] = None,
        require_auth_by_default: bool = True,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/health/ready",
            "/health/live",
            "/metrics",
        ]
        self.require_auth_by_default = require_auth_by_default
        self.authenticator = get_authenticator()
        self.rbac_manager = get_rbac_manager()
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication and authorization."""

        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            # Extract and validate JWT token
            token_data = await self._authenticate_request(request)

            # Inject authentication context into request
            if token_data:
                request.state.user = token_data
                request.state.tenant_id = token_data.tenant_id
                request.state.user_id = token_data.user_id
                request.state.roles = token_data.roles
                request.state.permissions = token_data.permissions

            # Check authorization for protected routes
            await self._authorize_request(request, token_data)

            # Process the request
            response = await call_next(request)

            # Add security headers
            self._add_security_headers(response)

            return response

        except JWTAuthenticationError as e:
            logger.warning(f"Authentication failed: {e.detail}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": e.detail},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException as e:
            if e.status_code == status.HTTP_403_FORBIDDEN:
                logger.warning(f"Authorization failed: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )
        except Exception as e:
            logger.error(f"Middleware error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    async def _authenticate_request(self, request: Request) -> Optional[TokenData]:
        """Extract and validate JWT token from request."""

        # Check if authentication is required for this path
        if not self._requires_authentication(request):
            return None

        # Extract Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise JWTAuthenticationError("Missing Authorization header")

        # Parse Bearer token
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise JWTAuthenticationError("Invalid authentication scheme")
        except ValueError:
            raise JWTAuthenticationError("Invalid Authorization header format")

        # Validate JWT token
        token_data = self.authenticator.validate_access_token(token)

        # Additional validation
        if not token_data.user_id:
            raise JWTAuthenticationError("Invalid token: missing user ID")

        return token_data

    def _requires_authentication(self, request: Request) -> bool:
        """Determine if request requires authentication."""

        # Check for route-specific authentication requirements
        # This can be extended to support route decorators or metadata

        # For now, use default behavior
        return self.require_auth_by_default

    async def _authorize_request(
        self, request: Request, token_data: Optional[TokenData]
    ) -> None:
        """Check if user is authorized to access the requested resource."""

        if not token_data:
            # No authentication required
            return

        # Get required permissions for this route
        required_permissions = self._get_required_permissions(request)

        if not required_permissions:
            # No specific permissions required
            return

        # Check permissions using RBAC manager
        for permission in required_permissions:
            # Create a mock user object for RBAC check
            mock_user = type(
                "MockUser",
                (),
                {
                    "id": token_data.user_id,
                    "username": token_data.username,
                    "roles": token_data.roles,
                },
            )()

            decision = self.rbac_manager.check_permission(mock_user, permission)
            if not decision.allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission}",
                )

    def _get_required_permissions(self, request: Request) -> List[str]:
        """Get required permissions for the current route."""

        # This is a simplified implementation
        # In a real application, you would extract permissions from:
        # - Route metadata/decorators
        # - Database configuration
        # - Route patterns

        path = request.url.path
        method = request.method

        # Example permission mapping
        permission_map = {
            ("GET", "/api/users"): ["users:read"],
            ("POST", "/api/users"): ["users:create"],
            ("PUT", "/api/users"): ["users:update"],
            ("DELETE", "/api/users"): ["users:delete"],
            ("GET", "/api/mcp/servers"): ["mcp:read"],
            ("POST", "/api/mcp/servers"): ["mcp:create"],
            ("PUT", "/api/mcp/servers"): ["mcp:update"],
            ("DELETE", "/api/mcp/servers"): ["mcp:delete"],
            ("GET", "/api/admin"): ["admin:read"],
            ("POST", "/api/admin"): ["admin:write"],
        }

        return permission_map.get((method, path), [])

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""

        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        for header, value in security_headers.items():
            response.headers[header] = value


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tenant context management.

    Ensures proper tenant isolation and context injection.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Inject tenant context into request."""

        # Get tenant ID from various sources
        tenant_id = self._extract_tenant_id(request)

        if tenant_id:
            request.state.tenant_id = tenant_id

            # Add tenant context to logging
            logger.info(f"Request for tenant: {tenant_id}")

        return await call_next(request)

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""

        # Priority order for tenant ID extraction:
        # 1. JWT token (if authenticated)
        # 2. Subdomain
        # 3. Header
        # 4. Query parameter

        # From JWT token (set by AuthenticationMiddleware)
        if hasattr(request.state, "tenant_id") and request.state.tenant_id:
            return request.state.tenant_id

        # From subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain and subdomain != "www":
                return subdomain

        # From X-Tenant-ID header
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            return tenant_header

        # From query parameter
        tenant_param = request.query_params.get("tenant_id")
        if tenant_param:
            return tenant_param

        return None


# Dependency for extracting current user from request
async def get_current_user(request: Request) -> TokenData:
    """
    FastAPI dependency to get current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return request.state.user


# Dependency for extracting current tenant ID
async def get_current_tenant_id(request: Request) -> Optional[str]:
    """
    FastAPI dependency to get current tenant ID.

    Usage:
        @app.get("/tenant-data")
        async def get_data(tenant_id: str = Depends(get_current_tenant_id)):
            return {"tenant_id": tenant_id}
    """
    return getattr(request.state, "tenant_id", None)


# Permission checking dependency factory
def require_permission(permission: str):
    """
    Factory for creating permission-checking dependencies.

    Usage:
        @app.get("/admin")
        async def admin_route(
            user: TokenData = Depends(require_permission("admin:read"))
        ):
            return {"message": "Admin access granted"}
    """

    async def check_permission(request: Request) -> TokenData:
        user = await get_current_user(request)

        rbac_manager = get_rbac_manager()
        # Create a mock user object for RBAC check
        mock_user = type(
            "MockUser",
            (),
            {"id": user.user_id, "username": user.username, "roles": user.roles},
        )()

        decision = rbac_manager.check_permission(mock_user, permission)
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission}",
            )

        return user

    return check_permission


# Role checking dependency factory
def require_role(role: str):
    """
    Factory for creating role-checking dependencies.

    Usage:
        @app.get("/admin")
        async def admin_route(user: TokenData = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """

    async def check_role(request: Request) -> TokenData:
        user = await get_current_user(request)

        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role not found: {role}",
            )

        return user

    return check_role


# Tenant isolation dependency
async def require_tenant_access(request: Request) -> str:
    """
    Dependency to ensure user has access to the current tenant.

    Usage:
        @app.get("/tenant/{tenant_id}/data")
        async def get_tenant_data(
            tenant_id: str,
            verified_tenant: str = Depends(require_tenant_access)
        ):
            return {"tenant_id": verified_tenant}
    """
    user = await get_current_user(request)
    tenant_id = await get_current_tenant_id(request)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required",
        )

    if user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: tenant mismatch",
        )

    return tenant_id
