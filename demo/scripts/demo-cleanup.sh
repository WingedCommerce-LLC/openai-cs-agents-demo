#!/bin/bash

# OpenAI Agents Enterprise Demo - Cleanup Script
# Version: 1.0.0
# Description: Clean shutdown and reset for the OpenAI Agents Enterprise Demo

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

# Default options
REMOVE_VOLUMES=false
REMOVE_IMAGES=false
REMOVE_DATA=false
FORCE=false
VERBOSE=false

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

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

# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

stop_services() {
    print_section "Stopping Demo Services"

    cd "$PROJECT_ROOT"

    print_step "Checking running services..."
    if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        print_step "Stopping services..."
        if [ "$VERBOSE" = true ]; then
            docker-compose -f docker-compose.dev.yml down
        else
            docker-compose -f docker-compose.dev.yml down >/dev/null 2>&1
        fi
        print_success "Services stopped"
    else
        print_info "No services running"
    fi
}

remove_volumes() {
    if [ "$REMOVE_VOLUMES" != true ]; then
        return
    fi

    print_section "Removing Docker Volumes"

    cd "$PROJECT_ROOT"

    print_step "Removing volumes..."
    if [ "$VERBOSE" = true ]; then
        docker-compose -f docker-compose.dev.yml down -v
    else
        docker-compose -f docker-compose.dev.yml down -v >/dev/null 2>&1
    fi
    print_success "Volumes removed"
}

remove_images() {
    if [ "$REMOVE_IMAGES" != true ]; then
        return
    fi

    print_section "Removing Docker Images"

    print_step "Removing demo images..."

    # Get image names from docker-compose
    local images=$(docker-compose -f docker-compose.dev.yml config | grep 'image:' | awk '{print $2}' | sort -u)

    for image in $images; do
        if docker images | grep -q "$image"; then
            print_step "Removing image: $image"
            if [ "$VERBOSE" = true ]; then
                docker rmi "$image" || true
            else
                docker rmi "$image" >/dev/null 2>&1 || true
            fi
        fi
    done

    # Remove built images
    local built_images=$(docker images | grep -E "(openai-cs-agents-demo|demo)" | awk '{print $3}')
    if [ -n "$built_images" ]; then
        print_step "Removing built demo images..."
        if [ "$VERBOSE" = true ]; then
            echo "$built_images" | xargs docker rmi || true
        else
            echo "$built_images" | xargs docker rmi >/dev/null 2>&1 || true
        fi
    fi

    print_success "Images removed"
}

remove_demo_data() {
    if [ "$REMOVE_DATA" != true ]; then
        return
    fi

    print_section "Removing Demo Data"

    print_step "Removing demo data files..."

    # Remove demo data directories
    if [ -d "$PROJECT_ROOT/demo/data" ]; then
        rm -rf "$PROJECT_ROOT/demo/data"
        print_success "Demo data directory removed"
    fi

    # Remove logs
    if [ -f "$PROJECT_ROOT/demo-setup.log" ]; then
        rm -f "$PROJECT_ROOT/demo-setup.log"
        print_success "Setup log removed"
    fi

    if [ -d "$PROJECT_ROOT/logs" ]; then
        rm -rf "$PROJECT_ROOT/logs"
        print_success "Logs directory removed"
    fi

    # Remove generated MCP servers (if any)
    if [ -d "$PROJECT_ROOT/mcp_registry" ]; then
        if [ "$FORCE" = true ] || confirm "Remove generated MCP servers?"; then
            rm -rf "$PROJECT_ROOT/mcp_registry"
            print_success "MCP registry removed"
        fi
    fi
}

clean_environment() {
    print_section "Cleaning Environment"

    print_step "Cleaning temporary files..."

    # Remove Python cache
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true

    # Remove Node.js cache
    if [ -d "$PROJECT_ROOT/ui/node_modules/.cache" ]; then
        rm -rf "$PROJECT_ROOT/ui/node_modules/.cache"
    fi

    # Remove coverage files
    if [ -f "$PROJECT_ROOT/.coverage" ]; then
        rm -f "$PROJECT_ROOT/.coverage"
    fi

    if [ -d "$PROJECT_ROOT/htmlcov" ]; then
        rm -rf "$PROJECT_ROOT/htmlcov"
    fi

    print_success "Temporary files cleaned"
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

confirm() {
    local message="$1"
    if [ "$FORCE" = true ]; then
        return 0
    fi

    echo -n -e "${YELLOW}$message [y/N]: ${NC}"
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

OpenAI Agents Enterprise Demo - Cleanup Script

OPTIONS:
    --volumes         Remove Docker volumes (deletes database data)
    --images          Remove Docker images
    --data            Remove demo data files
    --all             Remove everything (volumes, images, data)
    --force           Don't prompt for confirmation
    --verbose         Show detailed output
    --help            Show this help message

EXAMPLES:
    $0                      # Stop services only
    $0 --volumes            # Stop services and remove volumes
    $0 --all --force        # Complete cleanup without prompts
    $0 --images --data      # Remove images and data, keep volumes

CAUTION:
    --volumes will delete all database data
    --images will remove Docker images (will need to rebuild)
    --data will remove demo data and logs
    --all combines all cleanup options

For more information, see: docs/AUTOMATED_DEMO_PLAN.md
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --volumes)
                REMOVE_VOLUMES=true
                shift
                ;;
            --images)
                REMOVE_IMAGES=true
                shift
                ;;
            --data)
                REMOVE_DATA=true
                shift
                ;;
            --all)
                REMOVE_VOLUMES=true
                REMOVE_IMAGES=true
                REMOVE_DATA=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
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
}

show_cleanup_summary() {
    print_header "Demo Cleanup Complete!"

    echo -e "${GREEN}🧹 Cleanup completed successfully!${NC}\n"

    echo -e "${WHITE}📊 Cleanup Summary:${NC}"
    echo -e "  • Services: ${GREEN}Stopped${NC}"

    if [ "$REMOVE_VOLUMES" = true ]; then
        echo -e "  • Volumes: ${GREEN}Removed${NC}"
    else
        echo -e "  • Volumes: ${YELLOW}Preserved${NC}"
    fi

    if [ "$REMOVE_IMAGES" = true ]; then
        echo -e "  • Images: ${GREEN}Removed${NC}"
    else
        echo -e "  • Images: ${YELLOW}Preserved${NC}"
    fi

    if [ "$REMOVE_DATA" = true ]; then
        echo -e "  • Demo Data: ${GREEN}Removed${NC}"
    else
        echo -e "  • Demo Data: ${YELLOW}Preserved${NC}"
    fi

    echo -e "\n${WHITE}🚀 Next Steps:${NC}"
    echo -e "  • To restart demo: ${CYAN}./demo/scripts/demo-setup.sh${NC}"
    echo -e "  • To check status: ${CYAN}docker-compose -f docker-compose.dev.yml ps${NC}"
    echo -e "  • For help: ${CYAN}./demo/scripts/demo-setup.sh --help${NC}\n"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Parse command line arguments
    parse_arguments "$@"

    # Show header
    print_header "OpenAI Agents Enterprise Demo - Cleanup"

    echo -e "${WHITE}Cleaning up OpenAI Agents Enterprise Demo${NC}"

    if [ "$REMOVE_VOLUMES" = true ] || [ "$REMOVE_IMAGES" = true ] || [ "$REMOVE_DATA" = true ]; then
        echo -e "${YELLOW}Warning: This will remove demo components!${NC}"
        if [ "$FORCE" != true ]; then
            echo -e "${WHITE}Options selected:${NC}"
            [ "$REMOVE_VOLUMES" = true ] && echo -e "  • Remove volumes (database data)"
            [ "$REMOVE_IMAGES" = true ] && echo -e "  • Remove Docker images"
            [ "$REMOVE_DATA" = true ] && echo -e "  • Remove demo data files"
            echo ""

            if ! confirm "Continue with cleanup?"; then
                echo -e "${YELLOW}Cleanup cancelled${NC}"
                exit 0
            fi
        fi
    fi

    echo ""

    # Execute cleanup steps
    stop_services
    remove_volumes
    remove_images
    remove_demo_data
    clean_environment

    # Show completion summary
    show_cleanup_summary

    exit 0
}

# =============================================================================
# ERROR HANDLING
# =============================================================================

cleanup_on_error() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        print_error "Cleanup failed with exit code $exit_code"
        echo -e "\n${YELLOW}Troubleshooting Tips:${NC}"
        echo -e "  • Try running with --verbose for detailed output"
        echo -e "  • Check if Docker is running: ${CYAN}docker info${NC}"
        echo -e "  • Manual cleanup: ${CYAN}docker-compose -f docker-compose.dev.yml down -v${NC}"
        echo -e "  • See documentation: docs/AUTOMATED_DEMO_PLAN.md\n"
    fi
}

trap cleanup_on_error EXIT

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Ensure script is executable
if [ ! -x "$0" ]; then
    chmod +x "$0"
fi

# Run main function with all arguments
main "$@"
