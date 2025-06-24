#!/bin/bash
set -euo pipefail

# OpenAI Agents Enterprise Template Setup Script
# Ensures proper Python 3.11+ and Node.js 20+ LTS environment setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python_version() {
    if command_exists python3; then
        local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        local required_version="3.11"

        if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
            log_success "Python $python_version found (>= $required_version required)"
            return 0
        else
            log_error "Python $python_version found, but >= $required_version is required"
            return 1
        fi
    else
        log_error "Python 3 not found"
        return 1
    fi
}

# Check Node.js version
check_node_version() {
    if command_exists node; then
        local node_version=$(node --version | sed 's/v//')
        local required_version="20.0.0"

        if [ "$(printf '%s\n' "$required_version" "$node_version" | sort -V | head -n1)" = "$required_version" ]; then
            log_success "Node.js $node_version found (>= $required_version required)"
            return 0
        else
            log_error "Node.js $node_version found, but >= $required_version is required"
            return 1
        fi
    else
        log_error "Node.js not found"
        return 1
    fi
}

# Install uv if not present
install_uv() {
    if ! command_exists uv; then
        log_info "Installing uv (Python package manager)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"

        if command_exists uv; then
            log_success "uv installed successfully"
        else
            log_error "Failed to install uv"
            exit 1
        fi
    else
        log_success "uv already installed"
    fi
}

# Setup Python environment
setup_python_env() {
    log_info "Setting up Python environment with uv..."

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        log_info "Creating Python virtual environment..."
        uv venv --python 3.11
        log_success "Virtual environment created"
    else
        log_success "Virtual environment already exists"
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Install dependencies
    log_info "Installing Python dependencies..."
    uv pip install -e ".[dev,security]"

    log_success "Python dependencies installed"
}

# Setup Node.js environment
setup_node_env() {
    log_info "Setting up Node.js environment..."

    cd ui

    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        log_error "package.json not found in ui/ directory"
        exit 1
    fi

    # Install dependencies
    log_info "Installing Node.js dependencies..."
    npm ci

    # Install Cypress dependencies
    log_info "Installing Cypress and testing dependencies..."
    npm install --save-dev \
        cypress@^13.0.0 \
        @cypress/code-coverage@^3.12.0 \
        @testing-library/cypress@^10.0.0 \
        start-server-and-test@^2.0.0

    cd ..
    log_success "Node.js dependencies installed"
}

# Setup pre-commit hooks
setup_pre_commit() {
    log_info "Setting up pre-commit hooks..."

    # Ensure we're in the virtual environment
    source .venv/bin/activate

    # Install pre-commit hooks
    pre-commit install

    log_success "Pre-commit hooks installed"
}

# Create environment file
create_env_file() {
    if [ ! -f ".env" ]; then
        log_info "Creating .env file from template..."
        cp .env.example .env
        log_warning "Please update .env file with your actual configuration values"
    else
        log_success ".env file already exists"
    fi
}

# Run initial tests
run_initial_tests() {
    log_info "Running initial test suite to verify setup..."

    # Activate virtual environment
    source .venv/bin/activate

    # Run Python tests (with lower coverage for initial setup)
    log_info "Running Python unit tests..."
    if pytest tests/ --cov=. --cov-fail-under=50 -v; then
        log_success "Python tests passed"
    else
        log_warning "Some Python tests failed - this is expected for initial setup"
    fi

    # Run Node.js tests
    log_info "Running Node.js tests..."
    cd ui
    if npm test -- --watchAll=false --passWithNoTests; then
        log_success "Node.js tests passed"
    else
        log_warning "Some Node.js tests failed - this is expected for initial setup"
    fi
    cd ..
}

# Main setup function
main() {
    log_info "Starting OpenAI Agents Enterprise Template setup..."

    # Check prerequisites
    log_info "Checking prerequisites..."

    if ! check_python_version; then
        log_error "Please install Python 3.11 or higher"
        log_info "Visit: https://www.python.org/downloads/"
        exit 1
    fi

    if ! check_node_version; then
        log_error "Please install Node.js 20 LTS or higher"
        log_info "Visit: https://nodejs.org/en/download/"
        exit 1
    fi

    # Install uv
    install_uv

    # Setup environments
    setup_python_env
    setup_node_env

    # Setup development tools
    setup_pre_commit

    # Create configuration
    create_env_file

    # Run initial tests
    run_initial_tests

    log_success "Setup completed successfully!"
    echo
    log_info "Next steps:"
    echo "  1. Update .env file with your configuration"
    echo "  2. Run 'source .venv/bin/activate' to activate Python environment"
    echo "  3. Run 'uv run pytest tests/' to run Python tests"
    echo "  4. Run 'cd ui && npm test' to run frontend tests"
    echo "  5. Run 'cd ui && npx cypress open' to run E2E tests"
    echo "  6. Run 'docker-compose -f docker-compose.dev.yml up' to start development environment"
}

# Run main function
main "$@"
