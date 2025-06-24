# Technical Context

## Technology Stack

### Backend (Python)
- **Framework**: FastAPI - Modern, fast web framework for building APIs
- **AI/ML**: OpenAI Agents SDK - Official SDK for building multi-agent systems
- **Data Validation**: Pydantic - Data validation using Python type annotations
- **Server**: Uvicorn - ASGI server for running FastAPI applications
- **Environment**: python-dotenv - Environment variable management
- **Python Version**: Python 3.x (compatible with OpenAI Agents SDK)

### Frontend (Next.js/React)
- **Framework**: Next.js 15.2.4 - React framework with server-side rendering
- **Language**: TypeScript - Type-safe JavaScript
- **Styling**: Tailwind CSS 3.4.17 - Utility-first CSS framework
- **UI Components**:
  - Radix UI - Accessible component primitives
  - Lucide React - Icon library
  - Custom UI components in `ui/components/ui/`
- **State Management**: React hooks (useState, useEffect)
- **HTTP Client**: Fetch API for backend communication

### Development Tools
- **Process Management**: Concurrently - Run multiple npm scripts simultaneously
- **Code Quality**: ESLint, TypeScript compiler
- **Package Management**: npm (frontend), pip (backend)

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

### Current Security (Demo Level)
- CORS restricted to localhost
- No authentication required
- Environment variable for API key
- Input validation via Pydantic

### Production Security Needs
- Authentication/authorization system
- Rate limiting
- Input sanitization
- Secure API key management
- HTTPS enforcement
- Database security (when replacing in-memory storage)

## Deployment Considerations

### Development Deployment
- Local development server setup
- Hot reloading enabled
- Debug logging active

### Production Deployment Needs
- Replace in-memory storage with persistent database
- Configure production CORS settings
- Set up proper logging and monitoring
- Implement authentication
- Configure environment variables securely
- Set up CI/CD pipeline
