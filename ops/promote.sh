#!/usr/bin/env bash
set -euo pipefail

tag=${1:?tag}
archive=${2:?archive}
checksum=${3:?checksum}
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-preview\.[0-9]+$ ]]
[[ "$archive" == /tmp/cobri-*.tar.gz && "$checksum" == /tmp/cobri-*.sha256 ]]
test -f "$archive" -a -f "$checksum"
sha256sum --check "$checksum"

test -r /etc/cobri/cobri.env || { echo "/etc/cobri/cobri.env is required" >&2; exit 1; }
set -a
. /etc/cobri/cobri.env
set +a

release="/opt/cobri/releases/$tag"
previous=$(readlink -f /opt/cobri/current 2>/dev/null || true)
switched=0
rollback_on_error() {
  status=$?
  if [[ "$status" -ne 0 && "$switched" -eq 1 && -n "$previous" && -d "$previous" ]]; then
    ln -sfn "$previous" /opt/cobri/current
    systemctl restart cobri-api.service cobri-worker.service || true
    systemctl reload caddy || true
    echo "promotion failed; restored $previous" >&2
  fi
  exit "$status"
}
trap rollback_on_error EXIT
install -d -o cobri -g cobri -m 0750 "$release"
tar --extract --gzip --no-same-owner --file "$archive" --directory "$release"
chown -R cobri:cobri "$release"
install -d -o cobri -g cobri -m 0750 /var/lib/cobri/backups
test -n "${COBRI_PG_DSN:-}" || { echo "COBRI_PG_DSN is required for rollback safety" >&2; exit 1; }
pg_dump "$COBRI_PG_DSN" > "/var/lib/cobri/backups/$tag.sql"
(cd "$release" && /usr/local/bin/uv run --project "$release/backend" --locked alembic -c "$release/alembic.ini" upgrade head)
printf '%s\n' "$previous" > /opt/cobri/previous-release
ln -sfn "$release" /opt/cobri/current
switched=1
systemctl restart cobri-api.service cobri-worker.service
systemctl reload caddy
curl --fail --silent --show-error http://127.0.0.1:8000/health/live >/dev/null
trap - EXIT
echo "promoted $tag"
