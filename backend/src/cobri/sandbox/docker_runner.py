"""Docker-backed Python execution with bounded resources and no network."""

import json
import secrets
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class SandboxUnavailable(RuntimeError):
    """Docker is not available or the configured image cannot run."""


@dataclass(frozen=True)
class SandboxResult:
    passed: bool
    output: str


class DockerSandbox:
    def __init__(self, image: str, timeout_seconds: float) -> None:
        self.image = image
        self.timeout_seconds = timeout_seconds

    def run(self, code: str, tests: list[str]) -> SandboxResult:
        docker = shutil.which("docker")
        if docker is None:
            raise SandboxUnavailable("docker executable is unavailable")
        with tempfile.TemporaryDirectory(prefix="cobri-sandbox-") as directory:
            root = Path(directory)
            harness = root / "harness.py"
            nonce = secrets.token_urlsafe(24)
            harness.write_text(self._harness(code, tests, nonce), encoding="utf-8")
            container_name = f"cobri-sandbox-{secrets.token_hex(12)}"
            command = [
                docker,
                "run",
                "--rm",
                "--name",
                container_name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--pids-limit",
                "64",
                "--memory",
                "128m",
                "--cpus",
                "0.5",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                "--user",
                "65532:65532",
                "-v",
                f"{root}:/workspace:ro",
                self.image,
                "python",
                "/workspace/harness.py",
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds + 2,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                subprocess.run(
                    [docker, "rm", "--force", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                raise SandboxUnavailable("sandbox execution timed out") from exc
            output = (completed.stdout + completed.stderr)[-4000:]
            if completed.returncode != 0:
                raise SandboxUnavailable("sandbox container failed")
            prefix = f"COBRI_RESULT:{nonce}:"
            if any(
                line.startswith("COBRI_RESULT:") and not line.startswith(prefix)
                for line in completed.stdout.splitlines()
            ):
                raise SandboxUnavailable("sandbox returned an untrusted result marker")
            marker = next(
                (
                    line.removeprefix(prefix)
                    for line in completed.stdout.splitlines()
                    if line.startswith(prefix)
                ),
                None,
            )
            if marker is None:
                raise SandboxUnavailable("sandbox returned no trusted result")
            try:
                passed = json.loads(marker)["passed"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise SandboxUnavailable("sandbox returned an invalid result") from exc
            if not isinstance(passed, bool):
                raise SandboxUnavailable("sandbox returned an invalid result")
            return SandboxResult(passed, output)

    @staticmethod
    def _harness(code: str, tests: list[str], nonce: str) -> str:
        return (
            "import contextlib\n"
            "import json\n"
            "class _BoundedWriter:\n"
            "    def __init__(self, limit):\n"
            "        self.limit = limit\n"
            "        self.parts = []\n"
            "        self.size = 0\n"
            "    def write(self, value):\n"
            "        self.size += len(value)\n"
            "        if self.size > self.limit:\n"
            "            raise RuntimeError('sandbox output limit exceeded')\n"
            "        self.parts.append(value)\n"
            "        return len(value)\n"
            "    def flush(self):\n"
            "        return None\n"
            "    def getvalue(self):\n"
            "        return ''.join(self.parts)\n"
            "passed = False\n"
            "namespace = {'__name__': '__main__'}\n"
            "stdout = _BoundedWriter(8192)\n"
            "stderr = _BoundedWriter(8192)\n"
            "error = None\n"
            "try:\n"
            "    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):\n"
            f"        exec({code!r}, namespace)\n"
            + "\n".join(f"        exec({test!r}, namespace)" for test in tests)
            + "\n    passed = True\n"
            "except BaseException as exc:\n"
            "    error = type(exc).__name__ + ': ' + str(exc)\n"
            "print(stdout.getvalue(), end='')\n"
            "print(stderr.getvalue(), end='')\n"
            "if error:\n"
            "    print(error)\n"
            f"print('COBRI_RESULT:{nonce}:' + json.dumps({{'passed': passed}}))\n"
        )
