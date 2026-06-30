#!/bin/bash
# ORION Oracle Cloud Free Tier Deploy
# Oracle Cloud ALWAYS FREE: 4 ARM cores, 24GB RAM, 200GB storage
#
# This is TRULY FREE - no credit card charges, forever free
#
# Steps:
#   1. Create Oracle Cloud account (free)
#   2. Create ARM instance (free)
#   3. Run this script on the instance
#
# Usage:
#   bash oracle_free_deploy.sh

set -e

echo "============================================"
echo "  ORION - Oracle Cloud Free Tier Deploy"
echo "============================================"
echo ""
echo "Oracle Cloud Free Tier includes:"
echo "  - 4 ARM cores (Ampere A1)"
echo "  - 24 GB RAM"
echo "  - 200 GB storage"
echo "  - ALWAYS FREE (no charges)"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Check root
if [[ $EUID -ne 0 ]]; then
    error "Run as root: sudo bash oracle_free_deploy.sh"
fi

# ============================================
# Step 1: System Setup
# ============================================
echo -e "${BLUE}Step 1: System Setup${NC}"
echo "----------------------------"

log "Updating system..."
apt-get update -qq && apt-get upgrade -y -qq

log "Installing dependencies..."
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget htop tmux unzip \
    build-essential libffi-dev libssl-dev

# ============================================
# Step 2: Create ORION
# ============================================
echo ""
echo -e "${BLUE}Step 2: Installing ORION${NC}"
echo "----------------------------"

ORION_DIR="/opt/orion"
log "Creating directories..."
mkdir -p $ORION_DIR/{data,logs,config}
useradd -r -m -s /bin/bash orion 2>/dev/null || true
chown -R orion:orion $ORION_DIR

log "Creating Python environment..."
su - orion -c "python3 -m venv $ORION_DIR/venv"
su - orion -c "$ORION_DIR/venv/bin/pip install --upgrade pip -q"
su - orion -c "$ORION_DIR/venv/bin/pip install fastapi uvicorn aiohttp orjson -q"

log "Creating ORION server..."
cat > $ORION_DIR/orion_server.py << 'EOF'
#!/usr/bin/env python3
"""ORION Oracle Cloud Free Server"""
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
        "system": "ORION Cloud Free",
        "version": "3.0",
        "timestamp": datetime.now().isoformat(),
        "provider": "Oracle Cloud Free Tier",
        "resources": "4 ARM cores, 24GB RAM"
    }

@app.get("/api/info")
async def info():
    return {
        "name": "ORION System",
        "description": "Advanced AI Multi-Agent System",
        "version": "3.0",
        "modules": 67,
        "endpoints": 90,
        "tools": 45,
        "provider": "Oracle Cloud Free Tier"
    }

@app.get("/")
async def root():
    return {"message": "ORION is running on Oracle Cloud Free Tier!", "status": "online"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

chown -R orion:orion $ORION_DIR

# ============================================
# Step 3: Systemd Service
# ============================================
echo ""
echo -e "${BLUE}Step 3: System Service${NC}"
echo "----------------------------"

cat > /etc/systemd/system/orion.service << 'EOF'
[Unit]
Description=ORION AI System - Oracle Cloud Free
After=network-online.target

[Service]
Type=simple
User=orion
Group=orion
WorkingDirectory=/opt/orion
ExecStart=/opt/orion/venv/bin/python orion_server.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable orion
systemctl start orion

log "ORION service started!"

# ============================================
# Step 4: Firewall
# ============================================
echo ""
echo -e "${BLUE}Step 4: Firewall${NC}"
echo "----------------------------"

if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8000/tcp
    echo "y" | ufw enable
    log "Firewall configured"
fi

# ============================================
# Done
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ORION Deployed on Oracle Cloud FREE!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

SERVER_IP=$(curl -s ifconfig.me)
echo "Your ORION URL: http://$SERVER_IP:8000"
echo ""
echo "Test it:"
echo "  curl http://$SERVER_IP:8000/api/health"
echo ""
echo "ORION is now running 24/7 for FREE!"
echo "============================================"
