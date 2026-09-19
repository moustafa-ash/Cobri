"""Small, append-only content release lifecycle CLI."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from cobri.content.catalog import ContentPackage


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recorded_review(root: Path, path: Path) -> dict | None:
    ledger = root / "releases.json"
    entries = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    digest = _digest(path)
    return next(
        (
            entry
            for entry in reversed(entries)
            if entry.get("action") == "review"
            and entry.get("digest") == digest
            and entry.get("reviewer")
        ),
        None,
    )


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    seen_items: set[tuple[str, str]] = set()
    packages: dict[tuple[str, str], ContentPackage] = {}
    paths: dict[tuple[str, str], Path] = {}
    for path in sorted(root.glob("*/**/package.json")):
        try:
            package = ContentPackage.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:  # validation boundary: report every bad package
            errors.append(f"{path}: {exc}")
            continue
        approval = _recorded_review(root, path)
        if approval and package.review_status == "draft":
            package = package.model_copy(
                update={"review_status": "reviewed", "reviewed_by": approval["reviewer"]}
            )
        if path.parent.name != package.content_version:
            errors.append(f"{path}: folder/version mismatch")
        if path.parent.parent.name != package.content_package_id:
            errors.append(f"{path}: folder/package mismatch")
        package_key = (package.content_package_id, package.content_version)
        packages[package_key] = package
        paths[package_key] = path
        item_ids = [item.item_id for item in package.items]
        if len(item_ids) != len(set(item_ids)):
            errors.append(f"{path}: duplicate item identifier")
        for item in package.items:
            for identifier, values, id_field in (
                ("evidence", item.evidence, "evidence_id"),
                ("rubric", item.rubric, "criterion_id"),
                ("misconceptions", item.misconceptions, "misconception_id"),
            ):
                ids = [getattr(value, id_field) for value in values]
                if len(ids) != len(set(ids)):
                    errors.append(f"{path}: duplicate {identifier} identifier")
            if item.evidence and {source.evidence_id for source in item.evidence} != set(
                item.evidence_references
            ):
                errors.append(f"{path}: evidence references do not resolve")
            if item.misconceptions and {
                misconception.misconception_id for misconception in item.misconceptions
            } != set(item.misconception_ids):
                errors.append(f"{path}: misconception references do not resolve")
            all_ids = [item.item_id]
            all_ids.extend(m.practice.item_id for m in item.misconceptions)
            if item.transfer:
                all_ids.append(item.transfer.item_id)
            for child_id in all_ids:
                key = (package.content_package_id, child_id)
                if key in seen_items:
                    errors.append(f"{path}: duplicate follow-up identifier {child_id}")
                seen_items.add(key)
            if package.content_package_id == "python-control-flow":
                if (
                    not item.evidence
                    or not item.rubric
                    or not item.misconceptions
                    or not item.transfer
                ):
                    errors.append(f"{path}: control-flow lesson is incomplete")
        if package.review_status == "reviewed" and not package.reviewed_by:
            errors.append(f"{path}: reviewed package requires reviewer")

    item_keys = {
        (package.content_package_id, package.content_version, item.item_id)
        for package in packages.values()
        for item in package.items
    }
    graph: dict[tuple[str, str, str], list[tuple[str, str, str]]] = {}
    for package in packages.values():
        for item in package.items:
            key = (package.content_package_id, package.content_version, item.item_id)
            graph[key] = []
            for prerequisite in item.prerequisites:
                target = (
                    prerequisite.content_package_id,
                    prerequisite.content_version,
                    prerequisite.item_id,
                )
                if target not in item_keys:
                    package_path = paths[(package.content_package_id, package.content_version)]
                    errors.append(f"{package_path}: unknown prerequisite {target}")
                    continue
                target_package = packages[
                    (prerequisite.content_package_id, prerequisite.content_version)
                ]
                if (
                    package.review_status == "reviewed"
                    and target_package.review_status != "reviewed"
                ):
                    errors.append(f"{package_path}: reviewed package depends on draft {target}")
                graph[key].append(target)

    visiting: set[tuple[str, str, str]] = set()
    visited: set[tuple[str, str, str]] = set()

    def visit(key: tuple[str, str, str]) -> None:
        if key in visiting:
            errors.append(f"{paths[(key[0], key[1])]}: prerequisite cycle at {key[2]}")
            return
        if key in visited:
            return
        visiting.add(key)
        for target in graph.get(key, []):
            visit(target)
        visiting.remove(key)
        visited.add(key)

    for key in graph:
        visit(key)
    return errors


def append_release(
    root: Path,
    package_path: Path,
    actor: str,
    action: str,
    predecessor: str | None = None,
    reviewer: str | None = None,
    review_ref: str | None = None,
) -> None:
    if not package_path.is_file():
        raise ValueError("package target must be an existing package.json")
    if action in {"review", "publish", "supersede", "rollback"} and (
        not reviewer or reviewer == actor
    ):
        raise ValueError("review and publish require a distinct reviewer")
    if action in {"review", "publish", "supersede", "rollback"} and not review_ref:
        raise ValueError(
            "review and publish require a Git review or recorded human-approval reference"
        )
    if action in {"supersede", "rollback"} and not predecessor:
        raise ValueError(f"{action} requires a predecessor digest")
    ledger = root / "releases.json"
    entries = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    digest = _digest(package_path)
    package_data = json.loads(package_path.read_text(encoding="utf-8"))
    if action == "publish" and not any(
        entry.get("action") == "review" and entry.get("digest") == digest for entry in entries
    ):
        raise ValueError("publish requires a reviewed package digest")
    entries.append(
        {
            "content_package_id": package_data.get("content_package_id"),
            "content_version": package_data.get("content_version"),
            "digest": digest,
            "actor": actor,
            "reviewer": reviewer,
            "action": action,
            "predecessor": predecessor,
            "review_ref": review_ref,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    ledger.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def active_digest(root: Path) -> str | None:
    entries = (
        json.loads((root / "releases.json").read_text(encoding="utf-8"))
        if (root / "releases.json").exists()
        else []
    )
    active = None
    for entry in entries:
        if entry.get("action") in {"publish", "rollback"}:
            active = (
                entry.get("predecessor")
                if entry.get("action") == "rollback"
                else entry.get("digest")
            )
    return active


def active_digests(root: Path) -> dict[tuple[str, str], str]:
    """Return active package bytes without collapsing unrelated packages."""
    entries = (
        json.loads((root / "releases.json").read_text(encoding="utf-8"))
        if (root / "releases.json").exists()
        else []
    )
    active: dict[tuple[str, str], str] = {}
    for entry in entries:
        key = (entry.get("content_package_id"), entry.get("content_version"))
        if not all(key):
            continue
        if entry.get("action") == "rollback":
            if entry.get("predecessor"):
                active[key] = entry["predecessor"]
        elif entry.get("action") in {"publish", "supersede"}:
            if entry.get("digest"):
                active[key] = entry["digest"]
    return active


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("validate", "review", "publish", "supersede", "rollback")
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("package", nargs="?", type=Path)
    parser.add_argument("--actor", default="")
    parser.add_argument("--reviewer")
    parser.add_argument("--review-ref", help="Git review ID or recorded human-approval reference")
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("\n".join(errors))
        return 1
    if args.command == "validate":
        return 0
    if not args.package or not args.actor:
        parser.error("review and publish require package and --actor")
    try:
        append_release(
            args.root,
            args.package,
            args.actor,
            args.command,
            reviewer=args.reviewer,
            review_ref=args.review_ref,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
