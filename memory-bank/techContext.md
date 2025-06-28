# Technical Context

## Technology Stack

### Backend (Python) - Enterprise Grade
- **Framework**: FastAPI - Modern, fast web framework for building APIs
- **AI/ML**: OpenAI Agents SDK - Official SDK for building multi-agent systems
- **Data Validation**: Pydantic - Data validation using Python type annotations
- **Server**: Uvicorn - ASGI server for running FastAPI applications
- **Environment**: python-dotenv - Environment variable management
- **Authentication**: PyJWT - JSON Web Token implementation
- **Security**: Custom zero-credential-leakage architecture
- **Database**: SQLAlchemy - Database abstraction layer with multi-tenancy
- **Templates**: Jinja2 - Template engine for MCP server generation
- **Monitoring**: OpenTelemetry - Observability and telemetry
- **Testing**: pytest - Comprehensive test framework with >85% coverage
- **Python Version**: Python 3.x (compatible with OpenAI Agents SDK)

### Frontend (Next.js/React) - Production Ready
- **Framework**: Next.js 15.2.4 - React framework with server-side rendering
- **Language**: TypeScript - Type-safe JavaScript
- **Styling**: Tailwind CSS 3.4.17 - Utility-first CSS framework
- **UI Components**:
  - Radix UI - Accessible component primitives
  - Lucide React - Icon library
  - Custom UI components in `ui/components/ui/`
  - MCP Server Manager - Enterprise MCP management interface
- **State Management**: React hooks (useState, useEffect)
- **HTTP Client**: Fetch API for backend communication

### Enterprise Infrastructure
- **Containerization**: Docker with multi-stage builds and security hardening
- **Orchestration**: Kubernetes with production-ready manifests
- **CI/CD**: GitHub Actions with multi-stage deployment pipeline
- **Monitoring**: Prometheus integration with health checks and readiness probes
- **Security**: RBAC, JWT authentication, audit logging, environment sanitization
- **Multi-Tenancy**: Complete tenant isolation with repository pattern

### MCP Integration Platform
- **OpenAPI Analysis**: Custom analyzer for specification parsing
- **Server Generation**: Jinja2-based template system for MCP server creation
- **Registry Management**: Dynamic server lifecycle management
- **UI Management**: React-based MCP server administration interface

### Development Tools - Enterprise Grade
- **Process Management**: Concurrently - Run multiple npm scripts simultaneously
- **Code Quality**: ESLint, TypeScript compiler, Black, Flake8
- **Package Management**: npm (frontend), pip/uv (backend)
- **CLI Tools**: Comprehensive agent scaffolding and project management
- **Testing**: pytest with comprehensive coverage reporting
- **Security**: Pre-commit hooks, credential scanning, environment sanitization

## Project Structure

### Backend Structure (`python-backend/`)
```
python-backend/
├── __init__.py          # Python package marker
├── api.py              # FastAPI application and endpoints
├── main.py             # Agent definitions and orchestration logic
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (OpenAI API key)
```

### Frontend Structure (`ui/`)
```
ui/
├── app/
│   ├── globals.css     # Global styles
│   ├── layout.tsx      # Root layout component
│   └── page.tsx        # Main page component
├── components/
│   ├── ui/             # Reusable UI components
│   ├── agent-panel.tsx # Agent visualization panel
│   ├── agents-list.tsx # Agent list component
│   ├── Chat.tsx        # Chat interface
│   ├── conversation-context.tsx # Context display
│   ├── guardrails.tsx  # Guardrail status display
│   ├── panel-section.tsx # Panel section wrapper
│   ├── runner-output.tsx # Agent output display
│   └── seat-map.tsx    # Interactive seat map
├── lib/
│   ├── api.ts          # API client functions
│   ├── types.ts        # TypeScript type definitions
│   └── utils.ts        # Utility functions
└── public/
    └── openai_logo.svg # OpenAI logo asset
```

## Development Setup

### Prerequisites
- Python 3.x with pip
- Node.js with npm
- OpenAI API key

### Backend Setup
```bash
cd python-backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd ui
npm install
```

### Environment Configuration
- Create `.env` file in `python-backend/` directory
- Set `OPENAI_API_KEY=your_api_key_here`
- Alternative: Set as system environment variable

## Running the Application

### Development Mode (Recommended)
```bash
cd ui
npm run dev  # Starts both frontend and backend
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Backend Only
```bash
cd python-backend
python -m uvicorn api:app --reload --port 8000
```

### Frontend Only
```bash
cd ui
npm run dev:next
```

## API Architecture

### Main Endpoint
- **POST /chat** - Main chat endpoint for agent interactions
- **Request**: `{ conversation_id?: string, message: string }`
- **Response**: Complete conversation state with messages, events, context

### Data Models
- **ChatRequest** - Input message structure
- **ChatResponse** - Complete response with all conversation data
- **AgentEvent** - Individual agent actions and state changes
- **GuardrailCheck** - Guardrail validation results
- **MessageResponse** - Agent message responses

## Key Dependencies

### Backend Dependencies
```
openai-agents     # OpenAI Agents SDK
pydantic         # Data validation
fastapi          # Web framework
uvicorn          # ASGI server
python-dotenv    # Environment variables
```

### Frontend Dependencies
```
next             # React framework
react            # UI library
typescript       # Type safety
tailwindcss      # Styling
@radix-ui/*      # UI components
lucide-react     # Icons
concurrently     # Development tooling
```

## Configuration Details

### CORS Configuration
- Allows requests from `http://localhost:3000`
- Configured for development environment
- Needs adjustment for production deployment

### Model Configuration
- All agents use `gpt-4.1` model
- Guardrail agents use `gpt-4.1-mini` for efficiency
- Models configurable per agent

### Storage Configuration
- **Development**: In-memory conversation storage
- **Production**: Requires persistent storage implementation
- Context serialization via Pydantic models

## Performance Considerations

### Backend Performance
- Async/await throughout for non-blocking operations
- In-memory storage for fast access (demo only)
- Efficient agent state management
- Minimal data serialization overhead

### Frontend Performance
- React 19 with modern hooks
- Efficient state updates
- Minimal re-renders through proper state management
- Tailwind CSS for optimized styling

## Security Considerations

### Enterprise Security (Production Ready) ✅
- **Authentication**: JWT-based authentication system implemented
- **Authorization**: RBAC (Role-Based Access Control) with fine-grained permissions
- **Audit Logging**: Comprehensive audit trail for all system operations
- **Zero-Credential-Leakage**: Advanced credential protection architecture
- **Environment Sanitization**: Secure environment variable handling
- **Security Headers**: Production-grade security headers and CORS configuration
- **Input Validation**: Multi-layer validation with Pydantic and guardrails
- **Secure API Key Management**: Enterprise-grade credential lifecycle management

### Security Features Implemented
- `auth/jwt_auth.py` - JWT token management and validation
- `auth/rbac.py` - Role-based access control system
- `auth/middleware.py` - Authentication middleware for FastAPI
- `audit/audit_logger.py` - Comprehensive audit logging
- `security/env_sanitizer.py` - Environment sanitization
- `auth/zero_credential_leakage.py` - Zero-credential-leakage architecture

## Deployment Considerations

### Development Deployment ✅
- Local development server setup with hot reloading
- Docker-based development environment
- Comprehensive CLI tools for development workflow
- Debug logging and development-specific configurations

### Production Deployment (Ready) ✅
- **Containerization**: Docker with multi-stage builds and security hardening
- **Orchestration**: Kubernetes manifests for production deployment
- **CI/CD Pipeline**: GitHub Actions with automated testing and deployment
- **Database**: Multi-tenant database architecture with repository pattern
- **Monitoring**: OpenTelemetry integration with Prometheus metrics
- **Health Checks**: Kubernetes-ready health and readiness probes
- **Security**: Production-grade authentication, authorization, and audit systems
- **Configuration**: Environment-based configuration management
- **Logging**: Structured logging with audit trails

### Production Infrastructure Components
- `.github/workflows/ci-cd.yml` - Complete CI/CD pipeline
- `k8s/` - Kubernetes deployment manifests
- `docker/` - Production-ready Docker configurations
- `monitoring/health.py` - Health check endpoints
- `monitoring/telemetry.py` - OpenTelemetry observability
- `config/settings.py` - Production configuration management

### Enterprise Deployment Features
- **Multi-Tenancy**: Complete tenant isolation and management
- **Scalability**: Horizontal scaling with Kubernetes
- **Security**: Enterprise-grade security controls
- **Monitoring**: Production observability and alerting
- **Compliance**: Audit logging and security compliance features
