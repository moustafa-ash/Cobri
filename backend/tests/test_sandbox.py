"""Sandbox failure semantics and harness generation."""

import shutil

import pytest

from cobri.sandbox.docker_runner import DockerSandbox, SandboxUnavailable


def test_missing_docker_is_explicit_infrastructure_failure(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(SandboxUnavailable, match="docker"):
        DockerSandbox("python:3.12-slim@sha256:test", 1).run("print('x')", [])


def test_harness_runs_package_owned_tests() -> None:
    harness = DockerSandbox._harness("def double(n):\n    return n * 2", ["assert double(4) == 8"])
    assert "COBRI_RESULT" in harness
    assert "assert double(4) == 8" in harness
