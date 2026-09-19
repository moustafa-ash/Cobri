"""SQLite durable acceptance and offline worker integration coverage."""

import asyncio
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import update

from cobri.assessments.contracts import EvaluationView, SubmissionCreate
from cobri.config import Settings
from cobri.content.catalog import FileContentCatalog
from cobri.errors import IdempotencyConflict, IntegrationContractError, ResourceNotFound
from cobri.evaluations.contracts import (
    DiagnosticStatus,
    Evaluation,
    OutcomeVerdict,
    ReasoningVerdict,
)
from cobri.identity.auth import Principal
from cobri.persistence.database import Database
from cobri.persistence.models import EvaluationJobRecord
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


def test_worker_rejects_evaluation_outside_selected_content(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'validation.db'}",
        content_root=Path(__file__).parents[2] / "content-packages",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
    )
    worker = EvaluationWorker(settings, None, FileContentCatalog(settings.content_root))  # type: ignore[arg-type]
    item = worker.catalog.get_item("python-functions", "1.0.0", "python-function-return-1")
    fabricated = Evaluation(
        outcome_verdict=OutcomeVerdict.INCORRECT,
        reasoning_verdict=ReasoningVerdict.INCORRECT,
        diagnostic_status=DiagnosticStatus.SUPPORTED,
        evidence_references=["fabricated:evidence"],
        misconception_id=None,
    )
    with pytest.raises(IntegrationContractError, match="outside the selected item"):
        worker._validate_evaluation(fabricated, item)

    contradictory = fabricated.model_copy(
        update={
            "evidence_references": item.evidence_references,
            "diagnostic_status": DiagnosticStatus.UNCERTAIN,
            "misconception_id": "print-instead-of-return",
        }
    )
    with pytest.raises(IntegrationContractError, match="uncertain evaluations"):
        worker._validate_evaluation(contradictory, item)

    unsupported = fabricated.model_copy(
        update={"evidence_references": [], "misconception_id": "print-instead-of-return"}
    )
    with pytest.raises(IntegrationContractError, match="must cite evidence"):
        worker._validate_evaluation(unsupported, item)


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


def test_only_lease_owner_can_finish_job(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'lease.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="learner-3")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        accepted = await store.accept_submission(
            principal,
            session.session_id,
            SubmissionCreate(item_id="python-function-return-1", answer="answer"),
            "lease-key",
        )
        claimed = await store.claim_job("worker-a", 60, 3)
        assert claimed is not None
        evaluation = EvaluationView(
            outcome_verdict=OutcomeVerdict.INCORRECT,
            reasoning_verdict=ReasoningVerdict.INSUFFICIENT,
            diagnostic_status=DiagnosticStatus.UNCERTAIN,
            evidence_references=[],
        )
        assert not await store.finish_job(claimed[1].job_id, "worker-b", evaluation)
        assert await store.renew_job_lease(claimed[1].job_id, "worker-a", 60)
        assert await store.finish_job(claimed[1].job_id, "worker-a", evaluation)
        result = await store.get_submission(principal, accepted.submission_id)
        assert result.job.status == "succeeded"
        await database.dispose()

    asyncio.run(scenario())


def test_operator_deletion_requires_exact_target_confirmation(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'delete.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="delete-me")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        await store.accept_submission(
            principal,
            session.session_id,
            SubmissionCreate(item_id="python-function-return-1", answer="answer"),
            "delete-key",
        )
        with pytest.raises(PermissionError):
            await store.delete_learner("", principal.issuer, principal.subject, "wrong")
        await store.delete_learner(
            "operator-1",
            principal.issuer,
            principal.subject,
            f"DELETE:{principal.issuer}:{principal.subject}",
        )
        with pytest.raises(ResourceNotFound):
            await store.get_session(principal, session.session_id)
        await database.dispose()

    asyncio.run(scenario())


def test_stale_worker_cannot_finish_after_lease_reclaimed(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'stale.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="stale-worker")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        await store.accept_submission(
            principal,
            session.session_id,
            SubmissionCreate(item_id="python-function-return-1", answer="answer"),
            "stale-key",
        )
        claimed = await store.claim_job("worker-a", 60, 3)
        assert claimed is not None
        job_id = claimed[1].job_id
        async with database.session() as db:
            await db.execute(
                update(EvaluationJobRecord)
                .where(EvaluationJobRecord.job_id == job_id)
                .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
            )
            await db.commit()
        reclaimed = await store.claim_job("worker-b", 60, 3)
        assert reclaimed is not None
        evaluation = EvaluationView(
            outcome_verdict=OutcomeVerdict.INCORRECT,
            reasoning_verdict=ReasoningVerdict.INSUFFICIENT,
            diagnostic_status=DiagnosticStatus.UNCERTAIN,
            evidence_references=[],
        )
        assert not await store.finish_job(job_id, "worker-a", evaluation)
        assert await store.finish_job(job_id, "worker-b", evaluation)
        await database.dispose()

    asyncio.run(scenario())


def test_operator_export_requires_target_bound_confirmation(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'export.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="export-me")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        await store.accept_submission(
            principal,
            session.session_id,
            SubmissionCreate(item_id="python-function-return-1", answer="my learner answer"),
            "export-key",
        )
        with pytest.raises(PermissionError):
            await store.export_learner("", principal.issuer, principal.subject, "wrong")
        exported = await store.export_learner(
            "operator-1",
            principal.issuer,
            principal.subject,
            f"EXPORT:{principal.issuer}:{principal.subject}",
        )
        assert exported["submissions"][0]["answer"] == "my learner answer"
        assert exported["events"][0]["event_type"] == "assessment_submitted"
        await database.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("sandbox_passed", "expected"),
    [(False, "transfer_ready"), (True, "mastered")],
)
def test_mastery_requires_sandbox_verified_changed_context_transfer(
    tmp_path: Path, sandbox_passed: bool, expected: str
) -> None:
    async def scenario() -> None:
        database = Database(f"sqlite+aiosqlite:///{tmp_path / 'mastery.db'}")
        await database.create_schema()
        store = DatabaseStore(database)
        principal = Principal(issuer="https://issuer.example", subject="mastery-learner")
        session = await store.create_session(
            principal,
            SessionCreate(
                content_package_id="python-functions",
                content_version="2.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )
        assessment = await store.accept_submission(
            principal,
            session.session_id,
            SubmissionCreate(item_id="function-return-value", answer="return n * 2"),
            "assessment",
        )
        evaluation = EvaluationView(
            outcome_verdict=OutcomeVerdict.CORRECT,
            reasoning_verdict=ReasoningVerdict.SOUND,
            diagnostic_status=DiagnosticStatus.UNCERTAIN,
            evidence_references=["python-functions:2.0.0:return-values"],
        )
        claim = await store.claim_job("worker", 60)
        assert claim is not None
        await store.finish_job(claim[1].job_id, "worker", evaluation)
        transfer = await store.accept_submission(
            principal,
            session.session_id,
            SubmissionCreate(
                item_id="transfer-rectangle-area",
                answer="return width * height",
                purpose="transfer",
                parent_submission_id=assessment.submission_id,
            ),
            "transfer",
        )
        claim = await store.claim_job("worker", 60)
        assert claim is not None
        await store.finish_job(claim[1].job_id, "worker", evaluation, sandbox_passed=sandbox_passed)
        progress = await store.list_progress(principal)
        progress_item = assessment.item_id if expected == "mastered" else transfer.item_id
        transfer_progress = next(row for row in progress if row.item_id == progress_item)
        assert transfer_progress.status.value == expected
        events = await store.list_events(principal, session.session_id)
        event_types = {event.event_type.value for event in events}
        assert "assessment_submitted" in event_types
        assert "transfer_submitted" in event_types
        assert ("mastery_awarded" in event_types) is sandbox_passed
        await database.dispose()

    asyncio.run(scenario())
