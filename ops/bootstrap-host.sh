#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "run as root" >&2
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl docker.io fuse-overlayfs postgresql postgresql-contrib \
  python3-venv slirp4netns uidmap

command -v caddy >/dev/null || {
  echo "caddy is required on the host; install it from the vendor repository" >&2
  exit 1
}
command -v uv >/dev/null || {
  echo "uv is required on the host; install the pinned version before deployment" >&2
  exit 1
}

id cobri >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin cobri
install -d -o cobri -g cobri -m 0750 /opt/cobri/releases /opt/cobri/candidate /var/lib/cobri
install -d -o root -g cobri -m 0750 /etc/cobri /opt/cobri/ops /etc/caddy
install -d -o root -g root -m 0755 /etc/systemd/system/caddy.service.d
install -m 0644 ops/cobri-api.service /etc/systemd/system/cobri-api.service
install -m 0644 ops/cobri-worker.service /etc/systemd/system/cobri-worker.service
install -m 0644 ops/cobri-candidate-api.service /etc/systemd/system/cobri-candidate-api.service
install -m 0644 ops/cobri-candidate-worker.service /etc/systemd/system/cobri-candidate-worker.service
install -m 0644 ops/Caddyfile /etc/caddy/Caddyfile
install -m 0750 ops/candidate.sh ops/live-gates.sh ops/promote.sh ops/rollback.sh /opt/cobri/ops/
install -m 0755 "$(command -v uv)" /usr/local/bin/uv
printf 'DOCKER_HOST=unix:///run/user/%s/docker.sock\n' "$(id -u cobri)" > /etc/cobri/docker.env
chmod 0640 /etc/cobri/docker.env
printf '[Service]\nEnvironmentFile=-/etc/cobri/cobri.env\n' > /etc/systemd/system/caddy.service.d/cobri.conf
loginctl enable-linger cobri
if command -v dockerd-rootless-setuptool.sh >/dev/null; then
  runuser -u cobri -- env XDG_RUNTIME_DIR="/run/user/$(id -u cobri)" \
    dockerd-rootless-setuptool.sh install
else
  echo "dockerd-rootless-setuptool.sh is required for the sandbox worker" >&2
  exit 1
fi
systemctl daemon-reload
systemctl enable cobri-api.service cobri-worker.service
echo "host bootstrap complete; configure /etc/cobri/cobri.env and Caddy before starting services"
