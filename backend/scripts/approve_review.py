"""Record a designated reviewer's approval against exact content and dataset digests."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from cobri.content.lifecycle import append_release


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def approve(
    dataset_dir: Path,
    content_root: Path,
    reviewer: str,
    approval_digest: str,
    approval_ref: str,
) -> None:
    cases_path = dataset_dir / "evaluation.json"
    manifest_path = dataset_dir / "review-manifest.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if reviewer != manifest["reviewer"] or manifest["status"] != "pending":
        raise ValueError("reviewer mismatch or manifest is not pending")
    if not approval_ref.strip() or digest(cases) != manifest["dataset_digest"]:
        raise ValueError("approval reference is required and dataset digest must match")
    if approval_digest != manifest["dataset_digest"]:
        raise ValueError("confirmation digest does not match the reviewed dataset")

    case_reviews = manifest["case_reviews"]
    if len(case_reviews) != len(cases):
        raise ValueError("every evaluation case must have a review record")
    for case, review in zip(cases, case_reviews, strict=True):
        if (
            review["case_id"] != case["case_id"]
            or review["digest"] != digest(case)
            or review["status"] != "pending"
        ):
            raise ValueError(f"case review is stale or already changed: {case['case_id']}")

    case_scopes = {(case["content_package_id"], case["content_version"]) for case in cases}
    expected_items: set[tuple[str, str, str]] = set()
    packages: dict[tuple[str, str], tuple[Path, dict]] = {}
    for package_id, version in case_scopes:
        package_path = content_root / package_id / version / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packages[(package_id, version)] = (package_path, package)
        expected_items.update((package_id, version, item["item_id"]) for item in package["items"])
    content_reviews = manifest["content_reviews"]
    actual_items = {
        (entry["package_id"], entry["version"], entry["item_id"]) for entry in content_reviews
    }
    if actual_items != expected_items:
        raise ValueError("every referenced package item must have exactly one review record")
    for entry in content_reviews:
        package_path, package = packages[(entry["package_id"], entry["version"])]
        item = next(item for item in package["items"] if item["item_id"] == entry["item_id"])
        if (
            entry["package_digest"] != digest(package)
            or entry["item_digest"] != digest(item)
            or entry["status"] != "pending"
        ):
            raise ValueError(f"content review is stale or already changed: {entry['item_id']}")

    timestamp = datetime.now(UTC).isoformat()
    for entry in case_reviews + content_reviews:
        entry.update({"reviewer": reviewer, "status": "reviewed", "reviewed_at": timestamp})
    for package_path, _ in sorted(packages.values(), key=lambda item: str(item[0])):
        append_release(
            content_root,
            package_path,
            actor="codex",
            action="review",
            reviewer=reviewer,
            review_ref=approval_ref,
        )
    manifest.update({"status": "approved", "approved_at": timestamp, "approval_ref": approval_ref})
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--content-root", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--confirm-dataset-digest", required=True)
    parser.add_argument("--approval-ref", required=True)
    args = parser.parse_args()
    try:
        approve(
            args.dataset,
            args.content_root,
            args.reviewer,
            args.confirm_dataset_digest,
            args.approval_ref,
        )
    except (OSError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
