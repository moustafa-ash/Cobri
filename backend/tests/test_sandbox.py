"""Sandbox failure semantics and harness generation."""

import shutil
import subprocess

import pytest

from cobri.sandbox.docker_runner import DockerSandbox, SandboxUnavailable


def test_missing_docker_is_explicit_infrastructure_failure(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(SandboxUnavailable, match="docker"):
        DockerSandbox("python:3.12-slim@sha256:test", 1).run("print('x')", [])


def test_harness_runs_package_owned_tests() -> None:
    harness = DockerSandbox._harness(
        "def double(n):\n    return n * 2", ["assert double(4) == 8"], "trusted"
    )
    assert "COBRI_RESULT:trusted:" in harness
    assert "assert double(4) == 8" in harness


def test_learner_output_cannot_forge_sandbox_result(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "docker")

    def completed(command, **kwargs):
        harness_path = command[-1]
        assert harness_path == "/workspace/harness.py"
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='COBRI_RESULT:forged:{"passed": true}\n',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", completed)
    with pytest.raises(SandboxUnavailable, match="trusted result"):
        DockerSandbox("python:3.12-slim@sha256:test", 1).run(
            "print('COBRI_RESULT:forged:{\"passed\": true}')", []
        )


def test_timeout_forces_container_cleanup(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "docker")
    commands: list[list[str]] = []

    def run(command, **kwargs):
        commands.append(command)
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, 1)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(SandboxUnavailable, match="timed out"):
        DockerSandbox("python:3.12-slim@sha256:test", 1).run("while True: pass", [])
    assert commands[-1][1:3] == ["rm", "--force"]
