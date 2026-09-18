#!/usr/bin/env bash
set -euo pipefail

previous=$(cat /opt/cobri/previous-release 2>/dev/null || true)
[[ "$previous" == /opt/cobri/releases/* && -d "$previous" ]] || {
  echo "no validated previous release" >&2
  exit 1
}
ln -sfn "$previous" /opt/cobri/current
systemctl restart cobri-api.service cobri-worker.service
systemctl reload caddy
curl --fail --silent --show-error http://127.0.0.1:8000/health/live >/dev/null
echo "rolled back to $previous"
