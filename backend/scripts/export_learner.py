"""Create a target-bound, operator-mediated learner-data export."""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from cobri.config import Settings
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore


async def export(args: argparse.Namespace) -> None:
    database = Database(Settings().database_url)
    try:
        result = await DatabaseStore(database).export_learner(
            os.environ.get("COBRI_OPERATOR_ID", ""),
            args.issuer,
            args.subject,
            os.environ.get("COBRI_EXPORT_CONFIRMATION", ""),
        )
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, default=str)
            stream.write("\n")
        with Path(os.environ["COBRI_OPERATOR_AUDIT_FILE"]).open(
            "a", encoding="utf-8", newline="\n"
        ) as audit:
            audit.write(
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "operator_id": os.environ["COBRI_OPERATOR_ID"],
                        "action": "learner_export",
                        "issuer": args.issuer,
                        "subject": args.subject,
                        "output": str(args.output.resolve()),
                    }
                )
                + "\n"
            )
    finally:
        await database.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("COBRI_OPERATOR_ID"):
        parser.error("COBRI_OPERATOR_ID is required")
    approved = {
        value.strip()
        for value in os.environ.get("COBRI_APPROVED_OPERATOR_IDS", "").split(",")
        if value.strip()
    }
    if os.environ["COBRI_OPERATOR_ID"] not in approved:
        parser.error("operator is not in COBRI_APPROVED_OPERATOR_IDS")
    if not os.environ.get("COBRI_OPERATOR_AUDIT_FILE"):
        parser.error("COBRI_OPERATOR_AUDIT_FILE is required for audit logging")
    expected = f"EXPORT:{args.issuer}:{args.subject}"
    if os.environ.get("COBRI_EXPORT_CONFIRMATION") != expected:
        parser.error("COBRI_EXPORT_CONFIRMATION must exactly match the selected learner")
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    asyncio.run(export(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
