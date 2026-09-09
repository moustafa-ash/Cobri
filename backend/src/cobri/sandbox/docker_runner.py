"""Docker-backed Python execution with bounded resources and no network."""

import json
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
    timed_out: bool
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
            harness.write_text(self._harness(code, tests), encoding="utf-8")
            command = [
                docker,
                "run",
                "--rm",
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
                return SandboxResult(False, True, str(exc)[:4000])
            output = (completed.stdout + completed.stderr)[-4000:]
            if completed.returncode != 0:
                return SandboxResult(False, False, output)
            marker = next(
                (
                    line.removeprefix("COBRI_RESULT:")
                    for line in completed.stdout.splitlines()
                    if line.startswith("COBRI_RESULT:")
                ),
                None,
            )
            if marker is None:
                return SandboxResult(False, False, output)
            return SandboxResult(bool(json.loads(marker)["passed"]), False, output)

    @staticmethod
    def _harness(code: str, tests: list[str]) -> str:
        return (
            "import json\n"
            "passed = False\n"
            "namespace = {'__name__': '__main__'}\n"
            "try:\n"
            f"    exec({code!r}, namespace)\n"
            + "\n".join(f"    exec({test!r}, namespace)" for test in tests)
            + "\n    passed = True\n"
            "except Exception as exc:\n"
            "    print(type(exc).__name__ + ': ' + str(exc))\n"
            "print('COBRI_RESULT:' + json.dumps({'passed': passed}))\n"
        )
