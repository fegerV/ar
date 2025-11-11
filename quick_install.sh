#!/bin/bash

# Quick Vertex AR Installation Script
# Simplified version for fast deployment
# Usage: ./quick_install.sh [domain] [email]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
DOMAIN="$1"
EMAIL="$2"
PROJECT_DIR="/opt/vertex-ar"
PROJECT_USER="vertexar"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

echo -e "${BLUE}===================================${NC}"
echo -e "${BLUE}Vertex AR Quick Installer${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# Parse arguments
if [[ -n "$DOMAIN" && -n "$EMAIL" ]]; then
    INSTALL_ARGS="--domain $DOMAIN --email $EMAIL"
    print_status "Installing with SSL for domain: $DOMAIN"
else
    INSTALL_ARGS="--no-ssl"
    print_status "Installing without SSL"
fi

# Run the full installation script
if [[ -f "./install_ubuntu.sh" ]]; then
    print_step "Running enhanced installation script..."
    chmod +x ./install_ubuntu.sh
    ./install_ubuntu.sh $INSTALL_ARGS
else
    print_error "install_ubuntu.sh not found in current directory"
    exit 1
fi

echo ""
print_status "Quick installation completed!"
echo ""
echo "Next steps:"
echo "1. Access your application at: http://$(hostname -I | awk '{print $1}'):8000"
if [[ -n "$DOMAIN" ]]; then
    echo "2. Access via domain: https://$DOMAIN"
fi
echo "3. Configure your admin account"
echo "4. Test all features"
echo ""
echo "For detailed configuration, see: $PROJECT_DIR/.env"
