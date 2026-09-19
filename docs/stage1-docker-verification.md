# Stage One Docker Verification

Historical environment record. The commands and versions below document the original Docker check; they are not a claim that Docker was rerun during the 2026-09-19 project audit. See [current status](current-status.md).

Date: 2026-09-14

## Environment

- Docker Desktop 4.90.0, Docker Engine 29.7.2.
- Active context: `desktop-linux`.
- Engine: Linux amd64, cgroup v2, seccomp enabled, CPU/memory/PID limits available.
- Docker Desktop is installed at the user-local path `C:\Users\ps420\AppData\Local\Programs\DockerDesktop`.
- The current pre-existing shell did not inherit Docker's user-local PATH entry; verification used the installed CLI path and elevated Docker access. A new shell should be started before normal worker use.
- Sandbox image: `python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254`.

## Checks

| Check | Result |
| --- | --- |
| `hello-world` disposable container | Passed |
| Pinned Python image pull and digest inspection | Passed; digest preserved |
| Real valid Python submission | Passed |
| Real learner test failure | Passed; returned `passed=False` |
| Real timeout and forced cleanup | Passed; `SandboxUnavailable`, no leftover container |
| Forged `COBRI_RESULT` marker | Passed; rejected as untrusted |
| Bounded stdout/stderr | Passed; 9,000-character output returned 108 bounded characters and `output limit exceeded` |
| Non-root/read-only/no-network/tmpfs probe | Passed; UID 65532, `/tmp` writable, network and `/etc` write blocked |
| API → database → worker real sandbox flow | Passed, 3 tests |
| Focused sandbox regression suite | Passed, 6 tests |
| Backend suite | Historical Stage One result: 135 passed, 1 skipped |
| Ruff check and format check | Passed |

The skipped backend test is the existing opt-in live Auth0 check. No secrets were recorded.

## Changes

- `DockerSandbox` now rejects any untrusted `COBRI_RESULT:` marker, even when a trusted marker is also present.
- The generated harness bounds learner stdout and stderr to 8 KiB before host capture.
- Added regression tests for forged-marker rejection and bounded output.

## Operational note

The initial non-elevated Docker-enabled test could not access the Docker Desktop named pipe and correctly left jobs pending with `SandboxUnavailable`. Re-running with the installed CLI path and elevated engine access passed. This is an environment/shell-refresh issue, not a learner-verdict or sandbox-isolation failure.
