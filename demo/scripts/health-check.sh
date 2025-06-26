#!/bin/bash

# OpenAI Agents Enterprise Demo - Health Check Script
# Version: 1.0.0
# Description: Comprehensive service health verification and monitoring

set -euo pipefail

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Service configuration
FRONTEND_PORT=3000
BACKEND_PORT=8000
DB_PORT=5432
REDIS_PORT=6379
ADMINER_PORT=8080

# Health check configuration
TIMEOUT=30
RETRY_INTERVAL=2
MAX_RETRIES=15

# Default options
VERBOSE=false
CONTINUOUS=false
JSON_OUTPUT=false
SERVICES_ONLY=false

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_header() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${PURPLE}║${WHITE}  $1${PURPLE}$(printf "%*s" $((76 - ${#1})) "")║${NC}"
        echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}\n"
    fi
}

print_section() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "\n${CYAN}▶ $1${NC}"
    fi
}

print_step() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "  ${BLUE}• $1${NC}"
    fi
}

print_success() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "  ${GREEN}✓ $1${NC}"
    fi
}

print_warning() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "  ${YELLOW}⚠ $1${NC}"
    fi
}

print_error() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "  ${RED}✗ $1${NC}" >&2
    fi
}

print_info() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "  ${WHITE}ℹ $1${NC}"
    fi
}

# Logging function
log_result() {
    local service=$1
    local status=$2
    local message=$3
    local response_time=${4:-"N/A"}

    if [ "$JSON_OUTPUT" = true ]; then
        echo "{\"service\":\"$service\",\"status\":\"$status\",\"message\":\"$message\",\"response_time\":\"$response_time\",\"timestamp\":\"$(date -Iseconds)\"}"
    elif [ "$VERBOSE" = true ]; then
        echo "[$service] $status: $message (${response_time}ms)" >> "$PROJECT_ROOT/health-check.log"
    fi
}

# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

check_docker_services() {
    print_section "Checking Docker Services"

    local services_healthy=0
    local total_services=0

    cd "$PROJECT_ROOT"

    # Get list of services from docker-compose
    local services=$(docker-compose -f docker-compose.dev.yml config --services 2>/dev/null || echo "")

    if [ -z "$services" ]; then
        print_error "Could not read docker-compose configuration"
        log_result "docker" "error" "Could not read docker-compose configuration"
        return 1
    fi

    for service in $services; do
        ((total_services++))
        print_step "Checking $service container..."

        # Check if container is running
        local container_status=$(docker-compose -f docker-compose.dev.yml ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null || echo "not_found")

        if [ "$container_status" = "running" ]; then
            # Check container health if health check is defined
            local health_status=$(docker-compose -f docker-compose.dev.yml ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")

            if [ "$health_status" = "healthy" ] || [ "$health_status" = "none" ]; then
                print_success "$service is running and healthy"
                log_result "$service" "healthy" "Container running and healthy"
                ((services_healthy++))
            else
                print_warning "$service is running but unhealthy ($health_status)"
                log_result "$service" "unhealthy" "Container running but health check failed: $health_status"
            fi
        else
            print_error "$service is not running ($container_status)"
            log_result "$service" "down" "Container not running: $container_status"
        fi
    done

    if [ $services_healthy -eq $total_services ]; then
        print_success "All Docker services are healthy ($services_healthy/$total_services)"
        return 0
    else
        print_warning "Some Docker services are unhealthy ($services_healthy/$total_services)"
        return 1
    fi
}

check_port_connectivity() {
    print_section "Checking Port Connectivity"

    local ports=($FRONTEND_PORT $BACKEND_PORT $DB_PORT $REDIS_PORT $ADMINER_PORT)
    local port_names=("Frontend" "Backend" "Database" "Redis" "Adminer")
    local ports_accessible=0

    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local name=${port_names[$i]}

        print_step "Checking port $port ($name)..."

        local start_time=$(date +%s%3N)
        if timeout $TIMEOUT nc -z localhost $port >/dev/null 2>&1; then
            local end_time=$(date +%s%3N)
            local response_time=$((end_time - start_time))
            print_success "Port $port is accessible"
            log_result "$name" "accessible" "Port responding" "$response_time"
            ((ports_accessible++))
        else
            print_error "Port $port is not accessible"
            log_result "$name" "inaccessible" "Port not responding"
        fi
    done

    if [ $ports_accessible -eq ${#ports[@]} ]; then
        print_success "All ports are accessible ($ports_accessible/${#ports[@]})"
        return 0
    else
        print_warning "Some ports are not accessible ($ports_accessible/${#ports[@]})"
        return 1
    fi
}

check_backend_health() {
    print_section "Checking Backend Health"

    local backend_url="http://localhost:$BACKEND_PORT"

    # Check basic connectivity
    print_step "Testing backend connectivity..."
    local start_time=$(date +%s%3N)
    if timeout $TIMEOUT curl -s "$backend_url" >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        print_success "Backend is responding"
        log_result "backend" "responding" "Basic connectivity successful" "$response_time"
    else
        print_error "Backend is not responding"
        log_result "backend" "down" "Basic connectivity failed"
        return 1
    fi

    # Check health endpoint if available
    print_step "Testing health endpoint..."
    local health_url="$backend_url/health"
    start_time=$(date +%s%3N)
    local health_response=$(timeout $TIMEOUT curl -s "$health_url" 2>/dev/null || echo "")

    if [ -n "$health_response" ]; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))

        # Try to parse JSON response
        if echo "$health_response" | jq . >/dev/null 2>&1; then
            local status=$(echo "$health_response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
            if [ "$status" = "healthy" ] || [ "$status" = "ok" ]; then
                print_success "Health endpoint reports healthy"
                log_result "backend_health" "healthy" "Health endpoint OK" "$response_time"
            else
                print_warning "Health endpoint reports: $status"
                log_result "backend_health" "warning" "Health endpoint status: $status" "$response_time"
            fi
        else
            print_success "Health endpoint responding (non-JSON)"
            log_result "backend_health" "responding" "Health endpoint responding" "$response_time"
        fi
    else
        print_warning "Health endpoint not available"
        log_result "backend_health" "unavailable" "Health endpoint not responding"
    fi

    # Check API documentation endpoint
    print_step "Testing API docs endpoint..."
    local docs_url="$backend_url/docs"
    if timeout $TIMEOUT curl -s "$docs_url" >/dev/null 2>&1; then
        print_success "API documentation is accessible"
        log_result "backend_docs" "accessible" "API docs endpoint responding"
    else
        print_warning "API documentation not accessible"
        log_result "backend_docs" "inaccessible" "API docs endpoint not responding"
    fi

    return 0
}

check_frontend_health() {
    print_section "Checking Frontend Health"

    local frontend_url="http://localhost:$FRONTEND_PORT"

    # Check basic connectivity
    print_step "Testing frontend connectivity..."
    local start_time=$(date +%s%3N)
    local response=$(timeout $TIMEOUT curl -s -w "%{http_code}" "$frontend_url" 2>/dev/null || echo "000")
    local http_code="${response: -3}"

    if [ "$http_code" = "200" ]; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        print_success "Frontend is responding (HTTP $http_code)"
        log_result "frontend" "responding" "HTTP $http_code" "$response_time"
    elif [ "$http_code" != "000" ]; then
        print_warning "Frontend responding with HTTP $http_code"
        log_result "frontend" "warning" "HTTP $http_code"
    else
        print_error "Frontend is not responding"
        log_result "frontend" "down" "No response"
        return 1
    fi

    # Check if it's serving the expected content
    print_step "Testing frontend content..."
    local content=$(timeout $TIMEOUT curl -s "$frontend_url" 2>/dev/null || echo "")

    if echo "$content" | grep -q "OpenAI\|Agents\|Demo" >/dev/null 2>&1; then
        print_success "Frontend serving expected content"
        log_result "frontend_content" "valid" "Expected content found"
    elif [ -n "$content" ]; then
        print_warning "Frontend serving content but may not be the expected app"
        log_result "frontend_content" "warning" "Unexpected content"
    else
        print_error "Frontend not serving any content"
        log_result "frontend_content" "empty" "No content received"
    fi

    return 0
}

check_database_health() {
    print_section "Checking Database Health"

    # Check PostgreSQL connectivity
    print_step "Testing database connectivity..."

    local start_time=$(date +%s%3N)
    if timeout $TIMEOUT docker-compose -f docker-compose.dev.yml exec -T db pg_isready -U user >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        print_success "Database is accepting connections"
        log_result "database" "accessible" "PostgreSQL accepting connections" "$response_time"
    else
        print_error "Database is not accepting connections"
        log_result "database" "inaccessible" "PostgreSQL not accepting connections"
        return 1
    fi

    # Check database version and basic info
    print_step "Testing database queries..."
    local db_version=$(timeout $TIMEOUT docker-compose -f docker-compose.dev.yml exec -T db psql -U user -d agents_dev -t -c "SELECT version();" 2>/dev/null | head -1 | xargs || echo "")

    if [ -n "$db_version" ]; then
        print_success "Database queries working"
        log_result "database_query" "working" "Query execution successful"
        if [ "$VERBOSE" = true ]; then
            print_info "Database version: $(echo $db_version | cut -d' ' -f1-3)"
        fi
    else
        print_warning "Database queries not working"
        log_result "database_query" "failed" "Query execution failed"
    fi

    return 0
}

check_redis_health() {
    print_section "Checking Redis Health"

    # Check Redis connectivity
    print_step "Testing Redis connectivity..."

    local start_time=$(date +%s%3N)
    if timeout $TIMEOUT docker-compose -f docker-compose.dev.yml exec -T redis redis-cli ping >/dev/null 2>&1; then
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))
        print_success "Redis is responding to ping"
        log_result "redis" "responding" "Redis ping successful" "$response_time"
    else
        print_error "Redis is not responding"
        log_result "redis" "down" "Redis ping failed"
        return 1
    fi

    # Check Redis info
    print_step "Testing Redis operations..."
    local redis_info=$(timeout $TIMEOUT docker-compose -f docker-compose.dev.yml exec -T redis redis-cli info server 2>/dev/null | grep "redis_version" || echo "")

    if [ -n "$redis_info" ]; then
        print_success "Redis operations working"
        log_result "redis_ops" "working" "Redis operations successful"
        if [ "$VERBOSE" = true ]; then
            local version=$(echo "$redis_info" | cut -d':' -f2 | tr -d '\r')
            print_info "Redis version: $version"
        fi
    else
        print_warning "Redis operations not working"
        log_result "redis_ops" "failed" "Redis operations failed"
    fi

    return 0
}

check_system_resources() {
    if [ "$SERVICES_ONLY" = true ]; then
        return 0
    fi

    print_section "Checking System Resources"

    # Check memory usage
    print_step "Checking memory usage..."
    if command -v free >/dev/null 2>&1; then
        local mem_info=$(free -m)
        local total_mem=$(echo "$mem_info" | awk '/^Mem:/ {print $2}')
        local used_mem=$(echo "$mem_info" | awk '/^Mem:/ {print $3}')
        local mem_percent=$((used_mem * 100 / total_mem))

        if [ $mem_percent -lt 80 ]; then
            print_success "Memory usage: ${mem_percent}% (${used_mem}MB/${total_mem}MB)"
            log_result "memory" "ok" "Memory usage ${mem_percent}%"
        elif [ $mem_percent -lt 90 ]; then
            print_warning "Memory usage: ${mem_percent}% (${used_mem}MB/${total_mem}MB)"
            log_result "memory" "warning" "High memory usage ${mem_percent}%"
        else
            print_error "Memory usage: ${mem_percent}% (${used_mem}MB/${total_mem}MB)"
            log_result "memory" "critical" "Critical memory usage ${mem_percent}%"
        fi
    else
        print_info "Memory check not available"
        log_result "memory" "unavailable" "Memory check not available"
    fi

    # Check disk usage
    print_step "Checking disk usage..."
    local disk_usage=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ "$disk_usage" -lt 80 ]; then
        print_success "Disk usage: ${disk_usage}%"
        log_result "disk" "ok" "Disk usage ${disk_usage}%"
    elif [ "$disk_usage" -lt 90 ]; then
        print_warning "Disk usage: ${disk_usage}%"
        log_result "disk" "warning" "High disk usage ${disk_usage}%"
    else
        print_error "Disk usage: ${disk_usage}%"
        log_result "disk" "critical" "Critical disk usage ${disk_usage}%"
    fi

    # Check Docker resource usage
    print_step "Checking Docker resource usage..."
    if command -v docker >/dev/null 2>&1; then
        local docker_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "(backend|frontend|db|redis)" || echo "")

        if [ -n "$docker_stats" ]; then
            print_success "Docker containers resource usage available"
            log_result "docker_resources" "available" "Docker stats accessible"
            if [ "$VERBOSE" = true ]; then
                echo "$docker_stats"
            fi
        else
            print_info "Docker resource stats not available"
            log_result "docker_resources" "unavailable" "Docker stats not available"
        fi
    fi
}

# =============================================================================
# MAIN HEALTH CHECK FUNCTION
# =============================================================================

run_health_checks() {
    local overall_status=0

    if [ "$JSON_OUTPUT" != true ]; then
        print_header "OpenAI Agents Enterprise Demo - Health Check"
        echo -e "${WHITE}Checking system health and service status...${NC}\n"
    fi

    # Initialize log file
    if [ "$VERBOSE" = true ]; then
        echo "Health check started at $(date)" > "$PROJECT_ROOT/health-check.log"
    fi

    # Run health checks
    check_docker_services || ((overall_status++))
    check_port_connectivity || ((overall_status++))
    check_backend_health || ((overall_status++))
    check_frontend_health || ((overall_status++))
    check_database_health || ((overall_status++))
    check_redis_health || ((overall_status++))
    check_system_resources || ((overall_status++))

    # Summary
    if [ "$JSON_OUTPUT" != true ]; then
        echo ""
        if [ $overall_status -eq 0 ]; then
            print_success "All health checks passed! System is healthy."
        else
            print_warning "$overall_status health check(s) failed. See details above."
        fi

        echo -e "\n${WHITE}Health check completed at $(date)${NC}"

        if [ "$VERBOSE" = true ]; then
            echo -e "${WHITE}Detailed logs: ${PROJECT_ROOT}/health-check.log${NC}"
        fi
    fi

    return $overall_status
}

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OpenAI Agents Enterprise Demo - Health Check Script

OPTIONS:
    --verbose         Show detailed output and logging
    --continuous      Run health checks continuously (every 30 seconds)
    --json            Output results in JSON format
    --services-only   Check only services, skip system resources
    --timeout SECONDS Set timeout for individual checks (default: $TIMEOUT)
    --help            Show this help message

EXAMPLES:
    $0                          # Standard health check
    $0 --verbose                # Detailed health check with logging
    $0 --continuous             # Continuous monitoring
    $0 --json                   # JSON output for automation
    $0 --services-only          # Check only services

EXIT CODES:
    0    All health checks passed
    >0   Number of failed health checks

For more information, see: docs/AUTOMATED_DEMO_PLAN.md
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                VERBOSE=true
                shift
                ;;
            --continuous)
                CONTINUOUS=true
                shift
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --services-only)
                SERVICES_ONLY=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate timeout
    if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]] || [ "$TIMEOUT" -lt 1 ]; then
        echo "Invalid timeout: $TIMEOUT (must be a positive integer)" >&2
        exit 1
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Parse command line arguments
    parse_arguments "$@"

    # Change to project directory
    cd "$PROJECT_ROOT"

    if [ "$CONTINUOUS" = true ]; then
        if [ "$JSON_OUTPUT" != true ]; then
            echo "Starting continuous health monitoring (Ctrl+C to stop)..."
        fi

        while true; do
            run_health_checks
            if [ "$JSON_OUTPUT" != true ]; then
                echo -e "\n${BLUE}Waiting 30 seconds before next check...${NC}"
            fi
            sleep 30
        done
    else
        run_health_checks
        exit $?
    fi
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Ensure script is executable
if [ ! -x "$0" ]; then
    chmod +x "$0"
fi

# Run main function with all arguments
main "$@"
