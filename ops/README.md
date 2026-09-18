# Preview host operations

Run `bootstrap-host.sh` as root from this directory on an Ubuntu ARM64 OCI
instance after installing Caddy and the pinned `uv` release. The script does
not create credentials or provider secrets.

Create `/etc/cobri/cobri.env` with the normal `COBRI_*` settings plus:

```dotenv
COBRI_PG_DSN=postgresql://cobri:<password>@127.0.0.1:5432/cobri
COBRI_PREVIEW_HOST=<reserved-ip>.sslip.io
COBRI_CANDIDATE_HOST=candidate-<reserved-ip>.sslip.io
COBRI_TLS_EMAIL=<operator-email>
```

Create `/etc/cobri/candidate.env` with a separate PostgreSQL database and the
same Auth0, Groq, OpenRouter, sandbox, and CORS settings. Set
`COBRI_EVALUATION_MODE=provider` and `COBRI_AUTO_CREATE_SCHEMA=false`.

Both files are root-owned and group-readable by `cobri`; never commit them.
The candidate gate starts the isolated API and worker on port `8001` and runs
Alembic against its database before the GitHub workflow performs live checks.
`promote.sh` backs up the preview database, migrates the exact artifact, and
switches `/opt/cobri/current` atomically. `rollback.sh` restores the previous
release symlink and restarts both services.
