# Deployment

## DigitalOcean

The recommended way to run Jentic Mini - on a separate machine from your OpenClaw instance. This maintains a hard security boundary: the agent cannot access the Docker environment or database directly.

### What you need

- A [DigitalOcean](https://cloud.digitalocean.com) account
- A domain name (optional, but recommended for TLS)

### Step 1 - Create a droplet

1. Log into DigitalOcean and click **Create -> Droplets**
2. Choose **Ubuntu 22.04 LTS** or **24.04 LTS**
3. Pick a size - **Basic, $6/month** (1 vCPU, 1 GB RAM) is sufficient for personal use
4. Choose a region close to you
5. Expand **Advanced Options** and check **Add Initialization scripts (free)** - paste the contents of `setup.sh` into the field that appears
6. Click **Create Droplet**

### Step 2 - Wait for boot (~5 minutes)

The initialization script runs automatically on first boot. It:
- Installs Docker
- Detects the droplet's public IP and sets it as `JENTIC_PUBLIC_HOSTNAME`
- Pulls `ghcr.io/jentic/jentic-mini:latest` and starts the container
- Creates a named Docker volume (`jentic-mini-data`) for persistent data storage
- Adds a `jentic-update` helper script for future updates
- Configures the firewall (ports 22 and 8900 open)

> **Vault key:** Jentic Mini auto-generates and persists an encryption key for the credentials vault on first run. It's stored inside the `jentic-mini-data` volume and survives updates.

To check when it's ready, poll the health endpoint:

```bash
curl http://<droplet-ip>:8900/health
```

It will return `connection refused` until setup is complete, then respond with `{"status":"setup_required"}` or `{"status":"ok"}`. You can also SSH into the droplet and run `docker logs jentic-mini` to see progress.

### Step 3 - Connect your OpenClaw agent

In your OpenClaw agent, run the Jentic skill install flow and provide:
- **URL:** `http://<droplet-ip>:8900`

The agent will generate its API key automatically on first connection.

### Step 4 - Complete first-run setup

Visit `http://<droplet-ip>:8900` in your browser and follow the setup wizard to create your admin account.

### Step 5 (optional) - Add a domain + TLS

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

Then update the public hostname:

```bash
sed -i 's/JENTIC_PUBLIC_HOSTNAME=.*/JENTIC_PUBLIC_HOSTNAME=your-domain.com/' /opt/jentic-mini/jentic-mini.env
docker restart jentic-mini
```

### Step 5b (optional) - Mounting under a path prefix

Want Jentic Mini to share a domain with other apps (e.g. `your-domain.com/jentic`)?
Use Caddy's `handle_path` directive to strip the prefix before forwarding, and pin
the prefix on the container so the SPA bundle, hand-rolled docs, and self-links
resolve under the mount.

```caddyfile
your-domain.com {
    handle_path /jentic/* {
        reverse_proxy localhost:8900
    }
    # other apps on the same domain go here
}
```

```bash
cat >> /opt/jentic-mini/jentic-mini.env <<EOF
JENTIC_ROOT_PATH=/jentic
JENTIC_PUBLIC_BASE_URL=https://your-domain.com/jentic
EOF
docker restart jentic-mini
```

`JENTIC_PUBLIC_BASE_URL` must include the prefix — the OAuth issuer is pinned to
this value and is security-critical. Operators must set both env vars when mounting.

### Updating

SSH into the droplet and run:

```bash
jentic-update
```

This pulls the latest image, restarts the container, and preserves all data in the `jentic-mini-data` volume.
