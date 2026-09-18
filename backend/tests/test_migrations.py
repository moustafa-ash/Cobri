"""Migration smoke test using a disposable SQLite database."""

import os
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_head_and_check(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    env = os.environ.copy()
    env["COBRI_DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
    root = Path(__file__).parents[2]
    command = [sys.executable, "-m", "alembic", "-c", "alembic.ini"]
    upgraded = subprocess.run(
        [*command, "upgrade", "head"], cwd=root, env=env, capture_output=True, text=True
    )
    assert upgraded.returncode == 0, upgraded.stderr
    checked = subprocess.run([*command, "check"], cwd=root, env=env, capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    current = subprocess.run(
        [*command, "current"], cwd=root, env=env, capture_output=True, text=True
    )
    assert current.returncode == 0, current.stderr
    assert "0006_quarantined_sources" in current.stdout
