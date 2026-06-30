#!/bin/bash
# ORION VPS Setup Script
# Run this ONCE on your new VPS after getting access
#
# Usage:
#   ssh root@your-vps
#   bash vps_setup.sh
#
# After this script, ORION will be running 24/7

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  ORION Cloud VPS Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Check root
if [[ $EUID -ne 0 ]]; then
    error "Run as root: sudo bash vps_setup.sh"
fi

# ============================================
# STEP 1: System Setup
# ============================================
echo -e "${BLUE}STEP 1: System Setup${NC}"
echo "----------------------------"

log "Updating system..."
apt-get update -qq && apt-get upgrade -y -qq

log "Installing packages..."
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget htop tmux unzip \
    build-essential libffi-dev libssl-dev \
    net-tools jq

log "Setting timezone to UTC..."
timedatectl set-timezone UTC

# ============================================
# STEP 2: Create ORION User
# ============================================
echo ""
echo -e "${BLUE}STEP 2: User Setup${NC}"
echo "----------------------------"

if ! id "orion" &>/dev/null; then
    log "Creating orion user..."
    useradd -r -m -s /bin/bash orion
else
    log "User 'orion' already exists"
fi

# ============================================
# STEP 3: Install ORION
# ============================================
echo ""
echo -e "${BLUE}STEP 3: Installing ORION${NC}"
echo "----------------------------"

ORION_DIR="/opt/orion"
log "Creating directory structure..."
mkdir -p $ORION_DIR/{data,logs,config,venv}
chown -R orion:orion $ORION_DIR

log "Creating Python virtual environment..."
su - orion -c "python3 -m venv $ORION_DIR/venv"

log "Installing dependencies..."
su - orion -c "$ORION_DIR/venv/bin/pip install --upgrade pip -q"
su - orion -c "$ORION_DIR/venv/bin/pip install fastapi uvicorn aiohttp -q"

log "Creating ORION entry point..."
cat > $ORION_DIR/orion_cloud.py << 'EOF'
#!/usr/bin/env python3
"""ORION Cloud Server"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from datetime import datetime

app = FastAPI(title="ORION Cloud", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "system": "ORION Cloud",
        "version": "3.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running"
    }

@app.get("/api/info")
async def info():
    return {
        "name": "ORION System",
        "description": "Advanced AI Multi-Agent System",
        "version": "3.0",
        "modules": 67,
        "endpoints": 90,
        "tools": 45
    }

@app.get("/")
async def root():
    return {"message": "ORION Cloud is running", "status": "online"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

chown -R orion:orion $ORION_DIR

# ============================================
# STEP 4: Create Systemd Services
# ============================================
echo ""
echo -e "${BLUE}STEP 4: System Services${NC}"
echo "----------------------------"

cat > /etc/systemd/system/orion.service << 'EOF'
[Unit]
Description=ORION AI System - Cloud Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=orion
Group=orion
WorkingDirectory=/opt/orion
ExecStart=/opt/orion/venv/bin/python orion_cloud.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=ORION_ENV=production
StandardOutput=append:/opt/orion/logs/orion.log
StandardError=append:/opt/orion/logs/orion-error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable orion
systemctl start orion

log "ORION service started!"

# ============================================
# STEP 5: Firewall
# ============================================
echo ""
echo -e "${BLUE}STEP 5: Firewall${NC}"
echo "----------------------------"

if command -v ufw &> /dev/null; then
    log "Configuring UFW firewall..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw allow 8000/tcp  # ORION API
    ufw allow 8001/tcp  # MCP Server
    echo "y" | ufw enable
    log "Firewall configured"
else
    warn "UFW not found, skipping firewall setup"
fi

# ============================================
# STEP 6: Auto-Updates
# ============================================
echo ""
echo -e "${BLUE}STEP 6: Auto-Updates${NC}"
echo "----------------------------"

cat > /etc/cron.d/orion-backup << 'EOF'
# Backup ORION data daily at 3 AM
0 3 * * * orion tar -czf /opt/orion/data/backup-$(date +\%Y\%m\%d).tar.gz -C /opt/orion data ORION_SYSTEM
# Cleanup backups older than 7 days
0 4 * * * find /opt/orion/data -name "backup-*.tar.gz" -mtime +7 -delete
EOF

log "Auto-backup configured"

# ============================================
# Done
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ORION VPS Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Server IP: $SERVER_IP"
echo ""
echo "ORION Status:"
systemctl status orion --no-pager | head -5
echo ""
echo "Test it:"
echo "  curl http://$SERVER_IP:8000/api/health"
echo ""
echo "Next steps:"
echo "  1. Run: bash setup_remote.sh"
echo "  2. Configure your local opencode/Claude Desktop"
echo ""
echo "ORION is now running 24/7 on this server!"
echo "============================================"
