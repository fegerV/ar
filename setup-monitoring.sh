#!/bin/bash

# Vertex AR Monitoring Setup Script
# This script sets up comprehensive monitoring for Vertex AR application

set -e

echo "🚀 Setting up Vertex AR Comprehensive Monitoring System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating monitoring directories..."
    
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/provisioning/dashboards
    mkdir -p monitoring/grafana/provisioning/datasources
    mkdir -p logs
    
    # Create Grafana datasource configuration
    cat > monitoring/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
    
    print_status "Directories created successfully"
}

# Install required Python packages
install_python_deps() {
    print_status "Installing Python monitoring dependencies..."
    
    # Check if we're in a virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        pip install prometheus-client psutil requests
        print_status "Python dependencies installed"
    else
        print_warning "Not in a virtual environment. Installing globally..."
        pip install prometheus-client psutil requests
    fi
}

# Setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    # Create .env file for monitoring
    cat >> .env << EOF

# Monitoring Configuration
ALERTING_ENABLED=true
PROMETHEUS_ENABLED=true
CPU_THRESHOLD=80.0
MEMORY_THRESHOLD=85.0
DISK_THRESHOLD=90.0
HEALTH_CHECK_INTERVAL=60

# Notification Settings
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAILS=admin@vertex-ar.example.com
EOF
    
    print_status "Environment variables configured"
    print_warning "Please update the notification settings in .env file"
}

# Start monitoring stack
start_monitoring() {
    print_status "Starting monitoring stack..."
    
    # Pull latest images
    docker-compose -f docker-compose.monitoring.yml pull
    
    # Start services
    docker-compose -f docker-compose.monitoring.yml up -d
    
    print_status "Monitoring stack started successfully"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for Prometheus
    echo "Waiting for Prometheus..."
    for i in {1..30}; do
        if curl -s http://localhost:9090/-/healthy > /dev/null; then
            print_status "Prometheus is ready"
            break
        fi
        sleep 2
    done
    
    # Wait for Grafana
    echo "Waiting for Grafana..."
    for i in {1..30}; do
        if curl -s http://localhost:3000/api/health > /dev/null; then
            print_status "Grafana is ready"
            break
        fi
        sleep 2
    done
}

# Import dashboard to Grafana
import_dashboard() {
    print_status "Importing Grafana dashboard..."
    
    # Wait a bit more for Grafana to be fully ready
    sleep 10
    
    # Import dashboard using API
    curl -s -X POST \
        http://admin:admin123@localhost:3000/api/dashboards/db \
        -H 'Content-Type: application/json' \
        -d @monitoring/grafana-dashboard.json > /dev/null
    
    print_status "Dashboard imported successfully"
}

# Setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    # Create logrotate configuration
    sudo tee /etc/logrotate.d/vertex-ar > /dev/null << EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        # Send signal to application to reopen logs if needed
        # kill -USR1 \$(cat /var/run/vertex-ar.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
EOF
    
    print_status "Log rotation configured"
}

# Create systemd service for monitoring
create_systemd_service() {
    print_status "Creating systemd service for monitoring..."
    
    cat > vertex-ar-monitoring.service << EOF
[Unit]
Description=Vertex AR Monitoring Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker-compose -f docker-compose.monitoring.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.monitoring.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    # Install service
    if command -v systemctl &> /dev/null; then
        sudo cp vertex-ar-monitoring.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable vertex-ar-monitoring.service
        print_status "Systemd service created and enabled"
    else
        print_warning "systemctl not available. Service file created but not installed."
    fi
}

# Print final information
print_info() {
    echo ""
    echo "🎉 Vertex AR Monitoring Setup Complete!"
    echo ""
    echo "📊 Monitoring Services:"
    echo "   • Prometheus: http://localhost:9090"
    echo "   • Grafana: http://localhost:3000 (admin/admin123)"
    echo "   • AlertManager: http://localhost:9093"
    echo "   • Node Exporter: http://localhost:9100/metrics"
    echo "   • cAdvisor: http://localhost:8080"
    echo ""
    echo "📈 Vertex AR Metrics:"
    echo "   • Application metrics: http://localhost:8000/metrics"
    echo "   • Monitoring API: http://localhost:8000/admin/monitoring/"
    echo ""
    echo "🔧 Configuration Files:"
    echo "   • Prometheus: ./monitoring/prometheus.yml"
    echo "   • Alert Rules: ./monitoring/alert_rules.yml"
    echo "   • AlertManager: ./monitoring/alertmanager.yml"
    echo ""
    echo "⚠️  Important:"
    echo "   1. Update notification settings in .env file"
    echo "   2. Configure Slack webhook in alertmanager.yml"
    echo "   3. Update email settings in alertmanager.yml"
    echo "   4. Review alert thresholds in alert_rules.yml"
    echo ""
    echo "🚀 To start monitoring stack:"
    echo "   docker-compose -f docker-compose.monitoring.yml up -d"
    echo ""
    echo "🛑 To stop monitoring stack:"
    echo "   docker-compose -f docker-compose.monitoring.yml down"
    echo ""
}

# Main execution
main() {
    print_status "Starting Vertex AR monitoring setup..."
    
    check_docker
    create_directories
    install_python_deps
    setup_environment
    
    # Ask if user wants to start services
    read -p "Do you want to start the monitoring stack now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_monitoring
        wait_for_services
        import_dashboard
        setup_log_rotation
        create_systemd_service
    fi
    
    print_info
}

# Run main function
main "$@"