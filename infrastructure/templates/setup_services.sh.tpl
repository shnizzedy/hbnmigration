#!/bin/bash
set -e

CURRENT_USER="$${SUDO_USER:-$$(whoami)}"

echo "============================================"
echo "Setting up HBN migration monitoring services"
echo "============================================"
echo "Current User: $CURRENT_USER"
echo "Instance: ${INSTANCE_NAME}"
echo "Region: ${AWS_REGION}"
echo "Environment: ${ENVIRONMENT}"
echo "WebSocket URL: ${WEBSOCKET_URL}"
echo "============================================"

# Update system packages
echo "Updating system packages..."
apt-get update -qq

# Install build tools
apt-get install -y bash build-essential git curl wget unzip

# Install Python 3.12 (if not already installed)
if ! command -v uv &> /dev/null; then
    echo "Installing Python 3.12..."
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.12 python3.12-venv python3.12-dev pipx
    # Set Python 3.12 as default
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
    update-alternatives --set python3 /usr/bin/python3.12
    pipx install --quiet uv
    echo "✓ Python 3.12 installed"
else
    echo "✓ Python 3.12 already installed"
fi

# Install NodeJS (if not already installed)
if ! command -v node &> /dev/null; then
    echo "Installing NodeJS..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
    apt-get install -y nodejs
    echo "✓ NodeJS installed"
else
    echo "✓ NodeJS already installed"
fi

# Determine repository paths
REPO_ROOT="/home/$CURRENT_USER/hbnmigration"
PYTHON_JOBS_PATH="$REPO_ROOT/python_jobs"
NODE_JOBS_PATH="$REPO_ROOT/node_jobs"

# Install Python packages using UV
echo "Installing Python hbnmigration package with UV..."
if [ -d "$PYTHON_JOBS_PATH" ] && [ -f "$PYTHON_JOBS_PATH/pyproject.toml" ]; then
    echo "Installing from: $PYTHON_JOBS_PATH"
    # UV can install directly from path
    uv pip install --system "$PYTHON_JOBS_PATH"
    # Verify installation
    python3 -c "import hbnmigration; print(f'✓ Installed hbnmigration v{hbnmigration.__version__}')"
else
    echo "❌ Error: python_jobs not found at $PYTHON_JOBS_PATH"
    exit 1
fi
echo "✓ Python packages installed"

# Install Node.js packages
echo "Installing Node.js packages..."
if [ -d "$NODE_JOBS_PATH" ] && [ -f "$NODE_JOBS_PATH/package.json" ]; then
    echo "Installing from: $NODE_JOBS_PATH"
    cd "$NODE_JOBS_PATH"
    npm install --production --quiet
    # Verify installation
    if [ -d "$NODE_JOBS_PATH/node_modules" ]; then
        echo "✓ Node.js packages installed"
        echo "Installed packages:"
        npm list --depth=0 2>/dev/null | grep -E "@childmindresearch|mindlogger" || true
    else
        echo "⚠️  npm install may have failed"
    fi
else
    echo "⚠️  node_jobs not found at $NODE_JOBS_PATH, skipping Node.js dependencies"
fi

# Create application directory structure
echo "Creating directories..."
mkdir -p /opt/app
mkdir -p /var/log/app
chown -R $CURRENT_USER:$CURRENT_USER /opt/app /var/log/app

# Create systemd service files directly (no S3 download)
echo "Creating service files..."

# WebSocket Monitor Service
cat > /etc/systemd/system/websocket-monitor.service <<EOF
[Unit]
Description=WebSocket Monitor Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PYTHON_JOBS_PATH
Environment="PATH=/home/$CURRENT_USER/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="AWS_REGION=${AWS_REGION}"
Environment="WEBSOCKET_URL=${WEBSOCKET_URL}"
Environment="ENVIRONMENT=${ENVIRONMENT}"
ExecStart=/usr/bin/python3 -m hbnmigration.websocket_monitor
Restart=always
RestartSec=10
StandardOutput=append:/var/log/app/websocket-monitor.log
StandardError=append:/var/log/app/websocket-monitor.log

[Install]
WantedBy=multi-user.target
EOF

# API Jobs Service
cat > /etc/systemd/system/api-jobs.service <<EOF
[Unit]
Description=API Jobs Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$NODE_JOBS_PATH
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="NODE_ENV=production"
Environment="AWS_REGION=${AWS_REGION}"
Environment="WEBSOCKET_URL=${WEBSOCKET_URL}"
Environment="ENVIRONMENT=${ENVIRONMENT}"
ExecStart=/usr/bin/node index.js
Restart=always
RestartSec=10
StandardOutput=append:/var/log/app/api-jobs.log
StandardError=append:/var/log/app/api-jobs.log

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service files created"

# Create local Iceberg warehouse
echo "Setting up local Iceberg warehouse..."
mkdir -p /opt/iceberg/warehouse
chown -R "$CURRENT_USER":"$CURRENT_USER" /opt/iceberg

# Create Iceberg catalog configuration (local filesystem)
cat > /etc/iceberg/catalog.yaml <<EOF
catalog:
  default:
    type: hadoop
    warehouse: file:///opt/iceberg/warehouse
EOF

chown "$CURRENT_USER":"$CURRENT_USER" /etc/iceberg/catalog.yaml

# Create environment file
cat > /etc/profile.d/iceberg.sh <<EOF
export ICEBERG_CATALOG_CONFIG=/etc/iceberg/catalog.yaml
export ICEBERG_WAREHOUSE=file:///opt/iceberg/warehouse
export AWS_REGION=${AWS_REGION}
export WEBSOCKET_URL=${WEBSOCKET_URL}
EOF

# Create environment file
cat > /etc/profile.d/app.sh <<EOF
export AWS_REGION=${AWS_REGION}
export AWS_DEFAULT_REGION=${AWS_REGION}
export WEBSOCKET_URL=${WEBSOCKET_URL}
export ENVIRONMENT=${ENVIRONMENT}
EOF

echo "✓ Configuration files created"

# Reload systemd
echo "Configuring systemd services..."
systemctl daemon-reload

# Enable services
systemctl enable websocket-monitor.service
systemctl enable api-jobs.service

# Restart services (or start if not running)
echo "Starting/restarting services..."
systemctl restart websocket-monitor.service 2>/dev/null || systemctl start websocket-monitor.service
systemctl restart api-jobs.service 2>/dev/null || systemctl start api-jobs.service

# Wait and check status
sleep 3

echo ""
echo "========================================"
echo "Service Status"
echo "========================================"

if systemctl is-active --quiet websocket-monitor.service; then
    echo "✓ websocket-monitor.service is running"
else
    echo "✗ websocket-monitor.service is NOT running"
    systemctl status websocket-monitor.service --no-pager
fi

if systemctl is-active --quiet api-jobs.service; then
    echo "✓ api-jobs.service is running"
else
    echo "✗ api-jobs.service is NOT running"
    systemctl status api-jobs.service --no-pager
fi

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo "Python package: $PYTHON_JOBS_PATH"
echo "Node.js package: $NODE_JOBS_PATH"
echo ""
echo "View logs with:"
echo "  journalctl -u websocket-monitor.service -f"
echo "  journalctl -u api-jobs.service -f"
echo ""
echo "Or:"
echo "  tail -f /var/log/app/websocket-monitor.log"
echo "  tail -f /var/log/app/api-jobs.log"
echo "========================================"
