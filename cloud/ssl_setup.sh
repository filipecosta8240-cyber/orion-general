#!/bin/bash
# ORION SSL Setup (Let's Encrypt)
# Run this on the VPS to enable HTTPS
#
# Usage:
#   bash ssl_setup.sh your-domain.com your-email@domain.com

set -e

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo bash ssl_setup.sh domain.com email@domain.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: bash ssl_setup.sh your-domain.com your-email@domain.com"
    exit 1
fi

echo "Setting up SSL for $DOMAIN..."

# Install certbot
apt-get install -y certbot

# Create certbot webroot
mkdir -p /var/www/certbot

# Get certificate
certbot certonly --webroot -w /var/www/certbot -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

# Create SSL directory
mkdir -p /opt/orion/nginx/ssl

# Copy certificates
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /opt/orion/nginx/ssl/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /opt/orion/nginx/ssl/

# Update nginx config
sed -i "s/your-domain.com/$DOMAIN/g" /opt/orion/nginx/nginx.conf

# Reload nginx
docker compose -f /opt/orion/docker-compose.cloud.yml restart nginx

# Auto-renew cron
cat > /etc/cron.d/certbot-renew << EOF
0 12 * * * root certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/*.pem /opt/orion/nginx/ssl/ && docker compose -f /opt/orion/docker-compose.cloud.yml restart nginx
EOF

echo "SSL setup complete!"
echo "https://$DOMAIN is now accessible"
