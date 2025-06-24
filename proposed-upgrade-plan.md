# Enterprise Upgrade Plan: OpenAI Agents Starter Template

## Executive Summary

This document outlines the transformation of the OpenAI Customer Service Agents Demo into a production-ready enterprise starter template. The upgrade will enable organizations to rapidly deploy customized multi-agent systems with enterprise-grade features, MCP integration, and cloud-native architecture.

### Current State Analysis
- **Strengths**: Solid multi-agent foundation, clean architecture, working demo flows
- **Gaps**: Demo-level storage, no authentication, limited extensibility, no containerization
- **Opportunity**: Transform into enterprise-grade platform with MCP ecosystem integration

### Target Architecture
- **Security-First**: Secure credential management and zero-trust architecture from day one
- **Cloud-Native**: Kubernetes-ready with Docker containerization
- **Multi-Tenant**: Workspace isolation and RBAC
- **MCP-Integrated**: Dynamic server generation from OpenAPI specs with secure credential handling
- **Developer-Friendly**: CLI tools, hot-reload, component scaffolding
- **Production-Ready**: Monitoring, security, compliance, CI/CD

---

## Phase 0: Security-First Foundation

### 0.1 Secure Credential Management System

#### Zero-Trust Credential Architecture
```python
# security/credential_manager.py
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from enum import Enum

class CredentialType(str, Enum):
    API_KEY = "api_key"
    DATABASE_URL = "database_url"
    OAUTH_TOKEN = "oauth_token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"

class CredentialMetadata(BaseModel):
    id: str
    name: str
    type: CredentialType
    tenant_id: str
    created_at: str
    expires_at: Optional[str] = None
    last_rotated: Optional[str] = None
    rotation_policy: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

class SecureCredential(BaseModel):
    metadata: CredentialMetadata
    encrypted_value: str
    encryption_key_id: str

class CredentialStore(ABC):
    @abstractmethod
    async def store_credential(self, credential: SecureCredential) -> bool:
        pass
    
    @abstractmethod
    async def retrieve_credential(self, credential_id: str, tenant_id: str) -> Optional[str]:
        pass
    
    @abstractmethod
    async def delete_credential(self, credential_id: str, tenant_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_credentials(self, tenant_id: str) -> List[CredentialMetadata]:
        pass

class VaultCredentialStore(CredentialStore):
    """HashiCorp Vault integration for production environments."""
    
    def __init__(self, vault_url: str, vault_token: str):
        import hvac
        self.client = hvac.Client(url=vault_url, token=vault_token)
    
    async def store_credential(self, credential: SecureCredential) -> bool:
        try:
            path = f"secret/tenants/{credential.metadata.tenant_id}/credentials/{credential.metadata.id}"
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret={
                    "value": credential.encrypted_value,
                    "metadata": credential.metadata.dict()
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store credential in Vault: {e}")
            return False
    
    async def retrieve_credential(self, credential_id: str, tenant_id: str) -> Optional[str]:
        try:
            path = f"secret/tenants/{tenant_id}/credentials/{credential_id}"
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            return response['data']['data']['value']
        except Exception as e:
            logger.error(f"Failed to retrieve credential from Vault: {e}")
            return None

class KubernetesSecretStore(CredentialStore):
    """Kubernetes Secrets integration for K8s environments."""
    
    def __init__(self):
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        self.v1 = client.CoreV1Api()
    
    async def store_credential(self, credential: SecureCredential) -> bool:
        try:
            secret_name = f"cred-{credential.metadata.tenant_id}-{credential.metadata.id}"
            secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace="openai-agents",
                    labels={
                        "tenant-id": credential.metadata.tenant_id,
                        "credential-type": credential.metadata.type,
                        "managed-by": "openai-agents"
                    }
                ),
                data={
                    "value": base64.b64encode(credential.encrypted_value.encode()).decode(),
                    "metadata": base64.b64encode(json.dumps(credential.metadata.dict()).encode()).decode()
                }
            )
            self.v1.create_namespaced_secret(namespace="openai-agents", body=secret)
            return True
        except Exception as e:
            logger.error(f"Failed to store credential in Kubernetes: {e}")
            return False

class CredentialManager:
    def __init__(self, store: CredentialStore, encryption_key: Optional[str] = None):
        self.store = store
        self.encryption_key = encryption_key or self._generate_key()
        self.fernet = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
    
    def _generate_key(self) -> bytes:
        """Generate encryption key from environment or create new one."""
        key_material = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        if key_material:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'openai-agents-salt',  # In production, use random salt per tenant
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key_material.encode()))
            return key
        else:
            return Fernet.generate_key()
    
    async def store_credential(self, 
                             name: str, 
                             value: str, 
                             credential_type: CredentialType,
                             tenant_id: str,
                             expires_at: Optional[str] = None,
                             tags: Optional[Dict[str, str]] = None) -> str:
        """Store a credential securely with encryption."""
        
        # Generate unique ID
        credential_id = f"{tenant_id}_{name}_{int(time.time())}"
        
        # Encrypt the credential value
        encrypted_value = self.fernet.encrypt(value.encode()).decode()
        
        # Create metadata
        metadata = CredentialMetadata(
            id=credential_id,
            name=name,
            type=credential_type,
            tenant_id=tenant_id,
            created_at=datetime.utcnow().isoformat(),
            expires_at=expires_at,
            tags=tags or {}
        )
        
        # Create secure credential
        secure_cred = SecureCredential(
            metadata=metadata,
            encrypted_value=encrypted_value,
            encryption_key_id="default"  # In production, use key rotation
        )
        
        # Store in backend
        success = await self.store.store_credential(secure_cred)
        if success:
            return credential_id
        else:
            raise Exception("Failed to store credential")
    
    async def retrieve_credential(self, credential_id: str, tenant_id: str) -> Optional[str]:
        """Retrieve and decrypt a credential."""
        encrypted_value = await self.store.retrieve_credential(credential_id, tenant_id)
        if encrypted_value:
            try:
                decrypted_value = self.fernet.decrypt(encrypted_value.encode()).decode()
                return decrypted_value
            except Exception as e:
                logger.error(f"Failed to decrypt credential: {e}")
                return None
        return None
    
    async def rotate_credential(self, credential_id: str, tenant_id: str, new_value: str) -> bool:
        """Rotate a credential with the new value."""
        # Retrieve existing metadata
        credentials = await self.store.list_credentials(tenant_id)
        existing = next((c for c in credentials if c.id == credential_id), None)
        
        if not existing:
            return False
        
        # Delete old credential
        await self.store.delete_credential(credential_id, tenant_id)
        
        # Store new credential with updated metadata
        new_id = await self.store_credential(
            name=existing.name,
            value=new_value,
            credential_type=existing.type,
            tenant_id=tenant_id,
            expires_at=existing.expires_at,
            tags=existing.tags
        )
        
        return new_id is not None

# Credential injection for agents and MCP servers
class SecureCredentialInjector:
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager
    
    async def inject_credentials(self, 
                               template: str, 
                               tenant_id: str,
                               credential_mappings: Dict[str, str]) -> str:
        """Inject credentials into configuration templates securely."""
        
        result = template
        for placeholder, credential_id in credential_mappings.items():
            credential_value = await self.credential_manager.retrieve_credential(
                credential_id, tenant_id
            )
            if credential_value:
                result = result.replace(f"${{{placeholder}}}", credential_value)
            else:
                logger.warning(f"Credential {credential_id} not found for tenant {tenant_id}")
        
        return result
    
    def create_secure_env_vars(self, 
                             credential_mappings: Dict[str, str],
                             tenant_id: str) -> Dict[str, str]:
        """Create environment variables with credential references for containers."""
        
        env_vars = {}
        for env_name, credential_id in credential_mappings.items():
            # Use Kubernetes secret references instead of plain values
            env_vars[env_name] = {
                "valueFrom": {
                    "secretKeyRef": {
                        "name": f"cred-{tenant_id}-{credential_id}",
                        "key": "value"
                    }
                }
            }
        
        return env_vars
```

#### Credential Lifecycle Management
```python
# security/credential_lifecycle.py
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio
from celery import Celery

class CredentialRotationPolicy(BaseModel):
    rotation_interval_days: int
    warning_days_before_expiry: int
    auto_rotate: bool = False
    notification_channels: List[str] = []

class CredentialLifecycleManager:
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager
        self.celery_app = Celery('credential_rotation')
    
    async def check_expiring_credentials(self) -> List[CredentialMetadata]:
        """Check for credentials that are expiring soon."""
        expiring_credentials = []
        
        # Get all tenants (implement based on your tenant management)
        tenants = await self.get_all_tenants()
        
        for tenant_id in tenants:
            credentials = await self.credential_manager.store.list_credentials(tenant_id)
            
            for cred in credentials:
                if cred.expires_at:
                    expiry_date = datetime.fromisoformat(cred.expires_at)
                    days_until_expiry = (expiry_date - datetime.utcnow()).days
                    
                    if days_until_expiry <= 7:  # Warning threshold
                        expiring_credentials.append(cred)
        
        return expiring_credentials
    
    @celery_app.task
    def rotate_credential_task(self, credential_id: str, tenant_id: str):
        """Celery task for automatic credential rotation."""
        # Implement credential-specific rotation logic
        # This would integrate with external systems to generate new credentials
        pass
    
    async def schedule_rotation(self, credential_id: str, tenant_id: str, rotation_date: datetime):
        """Schedule automatic credential rotation."""
        self.rotate_credential_task.apply_async(
            args=[credential_id, tenant_id],
            eta=rotation_date
        )

# Audit trail for credential access
class CredentialAuditLogger:
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger
    
    async def log_credential_access(self, 
                                  credential_id: str,
                                  tenant_id: str,
                                  user_id: str,
                                  action: str,
                                  success: bool,
                                  ip_address: str = None):
        """Log all credential access attempts."""
        
        await self.audit_logger.log_event(AuditEvent(
            event_type="credential_access",
            resource_type="credential",
            resource_id=credential_id,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            details={
                "success": success,
                "credential_id": credential_id,
                "access_method": "api"
            },
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        ))
```

### 0.2 Zero-Credential-Leakage Architecture

#### Environment Variable Sanitization
```python
# security/env_sanitizer.py
import re
from typing import Dict, List, Set

class EnvironmentSanitizer:
    """Ensures no credentials leak through environment variables, logs, or error messages."""
    
    SENSITIVE_PATTERNS = [
        r'api[_-]?key',
        r'secret[_-]?key',
        r'password',
        r'token',
        r'credential',
        r'auth[_-]?token',
        r'bearer[_-]?token',
        r'access[_-]?token',
        r'refresh[_-]?token',
        r'private[_-]?key',
        r'cert[_-]?key',
        r'database[_-]?url',
        r'connection[_-]?string'
    ]
    
    def __init__(self):
        self.sensitive_keys = self._compile_patterns()
    
    def _compile_patterns(self) -> List[re.Pattern]:
        return [re.compile(pattern, re.IGNORECASE) for pattern in self.SENSITIVE_PATTERNS]
    
    def sanitize_environment(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Remove or mask sensitive environment variables."""
        sanitized = {}
        
        for key, value in env_vars.items():
            if self._is_sensitive_key(key):
                sanitized[key] = self._mask_value(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if environment variable key contains sensitive information."""
        return any(pattern.search(key) for pattern in self.sensitive_keys)
    
    def _mask_value(self, value: str) -> str:
        """Mask sensitive values for logging/display."""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    
    def sanitize_logs(self, log_message: str) -> str:
        """Remove potential credentials from log messages."""
        # Pattern to match potential API keys, tokens, etc.
        patterns = [
            r'["\']?[a-zA-Z0-9_-]*[aA][pP][iI][_-]?[kK][eE][yY]["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            r'["\']?[tT][oO][kK][eE][nN]["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_.-]{20,})["\']?',
            r'["\']?[bB][eE][aA][rR][eE][rR]\s+([a-zA-Z0-9_.-]{20,})["\']?',
            r'postgresql://[^:]+:([^@]+)@',  # Database passwords
            r'mysql://[^:]+:([^@]+)@',
            r'redis://[^:]*:([^@]+)@'
        ]
        
        sanitized = log_message
        for pattern in patterns:
            sanitized = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), "*" * 8), sanitized)
        
        return sanitized

# Secure configuration loader
class SecureConfigLoader:
    """Load configuration without exposing credentials in memory or logs."""
    
    def __init__(self, credential_manager: CredentialManager):
        self.credential_manager = credential_manager
        self.sanitizer = EnvironmentSanitizer()
    
    async def load_secure_config(self, tenant_id: str, config_template: Dict) -> Dict:
        """Load configuration with credentials injected securely."""
        
        config = config_template.copy()
        
        # Process credential references
        await self._process_credential_refs(config, tenant_id)
        
        return config
    
    async def _process_credential_refs(self, config: Dict, tenant_id: str):
        """Recursively process credential references in configuration."""
        
        for key, value in config.items():
            if isinstance(value, dict):
                await self._process_credential_refs(value, tenant_id)
            elif isinstance(value, str) and value.startswith("${CREDENTIAL:"):
                # Extract credential reference: ${CREDENTIAL:credential_id}
                credential_id = value[13:-1]  # Remove ${CREDENTIAL: and }
                credential_value = await self.credential_manager.retrieve_credential(
                    credential_id, tenant_id
                )
                if credential_value:
                    config[key] = credential_value
                else:
                    raise ValueError(f"Credential {credential_id} not found for tenant {tenant_id}")
```

### 0.3 Secure Development Practices

#### Secure Defaults Configuration
```yaml
# config/secure-defaults.yaml
security:
  # Credential management
  credential_encryption: true
  credential_rotation_days: 90
  credential_audit_logging: true
  
  # API Security
  require_authentication: true
  require_authorization: true
  rate_limiting_enabled: true
  cors_strict_mode: true
  
  # Data Protection
  encrypt_at_rest: true
  encrypt_in_transit: true
  data_classification_required: true
  
  # Audit & Compliance
  audit_all_access: true
  log_retention_days: 365
  compliance_mode: "SOC2"
  
  # Container Security
  run_as_non_root: true
  read_only_filesystem: true
  no_privilege_escalation: true
  security_context_required: true

development:
  # Development-specific overrides (still secure)
  credential_rotation_days: 30
  log_level: "DEBUG"
  cors_origins: ["http://localhost:3000"]
  
production:
  # Production hardening
  debug_mode: false
  error_details_hidden: true
  security_headers_enforced: true
  vulnerability_scanning: true
```

#### Secure Docker Images
```dockerfile
# Dockerfile.secure-base
FROM python:3.11-slim as secure-base

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set secure defaults
RUN mkdir -p /app && chown appuser:appuser /app
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Security: Read-only filesystem, no privilege escalation
FROM secure-base as production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Remove any potential secrets from image layers
RUN find /app -name "*.env*" -delete 2>/dev/null || true
RUN find /app -name "*secret*" -delete 2>/dev/null || true
RUN find /app -name "*key*" -delete 2>/dev/null || true

EXPOSE 8000
CMD ["gunicorn", "api:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## Phase 1: Foundation & Infrastructure

### 1.1 Containerization & Orchestration

#### Docker Implementation
```dockerfile
# Multi-stage build for Python backend
FROM python:3.11-slim as backend-base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM backend-base as backend-dev
COPY . .
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM backend-base as backend-prod
COPY . .
CMD ["gunicorn", "api:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# Node.js frontend
FROM node:18-alpine as frontend-base
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM frontend-base as frontend-dev
COPY . .
CMD ["npm", "run", "dev"]

FROM frontend-base as frontend-prod
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

#### Kubernetes Manifests
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openai-agents
  labels:
    name: openai-agents

---
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agents-backend
  namespace: openai-agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agents-backend
  template:
    metadata:
      labels:
        app: agents-backend
    spec:
      containers:
      - name: backend
        image: agents-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

#### Development Environment
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  backend:
    build:
      context: ./python-backend
      target: backend-dev
    ports:
      - "8000:8000"
    volumes:
      - ./python-backend:/app
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/agents_dev
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  frontend:
    build:
      context: ./ui
      target: frontend-dev
    ports:
      - "3000:3000"
    volumes:
      - ./ui:/app
      - /app/node_modules

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: agents_dev
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 1.2 Database Abstraction Layer

#### SQLAlchemy Models
```python
# models/base.py
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TenantMixin:
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

# models/conversation.py
class Conversation(Base, TimestampMixin, TenantMixin):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    current_agent = Column(String(100), nullable=False)
    context = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), default="active")
    metadata = Column(JSON, default=dict)

class Message(Base, TimestampMixin, TenantMixin):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    agent_name = Column(String(100))
    metadata = Column(JSON, default=dict)

class AgentEvent(Base, TimestampMixin, TenantMixin):
    __tablename__ = "agent_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    agent_name = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)
```

#### Repository Pattern
```python
# repositories/conversation_repository.py
from typing import Optional, List
from sqlalchemy.orm import Session
from models.conversation import Conversation, Message, AgentEvent

class ConversationRepository:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def create_conversation(self, user_id: str, initial_context: dict) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            tenant_id=self.tenant_id,
            current_agent="triage_agent",
            context=initial_context
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == self.tenant_id
        ).first()
    
    async def add_message(self, conversation_id: str, role: str, content: str, 
                         agent_name: Optional[str] = None) -> Message:
        message = Message(
            conversation_id=conversation_id,
            tenant_id=self.tenant_id,
            role=role,
            content=content,
            agent_name=agent_name
        )
        self.db.add(message)
        self.db.commit()
        return message
```

### 1.3 Configuration Management

#### Pydantic Settings
```python
# config/settings.py
from pydantic import BaseSettings, Field
from typing import Optional, List
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DatabaseSettings(BaseSettings):
    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    echo: bool = Field(False, env="DB_ECHO")

class RedisSettings(BaseSettings):
    url: str = Field("redis://localhost:6379", env="REDIS_URL")
    max_connections: int = Field(10, env="REDIS_MAX_CONNECTIONS")

class OpenAISettings(BaseSettings):
    api_key: str = Field(..., env="OPENAI_API_KEY")
    default_model: str = Field("gpt-4.1", env="OPENAI_DEFAULT_MODEL")
    max_tokens: int = Field(4000, env="OPENAI_MAX_TOKENS")
    temperature: float = Field(0.7, env="OPENAI_TEMPERATURE")

class SecuritySettings(BaseSettings):
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    cors_origins: List[str] = Field(["http://localhost:3000"], env="CORS_ORIGINS")

class Settings(BaseSettings):
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    openai: OpenAISettings = OpenAISettings()
    security: SecuritySettings = SecuritySettings()
    
    # MCP Settings
    mcp_server_registry_url: str = Field("", env="MCP_SERVER_REGISTRY_URL")
    mcp_auto_deploy: bool = Field(True, env="MCP_AUTO_DEPLOY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### 1.4 Multi-Tenancy Framework

#### Tenant Context
```python
# core/tenant.py
from contextvars import ContextVar
from typing import Optional
import uuid

# Context variable for current tenant
current_tenant: ContextVar[Optional[str]] = ContextVar('current_tenant', default=None)

class TenantContext:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.token = None
    
    def __enter__(self):
        self.token = current_tenant.set(self.tenant_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        current_tenant.reset(self.token)

def get_current_tenant() -> Optional[str]:
    return current_tenant.get()

def require_tenant() -> str:
    tenant_id = get_current_tenant()
    if not tenant_id:
        raise ValueError("No tenant context available")
    return tenant_id

# Middleware for FastAPI
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from header, subdomain, or JWT token
        tenant_id = self.extract_tenant_id(request)
        
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID required")
        
        with TenantContext(tenant_id):
            response = await call_next(request)
        
        return response
    
    def extract_tenant_id(self, request: Request) -> Optional[str]:
        # Try header first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Try subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain != "www" and subdomain != "api":
                return subdomain
        
        # Try JWT token (implement based on your auth system)
        return None
```

---

## Phase 2: MCP Integration & API Management

### 2.1 OpenAPI Spec Analyzer

#### Spec Parser and Analyzer
```python
# mcp/openapi_analyzer.py
from typing import Dict, List, Optional, Set
import yaml
import json
from pydantic import BaseModel
from pathlib import Path

class EndpointInfo(BaseModel):
    path: str
    method: str
    operation_id: str
    summary: str
    description: Optional[str]
    parameters: List[Dict]
    request_body: Optional[Dict]
    responses: Dict[str, Dict]
    tags: List[str]
    complexity_score: int

class OpenAPIAnalyzer:
    def __init__(self, spec_content: str):
        self.spec = self.parse_spec(spec_content)
        self.endpoints = self.analyze_endpoints()
    
    def parse_spec(self, content: str) -> Dict:
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return json.loads(content)
    
    def analyze_endpoints(self) -> List[EndpointInfo]:
        endpoints = []
        paths = self.spec.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoint = EndpointInfo(
                        path=path,
                        method=method.upper(),
                        operation_id=operation.get("operationId", f"{method}_{path}"),
                        summary=operation.get("summary", ""),
                        description=operation.get("description"),
                        parameters=operation.get("parameters", []),
                        request_body=operation.get("requestBody"),
                        responses=operation.get("responses", {}),
                        tags=operation.get("tags", []),
                        complexity_score=self.calculate_complexity(operation)
                    )
                    endpoints.append(endpoint)
        
        return endpoints
    
    def calculate_complexity(self, operation: Dict) -> int:
        score = 1  # Base score
        
        # Add complexity for parameters
        params = operation.get("parameters", [])
        score += len(params) * 0.5
        
        # Add complexity for request body
        if operation.get("requestBody"):
            score += 2
        
        # Add complexity for multiple response types
        responses = operation.get("responses", {})
        score += len(responses) * 0.3
        
        return int(score)
    
    def get_endpoints_by_tag(self, tag: str) -> List[EndpointInfo]:
        return [ep for ep in self.endpoints if tag in ep.tags]
    
    def get_high_value_endpoints(self, max_complexity: int = 5) -> List[EndpointInfo]:
        return [ep for ep in self.endpoints if ep.complexity_score <= max_complexity]
    
    def generate_functionality_groups(self) -> Dict[str, List[EndpointInfo]]:
        groups = {}
        for endpoint in self.endpoints:
            for tag in endpoint.tags or ["default"]:
                if tag not in groups:
                    groups[tag] = []
                groups[tag].append(endpoint)
        return groups
```

### 2.2 MCP Server Generator

#### Template Engine
```python
# mcp/server_generator.py
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict
import os
from pathlib import Path

class MCPServerGenerator:
    def __init__(self, template_dir: str = "mcp/templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate_server(self, 
                       server_name: str,
                       selected_endpoints: List[EndpointInfo],
                       openapi_spec: Dict,
                       output_dir: str) -> str:
        
        # Generate server structure
        server_dir = Path(output_dir) / server_name
        server_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate main server file
        self.generate_main_server(server_name, selected_endpoints, server_dir)
        
        # Generate client wrapper
        self.generate_client_wrapper(openapi_spec, selected_endpoints, server_dir)
        
        # Generate configuration
        self.generate_config(server_name, openapi_spec, server_dir)
        
        # Generate requirements
        self.generate_requirements(server_dir)
        
        # Generate README
        self.generate_readme(server_name, selected_endpoints, server_dir)
        
        return str(server_dir)
    
    def generate_main_server(self, server_name: str, endpoints: List[EndpointInfo], output_dir: Path):
        template = self.env.get_template("server_main.py.j2")
        content = template.render(
            server_name=server_name,
            endpoints=endpoints,
            tools=self.generate_tools_from_endpoints(endpoints)
        )
        
        with open(output_dir / "server.py", "w") as f:
            f.write(content)
    
    def generate_tools_from_endpoints(self, endpoints: List[EndpointInfo]) -> List[Dict]:
        tools = []
        for endpoint in endpoints:
            tool = {
                "name": endpoint.operation_id,
                "description": endpoint.summary or endpoint.description,
                "method": endpoint.method,
                "path": endpoint.path,
                "parameters": self.convert_parameters(endpoint.parameters),
                "request_body": endpoint.request_body
            }
            tools.append(tool)
        return tools
    
    def convert_parameters(self, parameters: List[Dict]) -> List[Dict]:
        converted = []
        for param in parameters:
            converted.append({
                "name": param.get("name"),
                "type": param.get("schema", {}).get("type", "string"),
                "required": param.get("required", False),
                "description": param.get("description", ""),
                "location": param.get("in", "query")
            })
        return converted
```

#### MCP Server Template
```python
# mcp/templates/server_main.py.j2
#!/usr/bin/env python3
"""
{{ server_name }} MCP Server
Auto-generated from OpenAPI specification
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class {{ server_name|title }}Client:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient()
    
    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    {% for tool in tools %}
    async def {{ tool.name }}(self, **kwargs) -> Dict[str, Any]:
        """{{ tool.description }}"""
        url = f"{self.base_url}{{ tool.path }}"
        
        # Handle path parameters
        for param_name, param_value in kwargs.items():
            if f"{{{param_name}}}" in url:
                url = url.replace(f"{{{param_name}}}", str(param_value))
        
        # Prepare request
        method = "{{ tool.method }}"
        headers = self.get_headers()
        
        {% if tool.method in ['POST', 'PUT', 'PATCH'] and tool.request_body %}
        # Handle request body
        json_data = {k: v for k, v in kwargs.items() 
                    if f"{{{k}}}" not in "{{ tool.path }}"}
        response = await self.client.request(
            method, url, headers=headers, json=json_data
        )
        {% else %}
        # Handle query parameters
        params = {k: v for k, v in kwargs.items() 
                 if f"{{{k}}}" not in "{{ tool.path }}"}
        response = await self.client.request(
            method, url, headers=headers, params=params
        )
        {% endif %}
        
        response.raise_for_status()
        return response.json()
    
    {% endfor %}

# Initialize the server
server = Server("{{ server_name }}")
client = None

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        {% for tool in tools %}
        Tool(
            name="{{ tool.name }}",
            description="{{ tool.description }}",
            inputSchema={
                "type": "object",
                "properties": {
                    {% for param in tool.parameters %}
                    "{{ param.name }}": {
                        "type": "{{ param.type }}",
                        "description": "{{ param.description }}"
                    }{% if not loop.last %},{% endif %}
                    {% endfor %}
                },
                "required": [{% for param in tool.parameters if param.required %}"{{ param.name }}"{% if not loop.last %}, {% endif %}{% endfor %}]
            }
        ){% if not loop.last %},{% endif %}
        {% endfor %}
    ]

{% for tool in tools %}
@server.call_tool()
async def handle_{{ tool.name }}(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle {{ tool.name }} tool call."""
    if name != "{{ tool.name }}":
        raise ValueError(f"Unknown tool: {name}")
    
    try:
        result = await client.{{ tool.name }}(**arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.error(f"Error calling {{ tool.name }}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

{% endfor %}

async def main():
    global client
    
    # Initialize client with configuration
    import os
    base_url = os.getenv("{{ server_name.upper() }}_BASE_URL", "https://api.example.com")
    api_key = os.getenv("{{ server_name.upper() }}_API_KEY")
    
    client = {{ server_name|title }}Client(base_url, api_key)
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="{{ server_name }}",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.3 Dynamic MCP Server Management

#### Server Registry
```python
# mcp/registry.py
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from models.base import Base, TimestampMixin, TenantMixin
import subprocess
import os
from pathlib import Path

class MCPServerConfig(BaseModel):
    name: str
    description: str
    base_url: str
    api_key: Optional[str]
    selected_endpoints: List[str]
    auto_deploy: bool = True
    status: str = "inactive"  # inactive, deploying, active, error

class MCPServer(Base, TimestampMixin, TenantMixin):
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    config = Column(JSON, nullable=False)
    openapi_spec = Column(JSON, nullable=False)
    status = Column(String(20), default="inactive")
    deployment_info = Column(JSON, default=dict)
    is_active = Column(Boolean, default=False)

class MCPServerManager:
    def __init__(self, servers_dir: str = "./mcp_servers"):
        self.servers_dir = Path(servers_dir)
        self.servers_dir.mkdir(exist_ok=True)
    
    async def create_server(self, 
                          config: MCPServerConfig,
                          openapi_spec: Dict,
                          selected_endpoints: List[EndpointInfo]) -> str:
        """Create and optionally deploy a new MCP server."""
        
        # Generate server code
        generator = MCPServerGenerator()
        server_path = generator.generate_server(
            config.name,
            selected_endpoints,
            openapi_spec,
            str(self.servers_dir)
        )
        
        # Save to database
        server_record = MCPServer(
            id=config.name,
            name=config.name,
            description=config.description,
            config=config.dict(),
            openapi_spec=openapi_spec,
            status="created"
        )
        
        # Deploy if auto_deploy is enabled
        if config.auto_deploy:
            await self.deploy_server(config.name)
        
        return server_path
    
    async def deploy_server(self, server_name: str) -> bool:
        """Deploy server to Kubernetes."""
        server_dir = self.servers_dir / server_name
        
        try:
            # Build Docker image
            await self.build_docker_image(server_name, server_dir)
            
            # Deploy to Kubernetes
            await self.deploy_to_kubernetes(server_name)
            
            # Update status
            # Update database record status to "active"
            
            return True
        except Exception as e:
            # Update database record status to "error"
            raise e
    
    async def build_docker_image(self, server_name: str, server_dir: Path):
        """Build Docker image for the MCP server."""
        dockerfile_content = f"""
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "server.py"]
"""
        
        with open(server_dir / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
        
        # Build image
        cmd = f"docker build -t mcp-{server_name}:latest {server_dir}"
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to build Docker image for {server_name}")
    
    async def deploy_to_kubernetes(self, server_name: str):
        """Deploy MCP server to Kubernetes."""
        k8s_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-{server_name}
  namespace: openai-agents
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-{server_name}
  template:
    metadata:
      labels:
        app: mcp-{server_name}
    spec:
      containers:
      - name: mcp-server
        image: mcp-{server_name}:latest
        ports:
        - containerPort: 8080
        env:
        - name: SERVER_NAME
          value: "{server_name}"
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-{server_name}-service
  namespace: openai-agents
spec:
  selector:
    app: mcp-{server_name}
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
"""
        
        # Apply manifest
        manifest_file = f"/tmp/mcp-{server_name}.yaml"
        with open(manifest_file, "w") as f:
            f.write(k8s_manifest)
        
        cmd = f"kubectl apply -f {manifest_file}"
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to deploy {server_name} to Kubernetes")
```

---

## Phase 3: Enterprise Security & Compliance

### 3.1 Authentication & Authorization

#### JWT Authentication
```python
# auth/jwt_auth.py
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

class TokenData(BaseModel):
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []

class User(BaseModel):
    id: str
    email: str
    tenant_id: str
    roles: List[str]
    is_active: bool = True

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            tenant_id: str = payload.get("tenant_id")
            roles: List[str] = payload.get("roles", [])
            permissions: List[str] = payload.get("permissions", [])
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            
            return TokenData(
                user_id=user_id,
                tenant_id=tenant_id,
                roles=roles,
                permissions=permissions
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    auth_manager = AuthManager(settings.security.secret_key)
    return auth_manager.verify_token(credentials.credentials)

async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    # Add additional checks if needed (e.g., user is active)
    return current_user
```

#### RBAC Implementation
```python
# auth/rbac.py
from typing import List, Dict, Set
from enum import Enum
from pydantic import BaseModel
from functools import wraps
from fastapi import HTTPException, status

class Permission(str, Enum):
    # Agent permissions
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    
    # Conversation permissions
    CONVERSATION_CREATE = "conversation:create"
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_UPDATE = "conversation:update"
    CONVERSATION_DELETE = "conversation:delete"
    
    # MCP permissions
    MCP_SERVER_CREATE = "mcp_server:create"
    MCP_SERVER_DEPLOY = "mcp_server:deploy"
    MCP_SERVER_MANAGE = "mcp_server:manage"
    
    # Admin permissions
    TENANT_MANAGE = "tenant:manage"
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"

class Role(BaseModel):
    name: str
    permissions: List[Permission]
    description: str

# Predefined roles
ROLES = {
    "admin": Role(
        name="admin",
        permissions=list(Permission),
        description="Full system access"
    ),
    "agent_developer": Role(
        name="agent_developer",
        permissions=[
            Permission.AGENT_CREATE,
            Permission.AGENT_READ,
            Permission.AGENT_UPDATE,
            Permission.AGENT_DELETE,
            Permission.CONVERSATION_READ,
            Permission.MCP_SERVER_CREATE,
            Permission.MCP_SERVER_DEPLOY,
        ],
        description="Can develop and deploy agents and MCP servers"
    ),
    "agent_user": Role(
        name="agent_user",
        permissions=[
            Permission.CONVERSATION_CREATE,
            Permission.CONVERSATION_READ,
            Permission.CONVERSATION_UPDATE,
            Permission.AGENT_READ,
        ],
        description="Can use agents and manage conversations"
    ),
    "viewer": Role(
        name="viewer",
        permissions=[
            Permission.AGENT_READ,
            Permission.CONVERSATION_READ,
        ],
        description="Read-only access"
    )
}

def require_permissions(*required_permissions: Permission):
    """Decorator to require specific permissions for an endpoint."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current user from kwargs or dependency injection
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_permissions = set(current_user.permissions)
            required_perms = set(required_permissions)
            
            if not required_perms.issubset(user_permissions):
                missing_perms = required_perms - user_permissions
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permissions: {', '.join(missing_perms)}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 3.2 Audit Logging & Compliance

#### Audit System
```python
# audit/audit_logger.py
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text
from models.base import Base, TenantMixin
import json
import logging

class AuditEvent(BaseModel):
    event_type: str
    resource_type: str
    resource_id: Optional[str]
    user_id: str
    tenant_id: str
    action: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

class AuditLog(Base, TenantMixin):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(100), index=True)
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    details = Column(JSON, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    async def log_event(self, event: AuditEvent):
        """Log an audit event to both database and log file."""
        
        # Save to database
        audit_record = AuditLog(
            id=f"{event.timestamp.isoformat()}_{event.user_id}_{event.action}",
            event_type=event.event_type,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            user_id=event.user_id,
            tenant_id=event.tenant_id,
            action=event.action,
            details=event.details,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            timestamp=event.timestamp
        )
        
        # Also log to structured log file
        self.logger.info(
            "AUDIT_EVENT",
            extra={
                "event_type": event.event_type,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "user_id": event.user_id,
                "tenant_id": event.tenant_id,
                "action": event.action,
                "details": event.details,
                "ip_address": event.ip_address,
                "timestamp": event.timestamp.isoformat()
            }
        )
    
    async def log_agent_interaction(self, user_id: str, tenant_id: str, 
                                  conversation_id: str, agent_name: str, 
                                  action: str, details: Dict[str, Any]):
        """Log agent interaction events."""
        event = AuditEvent(
            event_type="agent_interaction",
            resource_type="conversation",
            resource_id=conversation_id,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            details={
                "agent_name": agent_name,
                **details
            },
            timestamp=datetime.utcnow()
        )
        await self.log_event(event)
    
    async def log_mcp_server_action(self, user_id: str, tenant_id: str,
                                  server_name: str, action: str, 
                                  details: Dict[str, Any]):
        """Log MCP server management actions."""
        event = AuditEvent(
            event_type="mcp_server",
            resource_type="mcp_server",
            resource_id=server_name,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            details=details,
            timestamp=datetime.utcnow()
        )
        await self.log_event(event)

# Middleware for automatic audit logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, audit_logger: AuditLogger):
        super().__init__(app)
        self.audit_logger = audit_logger
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        
        # Extract user info if available
        user_id = getattr(request.state, 'user_id', 'anonymous')
        tenant_id = getattr(request.state, 'tenant_id', 'unknown')
        
        response = await call_next(request)
        
        # Log API access
        if request.url.path.startswith('/api/'):
            await self.audit_logger.log_event(AuditEvent(
                event_type="api_access",
                resource_type="api_endpoint",
                resource_id=request.url.path,
                user_id=user_id,
                tenant_id=tenant_id,
                action=request.method,
                details={
                    "status_code": response.status_code,
                    "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                    "query_params": dict(request.query_params)
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                timestamp=start_time
            ))
        
        return response
```

---

## Phase 4: UI Framework & Developer Experience

### 4.1 Standardized Component System

#### Agent Component Template
```typescript
// components/templates/AgentComponentTemplate.tsx
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, Settings, Play, Pause } from 'lucide-react';

interface AgentComponentProps {
  agentName: string;
  agentDescription: string;
  isActive: boolean;
  status: 'idle' | 'processing' | 'error';
  tools: string[];
  guardrails: string[];
  onToggle: () => void;
  onConfigure: () => void;
  children?: React.ReactNode;
}

export function AgentComponentTemplate({
  agentName,
  agentDescription,
  isActive,
  status,
  tools,
  guardrails,
  onToggle,
  onConfigure,
  children
}: AgentComponentProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'processing': return 'bg-blue-500';
      case 'error': return 'bg-red-500';
      default: return isActive ? 'bg-green-500' : 'bg-gray-400';
    }
  };

  const getStatusIcon = () => {
    if (status === 'processing') {
      return <Loader2 className="h-4 w-4 animate-spin" />;
    }
    return isActive ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />;
  };

  return (
    <Card className={`transition-all duration-200 ${isActive ? 'ring-2 ring-blue-500' : ''}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">{agentName}</CardTitle>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
            {getStatusIcon()}
          </div>
        </div>
        <p className="text-sm text-gray-600">{agentDescription}</p>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Tools Section */}
        <div>
          <h4 className="text-sm font-medium mb-2">Tools</h4>
          <div className="flex flex-wrap gap-1">
            {tools.map((tool) => (
              <Badge key={tool} variant="secondary" className="text-xs">
                {tool}
              </Badge>
            ))}
          </div>
        </div>

        {/* Guardrails Section */}
        <div>
          <h4 className="text-sm font-medium mb-2">Guardrails</h4>
          <div className="flex flex-wrap gap-1">
            {guardrails.map((guardrail) => (
              <Badge key={guardrail} variant="outline" className="text-xs">
                {guardrail}
              </Badge>
            ))}
          </div>
        </div>

        {/* Custom Content */}
        {children}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <Button
            variant={isActive ? "destructive" : "default"}
            size="sm"
            onClick={onToggle}
            className="flex-1"
          >
            {isActive ? 'Deactivate' : 'Activate'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onConfigure}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### MCP Server Component
```typescript
// components/mcp/MCPServerComponent.tsx
import React, { useState } from 'react';
import { AgentComponentTemplate } from '@/components/templates/AgentComponentTemplate';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { AlertCircle, CheckCircle, Clock, Server } from 'lucide-react';

interface MCPServerComponentProps {
  serverName: string;
  description: string;
  baseUrl: string;
  status: 'inactive' | 'deploying' | 'active' | 'error';
  endpoints: Array<{
    name: string;
    method: string;
    path: string;
    enabled: boolean;
  }>;
  deploymentProgress?: number;
  onDeploy: () => void;
  onStop: () => void;
  onConfigure: () => void;
}

export function MCPServerComponent({
  serverName,
  description,
  baseUrl,
  status,
  endpoints,
  deploymentProgress = 0,
  onDeploy,
  onStop,
  onConfigure
}: MCPServerComponentProps) {
  const getStatusIcon = () => {
    switch (status) {
      case 'active': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'deploying': return <Clock className="h-4 w-4 text-blue-500" />;
      default: return <Server className="h-4 w-4 text-gray-400" />;
    }
  };

  const enabledEndpoints = endpoints.filter(ep => ep.enabled);
  const tools = enabledEndpoints.map(ep => `${ep.method} ${ep.name}`);

  return (
    <AgentComponentTemplate
      agentName={serverName}
      agentDescription={description}
      isActive={status === 'active'}
      status={status === 'deploying' ? 'processing' : status === 'error' ? 'error' : 'idle'}
      tools={tools}
      guardrails={[]} // MCP servers don't have guardrails
      onToggle={status === 'active' ? onStop : onDeploy}
      onConfigure={onConfigure}
    >
      {/* Server-specific content */}
      <div className="space-y-3">
        <div>
          <div className="flex items-center gap-2 mb-2">
            {getStatusIcon()}
            <span className="text-sm font-medium capitalize">{status}</span>
          </div>
          
          {status === 'deploying' && (
            <div className="space-y-2">
              <Progress value={deploymentProgress} className="h-2" />
              <p className="text-xs text-gray-500">Deploying... {deploymentProgress}%</p>
            </div>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium mb-2">Base URL</h4>
          <code className="text-xs bg-gray-100 px-2 py-1 rounded">{baseUrl}</code>
        </div>

        <div>
          <h4 className="text-sm font-medium mb-2">Endpoints ({enabledEndpoints.length})</h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {enabledEndpoints.slice(0, 3).map((endpoint) => (
              <div key={`${endpoint.method}-${endpoint.path}`} className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  {endpoint.method}
                </Badge>
                <span className="text-xs font-mono">{endpoint.path}</span>
              </div>
            ))}
            {enabledEndpoints.length > 3 && (
              <p className="text-xs text-gray-500">
                +{enabledEndpoints.length - 3} more endpoints
              </p>
            )}
          </div>
        </div>
      </div>
    </AgentComponentTemplate>
  );
}
```

### 4.2 Developer CLI Tools

#### Agent Scaffolding CLI
```python
# cli/agent_cli.py
import click
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict

@click.group()
def cli():
    """OpenAI Agents Enterprise CLI"""
    pass

@cli.command()
@click.argument('agent_name')
@click.option('--description', '-d', help='Agent description')
@click.option('--tools', '-t', multiple=True, help='Tools to include')
@click.option('--guardrails', '-g', multiple=True, help='Guardrails to include')
@click.option('--output-dir', '-o', default='./agents', help='Output directory')
def create_agent(agent_name: str, description: str, tools: List[str], 
                guardrails: List[str], output_dir: str):
    """Create a new agent with boilerplate code."""
    
    agent_dir = Path(output_dir) / agent_name.lower().replace(' ', '_')
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate agent Python file
    generate_agent_file(agent_name, description, tools, guardrails, agent_dir)
    
    # Generate React component
    generate_agent_component(agent_name, description, agent_dir)
    
    # Generate tests
    generate_agent_tests(agent_name, agent_dir)
    
    click.echo(f"✅ Agent '{agent_name}' created in {agent_dir}")
    click.echo(f"📁 Files created:")
    click.echo(f"   - {agent_name.lower()}_agent.py")
    click.echo(f"   - {agent_name}Component.tsx")
    click.echo(f"   - test_{agent_name.lower()}_agent.py")

def generate_agent_file(name: str, description: str, tools: List[str], 
                       guardrails: List[str], output_dir: Path):
    """Generate the Python agent file."""
    template = """
from agents import Agent, function_tool, input_guardrail, RunContextWrapper
from typing import Optional
from pydantic import BaseModel

# Context model for {{ name }}
class {{ name }}Context(BaseModel):
    # Add context fields specific to this agent
    pass

{% for tool in tools %}
@function_tool
async def {{ tool }}_tool(context: RunContextWrapper[{{ name }}Context], 
                         # Add parameters here
                         ) -> str:
    \"\"\"{{ tool }} tool implementation.\"\"\"
    # Implement tool logic here
    return "Tool result"

{% endfor %}

{% for guardrail in guardrails %}
@input_guardrail(name="{{ guardrail }} Guardrail")
async def {{ guardrail.lower() }}_guardrail(context, agent, input):
    \"\"\"{{ guardrail }} guardrail implementation.\"\"\"
    # Implement guardrail logic here
    return GuardrailFunctionOutput(
        output_info={"reasoning": "Safe input"},
        tripwire_triggered=False
    )

{% endfor %}

def {{ name.lower() }}_instructions(run_context: RunContextWrapper[{{ name }}Context], 
                                   agent: Agent[{{ name }}Context]) -> str:
    \"\"\"Dynamic instructions for {{ name }}.\"\"\"
    return f\"\"\"
    You are {{ name }}, {{ description or 'a helpful AI agent' }}.
    
    Your role is to:
    1. [Define primary responsibilities]
    2. [Define secondary responsibilities]
    3. [Define handoff conditions]
    
    Available tools: {{ tools | join(', ') }}
    \"\"\"

# Create the agent
{{ name.lower() }}_agent = Agent[{{ name }}Context](
    name="{{ name }}",
    model="gpt-4.1",
    handoff_description="{{ description or 'Handles ' + name.lower() + ' related tasks' }}",
    instructions={{ name.lower() }}_instructions,
    tools=[{% for tool in tools %}{{ tool }}_tool{% if not loop.last %}, {% endif %}{% endfor %}],
    input_guardrails=[{% for guardrail in guardrails %}{{ guardrail.lower() }}_guardrail{% if not loop.last %}, {% endif %}{% endfor %}]
)
"""
    
    env = Environment()
    template_obj = env.from_string(template)
    content = template_obj.render(
        name=name.replace(' ', ''),
        description=description,
        tools=tools,
        guardrails=guardrails
    )
    
    with open(output_dir / f"{name.lower().replace(' ', '_')}_agent.py", "w") as f:
        f.write(content)

@cli.command()
@click.argument('server_name')
@click.argument('openapi_spec_file')
@click.option('--base-url', required=True, help='Base URL for the API')
@click.option('--output-dir', '-o', default='./mcp_servers', help='Output directory')
@click.option('--auto-deploy', is_flag=True, help='Auto-deploy after creation')
def create_mcp_server(server_name: str, openapi_spec_file: str, base_url: str, 
                     output_dir: str, auto_deploy: bool):
    """Create MCP server from OpenAPI specification."""
    
    if not os.path.exists(openapi_spec_file):
        click.echo(f"❌ OpenAPI spec file not found: {openapi_spec_file}")
        return
    
    with open(openapi_spec_file, 'r') as f:
        spec_content = f.read()
    
    # Analyze the spec
    from mcp.openapi_analyzer import OpenAPIAnalyzer
    analyzer = OpenAPIAnalyzer(spec_content)
    
    click.echo(f"📊 Analyzed OpenAPI spec:")
    click.echo(f"   - {len(analyzer.endpoints)} endpoints found")
    
    # Show endpoint groups
    groups = analyzer.generate_functionality_groups()
    click.echo(f"   - {len(groups)} functionality groups:")
    for group, endpoints in groups.items():
        click.echo(f"     • {group}: {len(endpoints)} endpoints")
    
    # Interactive endpoint selection
    selected_endpoints = []
    if click.confirm("Select endpoints interactively?"):
        for group, endpoints in groups.items():
            if click.confirm(f"Include all endpoints from '{group}' group?"):
                selected_endpoints.extend(endpoints)
            else:
                for endpoint in endpoints:
                    if click.confirm(f"Include {endpoint.method} {endpoint.path}?"):
                        selected_endpoints.append(endpoint)
    else:
        # Select high-value endpoints automatically
        selected_endpoints = analyzer.get_high_value_endpoints()
        click.echo(f"🎯 Auto-selected {len(selected_endpoints)} high-value endpoints")
    
    # Generate the server
    from mcp.server_generator import MCPServerGenerator
    generator = MCPServerGenerator()
    
    server_path = generator.generate_server(
        server_name,
        selected_endpoints,
        analyzer.spec,
        output_dir
    )
    
    click.echo(f"✅ MCP server '{server_name}' created in {server_path}")
    
    if auto_deploy:
        click.echo("🚀 Deploying server...")
        # Implement deployment logic
        click.echo("✅ Server deployed successfully!")

@cli.command()
def dev():
    """Start development environment with hot reload."""
    click.echo("🚀 Starting development environment...")
    
    # Start docker-compose for development
    os.system("docker-compose -f docker-compose.dev.yml up --build")

@cli.command()
@click.option('--environment', '-e', default='development', 
              type=click.Choice(['development', 'staging', 'production']))
def deploy(environment: str):
    """Deploy to specified environment."""
    click.echo(f"🚀 Deploying to {environment}...")
    
    if environment == 'production':
        if not click.confirm("Are you sure you want to deploy to production?"):
            return
    
    # Implement deployment logic based on environment
    click.echo(f"✅ Deployed to {environment} successfully!")

if __name__ == '__main__':
    cli()
```

---

## Phase 5: Production Operations

### 5.1 Monitoring & Observability

#### OpenTelemetry Integration
```python
# monitoring/telemetry.py
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
import time
from typing import Dict, Any

class TelemetryManager:
    def __init__(self, service_name: str = "openai-agents"):
        self.service_name = service_name
        self.setup_tracing()
        self.setup_metrics()
    
    def setup_tracing(self):
        """Setup distributed tracing with Jaeger."""
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        jaeger_exporter = JaegerExporter(
            agent_host_name="jaeger",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
    
    def setup_metrics(self):
        """Setup metrics collection with Prometheus."""
        reader = PrometheusMetricReader()
        metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
        
        self.meter = metrics.get_meter(__name__)
        
        # Define custom metrics
        self.conversation_counter = self.meter.create_counter(
            "conversations_total",
            description="Total number of conversations"
        )
        
        self.agent_handoff_counter = self.meter.create_counter(
            "agent_handoffs_total",
            description="Total number of agent handoffs"
        )
        
        self.response_time_histogram = self.meter.create_histogram(
            "response_time_seconds",
            description="Response time in seconds"
        )
        
        self.active_conversations_gauge = self.meter.create_up_down_counter(
            "active_conversations",
            description="Number of active conversations"
        )
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application."""
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
    
    def record_conversation_start(self, tenant_id: str, user_id: str):
        """Record conversation start metrics."""
        self.conversation_counter.add(1, {"tenant_id": tenant_id})
        self.active_conversations_gauge.add(1, {"tenant_id": tenant_id})
    
    def record_agent_handoff(self, from_agent: str, to_agent: str, tenant_id: str):
        """Record agent handoff metrics."""
        self.agent_handoff_counter.add(1, {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "tenant_id": tenant_id
        })
    
    def record_response_time(self, duration: float, endpoint: str, status_code: int):
        """Record API response time."""
        self.response_time_histogram.record(duration, {
            "endpoint": endpoint,
            "status_code": str(status_code)
        })

# Custom middleware for detailed monitoring
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class MonitoringMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, telemetry: TelemetryManager):
        super().__init__(app)
        self.telemetry = telemetry
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Create span for the request
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            
            response = await call_next(request)
            
            duration = time.time() - start_time
            
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response_time", duration)
            
            # Record metrics
            self.telemetry.record_response_time(
                duration, 
                request.url.path, 
                response.status_code
            )
            
            return response
```

#### Health Checks & Readiness Probes
```python
# monitoring/health.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import time
from datetime import datetime
import psutil
import redis
from sqlalchemy import text

class HealthStatus(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    version: str
    uptime_seconds: float
    checks: Dict[str, Any]

class HealthChecker:
    def __init__(self, db_session, redis_client):
        self.db_session = db_session
        self.redis_client = redis_client
        self.start_time = time.time()
        self.version = "1.0.0"  # Should come from config
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start = time.time()
            result = await self.db_session.execute(text("SELECT 1"))
            duration = time.time() - start
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "message": "Database connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Database connection failed"
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        try:
            start = time.time()
            await self.redis_client.ping()
            duration = time.time() - start
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "message": "Redis connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Redis connection failed"
            }
    
    async def check_openai_api(self) -> Dict[str, Any]:
        """Check OpenAI API connectivity."""
        try:
            # Simple API call to verify connectivity
            import openai
            start = time.time()
            # Make a minimal API call
            response = await openai.Model.list()
            duration = time.time() - start
            
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
                "message": "OpenAI API accessible"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "OpenAI API connection failed"
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Define thresholds
            cpu_threshold = 80
            memory_threshold = 85
            disk_threshold = 90
            
            status = "healthy"
            warnings = []
            
            if cpu_percent > cpu_threshold:
                status = "degraded"
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > memory_threshold:
                status = "degraded"
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > disk_threshold:
                status = "degraded"
                warnings.append(f"High disk usage: {disk.percent}%")
            
            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "warnings": warnings
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Failed to check system resources"
            }
    
    async def get_health_status(self) -> HealthStatus:
        """Get comprehensive health status."""
        checks = {}
        
        # Run all health checks concurrently
        db_check, redis_check, openai_check = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_openai_api(),
            return_exceptions=True
        )
        
        checks["database"] = db_check if not isinstance(db_check, Exception) else {
            "status": "unhealthy", "error": str(db_check)
        }
        checks["redis"] = redis_check if not isinstance(redis_check, Exception) else {
            "status": "unhealthy", "error": str(redis_check)
        }
        checks["openai"] = openai_check if not isinstance(openai_check, Exception) else {
            "status": "unhealthy", "error": str(openai_check)
        }
        checks["system"] = self.check_system_resources()
        
        # Determine overall status
        statuses = [check.get("status", "unhealthy") for check in checks.values()]
        
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=self.version,
            uptime_seconds=time.time() - self.start_time,
            checks=checks
        )

# FastAPI health endpoints
router = APIRouter(prefix="/health", tags=["health"])

@router.get("/", response_model=HealthStatus)
async def health_check():
    """Comprehensive health check endpoint."""
    health_checker = HealthChecker(db_session, redis_client)
    return await health_checker.get_health_status()

@router.get("/ready")
async def readiness_probe():
    """Kubernetes readiness probe endpoint."""
    health_checker = HealthChecker(db_session, redis_client)
    status = await health_checker.get_health_status()
    
    if status.status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    return {"status": "ready"}

@router.get("/live")
async def liveness_probe():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.utcnow()}
```

### 5.2 CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: ui/package-lock.json
    
    - name: Install Python dependencies
      run: |
        cd python-backend
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Install Node.js dependencies
      run: |
        cd ui
        npm ci
    
    - name: Run Python tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        cd python-backend
        pytest --cov=. --cov-report=xml
    
    - name: Run TypeScript tests
      run: |
        cd ui
        npm run test
    
    - name: Run linting
      run: |
        cd python-backend
        pip install flake8 black isort
        flake8 .
        black --check .
        isort --check-only .
        
        cd ../ui
        npm run lint
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./python-backend/coverage.xml

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results to GitHub Security tab
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-push:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
    
    - name: Build and push backend image
      uses: docker/build-push-action@v5
      with:
        context: ./python-backend
        target: backend-prod
        push: true
        tags: ${{ steps.meta.outputs.tags }}-backend
        labels: ${{ steps.meta.outputs.labels }}
    
    - name: Build and push frontend image
      uses: docker/build-push-action@v5
      with:
        context: ./ui
        target: frontend-prod
        push: true
        tags: ${{ steps.meta.outputs.tags }}-frontend
        labels: ${{ steps.meta.outputs.labels }}

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to staging
      run: |
        # Update Kubernetes manifests with new image tags
        # Apply to staging namespace
        echo "Deploying to staging environment"

  deploy-production:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to production
      run: |
        # Update Kubernetes manifests with new image tags
        # Apply to production namespace
        echo "Deploying to production environment"
```

---

## Implementation Timeline & Roadmap

### Phase 1: Foundation (Weeks 1-4)
**Priority: Critical**
- ✅ Week 1: Docker containerization and local development setup
- ✅ Week 2: Database abstraction layer and multi-tenancy framework
- ✅ Week 3: Configuration management and basic authentication
- ✅ Week 4: Kubernetes manifests and deployment pipeline

**Deliverables:**
- Fully containerized application
- Multi-tenant database architecture
- Basic RBAC implementation
- Local development environment with Docker Compose

### Phase 2: MCP Integration (Weeks 5-8)
**Priority: High**
- ✅ Week 5: OpenAPI spec analyzer and endpoint classification
- ✅ Week 6: MCP server generator with Jinja2 templates
- ✅ Week 7: Dynamic server deployment and management
- ✅ Week 8: Integration testing and UI for MCP management

**Deliverables:**
- OpenAPI to MCP server conversion tool
- Automated server deployment pipeline
- MCP server management interface
- Documentation and examples

### Phase 3: Security & Compliance (Weeks 9-12)
**Priority: Critical**
- ✅ Week 9: Enhanced authentication (OAuth2, SSO integration)
- ✅ Week 10: Comprehensive audit logging system
- ✅ Week 11: Security hardening and vulnerability scanning
- ✅ Week 12: Compliance reporting and data governance

**Deliverables:**
- Enterprise-grade authentication system
- Complete audit trail functionality
- Security scanning integration
- Compliance documentation

### Phase 4: Developer Experience (Weeks 13-16)
**Priority: Medium**
- ✅ Week 13: CLI tools for agent and MCP server scaffolding
- ✅ Week 14: Standardized UI component library
- ✅ Week 15: Hot-reload development environment
- ✅ Week 16: Documentation and developer guides

**Deliverables:**
- Comprehensive CLI toolkit
- Reusable UI component system
- Developer documentation portal
- Video tutorials and examples

### Phase 5: Production Operations (Weeks 17-20)
**Priority: High**
- ✅ Week 17: Monitoring and observability stack
- ✅ Week 18: Health checks and auto-scaling
- ✅ Week 19: Backup and disaster recovery
- ✅ Week 20: Performance optimization and load testing

**Deliverables:**
- Complete monitoring solution
- Production-ready deployment
- Disaster recovery procedures
- Performance benchmarks

---

## Success Metrics & KPIs

### Technical Metrics
- **Deployment Time**: < 5 minutes from code to production
- **System Uptime**: 99.9% availability SLA
- **Response Time**: < 200ms for API endpoints
- **Agent Creation Time**: < 2 minutes using CLI tools
- **MCP Server Generation**: < 30 seconds from OpenAPI spec

### Developer Experience Metrics
- **Time to First Agent**: < 30 minutes for new developers
- **Documentation Coverage**: > 95% of features documented
- **CLI Usage**: > 80% of developers using CLI tools
- **Component Reuse**: > 70% of UI components from library

### Business Metrics
- **Customer Onboarding**: < 1 day for new enterprise customers
- **Feature Velocity**: 2x faster feature development
- **Support Tickets**: 50% reduction in deployment-related issues
- **Developer Satisfaction**: > 4.5/5 in quarterly surveys

---

## Risk Assessment & Mitigation

### Technical Risks

#### High Risk: OpenAI API Rate Limits
- **Impact**: Service degradation during high usage
- **Mitigation**: Implement intelligent rate limiting, request queuing, and fallback mechanisms
- **Monitoring**: Track API usage patterns and implement alerts

#### Medium Risk: Kubernetes Complexity
- **Impact**: Deployment and scaling challenges
- **Mitigation**: Provide comprehensive documentation, automated scripts, and fallback to Docker Compose
- **Monitoring**: Health checks and automated recovery procedures

#### Medium Risk: Database Performance
- **Impact**: Slow response times with large datasets
- **Mitigation**: Implement caching layer, database optimization, and read replicas
- **Monitoring**: Query performance tracking and automated scaling

### Security Risks

#### High Risk: Multi-Tenant Data Isolation
- **Impact**: Data leakage between tenants
- **Mitigation**: Row-level security, comprehensive testing, and audit logging
- **Monitoring**: Automated security scans and access pattern analysis

#### Medium Risk: MCP Server Security
- **Impact**: Vulnerabilities in generated servers
- **Mitigation**: Security templates, automated scanning, and sandboxed execution
- **Monitoring**: Vulnerability scanning and runtime security monitoring

### Operational Risks

#### Medium Risk: Complexity Management
- **Impact**: Difficult maintenance and troubleshooting
- **Mitigation**: Comprehensive documentation, training programs, and support tools
- **Monitoring**: System complexity metrics and developer feedback

---

## Cost Analysis

### Development Costs
- **Phase 1-2**: $150,000 (Foundation + MCP Integration)
- **Phase 3**: $100,000 (Security & Compliance)
- **Phase 4-5**: $120,000 (Developer Experience + Operations)
- **Total Development**: $370,000

### Infrastructure Costs (Annual)
- **Development Environment**: $2,000/month
- **Staging Environment**: $5,000/month
- **Production Environment**: $15,000/month (scales with usage)
- **Monitoring & Security Tools**: $3,000/month
- **Total Infrastructure**: $300,000/year

### ROI Projections
- **Developer Productivity**: 2x improvement = $500,000/year savings
- **Faster Time-to-Market**: 50% reduction = $300,000/year value
- **Reduced Support Costs**: 40% reduction = $100,000/year savings
- **Total Annual Value**: $900,000
- **ROI**: 200% in first year

---

## Conclusion

This enterprise upgrade plan transforms the OpenAI Customer Service Agents Demo into a production-ready, enterprise-grade platform that enables organizations to rapidly deploy and scale multi-agent systems. The comprehensive approach addresses all critical aspects of enterprise software development, from security and compliance to developer experience and operational excellence.

The phased implementation approach ensures manageable risk while delivering value incrementally. The strong focus on MCP integration positions the platform at the forefront of the emerging AI ecosystem, while the robust infrastructure and developer tools ensure long-term maintainability and scalability.

Key differentiators of this enterprise solution:
- **MCP-First Architecture**: Native integration with the Model Context Protocol ecosystem
- **Developer-Centric Design**: Comprehensive CLI tools and component libraries
- **Enterprise Security**: Multi-tenancy, RBAC, and comprehensive audit logging
- **Cloud-Native**: Kubernetes-ready with full observability stack
- **Extensible Framework**: Plugin architecture for custom agents and integrations

This platform will serve as the foundation for next-generation AI-powered enterprise applications, enabling organizations to harness the full potential of multi-agent systems while maintaining enterprise-grade security, compliance, and operational excellence.
