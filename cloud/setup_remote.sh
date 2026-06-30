#!/bin/bash
# ORION Remote Setup Script
# Run this on your LOCAL machine to connect to ORION cloud
#
# Usage:
#   bash setup_remote.sh
#
# This will:
#   1. Generate SSH tunnel config
#   2. Create opencode.jsonc config
#   3. Create Claude Desktop config
#   4. Test connection

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  ORION Remote Connection Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
prompt() { echo -e "${BLUE}[?]${NC} $1"; }

# Get server info
prompt "Enter your VPS IP address:"
read VPS_IP

prompt "Enter SSH port (default: 22):"
read SSH_PORT
SSH_PORT=${SSH_PORT:-22}

prompt "Enter SSH username (default: root):"
read SSH_USER
SSH_USER=${SSH_USER:-root}

prompt "Enter ORION API port (default: 8000):"
read ORION_PORT
ORION_PORT=${ORION_PORT:-8000}

prompt "Enter MCP port (default: 8001):"
read MCP_PORT
MCP_PORT=${MCP_PORT:-8001}

echo ""
log "Testing connection to VPS..."

# Test SSH connection
if ssh -p $SSH_PORT -o ConnectTimeout=5 -o BatchMode=yes $SSH_USER@$VPS_IP "echo ok" &>/dev/null; then
    log "SSH connection successful!"
else
    warn "Could not auto-test SSH. Make sure SSH key is set up."
    echo "  Run: ssh-copy-id -p $SSH_PORT $SSH_USER@$VPS_IP"
fi

# Test ORION API
if curl -s --connect-timeout 5 "http://$VPS_IP:$ORION_PORT/api/health" | grep -q "online"; then
    log "ORION API is responding!"
else
    warn "ORION API not reachable. Make sure ORION is running on the VPS."
fi

echo ""
echo -e "${BLUE}Configuration Files${NC}"
echo "----------------------------"

# ============================================
# OpenCode Config
# ============================================
OPENCODE_DIR="$HOME/.config/opencode"
mkdir -p "$OPENCODE_DIR"

cat > "$OPENCODE_DIR/opencode.jsonc" << EOF
{
  "mcpServers": {
    "orion-remote": {
      "type": "sse",
      "url": "http://$VPS_IP:$MCP_PORT/sse",
      "description": "ORION Cloud Server - 45+ AI tools",
      "env": {},
      "alwaysAllow": [
        "health_check",
        "tiered_memory_stats",
        "security_dashboard",
        "kg_advanced_stats",
        "task_status"
      ]
    }
  }
}
EOF

log "OpenCode config created: $OPENCODE_DIR/opencode.jsonc"

# ============================================
# Claude Desktop Config
# ============================================
CLAUDE_DIR="$APPDATA/Claude"
mkdir -p "$CLAUDE_DIR"

cat > "$CLAUDE_DIR/claude_desktop_config.json" << EOF
{
  "mcpServers": {
    "orion-remote": {
      "url": "http://$VPS_IP:$MCP_PORT/sse",
      "description": "ORION Cloud Server"
    }
  }
}
EOF

log "Claude Desktop config created: $CLAUDE_DIR/claude_desktop_config.json"

# ============================================
# SSH Tunnel Script
# ============================================
cat > "$HOME/orion_tunnel.sh" << TUNNELEOF
#!/bin/bash
# ORION SSH Tunnel
# Creates a secure tunnel to ORION VPS
#
# Usage:
#   bash orion_tunnel.sh

echo "Creating SSH tunnel to ORION..."
echo "  VPS: $VPS_IP:$MCP_PORT -> localhost:$MCP_PORT"
echo "  Press Ctrl+C to stop"
echo ""

ssh -p $SSH_PORT -N -L $MCP_PORT:localhost:$MCP_PORT $SSH_USER@$VPS_IP
TUNNELEOF

chmod +x "$HOME/orion_tunnel.sh"
log "Tunnel script created: ~/orion_tunnel.sh"

# ============================================
# Quick Commands
# ============================================
cat > "$HOME/orion_cmd.sh" << CMDEOF
#!/bin/bash
# ORION Quick Commands
#
# Usage:
#   bash orion_cmd.sh status
#   bash orion_cmd.sh logs
#   bash orion_cmd.sh restart
#   bash orion_cmd.sh health

VPS_IP="$VPS_IP"
SSH_PORT="$SSH_PORT"
SSH_USER="$SSH_USER"
ORION_PORT="$ORION_PORT"

case "\$1" in
    status)
        echo "Checking ORION status..."
        ssh -p $SSH_PORT $SSH_USER@$VPS_IP "systemctl status orion --no-pager | head -10"
        ;;
    logs)
        echo "Showing ORION logs..."
        ssh -p $SSH_PORT $SSH_USER@$VPS_IP "journalctl -u orion -f"
        ;;
    restart)
        echo "Restarting ORION..."
        ssh -p $SSH_PORT $SSH_USER@$VPS_IP "systemctl restart orion"
        echo "ORION restarted."
        ;;
    health)
        echo "Health check..."
        curl -s "http://$VPS_IP:$ORION_PORT/api/health" | jq .
        ;;
    *)
        echo "Usage: bash orion_cmd.sh [status|logs|restart|health]"
        ;;
esac
CMDEOF

chmod +x "$HOME/orion_cmd.sh"
log "Quick commands created: ~/orion_cmd.sh"

# ============================================
# Done
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Remote Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "ORION Cloud: http://$VPS_IP:$ORION_PORT"
echo "MCP Server:  http://$VPS_IP:$MCP_PORT/sse"
echo ""
echo "Quick Commands:"
echo "  bash ~/orion_cmd.sh status   - Check ORION status"
echo "  bash ~/orion_cmd.sh health   - Health check"
echo "  bash ~/orion_cmd.sh logs     - View logs"
echo "  bash ~/orion_cmd.sh restart  - Restart ORION"
echo "  bash ~/orion_tunnel.sh       - SSH tunnel"
echo ""
echo "Restart opencode/Claude Desktop to use remote ORION!"
echo "============================================"
