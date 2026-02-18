#!/bin/bash
set -e

CURRENT_USER=$(whoami)

echo "============================================"
echo "Setting up HBN migration monitoring services"
echo "============================================"
echo "Current User: $CURRENT_USER"
echo "S3 Bucket: ${S3_BUCKET}"
echo "Config Bucket: ${CONFIG_BUCKET}"
echo "Region: ${AWS_REGION}"
echo "Environment: ${ENVIRONMENT}"
echo "WebSocket URL: ${WEBSOCKET_URL}"
echo "============================================"

# Update system packages
echo "Updating system packages..."
apt-get update -qq

# Install/Update SSM Agent (usually pre-installed on Ubuntu)
echo "Checking SSM Agent..."
if ! systemctl is-active --quiet amazon-ssm-agent; then
    echo "Installing SSM Agent..."
    apt-get install -y amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
    echo "✓ SSM Agent installed and started"
else
    echo "✓ SSM Agent already running"
fi

# Install Python 3.12 (if not already installed)
if ! command -v python3.12 &> /dev/null; then
    echo "Installing Python 3.12..."
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.12 python3.12-venv python3.12-dev

    # Set Python 3.12 as default
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
    update-alternatives --set python3 /usr/bin/python3.12
    echo "✓ Python 3.12 installed"
else
    echo "✓ Python 3.12 already installed"
fi

# Install UV (if not already installed)
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"

    # Add to shell profile for future sessions
    if ! grep -q 'cargo/bin' ~/.bashrc; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
    fi

    echo "✓ UV installed"
else
    echo "✓ UV already installed"
    uv --version
fi

# Ensure UV is in PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Install NodeJS (if not already installed)
if ! command -v node &> /dev/null; then
    echo "Installing NodeJS..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
    apt-get install -y nodejs
    echo "✓ NodeJS installed"
else
    echo "✓ NodeJS already installed"
fi

# Install build tools
apt-get install -y build-essential git curl wget unzip

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
mkdir -p /etc/iceberg
chown -R $CURRENT_USER:$CURRENT_USER /opt/app /var/log/app

# Download systemd service files from S3
echo "Downloading service files from S3..."
aws s3 cp s3://${CONFIG_BUCKET}/websocket-monitor.service /tmp/websocket-monitor.service
aws s3 cp s3://${CONFIG_BUCKET}/api-jobs.service /tmp/api-jobs.service

# Replace User=ubuntu with current user in service files
sed -i "s/User=ubuntu/User=$CURRENT_USER/g" /tmp/websocket-monitor.service
sed -i "s/User=ubuntu/User=$CURRENT_USER/g" /tmp/api-jobs.service

# Move service files to systemd
mv /tmp/websocket-monitor.service /etc/systemd/system/
mv /tmp/api-jobs.service /etc/systemd/system/

echo "✓ Service files configured"

# Create Iceberg catalog configuration
echo "Creating Iceberg configuration..."
cat > /etc/iceberg/catalog.yaml <<EOF
catalog:
  default:
    type: glue
    s3.endpoint: https://s3.${AWS_REGION}.amazonaws.com
    s3.region: ${AWS_REGION}
    warehouse: s3://${S3_BUCKET}/warehouse
    glue.skip-name-validation: true
EOF

chown $CURRENT_USER:$CURRENT_USER /etc/iceberg/catalog.yaml

# Create environment file
cat > /etc/profile.d/iceberg.sh <<EOF
export ICEBERG_CATALOG_CONFIG=/etc/iceberg/catalog.yaml
export ICEBERG_S3_BUCKET=${S3_BUCKET}
export ICEBERG_WAREHOUSE=s3://${S3_BUCKET}/warehouse
export AWS_REGION=${AWS_REGION}
export AWS_DEFAULT_REGION=${AWS_REGION}
export WEBSOCKET_URL=${WEBSOCKET_URL}
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
