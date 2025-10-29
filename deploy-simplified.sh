#!/bin/bash

# Simplified AR Backend Deployment Script for Vertex-Art-AR
# Based on Stogram approach but for Vertex-Art-AR project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}===================================${NC}"
echo -e "${GREEN}Vertex-Art-AR Simplified Deployment${NC}"
echo -e "${GREEN}===================================${NC}"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   echo "Please run as a regular user with sudo privileges"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Docker if not present
install_docker() {
    echo -e "${YELLOW}Installing Docker...${NC}"
    
    # Update package index
    sudo apt-get update
    
    # Install prerequisites
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    echo -e "${GREEN}Docker installed successfully${NC}"
    echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"
}

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

if ! command_exists docker; then
    echo -e "${YELLOW}Docker not found${NC}"
    read -p "Do you want to install Docker? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_docker
    else
        echo -e "${RED}Docker is required. Exiting.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Docker is installed${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p storage/ar_content
mkdir -p storage/nft-markers
mkdir -p ssl
echo -e "${GREEN}✓ Directories created${NC}"

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
docker compose build

echo -e "${YELLOW}Starting services...${NC}"
docker compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check service status
echo -e "${YELLOW}Checking service status...${NC}"
docker compose ps

echo ""
echo -e "${GREEN}===================================${NC}"
echo -e "${GREEN}Simplified Deployment Complete!${NC}"
echo -e "${GREEN}===================================${NC}"
echo ""
echo "Services are running:"
echo "  - Application: http://localhost:8000"
echo "  - Frontend: http://localhost (via Nginx)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Create admin user via API or UI"
echo "2. Configure firewall if needed"
echo "3. Set up SSL certificates if required"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose logs -f"
echo "  - Stop services: docker compose down"
echo " - Restart services: docker compose restart"
echo ""