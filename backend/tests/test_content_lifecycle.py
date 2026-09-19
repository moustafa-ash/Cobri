import json
import shutil
from pathlib import Path

import pytest

from cobri.content.catalog import FileContentCatalog
from cobri.content.lifecycle import active_digest, append_release, validate


def test_publish_requires_prior_review(tmp_path: Path) -> None:
    package = tmp_path / "package.json"
    package.write_text(json.dumps({"content_package_id": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="reviewed package digest"):
        append_release(
            tmp_path, package, "operator", "publish", reviewer="reviewer", review_ref="PR-1"
        )


def test_content_packages_validate_cleanly() -> None:
    assert validate(Path(__file__).parents[2] / "content-packages") == []


def test_release_ledger_review_approves_immutable_draft_bytes(tmp_path: Path) -> None:
    source = (
        Path(__file__).parents[2]
        / "content-packages"
        / "python-control-flow"
        / "1.0.0"
        / "package.json"
    )
    package = tmp_path / "python-control-flow" / "1.0.0" / "package.json"
    package.parent.mkdir(parents=True)
    shutil.copy2(source, package)
    before = package.read_bytes()
    append_release(
        tmp_path,
        package,
        "codex",
        "review",
        reviewer="moustafa-ash",
        review_ref="codex-approval:test",
    )
    assert package.read_bytes() == before
    assert validate(tmp_path) == []
    selected = FileContentCatalog(tmp_path).list_reviewed()
    assert len(selected) == 1
    assert selected[0].review_status == "reviewed"
    assert selected[0].reviewed_by == "moustafa-ash"


def test_supersession_and_rollback_require_predecessor(tmp_path: Path) -> None:
    package = tmp_path / "package.json"
    package.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="predecessor"):
        append_release(
            tmp_path, package, "author", "rollback", reviewer="reviewer", review_ref="PR-1"
        )


def test_active_digest_is_empty_without_activation(tmp_path: Path) -> None:
    (tmp_path / "releases.json").write_text("[]", encoding="utf-8")
    assert active_digest(tmp_path) is None


def test_active_digest_follows_rollback_predecessor(tmp_path: Path) -> None:
    (tmp_path / "releases.json").write_text(
        json.dumps(
            [
                {"action": "publish", "digest": "new"},
                {"action": "rollback", "digest": "new", "predecessor": "old"},
            ]
        ),
        encoding="utf-8",
    )
    assert active_digest(tmp_path) == "old"


def test_validate_rejects_folder_version_mismatch(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg" / "2.0.0"
    package_dir.mkdir(parents=True)
    package_dir.joinpath("package.json").write_text(
        json.dumps(
            {
                "content_package_id": "pkg",
                "content_version": "1.0.0",
                "topic": "topic",
                "review_status": "draft",
                "items": [
                    {
                        "item_id": "item",
                        "title": {"en": "T", "ar": "ت"},
                        "prompt": {"en": "P", "ar": "س"},
                        "expected_code": "x",
                        "tests": ["assert True"],
                        "evidence_references": ["evidence"],
                        "transfer_prompt": {"en": "T", "ar": "ت"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert any("folder/version mismatch" in error for error in validate(tmp_path))


def test_validate_requires_complete_control_flow_items(tmp_path: Path) -> None:
    package_dir = tmp_path / "python-control-flow" / "1.0.0"
    package_dir.mkdir(parents=True)
    package_dir.joinpath("package.json").write_text(
        json.dumps(
            {
                "content_package_id": "python-control-flow",
                "content_version": "1.0.0",
                "topic": "Python control flow",
                "review_status": "draft",
                "items": [
                    {
                        "item_id": "lesson",
                        "title": {"en": "Lesson", "ar": "درس"},
                        "prompt": {"en": "Prompt", "ar": "سؤال"},
                        "expected_code": "return 1",
                        "tests": ["assert True"],
                        "evidence_references": ["missing"],
                        "transfer_prompt": {"en": "Transfer", "ar": "نقل"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert any("control-flow lesson is incomplete" in error for error in validate(tmp_path))


def test_validate_rejects_missing_and_cyclic_prerequisites(tmp_path: Path) -> None:
    package_dir = tmp_path / "python-control-flow" / "1.0.0"
    package_dir.mkdir(parents=True)
    source = json.loads(
        (
            Path(__file__).parents[2] / "content-packages/python-control-flow/1.0.0/package.json"
        ).read_text(encoding="utf-8")
    )
    first, second = source["items"][:2]
    first["prerequisites"] = [
        {
            "content_package_id": "python-control-flow",
            "content_version": "1.0.0",
            "item_id": "missing",
        },
        {
            "content_package_id": "python-control-flow",
            "content_version": "1.0.0",
            "item_id": second["item_id"],
        },
    ]
    second["prerequisites"] = [
        {
            "content_package_id": "python-control-flow",
            "content_version": "1.0.0",
            "item_id": first["item_id"],
        }
    ]
    (package_dir / "package.json").write_text(json.dumps(source), encoding="utf-8")
    errors = validate(tmp_path)
    assert any("unknown prerequisite" in error for error in errors)
    assert any("prerequisite cycle" in error for error in errors)
