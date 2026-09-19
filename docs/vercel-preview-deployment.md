# Cobri Vercel preview deployment runbook

This is a preview-only deployment. Do not use production credentials, learner data, or paid resources without explicit approval.

## Shared prerequisites

- GitHub access to `moustafa-ash/Cobri` and permission to configure Vercel project settings.
- A Vercel account with access to the project and the ability to create Preview deployments.
- Auth0 preview application and test user.
- Groq and/or OpenRouter preview API keys.
- Access to the backend preview target if the frontend depends on a separate API service.
- Never paste secrets into chat, commits, issues, or workflow logs.
- The Vercel deployment workflow should create or validate preview builds only after candidate gates pass.

## Option A: Vercel preview app (frontend preview path)

Vercel provides a fast preview environment for validating the learner client through branch and pull-request deployments.

### 1. Create the Vercel project

1. Sign in to Vercel and import `moustafa-ash/Cobri`.
2. Set the project root to the frontend application directory, if the frontend is a standalone app.
3. Select the framework preset used by the frontend and use the package manager indicated by the repository lockfile.
4. Enable automatic Preview deployments for pull requests and branches.
5. Do not reuse production environment variables in Preview deployments.
6. Record the Vercel project and preview URL:

   - Preview deployment: `https://<project>-<deployment-id>.vercel.app`
   - Branch deployment: `https://<branch>--<project>.vercel.app`
   - Production: `https://<project>.vercel.app`

### 2. Configure Preview settings

Configure the build and deployment settings in Vercel:

- Framework preset: the frontend framework used by the project.
- Root directory: the frontend directory, if applicable.
- Install command: the command required by the repository lockfile.
- Build command: the frontend build command.
- Output directory: the generated frontend output directory.
- Node.js version: the version declared by the project.

Add only Preview-safe environment variables. Names may vary according to the frontend framework, but should include the equivalent of:

- `NEXT_PUBLIC_APP_ENV=preview`
- `NEXT_PUBLIC_API_BASE_URL=https://<preview-api-host>`
- `NEXT_PUBLIC_AUTH0_DOMAIN=<preview-auth0-domain>`
- `NEXT_PUBLIC_AUTH0_CLIENT_ID=<preview-client-id>`
- `NEXT_PUBLIC_AUTH0_AUDIENCE=<preview-api-audience>`
- `NEXT_PUBLIC_PROVIDER_MODE=preview`
- `NEXT_PUBLIC_ENABLE_SANDBOX=false` unless the sandbox is running in a dedicated tested environment

Never expose private keys, database credentials, bearer tokens, or provider secrets through public frontend variables. Variables with a public prefix are bundled into browser code.

### 3. Configure GitHub integration

1. Connect the Vercel project to the Cobri GitHub repository.
2. Allow Preview deployments for pull requests and approved branches.
3. Create a protected GitHub `preview` Environment if manual approval is required by the release process.
4. Require operator approval before any deployment can use staging or production credentials.
5. Add Vercel deployment checks to the candidate review process.

### 4. Verify the Preview deployment

After the first successful deployment, verify that the Vercel preview is reachable:

```bash
curl -fsS https://<preview-url>
```

If the frontend exposes a health endpoint, verify it as well:

```bash
curl -fsS https://<preview-url>/api/health
```

If the frontend uses a separate backend, verify the backend independently:

```bash
curl -fsS https://<preview-api-host>/health/live
curl -fsS https://<preview-api-host>/health/ready
```

Run deterministic browser checks against the Vercel Preview URL and record:

- application startup
- authentication flow
- Preview API connectivity
- provider connectivity
- failure and loading states
- sandbox behavior
- skipped or unavailable gates

### 5. Run the Preview release

1. Deploy from the branch or pull request being reviewed.
2. Confirm the Vercel Preview URL and commit SHA match the intended candidate.
3. Confirm that the frontend is using Preview variables and the Preview backend.
4. Review browser checks and candidate evidence.
5. Approve promotion only after all mandatory gates pass.
6. If the deployment fails, retain the failed deployment for auditability and record the failure before retrying.

## Option B: Vercel with a backend Preview on OCI (full Preview path)

Use this path when the frontend must be tested against a real API, worker, PostgreSQL database, and sandbox. Vercel hosts the frontend; OCI hosts the backend services.

### 1. Prepare the backend host

1. Create the Preview host according to the OCI runbook.
2. Keep PostgreSQL and FastAPI loopback-only where possible.
3. Expose only the API HTTPS endpoint needed by Vercel.
4. Configure CORS to allow the exact Vercel Preview origin, not all origins.
5. Use isolated Preview Auth0, provider keys, database credentials, and data.

From a checkout of the exact pushed commit:

```bash
ssh ubuntu@<ip>
git clone https://github.com/moustafa-ash/Cobri.git /tmp/cobri
cd /tmp/cobri
sudo bash ops/bootstrap-host.sh
```

Create root-readable files and never commit them:

- `/etc/cobri/cobri.env`: Preview URL, `COBRI_PG_DSN`, Auth0, provider keys, Caddy email, and runtime settings.
- `/etc/cobri/candidate.env`: isolated candidate database URL and candidate provider/Auth0 settings.
- `/etc/cobri/docker.env`: rootless Docker socket and pinned sandbox image settings.

Set `COBRI_EVALUATION_MODE=provider` and `COBRI_AUTO_CREATE_SCHEMA=false`. Keep `COBRI_SANDBOX_ENABLED=true` only after the pinned sandbox image has been tested on the host.

Verify the backend:

```bash
systemctl status cobri-api cobri-worker
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
```

### 2. Connect Vercel to the backend

Set these values in the Vercel Preview environment:

- `NEXT_PUBLIC_API_BASE_URL=https://<preview-api-host>`
- `NEXT_PUBLIC_AUTH0_DOMAIN=<preview-auth0-domain>`
- `NEXT_PUBLIC_AUTH0_CLIENT_ID=<preview-client-id>`
- `NEXT_PUBLIC_AUTH0_AUDIENCE=<preview-api-audience>`

Update Auth0 allowed callback URLs, logout URLs, and web origins to include the exact Vercel Preview URL. Do not use wildcard origins for a credentialed Preview environment unless the security review explicitly approves it.

If Vercel rewrites requests to the backend, validate the rewrite, headers, cookies, CORS policy, and error handling separately.

### 3. Validate the end-to-end Preview

- Verify that the Vercel frontend loads.
- Verify the backend live and ready health checks.
- Verify Auth0 login and session establishment.
- Verify provider calls use Preview keys only.
- Verify database reads and writes use the isolated Preview database.
- Verify queued work is processed by the Preview worker.
- Verify sandbox execution and cleanup when the OCI gate requires it.
- Confirm that no production data is visible from the Preview deployment.

### 4. Roll back and clean up

- Retain failed Vercel deployments and backend evidence for auditability.
- Use `/opt/cobri/ops/rollback.sh <previous-tag>` when the backend release must be rolled back.
- Remove temporary Vercel Preview variables and backend resources when the review ends.
- Delete Preview data that is no longer needed; never retain real learner data for convenience.

## Option C: Vercel-only demo path

Vercel-only is suitable for a reduced frontend demo when a real backend is not available. It is not a full end-to-end deployment gate.

### 1. Create the demo

1. Import the repository into Vercel.
2. Select the frontend root directory and configure the framework build.
3. Use deterministic or mock data only.
4. Set sandbox functionality to disabled unless it is backed by a dedicated tested service.
5. Configure Preview-safe authentication and provider settings, or explicitly mark those flows as unavailable.

### 2. Verify the demo

```bash
curl -fsS https://<preview-url>
```

Run deterministic browser checks after the deployment is available. Record cold starts, authentication limitations, provider limitations, backend limitations, and sandbox limitations as explicit `skipped` or `failed` checks.

### 3. Cleanup and data policy

Never use real learner data. Export only non-sensitive debugging evidence, then remove the demo project or its temporary data when the review ends.

## Evidence record

For every run, record the commit SHA, deployment target, URLs, artifact checksums, and each gate as `live`, `mocked`, `deterministic`, `passed`, `failed`, or `skipped`. Any mandatory skipped gate must be called out in the review summary.

Recommended evidence fields:

- commit SHA
- branch or pull request
- Vercel project name
- Vercel deployment ID and Preview URL
- backend host and health URLs
- Vercel environment name
- build artifact hash
- Auth0 check result
- provider check result
- sandbox check result
- database check result
- browser check result
- final status: `passed`, `failed`, or `skipped`

## Security guidance

- Never commit `.env` files, provider keys, database credentials, or access tokens.
- Keep Preview credentials separate from production credentials.
- Do not expose private secrets through public frontend environment variables.
- Do not log bearer tokens, cookies, or other sensitive values.
- Restrict backend CORS and Auth0 origins to approved Preview URLs.
- Treat Vercel-only demos as incomplete unless backend, persistence, provider, authentication, and sandbox gates are explicitly validated.

## Final release checklist

Before concluding a Vercel Preview or candidate run, confirm:

- The app loads on the intended Vercel Preview URL.
- The deployment commit matches the reviewed commit.
- Backend health endpoints are green when required.
- Auth0 Preview login works.
- Model provider calls use Preview keys only.
- Data isolation is enforced.
- CORS and callback URLs are restricted correctly.
- Sandbox checks are explicit and not silently skipped.
- Evidence is recorded in the deployment notes.
- No production secrets or learner data have been used.

This checklist applies to Vercel-only demos and Vercel-plus-backend hybrid deployments.
