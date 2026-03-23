# Deployment

## DigitalOcean (recommended)

The quickest way to run Jentic Mini on a separate machine — which is strongly recommended for security (see [SECURITY.md](../docs/SECURITY.md)).

### Steps

1. Create a new Ubuntu 22.04 or 24.04 droplet on [DigitalOcean](https://cloud.digitalocean.com)
2. Under **Advanced Options → User Data**, paste the contents of `cloud-init-do.yml`
3. Create the droplet — Jentic Mini will be running at `http://<droplet-ip>:8900` within ~2 minutes
4. Visit that URL to complete first-run setup

A $6/month Basic droplet (1 vCPU, 1 GB RAM) is sufficient for personal use.

### Updating

SSH into the droplet and run:

```bash
jentic-update
```

This pulls the latest image and restarts the container. Your data directory is preserved.

### TLS / custom domain

Once you have a domain pointed at the droplet, add Caddy as a reverse proxy:

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

Then update `JENTIC_PUBLIC_HOSTNAME` in `/opt/jentic-mini/.env` and restart:

```bash
cd /opt/jentic-mini && docker compose restart
```

## Railway

`railway.json` is provided for Railway deployments. Note that Railway uses managed volumes rather than bind mounts — configure a Volume mounted at `/app/data` in the Railway dashboard after deploying.

> **Note:** Railway auto-deploys on new image pushes. Ensure DB migrations are in place before enabling auto-deploy to avoid schema breakage on update (see [issue #13](https://github.com/jentic/jentic-mini/issues/13)).
