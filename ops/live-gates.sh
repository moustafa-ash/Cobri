#!/usr/bin/env bash
set -euo pipefail

test -r /etc/cobri/candidate.env || { echo "candidate environment is required" >&2; exit 1; }
set -a
. /etc/cobri/candidate.env
. /etc/cobri/docker.env
set +a
test "${COBRI_RUN_LIVE_PROVIDERS:-}" = 1 || { echo "COBRI_RUN_LIVE_PROVIDERS=1 is required" >&2; exit 1; }
test "${COBRI_RUN_LIVE_AUTH:-}" = 1 || { echo "COBRI_RUN_LIVE_AUTH=1 is required" >&2; exit 1; }
test -n "${COBRI_LIVE_ACCESS_TOKEN:-}" || { echo "COBRI_LIVE_ACCESS_TOKEN is required" >&2; exit 1; }

cd /opt/cobri/candidate/current
COBRI_RUN_LIVE_AUTH=1 COBRI_RUN_LIVE_PROVIDERS=1 \
  /usr/local/bin/uv run --project backend --locked pytest \
  backend/tests/test_live_auth.py backend/tests/test_live_providers.py -q -p no:cacheprovider

runuser -u cobri -- env XDG_RUNTIME_DIR="/run/user/$(id -u cobri)" DOCKER_HOST="$DOCKER_HOST" \
  /usr/local/bin/uv run --project backend --locked python -c \
  'from cobri.sandbox.docker_runner import DockerSandbox; r=DockerSandbox("python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254", 3).run("def double(n): return n * 2", ["assert double(4) == 8"]); assert r.passed'

echo "live provider, Auth0, and rootless Docker gates passed"
