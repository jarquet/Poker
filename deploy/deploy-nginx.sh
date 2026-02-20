#!/bin/bash
# Deploy nginx HTTPS config for Poker app.
# 1. Creates self-signed SSL certs (if missing)
# 2. Copies nginx config to /etc/nginx/conf.d/
# Run with: sudo ./deploy-nginx.sh
# From project root: sudo ./deploy/deploy-nginx.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="${SCRIPT_DIR}/nginx/poker-https.conf"
NGINX_DEST="/etc/nginx/conf.d/poker-https.conf"

# Ensure we're root
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run with sudo." >&2
    exit 1
fi

if [ ! -f "$NGINX_CONF" ]; then
    echo "Config not found: $NGINX_CONF" >&2
    exit 1
fi

# Create certs if they don't exist
if [ ! -f /etc/nginx/ssl/poker.crt ] || [ ! -f /etc/nginx/ssl/poker.key ]; then
    echo "Creating self-signed certificates..."
    "$SCRIPT_DIR/create-ssl-certs.sh"
else
    echo "Certificates already exist, skipping."
fi

# Copy nginx config
echo "Copying nginx config to $NGINX_DEST"
cp "$NGINX_CONF" "$NGINX_DEST"

# Test nginx config
echo "Testing nginx configuration..."
nginx -t

echo ""
echo "Deploy complete."
echo "Reload nginx: sudo systemctl reload nginx"
echo "Access app: https://localhost:3077"
