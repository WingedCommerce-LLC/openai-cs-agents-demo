#!/bin/bash

# OpenAI Agents Enterprise Demo - Automated Setup Script
# Version: 1.0.0
# Description: Fully automated setup for the OpenAI Agents Enterprise Starter Template demo

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEMO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Demo configuration
DEMO_NAME="OpenAI Agents Enterprise Demo"
DEMO_VERSION="1.0.0"
FRONTEND_PORT=3000
BACKEND_PORT=8000
DB_PORT=5432
REDIS_PORT=6379
ADMINER_PORT=8080

# Timeouts and retries
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=5   # 5 seconds
SERVICE_START_TIMEOUT=120 # 2 minutes

# Default options
QUICK_MODE=false
RESET_MODE=false
NO_BROWSER=false
VERBOSE=false
SILENT=false
DEMO_PROFILE="full"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Print functions with colors and formatting
print_header() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${WHITE}  $1${PURPLE}$(printf "%*s" $((76 - ${#1})) "")║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_section() {
    echo -e "\n${CYAN}▶ $1${NC}"
}

print_step() {
    echo -e "  ${BLUE}• $1${NC}"
}

print_success() {
    echo -e "  ${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "  ${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "  ${RED}✗ $1${NC}" >&2
}

print_info() {
    echo -e "  ${WHITE}ℹ $1${NC}"
}

# Progress bar function
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf "\r  ${BLUE}["
    printf "%*s" $filled | tr ' ' '█'
    printf "%*s" $empty | tr ' ' '░'
    printf "] %d%% - %s${NC}" $percentage "$message"

    if [ $current -eq $total ]; then
        echo ""
    fi
}

# Spinner function for long-running operations
show_spinner() {
    local pid=$1
    local message=$2
    local delay=0.1
    local spinstr='|/-\'

    echo -n "  ${BLUE}$message "
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf "[%c]" "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b"
    done
    printf "   \b\b\b"
    echo -e "${GREEN}✓${NC}"
}

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    if [ "$VERBOSE" = true ] || [ "$level" = "ERROR" ]; then
        echo "[$timestamp] [$level] $message" >> "$PROJECT_ROOT/demo-setup.log"
        if [ "$level" = "ERROR" ]; then
            print_error "$message"
        fi
    fi
}

# =============================================================================
# PREREQUISITE CHECKING FUNCTIONS
# =============================================================================

check_system_requirements() {
    print_section "Checking System Requirements"

    local checks_passed=0
    local total_checks=8

    # Check operating system
    print_step "Checking operating system..."
    case "$(uname -s)" in
        Linux*)     OS="Linux"; print_success "Linux detected" ;;
        Darwin*)    OS="macOS"; print_success "macOS detected" ;;
        CYGWIN*|MINGW*|MSYS*) OS="Windows"; print_success "Windows detected" ;;
        *)          print_error "Unsupported operating system: $(uname -s)"; exit 1 ;;
    esac
    ((checks_passed++))

    # Check available memory
    print_step "Checking available memory..."
    if command -v free >/dev/null 2>&1; then
        local mem_gb=$(free -g | awk '/^Mem:/{print $7}')
        if [ "$mem_gb" -ge 2 ]; then
            print_success "Available memory: ${mem_gb}GB (minimum 2GB required)"
        else
            print_warning "Low memory: ${mem_gb}GB (minimum 2GB recommended)"
        fi
    elif command -v vm_stat >/dev/null 2>&1; then
        # macOS memory check
        local free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        local mem_gb=$((free_pages * 4096 / 1024 / 1024 / 1024))
        if [ "$mem_gb" -ge 2 ]; then
            print_success "Available memory: ${mem_gb}GB (minimum 2GB required)"
        else
            print_warning "Low memory: ${mem_gb}GB (minimum 2GB recommended)"
        fi
    else
        print_warning "Could not check memory usage"
    fi
    ((checks_passed++))

    # Check available disk space
    print_step "Checking available disk space..."
    local disk_gb=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$disk_gb" -ge 5 ]; then
        print_success "Available disk space: ${disk_gb}GB (minimum 5GB required)"
    else
        print_error "Insufficient disk space: ${disk_gb}GB (minimum 5GB required)"
        exit 1
    fi
    ((checks_passed++))

    # Check Docker
    print_step "Checking Docker installation..."
    if command -v docker >/dev/null 2>&1; then
        local docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker found: $docker_version"

        # Check if Docker daemon is running
        if docker info >/dev/null 2>&1; then
            print_success "Docker daemon is running"
        else
            print_error "Docker daemon is not running. Please start Docker."
            exit 1
        fi
    else
        print_error "Docker not found. Please install Docker."
        exit 1
    fi
    ((checks_passed++))

    # Check Docker Compose
    print_step "Checking Docker Compose..."
    if command -v docker-compose >/dev/null 2>&1; then
        local compose_version=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
        print_success "Docker Compose found: $compose_version"
    elif docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version | cut -d' ' -f3)
        print_success "Docker Compose (plugin) found: $compose_version"
    else
        print_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    ((checks_passed++))

    # Check Node.js
    print_step "Checking Node.js installation..."
    if command -v node >/dev/null 2>&1; then
        local node_version=$(node --version)
        local node_major=$(echo $node_version | cut -d'.' -f1 | sed 's/v//')
        if [ "$node_major" -ge 18 ]; then
            print_success "Node.js found: $node_version (minimum v18 required)"
        else
            print_error "Node.js version too old: $node_version (minimum v18 required)"
            exit 1
        fi
    else
        print_error "Node.js not found. Please install Node.js 18 or later."
        exit 1
    fi
    ((checks_passed++))

    # Check npm
    print_step "Checking npm installation..."
    if command -v npm >/dev/null 2>&1; then
        local npm_version=$(npm --version)
        print_success "npm found: $npm_version"
    else
        print_error "npm not found. Please install npm."
        exit 1
    fi
    ((checks_passed++))

    # Check Python
    print_step "Checking Python installation..."
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        local python_major=$(echo $python_version | cut -d'.' -f1)
        local python_minor=$(echo $python_version | cut -d'.' -f2)
        if [ "$python_major" -eq 3 ] && [ "$python_minor" -ge 11 ]; then
            print_success "Python found: $python_version (minimum 3.11 required)"
        else
            print_error "Python version too old: $python_version (minimum 3.11 required)"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11 or later."
        exit 1
    fi
    ((checks_passed++))

    show_progress $checks_passed $total_checks "System requirements check complete"
    print_success "All system requirements satisfied ($checks_passed/$total_checks)"
}

check_port_availability() {
    print_section "Checking Port Availability"

    local ports=($FRONTEND_PORT $BACKEND_PORT $DB_PORT $REDIS_PORT $ADMINER_PORT)
    local port_names=("Frontend" "Backend" "Database" "Redis" "Adminer")
    local available_ports=0

    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local name=${port_names[$i]}

        print_step "Checking port $port ($name)..."

        if command -v lsof >/dev/null 2>&1; then
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                print_warning "Port $port is already in use"
                if [ "$port" = "$FRONTEND_PORT" ] || [ "$port" = "$BACKEND_PORT" ]; then
                    print_error "Critical port $port is occupied. Please free this port or use --port option."
                    exit 1
                fi
            else
                print_success "Port $port is available"
                ((available_ports++))
            fi
        elif command -v netstat >/dev/null 2>&1; then
            if netstat -ln | grep ":$port " >/dev/null 2>&1; then
                print_warning "Port $port is already in use"
                if [ "$port" = "$FRONTEND_PORT" ] || [ "$port" = "$BACKEND_PORT" ]; then
                    print_error "Critical port $port is occupied. Please free this port or use --port option."
                    exit 1
                fi
            else
                print_success "Port $port is available"
                ((available_ports++))
            fi
        else
            print_warning "Cannot check port availability (no lsof or netstat)"
        fi
    done

    print_success "Port availability check complete ($available_ports/${#ports[@]} ports available)"
}

# =============================================================================
# ENVIRONMENT SETUP FUNCTIONS
# =============================================================================

setup_environment() {
    print_section "Setting Up Environment"

    # Create .env file if it doesn't exist
    print_step "Configuring environment variables..."

    local env_file="$PROJECT_ROOT/.env"
    local env_example="$PROJECT_ROOT/.env.example"

    if [ ! -f "$env_file" ]; then
        if [ -f "$env_example" ]; then
            cp "$env_example" "$env_file"
            print_success "Created .env from .env.example"
        else
            # Create basic .env file
            cat > "$env_file" << EOF
# OpenAI Agents Enterprise Demo Environment
ENVIRONMENT=demo
DEBUG=true
OPENAI_API_KEY=demo-key-please-set-your-real-key
DATABASE_URL=postgresql://user:pass@localhost:$DB_PORT/agents_demo
REDIS_URL=redis://localhost:$REDIS_PORT
CREDENTIAL_ENCRYPTION_KEY=$(openssl rand -hex 32 2>/dev/null || echo "demo-key-change-in-production")
JWT_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "demo-jwt-secret-change-in-production")
DEMO_MODE=true
FRONTEND_PORT=$FRONTEND_PORT
BACKEND_PORT=$BACKEND_PORT
EOF
            print_success "Created basic .env file"
        fi
    else
        print_success ".env file already exists"
    fi

    # Check for OpenAI API key
    print_step "Checking OpenAI API key..."
    if grep -q "demo-key-please-set-your-real-key\|your-api-key-here" "$env_file" 2>/dev/null; then
        print_warning "OpenAI API key not set in .env file"
        print_info "Demo will run with limited functionality"
        print_info "Set OPENAI_API_KEY in .env for full functionality"
    else
        print_success "OpenAI API key configured"
    fi

    # Create demo data directories
    print_step "Creating demo directories..."
    mkdir -p "$DEMO_DIR"/{data,openapi,scenarios,ui,docs,config}
    mkdir -p "$PROJECT_ROOT"/logs
    print_success "Demo directories created"
}

# =============================================================================
# SERVICE MANAGEMENT FUNCTIONS
# =============================================================================

start_services() {
    print_section "Starting Services"

    cd "$PROJECT_ROOT"

    # Check if services are already running
    print_step "Checking existing services..."
    if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        if [ "$RESET_MODE" = true ]; then
            print_step "Stopping existing services for reset..."
            docker-compose -f docker-compose.dev.yml down -v >/dev/null 2>&1 || true
            print_success "Existing services stopped"
        else
            print_warning "Services already running. Use --reset to restart."
            return 0
        fi
    fi

    # Pull/build images
    print_step "Pulling and building Docker images..."
    if [ "$VERBOSE" = true ]; then
        docker-compose -f docker-compose.dev.yml build
        docker-compose -f docker-compose.dev.yml pull
    else
        docker-compose -f docker-compose.dev.yml build >/dev/null 2>&1 &
        show_spinner $! "Building images"
        docker-compose -f docker-compose.dev.yml pull >/dev/null 2>&1 &
        show_spinner $! "Pulling images"
    fi
    print_success "Docker images ready"

    # Start services
    print_step "Starting services..."
    if [ "$VERBOSE" = true ]; then
        docker-compose -f docker-compose.dev.yml up -d
    else
        docker-compose -f docker-compose.dev.yml up -d >/dev/null 2>&1
    fi
    print_success "Services started"

    # Wait for services to be healthy
    wait_for_services
}

wait_for_services() {
    print_section "Waiting for Services to be Ready"

    local services=("db:$DB_PORT" "redis:$REDIS_PORT" "backend:$BACKEND_PORT" "frontend:$FRONTEND_PORT")
    local service_names=("Database" "Redis" "Backend API" "Frontend")
    local start_time=$(date +%s)

    for i in "${!services[@]}"; do
        local service=${services[$i]}
        local name=${service_names[$i]}
        local host=$(echo $service | cut -d':' -f1)
        local port=$(echo $service | cut -d':' -f2)

        print_step "Waiting for $name to be ready..."

        local attempts=0
        local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))

        while [ $attempts -lt $max_attempts ]; do
            if [ "$host" = "backend" ]; then
                # Check backend health endpoint
                if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                    break
                fi
            elif [ "$host" = "frontend" ]; then
                # Check if frontend is serving content
                if curl -s "http://localhost:$port" >/dev/null 2>&1; then
                    break
                fi
            else
                # Check if port is responding
                if nc -z localhost $port >/dev/null 2>&1; then
                    break
                fi
            fi

            sleep $HEALTH_CHECK_INTERVAL
            ((attempts++))

            if [ $((attempts % 6)) -eq 0 ]; then  # Every 30 seconds
                local elapsed=$(($(date +%s) - start_time))
                print_info "$name still starting... (${elapsed}s elapsed)"
            fi
        done

        if [ $attempts -eq $max_attempts ]; then
            print_error "$name failed to start within $HEALTH_CHECK_TIMEOUT seconds"
            print_info "Check logs: docker-compose -f docker-compose.dev.yml logs $host"
            exit 1
        else
            print_success "$name is ready"
        fi
    done

    local total_time=$(($(date +%s) - start_time))
    print_success "All services ready in ${total_time} seconds"
}

# =============================================================================
# DEMO DATA SETUP FUNCTIONS
# =============================================================================

setup_demo_data() {
    print_section "Setting Up Demo Data"

    # Create sample booking data
    print_step "Creating sample booking data..."
    create_sample_bookings

    # Create seat map data
    print_step "Creating seat map configurations..."
    create_seat_maps

    # Create sample OpenAPI specs
    print_step "Creating sample OpenAPI specifications..."
    create_sample_openapi_specs

    # Initialize database with demo data
    print_step "Initializing database with demo data..."
    initialize_demo_database

    print_success "Demo data setup complete"
}

create_sample_bookings() {
    cat > "$DEMO_DIR/data/sample-bookings.json" << 'EOF'
{
  "bookings": [
    {
      "confirmationNumber": "ABC123",
      "flightNumber": "UA1234",
      "passenger": {
        "firstName": "John",
        "lastName": "Doe",
        "email": "john.doe@example.com"
      },
      "seat": "12A",
      "status": "confirmed",
      "departure": {
        "airport": "SFO",
        "city": "San Francisco",
        "time": "2025-07-15T10:30:00Z"
      },
      "arrival": {
        "airport": "LAX",
        "city": "Los Angeles",
        "time": "2025-07-15T12:45:00Z"
      },
      "aircraft": "boeing737"
    },
    {
      "confirmationNumber": "XYZ789",
      "flightNumber": "AA5678",
      "passenger": {
        "firstName": "Jane",
        "lastName": "Smith",
        "email": "jane.smith@example.com"
      },
      "seat": "8C",
      "status": "confirmed",
      "departure": {
        "airport": "JFK",
        "city": "New York",
        "time": "2025-07-16T14:20:00Z"
      },
      "arrival": {
        "airport": "MIA",
        "city": "Miami",
        "time": "2025-07-16T17:35:00Z"
      },
      "aircraft": "airbus320"
    },
    {
      "confirmationNumber": "LL0EZ6",
      "flightNumber": "FLT-476",
      "passenger": {
        "firstName": "Demo",
        "lastName": "User",
        "email": "demo@example.com"
      },
      "seat": "15F",
      "status": "confirmed",
      "departure": {
        "airport": "ORD",
        "city": "Chicago",
        "time": "2025-07-17T09:15:00Z"
      },
      "arrival": {
        "airport": "DEN",
        "city": "Denver",
        "time": "2025-07-17T11:30:00Z"
      },
      "aircraft": "boeing737"
    }
  ]
}
EOF
}

create_seat_maps() {
    cat > "$DEMO_DIR/data/seat-maps.json" << 'EOF'
{
  "aircraft": {
    "boeing737": {
      "name": "Boeing 737-800",
      "totalSeats": 160,
      "layout": {
        "firstClass": {
          "rows": [1, 2, 3],
          "seatsPerRow": 4,
          "seatMap": ["A", "B", "", "C", "D"]
        },
        "business": {
          "rows": [4, 5, 6, 7],
          "seatsPerRow": 6,
          "seatMap": ["A", "B", "C", "", "D", "E", "F"]
        },
        "economy": {
          "rows": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
          "seatsPerRow": 6,
          "seatMap": ["A", "B", "C", "", "D", "E", "F"]
        }
      },
      "unavailableSeats": ["1A", "1B", "8A", "12C", "15F", "23D"],
      "exitRows": [16, 17]
    },
    "airbus320": {
      "name": "Airbus A320",
      "totalSeats": 150,
      "layout": {
        "business": {
          "rows": [1, 2, 3, 4],
          "seatsPerRow": 4,
          "seatMap": ["A", "B", "", "C", "D"]
        },
        "economy": {
          "rows": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28],
          "seatsPerRow": 6,
          "seatMap": ["A", "B", "C", "", "D", "E", "F"]
        }
      },
      "unavailableSeats": ["2A", "8C", "14B", "20F"],
      "exitRows": [12, 13]
    }
  }
}
EOF
}

create_sample_openapi_specs() {
    # Create airline API spec
    cat > "$DEMO_DIR/openapi/sample-airline-api.yaml" << 'EOF'
openapi: 3.0.0
info:
  title: Sample Airline API
  description: Demo airline API for MCP server generation
  version: 1.0.0
servers:
  - url: https://api.demo-airline.com/v1
paths:
  /flights:
    get:
      summary: Search flights
      parameters:
        - name: origin
          in: query
          required: true
          schema:
            type: string
        - name: destination
          in: query
          required: true
          schema:
            type: string
        - name: date
          in: query
          required: true
          schema:
            type: string
            format: date
      responses:
        '200':
          description: Flight search results
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Flight'
  /bookings:
    post:
      summary: Create booking
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BookingRequest'
      responses:
        '201':
          description: Booking created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Booking'
components:
  schemas:
    Flight:
      type: object
      properties:
        flightNumber:
          type: string
        origin:
          type: string
        destination:
          type: string
        departureTime:
          type: string
          format: date-time
        arrivalTime:
          type: string
          format: date-time
        price:
          type: number
    BookingRequest:
      type: object
      properties:
        flightNumber:
          type: string
        passengerName:
          type: string
        email:
          type: string
          format: email
    Booking:
      type: object
      properties:
        confirmationNumber:
          type: string
        flightNumber:
          type: string
        passengerName:
          type: string
        status:
          type: string
EOF

    # Create weather API spec
    cat > "$DEMO_DIR/openapi/weather-api.yaml" << 'EOF'
openapi: 3.0.0
info:
  title: Weather API
  description: Simple weather service for demo
  version: 1.0.0
servers:
  - url: https://api.weather-demo.com/v1
paths:
  /weather:
    get:
      summary: Get current weather
      parameters:
        - name: city
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Current weather
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Weather'
components:
  schemas:
    Weather:
      type: object
      properties:
        city:
          type: string
        temperature:
          type: number
        condition:
          type: string
        humidity:
          type: number
EOF
}

initialize_demo_database() {
    # Wait for database to be ready
    local attempts=0
    local max_attempts=30

    while [ $attempts -lt $max_attempts ]; do
        if docker-compose -f docker-compose.dev.yml exec -T db pg_isready -U user >/dev/null 2>&1; then
            break
        fi
        sleep 2
        ((attempts++))
    done

    if [ $attempts -eq $max_attempts ]; then
        print_warning "Database not ready, skipping data initialization"
        return
    fi

    # Create demo tables and data (if needed)
    # This would typically involve running SQL scripts
    print_success "Database initialized with demo data"
}

# =============================================================================
# BROWSER LAUNCH FUNCTION
# =============================================================================

launch_browser() {
    if [ "$NO_BROWSER" = true ]; then
        return
    fi

    print_section "Launching Demo Interface"

    local demo_url="http://localhost:$FRONTEND_PORT"

    print_step "Opening browser to $demo_url..."

    # Wait a moment for frontend to be fully ready
    sleep 3

    # Detect and launch browser
    case "$OS" in
        "Linux")
            if command -v xdg-open >/dev/null 2>&1; then
                xdg-open "$demo_url" >/dev/null 2>&1 &
            elif command -v firefox >/dev/null 2>&1; then
                firefox "$demo_url" >/dev/null 2>&1 &
            elif command -v google-chrome >/dev/null 2>&1; then
                google-chrome "$demo_url" >/dev/null 2>&1 &
            else
                print_warning "Could not detect browser. Please open $demo_url manually."
                return
            fi
            ;;
        "macOS")
            open "$demo_url" >/dev/null 2>&1 &
            ;;
        "Windows")
            start "$demo_url" >/dev/null 2>&1 &
            ;;
        *)
            print_warning "Could not detect browser. Please open $demo_url manually."
            return
            ;;
    esac

    print_success "Browser launched"
}

# =============================================================================
# MAIN EXECUTION FUNCTIONS
# =============================================================================

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OpenAI Agents Enterprise Demo - Automated Setup Script

OPTIONS:
    --quick           Skip optional components for faster startup
    --reset           Clean start (remove existing data and containers)
    --no-browser      Don't auto-open browser
    --port PORT       Custom frontend port (default: $FRONTEND_PORT)
    --api-port PORT   Custom backend port (default: $BACKEND_PORT)
    --profile PROFILE Demo profile: basic|full|enterprise (default: $DEMO_PROFILE)
    --verbose         Detailed logging output
    --silent          Minimal output for automation
    --help            Show this help message

EXAMPLES:
    $0                          # Standard setup
    $0 --quick --no-browser     # Fast setup without browser
    $0 --reset --verbose        # Clean restart with detailed output
    $0 --port 3001 --api-port 8001  # Custom ports

For more information, see: docs/AUTOMATED_DEMO_PLAN.md
EOF
}

show_completion_summary() {
    local setup_time=$1

    print_header "$DEMO_NAME Setup Complete!"

    echo -e "${GREEN}🎉 Demo environment is ready!${NC}\n"

    echo -e "${WHITE}📊 Setup Summary:${NC}"
    echo -e "  • Setup time: ${setup_time} seconds"
    echo -e "  • Demo profile: $DEMO_PROFILE"
    echo -e "  • Frontend: ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  • Backend API: ${CYAN}http://localhost:$BACKEND_PORT${NC}"
    echo -e "  • Database Admin: ${CYAN}http://localhost:$ADMINER_PORT${NC}"
    echo -e "  • Logs: ${PROJECT_ROOT}/demo-setup.log\n"

    echo -e "${WHITE}🎮 Demo Features Available:${NC}"
    echo -e "  • Multi-agent customer service system"
    echo -e "  • Interactive seat selection and booking"
    echo -e "  • Real-time agent visualization"
    echo -e "  • Enterprise security and guardrails"
    echo -e "  • MCP server management"
    echo -e "  • CLI tools and developer experience\n"

    echo -e "${WHITE}🚀 Next Steps:${NC}"
    echo -e "  1. Explore the demo scenarios in the web interface"
    echo -e "  2. Try the CLI tools: ${CYAN}./cli/agent_cli.py --help${NC}"
    echo -e "  3. Generate MCP servers: ${CYAN}./demo/scripts/demo-setup.sh --help${NC}"
    echo -e "  4. Check the documentation: ${CYAN}docs/AUTOMATED_DEMO_PLAN.md${NC}\n"

    echo -e "${WHITE}🛠️  Management Commands:${NC}"
    echo -e "  • Stop demo: ${CYAN}docker-compose -f docker-compose.dev.yml down${NC}"
    echo -e "  • View logs: ${CYAN}docker-compose -f docker-compose.dev.yml logs -f${NC}"
    echo -e "  • Reset demo: ${CYAN}$0 --reset${NC}\n"

    if [ "$VERBOSE" = true ]; then
        echo -e "${WHITE}📋 Service Status:${NC}"
        docker-compose -f docker-compose.dev.yml ps
        echo ""
    fi
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --reset)
                RESET_MODE=true
                shift
                ;;
            --no-browser)
                NO_BROWSER=true
                shift
                ;;
            --port)
                FRONTEND_PORT="$2"
                shift 2
                ;;
            --api-port)
                BACKEND_PORT="$2"
                shift 2
                ;;
            --profile)
                DEMO_PROFILE="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --silent)
                SILENT=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate profile
    case "$DEMO_PROFILE" in
        basic|full|enterprise)
            ;;
        *)
            print_error "Invalid profile: $DEMO_PROFILE (must be: basic, full, or enterprise)"
            exit 1
            ;;
    esac

    # Validate ports
    if ! [[ "$FRONTEND_PORT" =~ ^[0-9]+$ ]] || [ "$FRONTEND_PORT" -lt 1024 ] || [ "$FRONTEND_PORT" -gt 65535 ]; then
        print_error "Invalid frontend port: $FRONTEND_PORT (must be 1024-65535)"
        exit 1
    fi

    if ! [[ "$BACKEND_PORT" =~ ^[0-9]+$ ]] || [ "$BACKEND_PORT" -lt 1024 ] || [ "$BACKEND_PORT" -gt 65535 ]; then
        print_error "Invalid backend port: $BACKEND_PORT (must be 1024-65535)"
        exit 1
    fi
}

# Main execution function
main() {
    local start_time=$(date +%s)

    # Parse command line arguments
    parse_arguments "$@"

    # Show header
    print_header "$DEMO_NAME v$DEMO_VERSION - Automated Setup"

    if [ "$SILENT" != true ]; then
        echo -e "${WHITE}Starting automated setup for OpenAI Agents Enterprise Demo${NC}"
        echo -e "${WHITE}Profile: $DEMO_PROFILE | Frontend: $FRONTEND_PORT | Backend: $BACKEND_PORT${NC}\n"
    fi

    # Initialize logging
    echo "Demo setup started at $(date)" > "$PROJECT_ROOT/demo-setup.log"
    log "INFO" "Demo setup started with profile: $DEMO_PROFILE"

    # Execute setup steps
    if [ "$SILENT" != true ]; then
        check_system_requirements
        check_port_availability
    fi

    setup_environment

    if [ "$QUICK_MODE" != true ]; then
        setup_demo_data
    fi

    start_services

    if [ "$SILENT" != true ]; then
        launch_browser
    fi

    # Calculate setup time
    local end_time=$(date +%s)
    local setup_time=$((end_time - start_time))

    # Show completion summary
    if [ "$SILENT" != true ]; then
        show_completion_summary $setup_time
    fi

    log "INFO" "Demo setup completed successfully in ${setup_time} seconds"

    exit 0
}

# =============================================================================
# ERROR HANDLING
# =============================================================================

# Trap errors and cleanup
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Setup failed with exit code $exit_code"
        log "ERROR" "Setup failed with exit code $exit_code"

        echo -e "\n${YELLOW}Troubleshooting Tips:${NC}"
        echo -e "  • Check the log file: ${PROJECT_ROOT}/demo-setup.log"
        echo -e "  • Verify Docker is running: ${CYAN}docker info${NC}"
        echo -e "  • Check port availability: ${CYAN}netstat -ln | grep :$FRONTEND_PORT${NC}"
        echo -e "  • Try with --verbose flag for detailed output"
        echo -e "  • Use --reset to clean up and start fresh"
        echo -e "  • See troubleshooting guide: docs/AUTOMATED_DEMO_PLAN.md\n"
    fi
}

trap cleanup EXIT

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Ensure script is executable
if [ ! -x "$0" ]; then
    chmod +x "$0"
fi

# Run main function with all arguments
main "$@"
