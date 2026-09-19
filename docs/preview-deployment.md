# Cobri preview deployment runbook

This is a preview-only deployment. Do not use production credentials, learner data, or paid resources without explicit approval.

## Shared prerequisites

- GitHub access to `moustafa-ash/Cobri` and permission to run Actions.
- Auth0 preview application and test user.
- Groq and/or OpenRouter preview API keys.
- Never paste secrets into chat, commits, issues, or workflow logs.
- The GitHub workflow is `.github/workflows/preview-release.yml`; it creates a tag only after candidate gates pass.

## Option A: OCI Always Free VM (full preview path)

OCI is the required path for the complete gate because it provides a real Linux host for PostgreSQL, the worker, Caddy, and rootless Docker.

### 1. Create the tenancy

1. Create one Oracle Cloud Free Tier account using accurate billing and contact information.
2. Choose the immutable home region `me-jeddah-1`.
3. Complete Oracle phone/payment verification. Do not create duplicate accounts to work around capacity.
4. In the Console, create compartment `cobri-preview` and a least-privilege deployment user.

### 2. Create the host

1. Create a VCN and public subnet with inbound TCP `80` and `443` open.
2. Restrict TCP `22` to the maintainer IP only. Keep PostgreSQL and FastAPI loopback-only.
3. Create an Ubuntu ARM64 `VM.Standard.A1.Flex` instance with 2 OCPUs, 12 GB RAM, and a 50 GB boot volume.
4. Allocate and attach a reserved public IPv4 address.
5. If OCI reports `out of host capacity`, stop and retry later; do not switch region or select paid compute.
6. Record the reserved IP and derive:
   - Preview: `https://<ip>.sslip.io`
   - Candidate: `https://candidate-<ip>.sslip.io`

### 3. Install the host bundle

From a checkout of the exact pushed commit:

```bash
ssh ubuntu@<ip>
git clone https://github.com/moustafa-ash/Cobri.git /tmp/cobri
cd /tmp/cobri
sudo bash ops/bootstrap-host.sh
```

Create root-readable files, never commit them:

- `/etc/cobri/cobri.env`: production preview URL, `COBRI_PG_DSN`, Auth0, provider keys, Caddy email, and runtime settings.
- `/etc/cobri/candidate.env`: isolated candidate database URL and candidate provider/Auth0 settings.
- `/etc/cobri/docker.env`: rootless Docker socket and pinned sandbox image settings.

Set `COBRI_EVALUATION_MODE=provider`, `COBRI_AUTO_CREATE_SCHEMA=false`, and keep `COBRI_SANDBOX_ENABLED=true` only on the OCI host after the pinned ARM64 sandbox image has been tested.

Verify:

```bash
systemctl status cobri-api cobri-worker
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
```

### 4. Configure GitHub Environment `preview`

Create the protected `preview` Environment and require operator approval. Add these Environment variables:

- `PREVIEW_URL=https://<ip>.sslip.io`
- `PREVIEW_CANDIDATE_URL=https://candidate-<ip>.sslip.io`

Generate a deployment key locally and install only the public key on the host:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/cobri-preview
ssh-copy-id -i ~/.ssh/cobri-preview.pub ubuntu@<ip>
ssh-keyscan -H <ip>.sslip.io > /tmp/cobri-known-hosts
```

Add these Environment secrets without exposing them in chat:

- `PREVIEW_HOST`: reserved IP or its `sslip.io` hostname.
- `PREVIEW_SSH_USER`: normally `ubuntu`.
- `PREVIEW_SSH_PRIVATE_KEY`: contents of `~/.ssh/cobri-preview`.
- `PREVIEW_KNOWN_HOSTS`: contents of `/tmp/cobri-known-hosts`.
- `PREVIEW_LIVE_ACCESS_TOKEN`: Auth0 API access token for the dedicated preview test user.

### 5. Run the release

1. Start **Preview release** manually with an unused version such as `v0.2.0-preview.1`.
2. Approve the protected Environment only after reviewing the candidate evidence.
3. Confirm OCI candidate health, sandbox cleanup, migrations, provider checks, and Auth0 checks.
4. The workflow creates the annotated tag only after candidate validation, then promotes the exact artifact.
5. On failure, use `/opt/cobri/ops/rollback.sh <previous-tag>` and retain the failed tag for auditability.

## Option B: Render Free (demo-only path)

Render is suitable only for a reduced demo. Render requires card verification in the current signup flow, and its free Postgres is temporary and has no backups. Render services do not provide the host-level rootless Docker sandbox required by the full gate.

### 1. Create the services

1. Complete Render account verification.
2. Open **New → Blueprint**.
3. Select `moustafa-ash/Cobri` and apply the tracked `render.yaml`.
4. Use the free plans for `cobri-api`, `cobri-worker`, `cobri-frontend`, and `cobri-db`.
5. Enter the marked Auth0, Groq, OpenRouter, and frontend variables in the Render dashboard.

The blueprint intentionally sets `COBRI_SANDBOX_ENABLED=false`. Do not claim the sandbox gate passed on Render.

### 2. Verify the demo

```bash
curl -fsS https://cobri-api.onrender.com/health/live
curl -fsS https://cobri-api.onrender.com/health/ready
```

Run the deterministic browser checks against the frontend URL after the service wakes. Record cold-start, database expiry, provider, authentication, and sandbox limitations as explicit skipped or failed gates.

### 3. Cleanup and data policy

Render free Postgres is not a durable preview database. Export any data needed for debugging, then delete the demo services when the review ends. Never use real learner data.

## Evidence record

For every run, record the commit SHA, deployment target, URLs, artifact checksums, and each gate as `live`, `mocked`, `deterministic`, `passed`, `failed`, or `skipped`. Any mandatory skipped gate blocks tagging.
