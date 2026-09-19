import hashlib
import json
import runpy
import shutil
from collections import Counter
from pathlib import Path

import pytest


def test_v1_dataset_has_required_bilingual_allocation() -> None:
    path = Path(__file__).parent / "fixtures" / "evaluations" / "v1" / "evaluation.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert len(cases) == 120
    assert Counter(case["language"] for case in cases) == {"en": 60, "ar": 60}
    for language in ("en", "ar"):
        counts = Counter(case["category"] for case in cases if case["language"] == language)
        assert set(counts.values()) == {10}
    assert (
        len(
            {
                (case["content_package_id"], case["content_version"], case["item_id"])
                for case in cases
            }
        )
        >= 6
    )
    assert {case["category"] for case in cases} == {
        "correct_sound",
        "reasoning_disagreement",
        "supported_misconception",
        "prerequisite_gap",
        "insufficient_evidence",
        "adversarial",
    }
    manifest = json.loads((path.parent / "review-manifest.json").read_text(encoding="utf-8"))
    assert manifest["reviewer"] == "moustafa-ash"
    assert manifest["status"] == "approved"
    assert len(manifest["case_reviews"]) == len(cases)
    assert all(entry["status"] == "reviewed" for entry in manifest["case_reviews"])

    def stable_json(value) -> bytes:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    assert manifest["dataset_digest"] == hashlib.sha256(stable_json(cases)).hexdigest()
    assert [entry["digest"] for entry in manifest["case_reviews"]] == [
        hashlib.sha256(stable_json(case)).hexdigest() for case in cases
    ]
    repo_root = Path(__file__).parents[2]
    packages = [
        json.loads(package.read_text(encoding="utf-8"))
        for package in (repo_root / "content-packages").glob("*/**/package.json")
    ]
    content_reviews = manifest["content_reviews"]
    approved_scopes = {("python-functions", "2.0.0"), ("python-control-flow", "1.0.0")}
    assert len(content_reviews) == sum(
        len(package["items"])
        for package in packages
        if (package["content_package_id"], package["content_version"]) in approved_scopes
    )
    assert {entry["status"] for entry in content_reviews} == {"reviewed"}


def test_evaluation_report_separates_observed_and_unavailable_metrics() -> None:
    path = Path(__file__).parent / "fixtures" / "evaluations" / "v1" / "evaluation.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    case = cases[0]
    report_metrics = runpy.run_path(
        str(Path(__file__).parents[1] / "scripts" / "evaluate_dataset.py")
    )
    assert report_metrics["_review_approved"](path.parent) is True
    report_metrics = report_metrics["report_metrics"]
    report = report_metrics(
        [
            {
                "case_id": case["case_id"],
                "result": case["expected_verdict"],
                "expected": case["expected_verdict"],
                "latency_ms": 25,
            }
        ],
        cases,
    )
    assert report["outcome_accuracy"]["value"] == 1.0
    assert report["reasoning_classification"]["value"] == 1.0
    assert report["supported_recall_at_3"]["gate"] == "blocked"
    assert report["uncertainty_calibration"]["gate"] == "blocked"


def test_approval_workflow_binds_signoff_without_mutating_package_bytes(tmp_path: Path) -> None:
    repo_root = Path(__file__).parents[2]
    source_dataset = Path(__file__).parent / "fixtures" / "evaluations" / "v1"
    dataset = tmp_path / "evaluations" / "v1"
    shutil.copytree(source_dataset, dataset)
    content = tmp_path / "content-packages"
    for package_id, version in {("python-functions", "2.0.0"), ("python-control-flow", "1.0.0")}:
        source = repo_root / "content-packages" / package_id / version
        shutil.copytree(source, content / package_id / version)
    manifest = json.loads((dataset / "review-manifest.json").read_text(encoding="utf-8"))
    manifest["status"] = "pending"
    manifest.pop("approved_at", None)
    manifest.pop("approval_ref", None)
    for entry in manifest["case_reviews"] + manifest["content_reviews"]:
        entry["status"] = "pending"
        entry.pop("reviewed_at", None)
    (dataset / "review-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    approve = runpy.run_path(str(repo_root / "backend" / "scripts" / "approve_review.py"))[
        "approve"
    ]
    with pytest.raises(ValueError, match="confirmation digest"):
        approve(dataset, content, "moustafa-ash", "wrong", "codex-approval:test")
    package_before = {path: path.read_bytes() for path in content.glob("*/**/package.json")}
    approve(
        dataset,
        content,
        "moustafa-ash",
        manifest["dataset_digest"],
        "codex-approval:test",
    )
    approved = json.loads((dataset / "review-manifest.json").read_text(encoding="utf-8"))
    ledger = json.loads((content / "releases.json").read_text(encoding="utf-8"))
    assert approved["status"] == "approved"
    assert all(record["action"] == "review" for record in ledger)
    assert all(path.read_bytes() == package_before[path] for path in package_before)
