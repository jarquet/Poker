#!/bin/bash
# Create self-signed SSL certificates for nginx HTTPS (Poker app).
# Run with: sudo ./create-ssl-certs.sh
# Certificates are written to /etc/nginx/ssl/

set -e

SSL_DIR="/etc/nginx/ssl"
CERT_FILE="${SSL_DIR}/poker.crt"
KEY_FILE="${SSL_DIR}/poker.key"
DAYS=365

# Ensure we're root
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run with sudo." >&2
    exit 1
fi

mkdir -p "$SSL_DIR"

if [ -f "$CERT_FILE" ] || [ -f "$KEY_FILE" ]; then
    echo "Certificates already exist at ${SSL_DIR}/" >&2
    echo "Delete poker.crt and poker.key first to regenerate." >&2
    exit 1
fi

echo "Generating self-signed certificate..."
openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/CN=localhost/O=Poker/C=US"

chmod 644 "$CERT_FILE"
chmod 600 "$KEY_FILE"

echo "Done. Certificates created:"
echo "  $CERT_FILE"
echo "  $KEY_FILE"
