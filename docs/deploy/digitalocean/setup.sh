#!/bin/bash
# Jentic Mini - DigitalOcean initialization script
# When creating a droplet: expand Advanced Options, check "Add Initialization scripts (free)"
# and paste this entire file into the field that appears.
# Once complete (~10 min), visit http://<droplet-ip>:8900 to complete setup.
set -e

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Get public IP for initial hostname
PUBLIC_IP=$(curl -sf http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address || curl -sf https://api.ipify.org)
mkdir -p /opt/jentic-mini
echo "JENTIC_PUBLIC_HOSTNAME=${PUBLIC_IP}" > /opt/jentic-mini/jentic-mini.env

# Pull and start Jentic Mini
docker run -d \
  --name jentic-mini \
  --restart unless-stopped \
  -p 8900:8900 \
  -v jentic-mini-data:/app/data \
  --env-file /opt/jentic-mini/jentic-mini.env \
  ghcr.io/jentic/jentic-mini:latest

# Write update script
cat > /usr/local/bin/jentic-update << 'UPDATEEOF'
#!/bin/bash
set -e
echo "Pulling latest Jentic Mini image..."
docker pull ghcr.io/jentic/jentic-mini:latest
docker stop jentic-mini && docker rm jentic-mini
docker run -d \
  --name jentic-mini \
  --restart unless-stopped \
  -p 8900:8900 \
  -v jentic-mini-data:/app/data \
  --env-file /opt/jentic-mini/jentic-mini.env \
  ghcr.io/jentic/jentic-mini:latest
echo "Done. Jentic Mini updated."
UPDATEEOF
chmod +x /usr/local/bin/jentic-update

# Configure firewall
ufw allow 22/tcp
ufw allow 8900/tcp
ufw --force enable
