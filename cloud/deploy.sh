#!/bin/bash
# ORION Cloud Deploy Script
# One-click deploy to any VPS (Ubuntu/Debian)
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/.../deploy.sh | bash
#   OR
#   bash deploy.sh
#
# Requirements:
#   - Ubuntu 22.04+ / Debian 12+ VPS
#   - Root access or sudo
#   - Minimum: 2 vCPU, 4GB RAM, 40GB disk

set -e

echo "============================================"
echo "  ORION System - Cloud Deployment"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ORION_USER="orion"
ORION_DIR="/opt/orion"
ORION_PORT=8000
MCP_PORT=8001
PYTHON_VERSION="3.12"

log() { echo -e "${GREEN}[ORION]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

# Detect OS
if ! grep -q "Ubuntu\|Debian" /etc/os-release 2>/dev/null; then
    warn "This script is tested on Ubuntu/Debian. Proceeding anyway..."
fi

log "Starting ORION deployment..."

# 1. System updates
log "Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. Install dependencies
log "Installing system dependencies..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    htop \
    tmux \
    unzip \
    build-essential

# 3. Create ORION user
log "Creating ORION user..."
if ! id "$ORION_USER" &>/dev/null; then
    useradd -r -m -s /bin/bash $ORION_USER
fi

# 4. Create directories
log "Creating ORION directories..."
mkdir -p $ORION_DIR
mkdir -p $ORION_DIR/data
mkdir -p $ORION_DIR/logs
mkdir -p $ORION_DIR/config

# 5. Download ORION
log "Downloading ORION..."
cd $ORION_DIR

if [ -d ".git" ]; then
    git pull
else
    # If deploying from a release zip
    if [ -f "/tmp/orion.zip" ]; then
        unzip -q /tmp/orion.zip -d $ORION_DIR
    else
        # Create minimal ORION structure for cloud
        cat > orion_server.py << 'SERVEREOF'
#!/usr/bin/env python3
"""ORION Cloud Server - Standalone"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from orion.daemon import ORIONDaemon
from orion.server import run_server

if __name__ == "__main__":
    run_server(host="0.0.0.0", port=8000)
SERVEREOF
    fi
fi

# 6. Create virtual environment
log "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 7. Install Python dependencies
log "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q 2>/dev/null || pip install fastapi uvicorn aiohttp -q

# 8. Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/orion.service << 'EOF'
[Unit]
Description=ORION AI System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=orion
Group=orion
WorkingDirectory=/opt/orion
ExecStart=/opt/orion/venv/bin/python -m orion.server
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=ORION_ENV=production
StandardOutput=journal+console
StandardError=journal+console

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/orion/data /opt/orion/logs

[Install]
WantedBy=multi-user.target
EOF

# 9. Create MCP service (optional remote access)
cat > /etc/systemd/system/orion-mcp.service << 'EOF'
[Unit]
Description=ORION MCP Remote Server
After=network.target orion.service

[Service]
Type=simple
User=orion
Group=orion
WorkingDirectory=/opt/orion
ExecStart=/opt/orion/venv/bin/python orion_mcp_server.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 10. Create startup script
cat > /opt/orion/start.sh << 'STARTEOF'
#!/bin/bash
cd /opt/orion
source venv/bin/activate
python -m orion.server
STARTEOF
chmod +x /opt/orion/start.sh

# 11. Create health check endpoint
cat > /opt/orion/health_check.py << 'HEALTHEOF'
#!/usr/bin/env python3
"""ORION Health Check"""
import json
import urllib.request

try:
    response = urllib.request.urlopen("http://localhost:8000/api/health", timeout=5)
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
except Exception as e:
    print(json.dumps({"status": "error", "error": str(e)}))
HEALTHEOF

# 12. Set permissions
chown -R $ORION_USER:$ORION_USER $ORION_DIR

# 13. Enable and start services
log "Enabling and starting services..."
systemctl daemon-reload
systemctl enable orion.service
systemctl start orion.service
systemctl enable orion-mcp.service
systemctl start orion-mcp.service

# 14. Configure firewall
log "Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp    # SSH
    ufw allow $ORION_PORT/tcp   # ORION API
    ufw allow $MCP_PORT/tcp    # MCP Server
    ufw allow 3000/tcp  # Web UI (optional)
    ufw --force enable
fi

# 15. Create status script
cat > /usr/local/bin/orion-status << 'STATUSEOF'
#!/bin/bash
echo "=== ORION System Status ==="
echo ""
echo "Services:"
systemctl status orion.service --no-pager -l | head -5
echo ""
systemctl status orion-mcp.service --no-pager -l | head -5
echo ""
echo "Health Check:"
/opt/orion/health_check.py 2>/dev/null || echo "  API not responding"
echo ""
echo "Logs (last 5 lines):"
journalctl -u orion.service -n 5 --no-pager
STATUSEOF
chmod +x /usr/local/bin/orion-status

# 16. Create restart script
cat > /usr/local/bin/orion-restart << 'RESTATEOF'
#!/bin/bash
echo "Restarting ORION..."
systemctl restart orion.service
systemctl restart orion-mcp.service
echo "ORION restarted."
RESTATEOF
chmod +x /usr/local/bin/orion-restart

# Done
echo ""
echo "============================================"
echo -e "${GREEN}  ORION Deployed Successfully!${NC}"
echo "============================================"
echo ""
echo "Services:"
echo "  - ORION API:  http://$(hostname -I | awk '{print $1}'):$ORION_PORT"
echo "  - MCP Server: $(hostname -I | awk '{print $1}'):$MCP_PORT"
echo "  - Web UI:     http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "Commands:"
echo "  orion-status    - Check ORION status"
echo "  orion-restart   - Restart ORION"
echo "  journalctl -u orion -f  - View logs"
echo ""
echo "Remote MCP Config (opencode/Claude Desktop):"
echo '  "mcpServers": {'
echo '    "orion-remote": {'
echo '      "type": "sse",'
echo "      \"url\": \"http://$(hostname -I | awk '{print $1}'):$MCP_PORT/sse\""
echo "    }"
echo "  }"
echo ""
echo "ORION is now running 24/7 on this server!"
echo "============================================"
