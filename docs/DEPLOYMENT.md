# VLearn deployment

## Architecture

The Docker image contains application code and Python dependencies only. Lecture files, transcripts, chunks, and embeddings stay on the server at:

```text
/home/tu/hosting/vlearn-notebooklm/materials/
```

Compose mounts that directory read-only into `/app/materials`. Therefore a code deploy does not rebuild embeddings, and an artifact sync does not rebuild the image.

## One-time server bootstrap

On the Debian server:

```bash
mkdir -p /home/tu/hosting/vlearn-notebooklm/materials/{raw,derived}
cd /home/tu/hosting/vlearn-notebooklm
install -m 600 /dev/null .env
```

Create `.env` directly on the server with the same variables as `.env.example`. The file must contain the server-side LLM key and model before starting Compose.

Populate `.env` with the server-side LLM key and model. Do not commit this file. The server must also be logged in to GHCR if the package is private:

```bash
docker login ghcr.io
```

From the development machine, upload the prepared lecture artifacts once:

```bash
DEPLOY_HOST=debian bash scripts/sync_artifacts.sh
```

The command only copies `materials/raw` and `materials/derived`; it never runs ingestion or embedding.

## GitHub configuration

Add these repository Actions secrets:

```text
TS_OAUTH_CLIENT_ID
TS_OAUTH_SECRET
DEPLOY_HOST       # server Tailscale IP or MagicDNS name
DEPLOY_USER       # usually tu
DEPLOY_SSH_KEY    # private key whose public key is authorized on Debian
DEPLOY_PATH       # /home/tu/hosting/vlearn-notebooklm
GHCR_READ_USERNAME # GitHub username with read access to the package
GHCR_READ_TOKEN    # GitHub PAT classic with read:packages only
```

The Tailscale OAuth client needs a tag accepted by the tailnet ACL. The workflow runs CI on pull requests. Deployment is currently manual via `workflow_dispatch`, so merging to `main` does not contact the server until deployment setup is ready. Enable GitHub branch protection and require the `CI / test` check before merging.

## Nginx Proxy Manager

Create a Proxy Host in NPM with:

```text
Domain: the chosen public domain
Forward scheme: http
Forward host: vlearn-notebooklm
Forward port: 8501
Websockets: enabled
```

The Compose service joins the existing external Docker network `homelab`, which is also used by NPM. Do not use `127.0.0.1` as the upstream host inside NPM; that address refers to the NPM container itself.

Request the SSL certificate in NPM and force HTTPS. Do not expose port 8501 directly to the Internet; Compose binds it to loopback.

ngrok is useful for a temporary demo tunnel, but it is not part of production deployment because the VPS already has NPM and a stable domain.

## Existing Cloudflare Tunnel

The server already runs `cloudflared.service` from `/etc/cloudflared/config.yml`. To expose VLearn directly at `tutran-dev.id.vn`, add this ingress rule before the final 404 rule:

```yaml
  - hostname: tutran-dev.id.vn
    service: http://127.0.0.1:8501
```

Then reload it on the server:

```bash
sudo systemctl restart cloudflared
```

This route is independent of NPM. Use either this direct Cloudflare route or an NPM Proxy Host for VLearn, not both for the same hostname.

## Rollback

The workflow tags every image with its commit SHA. On the server, set `IMAGE_TAG` to a known good SHA and run:

```bash
cd /home/tu/hosting/vlearn-notebooklm
IMAGE_TAG=<known-good-sha> docker compose pull
IMAGE_TAG=<known-good-sha> docker compose up -d
```
