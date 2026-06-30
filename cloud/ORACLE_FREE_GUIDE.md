# ORION - Oracle Cloud Free Tier Guide

## Oracle Cloud Free Tier - TRULY FREE

Oracle Cloud offers **ALWAYS FREE** resources:
- **4 ARM cores** (Ampere A1)
- **24 GB RAM**
- **200 GB storage**
- **No credit card charges**
- **No time limit**

## Step-by-Step Setup

### 1. Create Oracle Cloud Account

1. Go to: https://cloud.oracle.com/free
2. Click "Start for Free"
3. Fill in your details
4. **Credit card required for verification** but you will NOT be charged
5. Verify email and log in

### 2. Create ARM Instance

1. In Oracle Cloud Console, go to: **Compute > Instances**
2. Click "Create Instance"
3. Fill in:
   - **Name**: `orion-server`
   - **Image**: Ubuntu 22.04 (or any Linux)
   - **Shape**: **Ampere A1** (ARM) - Select "VM.Standard.A1.Flex"
   - **OCPU**: 4 (max free)
   - **RAM**: 24 GB (max free)
4. Add SSH key (generate new or upload existing)
5. Click "Create"
6. Wait 2-3 minutes for instance to start

### 3. Connect to Instance

```bash
# From your local machine
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP
```

### 4. Deploy ORION

```bash
# On the instance
wget https://raw.githubusercontent.com/.../oracle_free_deploy.sh
sudo bash oracle_free_deploy.sh
```

### 5. Test

```bash
curl http://YOUR_INSTANCE_IP:8000/api/health
```

### 6. Connect Local Machine

```bash
# On your local machine
bash setup_remote.sh
```

## Dashboard

Access ORION dashboard at:
```
http://YOUR_INSTANCE_IP:8000
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/health` | Health check |
| `/api/info` | System info |
| `/` | Dashboard |

## Troubleshooting

### Check Status
```bash
sudo systemctl status orion
```

### View Logs
```bash
sudo journalctl -u orion -f
```

### Restart
```bash
sudo systemctl restart orion
```

## Cost

**$0.00** - Oracle Cloud Free Tier is always free!

## Security

- Change SSH port
- Set up firewall
- Use strong passwords
- Enable 2FA on Oracle Cloud

## Next Steps

1. Set up SSL with Let's Encrypt
2. Configure domain name
3. Enable monitoring
4. Set up backups

---

**ORION is now running 24/7 for FREE!**
