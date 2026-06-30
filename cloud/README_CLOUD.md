# ORION Cloud - Quick Deploy Guide

## Option 1: One-Click Deploy (Recommended)

```bash
# On your VPS (as root):
wget -qO- https://raw.githubusercontent.com/.../deploy.sh | bash
```

## Option 2: Manual Deploy

### Step 1: Prepare VPS

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Run setup
bash vps_setup.sh
```

### Step 2: Upload ORION Code

```bash
# From your local machine
scp -r /path/to/ORION_SYSTEM root@your-vps-ip:/opt/orion/

# Or clone from git
ssh root@your-vps-ip
cd /opt/orion
git clone https://github.com/your-repo/orion.git .
```

### Step 3: Install & Start

```bash
# On VPS
cd /opt/orion
bash deploy.sh
```

### Step 4: Connect Local Machine

```bash
# On your local machine
bash setup_remote.sh
```

## Option 3: Docker Deploy

```bash
# On VPS
cd /opt/orion
docker compose -f docker-compose.cloud.yml up -d
```

## VPS Providers

### DigitalOcean ($12/mo)
```bash
# Create droplet:
# - Ubuntu 22.04
# - 2 vCPU, 4GB RAM
# - 40GB SSD
# - SSH key enabled
```

### AWS Lightsail ($10/mo)
```bash
# Create instance:
# - Ubuntu 22.04
# - 2 vCPU, 4GB RAM
# - 40GB SSD
```

### Hetzner ($7/mo)
```bash
# Create server:
# - Ubuntu 22.04
# - 2 vCPU, 4GB RAM
# - 40GB SSD
```

## Verify Deployment

```bash
# Test API
curl http://your-vps-ip:8000/api/health

# Test MCP
curl http://your-vps-ip:8001/sse
```

## Troubleshooting

```bash
# Check status
orion-status

# View logs
journalctl -u orion -f

# Restart
orion-restart
```
