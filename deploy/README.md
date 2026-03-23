# Deployment

## DigitalOcean

The recommended way to run Jentic Mini — on a separate machine from your OpenClaw instance. This maintains a hard security boundary: the agent cannot access the Docker environment or database directly.

### What you need

- A [DigitalOcean](https://cloud.digitalocean.com) account
- A domain name (optional, but recommended for TLS)

### Step 1 — Create a droplet

1. Log into DigitalOcean and click **Create → Droplets**
2. Choose **Ubuntu 22.04 LTS** or **24.04 LTS**
3. Pick a size — **Basic, $6/month** (1 vCPU, 1 GB RAM) is sufficient for personal use
4. Choose a region close to you
5. Under **Advanced Options**, enable **User Data** and paste the contents of `cloud-init-do.yml`
6. Click **Create Droplet**

### Step 2 — Wait for boot (~2 minutes)

The cloud-init script runs automatically on first boot. It:
- Installs Docker
- Generates a secure vault encryption key
- Pulls the Jentic Mini Docker image
- Starts the container on port 8900
- Configures the firewall (ports 22 and 8900 open)

### Step 3 — Complete first-run setup

Visit `http://<droplet-ip>:8900` in your browser and follow the setup wizard to create your admin account.

### Step 4 — Connect your OpenClaw agent

In your OpenClaw agent, run the Jentic skill install flow and provide:
- **URL:** `http://<droplet-ip>:8900`
- The agent key generated during setup

### Step 5 (optional) — Add a domain + TLS

Point a DNS A record at your droplet IP, then SSH in and run:

```bash
apt install -y caddy
cat > /etc/caddy/Caddyfile <<EOF
your-domain.com {
    reverse_proxy localhost:8900
}
EOF
systemctl reload caddy
ufw allow 443/tcp
```

Then update the public hostname in `/opt/jentic-mini/.env`:
```
JENTIC_PUBLIC_HOSTNAME=your-domain.com
```

And restart:
```bash
cd /opt/jentic-mini && docker compose restart
```

### Updating

SSH into the droplet and run:

```bash
jentic-update
```

This pulls the latest image and restarts the container. Your data directory (`/opt/jentic-mini/data/`) is preserved across updates.
