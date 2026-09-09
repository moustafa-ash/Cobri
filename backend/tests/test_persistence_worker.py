"""SQLite durable acceptance and offline worker integration coverage."""

import asyncio
import shutil
from pathlib import Path

import pytest

from cobri.assessments.contracts import SubmissionCreate
from cobri.config import Settings
from cobri.content.catalog import FileContentCatalog
from cobri.errors import IdempotencyConflict
from cobri.identity.auth import Principal
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore
from cobri.tutoring.contracts import SessionCreate
from cobri.worker import EvaluationWorker


def test_sqlite_acceptance_replay_conflict_and_worker(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'cobri.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="learner-1")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        request = SubmissionCreate(
            item_id="python-function-return-1",
            answer="def double(n):\n    return n * 2",
            reasoning="The function returns a value instead of printing it.",
        )
        accepted = await store.accept_submission(principal, session.session_id, request, "key-1")
        replay = await store.accept_submission(principal, session.session_id, request, "key-1")
        assert accepted.submission_id == replay.submission_id
        with pytest.raises(IdempotencyConflict):
            await store.accept_submission(
                principal,
                session.session_id,
                request.model_copy(update={"answer": "different"}),
                "key-1",
            )

        concurrent = await asyncio.gather(
            *[
                store.accept_submission(principal, session.session_id, request, "concurrent-key")
                for _ in range(2)
            ]
        )
        assert concurrent[0].submission_id == concurrent[1].submission_id

        settings = Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'cobri.db'}",
            content_root=Path(__file__).parents[2] / "content-packages",
            auth_issuer=None,
            auth_audience=None,
            auth_jwks_url=None,
        )
        worker = EvaluationWorker(settings, store, FileContentCatalog(settings.content_root))
        assert await worker.run_once()
        result = await store.get_submission(principal, accepted.submission_id)
        assert result.job.status == "succeeded"
        assert result.evaluation is not None
        assert result.evaluation.outcome_verdict == "correct"
        await database.dispose()

    asyncio.run(scenario())


def test_sandbox_failure_is_retried_without_learner_verdict(tmp_path: Path, monkeypatch) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="learner-2")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        request = SubmissionCreate(
            item_id="python-function-return-1",
            answer="def double(n):\n    return n * 2",
        )
        submission = await store.accept_submission(
            principal, session.session_id, request, "retry-key"
        )
        settings = Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}",
            content_root=Path(__file__).parents[2] / "content-packages",
            sandbox_enabled=True,
            auth_issuer=None,
            auth_audience=None,
            auth_jwks_url=None,
        )
        monkeypatch.setattr(shutil, "which", lambda _: None)
        worker = EvaluationWorker(settings, store, FileContentCatalog(settings.content_root))
        assert await worker.run_once()
        result = await store.get_submission(principal, submission.submission_id)
        assert result.job.status == "pending"
        assert result.evaluation is None
        await database.dispose()

    asyncio.run(scenario())
