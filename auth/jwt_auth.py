#!/usr/bin/env python3
"""
JWT Authentication System

This module provides enterprise-grade JWT authentication functionality
including token generation, validation, refresh, and user management.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field, validator

from config.settings import get_settings


class TokenData(BaseModel):
    """Token payload data structure."""

    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email address")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    tenant_id: Optional[str] = Field(
        None, description="Tenant identifier for multi-tenancy"
    )
    session_id: str = Field(..., description="Unique session identifier")

    # Token metadata
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    token_type: str = Field(default="access", description="Token type (access/refresh)")

    @validator("expires_at", pre=True, always=True)
    def set_expires_at(cls, v, values):
        """Set expiration time based on token type."""
        if v is None:
            settings = get_settings()
            issued_at = values.get("issued_at", datetime.now(timezone.utc))
            token_type = values.get("token_type", "access")

            if token_type == "access":
                delta = timedelta(
                    minutes=settings.security.jwt_access_token_expire_minutes
                )
            else:  # refresh token
                delta = timedelta(days=settings.security.jwt_refresh_token_expire_days)

            return issued_at + delta
        return v


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class UserCredentials(BaseModel):
    """User login credentials."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")


class UserInfo(BaseModel):
    """User information for token generation."""

    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email address")
    roles: List[str] = Field(default_factory=list, description="User roles")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    is_active: bool = Field(default=True, description="User active status")
    password_hash: Optional[str] = Field(None, description="Hashed password")


class JWTAuthenticationError(HTTPException):
    """Custom JWT authentication exception."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class JWTAuthenticator:
    """
    Enterprise JWT Authentication System

    Provides secure JWT token generation, validation, and management
    with support for access/refresh tokens, role-based permissions,
    and multi-tenancy.
    """

    def __init__(self):
        """Initialize JWT authenticator with settings."""
        self.settings = get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Validate JWT configuration
        if len(self.settings.security.jwt_secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_session_id(self) -> str:
        """
        Generate a unique session identifier.

        Returns:
            Cryptographically secure session ID
        """
        return secrets.token_urlsafe(32)

    def create_access_token(self, user_info: UserInfo) -> str:
        """
        Create a JWT access token.

        Args:
            user_info: User information for token payload

        Returns:
            Encoded JWT access token
        """
        session_id = self.generate_session_id()

        token_data = TokenData(
            user_id=user_info.user_id,
            username=user_info.username,
            email=user_info.email,
            roles=user_info.roles,
            permissions=user_info.permissions,
            tenant_id=user_info.tenant_id,
            session_id=session_id,
            token_type="access",
        )

        payload = {
            "sub": token_data.user_id,
            "username": token_data.username,
            "email": token_data.email,
            "roles": token_data.roles,
            "permissions": token_data.permissions,
            "tenant_id": token_data.tenant_id,
            "session_id": token_data.session_id,
            "type": token_data.token_type,
            "iat": int(token_data.issued_at.timestamp()),
            "exp": int(token_data.expires_at.timestamp())
            if token_data.expires_at
            else 0,
        }

        return jwt.encode(
            payload,
            self.settings.security.jwt_secret_key,
            algorithm=self.settings.security.jwt_algorithm,
        )

    def create_refresh_token(self, user_info: UserInfo, session_id: str) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_info: User information for token payload
            session_id: Session ID to associate with refresh token

        Returns:
            Encoded JWT refresh token
        """
        token_data = TokenData(
            user_id=user_info.user_id,
            username=user_info.username,
            email=user_info.email,
            roles=user_info.roles,
            permissions=user_info.permissions,
            tenant_id=user_info.tenant_id,
            session_id=session_id,
            token_type="refresh",
        )

        payload = {
            "sub": token_data.user_id,
            "username": token_data.username,
            "email": token_data.email,
            "session_id": token_data.session_id,
            "type": token_data.token_type,
            "iat": int(token_data.issued_at.timestamp()),
            "exp": int(token_data.expires_at.timestamp())
            if token_data.expires_at
            else 0,
        }

        return jwt.encode(
            payload,
            self.settings.security.jwt_secret_key,
            algorithm=self.settings.security.jwt_algorithm,
        )

    def create_token_pair(self, user_info: UserInfo) -> TokenPair:
        """
        Create access and refresh token pair.

        Args:
            user_info: User information for token generation

        Returns:
            Token pair with access and refresh tokens
        """
        # Generate session ID for both tokens
        session_id = self.generate_session_id()

        # Create user info with session ID for refresh token
        user_with_session = UserInfo(**user_info.dict())

        access_token = self.create_access_token(user_info)
        refresh_token = self.create_refresh_token(user_with_session, session_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.security.jwt_access_token_expire_minutes * 60,
        )

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            JWTAuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.security.jwt_secret_key,
                algorithms=[self.settings.security.jwt_algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise JWTAuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise JWTAuthenticationError("Invalid token")

    def validate_access_token(self, token: str) -> TokenData:
        """
        Validate an access token and return token data.

        Args:
            token: JWT access token to validate

        Returns:
            Validated token data

        Raises:
            JWTAuthenticationError: If token is invalid or not an access token
        """
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise JWTAuthenticationError("Invalid token type")

        try:
            return TokenData(
                user_id=payload["sub"],
                username=payload["username"],
                email=payload["email"],
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                tenant_id=payload.get("tenant_id"),
                session_id=payload["session_id"],
                issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                token_type="access",
            )
        except KeyError as e:
            raise JWTAuthenticationError(f"Missing required token field: {e}")

    def validate_refresh_token(self, token: str) -> TokenData:
        """
        Validate a refresh token and return token data.

        Args:
            token: JWT refresh token to validate

        Returns:
            Validated token data

        Raises:
            JWTAuthenticationError: If token is invalid or not a refresh token
        """
        payload = self.decode_token(token)

        if payload.get("type") != "refresh":
            raise JWTAuthenticationError("Invalid token type")

        try:
            return TokenData(
                user_id=payload["sub"],
                username=payload["username"],
                email=payload["email"],
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                tenant_id=payload.get("tenant_id"),
                session_id=payload["session_id"],
                issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                token_type="refresh",
            )
        except KeyError as e:
            raise JWTAuthenticationError(f"Missing required token field: {e}")

    def refresh_access_token(self, refresh_token: str, user_info: UserInfo) -> str:
        """
        Generate a new access token using a refresh token.

        Args:
            refresh_token: Valid refresh token
            user_info: Updated user information

        Returns:
            New access token

        Raises:
            JWTAuthenticationError: If refresh token is invalid
        """
        # Validate refresh token
        token_data = self.validate_refresh_token(refresh_token)

        # Verify user ID matches
        if token_data.user_id != user_info.user_id:
            raise JWTAuthenticationError("Token user mismatch")

        # Create new access token with same session ID
        session_id = token_data.session_id

        token_data = TokenData(
            user_id=user_info.user_id,
            username=user_info.username,
            email=user_info.email,
            roles=user_info.roles,
            permissions=user_info.permissions,
            tenant_id=user_info.tenant_id,
            session_id=session_id,
            token_type="access",
        )

        payload = {
            "sub": token_data.user_id,
            "username": token_data.username,
            "email": token_data.email,
            "roles": token_data.roles,
            "permissions": token_data.permissions,
            "tenant_id": token_data.tenant_id,
            "session_id": token_data.session_id,
            "type": token_data.token_type,
            "iat": int(token_data.issued_at.timestamp()),
            "exp": int(token_data.expires_at.timestamp())
            if token_data.expires_at
            else 0,
        }

        return jwt.encode(
            payload,
            self.settings.security.jwt_secret_key,
            algorithm=self.settings.security.jwt_algorithm,
        )

    def authenticate_user(
        self, credentials: UserCredentials, user_info: UserInfo
    ) -> bool:
        """
        Authenticate user credentials.

        Args:
            credentials: User login credentials
            user_info: User information from database

        Returns:
            True if authentication successful, False otherwise
        """
        # Check if user is active
        if not user_info.is_active:
            return False

        # Verify password
        if not user_info.password_hash:
            return False

        if not self.verify_password(credentials.password, user_info.password_hash):
            return False

        # Check tenant match if specified
        if credentials.tenant_id and credentials.tenant_id != user_info.tenant_id:
            return False

        return True

    def has_permission(self, token_data: TokenData, required_permission: str) -> bool:
        """
        Check if user has required permission.

        Args:
            token_data: Validated token data
            required_permission: Permission to check

        Returns:
            True if user has permission, False otherwise
        """
        return required_permission in token_data.permissions

    def has_role(self, token_data: TokenData, required_role: str) -> bool:
        """
        Check if user has required role.

        Args:
            token_data: Validated token data
            required_role: Role to check

        Returns:
            True if user has role, False otherwise
        """
        return required_role in token_data.roles

    def has_any_role(self, token_data: TokenData, required_roles: List[str]) -> bool:
        """
        Check if user has any of the required roles.

        Args:
            token_data: Validated token data
            required_roles: List of roles to check

        Returns:
            True if user has any required role, False otherwise
        """
        return any(role in token_data.roles for role in required_roles)

    def is_same_tenant(self, token_data: TokenData, tenant_id: str) -> bool:
        """
        Check if token belongs to the same tenant.

        Args:
            token_data: Validated token data
            tenant_id: Tenant ID to check

        Returns:
            True if same tenant, False otherwise
        """
        return token_data.tenant_id == tenant_id


# Global authenticator instance
_authenticator: Optional[JWTAuthenticator] = None


def get_authenticator() -> JWTAuthenticator:
    """
    Get the global JWT authenticator instance (singleton pattern).

    Returns:
        JWT authenticator instance
    """
    global _authenticator
    if _authenticator is None:
        _authenticator = JWTAuthenticator()
    return _authenticator


def create_demo_user() -> UserInfo:
    """
    Create a demo user for testing purposes.

    Returns:
        Demo user information
    """
    authenticator = get_authenticator()

    return UserInfo(
        user_id="demo-user-001",
        username="demo",
        email="demo@example.com",
        roles=["user", "admin"],
        permissions=["read", "write", "admin"],
        tenant_id="demo-tenant",
        is_active=True,
        password_hash=authenticator.hash_password("demo123!"),
    )


if __name__ == "__main__":
    # Example usage and testing
    authenticator = get_authenticator()

    # Create demo user
    demo_user = create_demo_user()
    print(f"Demo user created: {demo_user.username}")

    # Create token pair
    tokens = authenticator.create_token_pair(demo_user)
    print(f"Access token created (expires in {tokens.expires_in}s)")

    # Validate access token
    token_data = authenticator.validate_access_token(tokens.access_token)
    print(f"Token validated for user: {token_data.username}")

    # Test authentication
    credentials = UserCredentials(username="demo", password="demo123!")
    is_authenticated = authenticator.authenticate_user(credentials, demo_user)
    print(f"Authentication successful: {is_authenticated}")
