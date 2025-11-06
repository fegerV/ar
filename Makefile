# Makefile for Vertex-AR Simplified deployment

.PHONY: help build up down restart logs clean deploy ssl backup restore

help: ## Show this help message
    @echo 'Usage: make [target]'
    @echo ''
    @echo 'Available targets:'
    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
    docker compose build

up: ## Start all services
    docker compose up -d

down: ## Stop all services
    docker compose down

restart: ## Restart all services
    docker compose restart

logs: ## Show logs from all services
    docker compose logs -f

logs-app: ## Show app logs
    docker compose logs -f app

status: ## Show status of all services
    docker compose ps

shell-app: ## Open shell in app container
    docker compose exec app bash

clean: ## Remove all containers and volumes
    docker compose down -v
    docker system prune -f

deploy: ## Deploy application (first time setup)
    chmod +x deploy-simplified.sh
    ./deploy-simplified.sh

backup-db: ## Backup SQLite database
    @mkdir -p backups
    cp app_data.db backups/db_backup_$$(date +%Y%m%d_%H%M%S).db
    @echo "Database backup created in backups/"

update: ## Update and restart services
    git pull
    docker compose build
    docker compose up -d
    @echo "Services updated and restarted"

health: ## Check health of all services
    @echo "Checking service health..."
    @docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

create-admin: ## Create admin user (interactive)
    @echo "Creating admin user..."
    @read -p "Username: " username; \
    read -sp "Password: " password; \
    echo ""; \
    curl -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$$username\",\"password\":\"$$password\"}"; \
    echo ""; \
    echo "Admin user created successfully"
