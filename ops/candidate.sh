#!/usr/bin/env bash
set -euo pipefail

tag=${1:?tag}
archive=${2:?archive}
checksum=${3:?checksum}
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-preview\.[0-9]+$ ]]
[[ "$archive" == /tmp/cobri-*.tar.gz && "$checksum" == /tmp/cobri-*.sha256 ]]
test -f "$archive" -a -f "$checksum"
sha256sum --check "$checksum"

release="/opt/cobri/candidate/$tag"
rm -rf -- "$release"
install -d -o cobri -g cobri -m 0750 "$release"
tar --extract --gzip --no-same-owner --file "$archive" --directory "$release"
test -s "$release/COMMIT_SHA"
test -d "$release/backend" -a -d "$release/frontend/dist" -a -d "$release/content-packages"
chown -R cobri:cobri "$release"

test -r /etc/cobri/candidate.env || {
  echo "/etc/cobri/candidate.env is required for live candidate validation" >&2
  exit 1
}
set -a
. /etc/cobri/candidate.env
set +a
test -n "${COBRI_DATABASE_URL:-}" || { echo "candidate database URL is required" >&2; exit 1; }
test "${COBRI_EVALUATION_MODE:-}" = provider || { echo "candidate must use provider evaluation" >&2; exit 1; }
ln -sfn "$release" /opt/cobri/candidate/current
(
  cd "$release"
  /usr/local/bin/uv run --project "$release/backend" --locked alembic -c "$release/alembic.ini" upgrade head
)
systemctl restart cobri-candidate-api.service cobri-candidate-worker.service
systemctl reload caddy
curl --fail --silent --show-error http://127.0.0.1:8001/health/live >/dev/null
echo "candidate artifact is running at $release"
