"""Operator-only learner deletion command with target-bound confirmation."""

import argparse
import asyncio

from cobri.config import Settings
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore


async def run(args: argparse.Namespace) -> None:
    settings = Settings(_env_file=None)
    database = Database(settings.database_url)
    try:
        await DatabaseStore(database).delete_learner(
            args.operator,
            args.issuer,
            args.subject,
            args.confirmation,
        )
    finally:
        await database.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator", required=True)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args()
    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
