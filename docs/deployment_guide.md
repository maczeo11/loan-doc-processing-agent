# FinScan AI — Production Deployment Guide

This describes the **actual** deployment setup on the single production EC2
instance. Earlier drafts of this document described a different (ARM64,
CloudWatch, `docker-compose.prod.yml`, scheduled start/stop) architecture that
was never built — treat everything below, and the scripts in `infra/`, as the
only source of truth.

## Architecture

One Ubuntu EC2 instance (`i-008fcd01dbd088e87`, `ap-south-1`, public IP
`13.207.15.137`), hybrid Docker/native:

| Component | Runtime | Why |
|---|---|---|
| PostgreSQL, Redis | Docker (`infra/docker-compose.yml`) | Stock images (`postgres:16-alpine`, `redis:7-alpine`) — never rebuilt, zero disk-growth cost from containerizing them. Ports `5432`/`6379` published to the host. |
| Caddy (reverse proxy, TLS termination) | Docker, `network_mode: host` | Stock image (`caddy:2-alpine`). Host networking so `127.0.0.1:8000` inside its config reaches the native `api` process. |
| API (`uvicorn`), Worker, Outbox Dispatcher | **Native**, via `systemd` (`infra/systemd/*.service`) | Removes the Docker image rebuild step entirely (previously ~5.7GB per custom image, rebuilt on every deploy) — faster iteration and no more unbounded EBS growth from image layers/build cache. |

This mirrors `scripts/demo-local.ps1`'s local-dev pattern (DB/Redis in Docker,
everything else native) applied to production.

**Known simplifications** (deliberate, for a fast-moving single-operator
deployment — revisit if this ever needs a second operator or stricter
isolation):
- All three systemd units run as `User=ubuntu` (the SSH/git/sudo identity),
  not a dedicated locked-down service account, even though `ec2_setup.sh`
  creates an unused `finscan` system user for that purpose.
- No GitHub Actions OIDC/IAM role exists yet for automated CI deploys — the
  `deploy` job in `.github/workflows/ci.yml` is wired up (SSM
  `AWS-RunShellScript` calling `./infra/deploy.sh $SHA`) but will fail at the
  `configure-aws-credentials` step until `secrets.FINSCAN_DEPLOY_ROLE_ARN` and
  its IAM role/OIDC provider are created — an explicit, separate decision, not
  part of this deploy model.
- `auto_https off` in `infra/Caddyfile.production` — no real domain is
  configured yet (`DOMAIN_NAME` defaults to the bare EC2 IP), so Caddy serves
  plain HTTP. Remove that line (and the `http://` prefix) once a real domain +
  DNS exists.

## One-time bootstrap (fresh box, or migrating an existing all-Docker box)

Run `infra/ec2_setup.sh` (as the `ubuntu` user), which:
1. Installs Docker (db/redis/caddy only), Python 3.11 (via deadsnakes PPA —
   matches `python:3.11-slim`, what every pinned ML dependency was actually
   tested against), Node 20, and system packages (`build-essential`,
   `tesseract-ocr`).
2. Clones/updates the repo into `/opt/finscan/app`.
3. Creates `.env` from `.env.production.example` if missing, stamps version
   metadata.
4. Runs `infra/setup_venv.sh` (venv + CPU-only torch first, then
   `requirements.txt`, then `pip install -e .`, then `npm ci && npm run
   build` for the UI).
5. Installs the three systemd unit files and `enable`s (but does not yet
   start) them — the first real start happens via `./infra/deploy.sh`, after
   `.env` has real secrets filled in.
6. Verifies (or sets up) passwordless `sudo` for the specific `systemctl`
   commands `deploy.sh` needs, so deploys stay non-interactive.

**Migrating an existing all-Docker box to this model** additionally requires,
before running `ec2_setup.sh`/`deploy.sh`:
```bash
cd /opt/finscan/app
docker compose -f infra/docker-compose.yml stop api worker outbox-dispatcher migrate caddy
docker compose -f infra/docker-compose.yml rm -f api worker outbox-dispatcher migrate caddy
docker compose -f infra/docker-compose.yml up -d db redis   # now with published ports
# Only relevant if STORAGE_BACKEND=local (production uses S3) — migrate the
# old dossiers_storage Docker volume to a host directory:
mkdir -p /opt/finscan/app/data/storage
docker run --rm -v dossiers_storage:/from -v /opt/finscan/app/data/storage:/to alpine \
    sh -c "cp -a /from/. /to/ 2>/dev/null || true"
```
Postgres/Redis data volumes (`postgres_data`, `redis_data`) are never touched.

## Deploying a release

```bash
./infra/deploy.sh              # deploys the current HEAD
./infra/deploy.sh <sha-or-tag>  # deploys an explicit ref
```

Internally: records the current release for rollback → `git fetch`+`checkout`
→ stamps `RELEASE_VERSION`/`GIT_SHA`/`BUILD_TIMESTAMP` into `.env` → ensures
Postgres/Redis are up → `infra/setup_venv.sh` (idempotent — pip/npm caches
make a no-op reinstall fast) → `alembic upgrade head` → `sudo systemctl
restart finscan-api finscan-worker finscan-outbox-dispatcher` → recreates the
Caddy container (picks up any Caddyfile/env changes) → polls
`http://localhost/health` up to 30×2s → prunes dangling Docker
images/build-cache on success (mostly routine hygiene now — stock images
don't accumulate the way custom-built ones did).

From Windows: `.\scripts\update-ec2.ps1` (runs `allow-my-ip.ps1` first, then
SSHes in and runs `deploy.sh` remotely).

## Rolling back

```bash
./infra/rollback.sh              # rolls back to the last-recorded previous release
./infra/rollback.sh <sha-or-tag>  # rolls back to an explicit ref
```

**Time-cost note**: unlike the old Docker-image-cache-based rollback (~10s,
reusing a cached image tag), there's no cached image to fall back to anymore
— rollback re-runs `setup_venv.sh` at the target ref. This is fast when
`requirements.txt`/`package-lock.json` haven't changed between the two refs
(pip/npm caches do most of the work), but can take 1–3 minutes when they have.
Acceptable for a rarely-used break-glass path — correctness (the rollback
ref's actually-pinned dependency versions) matters more than speed here.

## Operational cheat sheet

```bash
# Service status / logs
sudo systemctl status finscan-api finscan-worker finscan-outbox-dispatcher
journalctl -u finscan-api -n 100 --no-pager -f     # tail live
journalctl -u finscan-worker -n 100 --no-pager

# Restart one service without a full deploy
sudo systemctl restart finscan-api

# Docker tier (db/redis/caddy only)
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml logs -f caddy

# Health check
curl -sf http://localhost/health   # from the box
curl -sf http://13.207.15.137/health   # from anywhere
```

## CI/CD

`.github/workflows/ci.yml`'s `deploy` job calls `./infra/deploy.sh $SHA` via
AWS SSM `AWS-RunShellScript` on push to `main` — the same script described
above, unchanged in its calling contract by this deploy model. It currently
fails at the AWS-credentials step because no OIDC provider + scoped IAM role
have been created yet (`secrets.FINSCAN_DEPLOY_ROLE_ARN` doesn't exist) — a
deliberate, separate decision pending explicit sign-off, since it's a new AWS
account trust boundary. Until then, deploys are triggered manually via
`scripts/update-ec2.ps1` or by SSHing in and running `infra/deploy.sh`
directly.
