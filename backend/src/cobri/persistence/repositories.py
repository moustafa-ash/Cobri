"""Database-backed implementations of the Day 1 adapter contracts."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError

from cobri.assessments.contracts import (
    EvaluationView,
    SubmissionCreate,
    SubmissionView,
)
from cobri.errors import IdempotencyConflict, ResourceNotFound
from cobri.identity.auth import Principal
from cobri.persistence.database import Database
from cobri.persistence.models import (
    EmbeddingRecord,
    EvaluationJobRecord,
    EvaluationRecord,
    IdempotencyRecord,
    LearnerEventRecord,
    LearnerProgressRecord,
    QuarantinedSourceRecord,
    SessionRecord,
    SubmissionRecord,
    WorkerHeartbeatRecord,
)
from cobri.tutoring.contracts import (
    LearnerEventView,
    LearnerProgressView,
    SessionCreate,
    SessionView,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _payload_hash(request: SubmissionCreate) -> str:
    payload = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DatabaseStore:
    """One transaction boundary for sessions, submissions, idempotency, and jobs."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def create_session(self, principal: Principal, request: SessionCreate) -> SessionView:
        record = SessionRecord(
            session_id=str(uuid4()),
            issuer=principal.issuer,
            subject=principal.subject,
            **request.model_dump(),
            created_at=utc_now(),
        )
        async with self.database.session() as session:
            session.add(record)
            await session.commit()
        return self._session_view(record)

    async def get_session(self, principal: Principal, session_id: UUID) -> SessionView:
        async with self.database.session() as session:
            result = await session.scalar(
                select(SessionRecord).where(
                    SessionRecord.session_id == str(session_id),
                    SessionRecord.issuer == principal.issuer,
                    SessionRecord.subject == principal.subject,
                )
            )
        if result is None:
            raise ResourceNotFound
        return self._session_view(result)

    async def list_events(self, principal: Principal, session_id: UUID) -> list[LearnerEventView]:
        async with self.database.session() as session:
            rows = await session.scalars(
                select(LearnerEventRecord)
                .where(
                    LearnerEventRecord.issuer == principal.issuer,
                    LearnerEventRecord.subject == principal.subject,
                    LearnerEventRecord.session_id == str(session_id),
                )
                .order_by(LearnerEventRecord.created_at, LearnerEventRecord.event_id)
            )
            return [LearnerEventView.model_validate(row, from_attributes=True) for row in rows]

    async def list_progress(self, principal: Principal) -> list[LearnerProgressView]:
        async with self.database.session() as session:
            rows = await session.scalars(
                select(LearnerProgressRecord)
                .where(
                    LearnerProgressRecord.issuer == principal.issuer,
                    LearnerProgressRecord.subject == principal.subject,
                )
                .order_by(LearnerProgressRecord.content_package_id, LearnerProgressRecord.item_id)
            )
            return [LearnerProgressView.model_validate(row, from_attributes=True) for row in rows]

    async def save_quarantined_source(self, url: str, digest: str, retrieved_at: datetime) -> None:
        async with self.database.session() as session:
            async with session.begin():
                existing = await session.get(QuarantinedSourceRecord, digest)
                if existing is None:
                    session.add(
                        QuarantinedSourceRecord(
                            digest=digest,
                            url=url,
                            retrieved_at=retrieved_at,
                            review_status="quarantined",
                        )
                    )

    async def save_embeddings(
        self,
        package_id: str,
        version: str,
        package_digest: str,
        model_revision: str,
        vectors: dict[str, list[float]],
        *,
        tokenizer_revision: str = "",
        normalized: bool = True,
    ) -> None:
        async with self.database.session() as session:
            async with session.begin():
                for item_id, vector in vectors.items():
                    existing = await session.scalar(
                        select(EmbeddingRecord).where(
                            EmbeddingRecord.content_package_id == package_id,
                            EmbeddingRecord.content_version == version,
                            EmbeddingRecord.item_id == item_id,
                            EmbeddingRecord.model_revision == model_revision,
                        )
                    )
                    if existing is None:
                        session.add(
                            EmbeddingRecord(
                                content_package_id=package_id,
                                content_version=version,
                                item_id=item_id,
                                package_digest=package_digest,
                                model_revision=model_revision,
                                tokenizer_revision=tokenizer_revision,
                                dimensions=len(vector),
                                normalized=normalized,
                                vector=vector,
                            )
                        )

    async def load_embeddings(
        self, package_id: str, version: str, package_digest: str, model_revision: str
    ) -> list[EmbeddingRecord]:
        async with self.database.session() as session:
            rows = await session.scalars(
                select(EmbeddingRecord).where(
                    EmbeddingRecord.content_package_id == package_id,
                    EmbeddingRecord.content_version == version,
                    EmbeddingRecord.package_digest == package_digest,
                    EmbeddingRecord.model_revision == model_revision,
                )
            )
            return list(rows)

    async def delete_learner(
        self, operator_id: str, issuer: str, subject: str, confirmation: str
    ) -> None:
        """Operator-only deletion guarded by an exact, target-bound confirmation."""
        if not operator_id or confirmation != f"DELETE:{issuer}:{subject}":
            raise PermissionError("operator identity and exact learner confirmation are required")
        async with self.database.session() as session:
            async with session.begin():
                submission_ids = list(
                    await session.scalars(
                        select(SubmissionRecord.submission_id).where(
                            SubmissionRecord.issuer == issuer,
                            SubmissionRecord.subject == subject,
                        )
                    )
                )
                if submission_ids:
                    await session.execute(
                        sa.delete(EvaluationRecord).where(
                            EvaluationRecord.submission_id.in_(submission_ids)
                        )
                    )
                    await session.execute(
                        sa.delete(EvaluationJobRecord).where(
                            EvaluationJobRecord.submission_id.in_(submission_ids)
                        )
                    )
                    await session.execute(
                        sa.delete(IdempotencyRecord).where(
                            IdempotencyRecord.submission_id.in_(submission_ids)
                        )
                    )
                await session.execute(
                    sa.delete(LearnerEventRecord).where(
                        LearnerEventRecord.issuer == issuer,
                        LearnerEventRecord.subject == subject,
                    )
                )
                await session.execute(
                    sa.delete(LearnerProgressRecord).where(
                        LearnerProgressRecord.issuer == issuer,
                        LearnerProgressRecord.subject == subject,
                    )
                )
                await session.execute(
                    sa.delete(SubmissionRecord).where(
                        SubmissionRecord.issuer == issuer,
                        SubmissionRecord.subject == subject,
                    )
                )
                await session.execute(
                    sa.delete(SessionRecord).where(
                        SessionRecord.issuer == issuer,
                        SessionRecord.subject == subject,
                    )
                )

    async def accept_submission(
        self,
        principal: Principal,
        session_id: UUID,
        request: SubmissionCreate,
        idempotency_key: str,
    ) -> SubmissionView:
        fingerprint = _payload_hash(request)
        try:
            return await self._accept_submission(
                principal, session_id, request, idempotency_key, fingerprint
            )
        except IntegrityError:
            async with self.database.session() as session:
                existing = await session.scalar(
                    select(IdempotencyRecord).where(
                        IdempotencyRecord.issuer == principal.issuer,
                        IdempotencyRecord.subject == principal.subject,
                        IdempotencyRecord.session_id == str(session_id),
                        IdempotencyRecord.idempotency_key == idempotency_key,
                    )
                )
                if existing is None:
                    raise IdempotencyConflict from None
                if existing.payload_hash != fingerprint:
                    raise IdempotencyConflict from None
                submission = await session.get(SubmissionRecord, existing.submission_id)
                if submission is None:
                    raise ResourceNotFound from None
                return await self._submission_view(session, submission)

    async def _accept_submission(
        self,
        principal: Principal,
        session_id: UUID,
        request: SubmissionCreate,
        idempotency_key: str,
        fingerprint: str,
    ) -> SubmissionView:
        async with self.database.session() as session:
            async with session.begin():
                owned_session = await session.scalar(
                    select(SessionRecord).where(
                        SessionRecord.session_id == str(session_id),
                        SessionRecord.issuer == principal.issuer,
                        SessionRecord.subject == principal.subject,
                    )
                )
                if owned_session is None:
                    raise ResourceNotFound
                existing = await session.scalar(
                    select(IdempotencyRecord).where(
                        IdempotencyRecord.issuer == principal.issuer,
                        IdempotencyRecord.subject == principal.subject,
                        IdempotencyRecord.session_id == str(session_id),
                        IdempotencyRecord.idempotency_key == idempotency_key,
                    )
                )
                if existing is not None:
                    if existing.payload_hash != fingerprint:
                        raise IdempotencyConflict
                    submission = await session.get(SubmissionRecord, existing.submission_id)
                    if submission is None:
                        raise ResourceNotFound
                    return await self._submission_view(session, submission)

                submission = SubmissionRecord(
                    submission_id=str(uuid4()),
                    session_id=str(session_id),
                    issuer=principal.issuer,
                    subject=principal.subject,
                    content_package_id=owned_session.content_package_id,
                    content_version=owned_session.content_version,
                    **request.model_dump(mode="json"),
                    created_at=utc_now(),
                )
                job = EvaluationJobRecord(
                    job_id=str(uuid4()),
                    submission_id=submission.submission_id,
                    status="pending",
                    attempts=0,
                    available_at=utc_now(),
                )
                session.add_all(
                    [
                        submission,
                        job,
                        IdempotencyRecord(
                            issuer=principal.issuer,
                            subject=principal.subject,
                            session_id=str(session_id),
                            idempotency_key=idempotency_key,
                            payload_hash=fingerprint,
                            submission_id=submission.submission_id,
                        ),
                    ]
                )
                await session.flush()
                session.add(
                    LearnerEventRecord(
                        event_id=str(uuid4()),
                        issuer=principal.issuer,
                        subject=principal.subject,
                        session_id=str(session_id),
                        submission_id=submission.submission_id,
                        event_type="submission_accepted",
                        payload={"purpose": request.purpose.value},
                        created_at=utc_now(),
                    )
                )
                return await self._submission_view(session, submission)

    async def get_submission(self, principal: Principal, submission_id: UUID) -> SubmissionView:
        async with self.database.session() as session:
            submission = await session.scalar(
                select(SubmissionRecord).where(
                    SubmissionRecord.submission_id == str(submission_id),
                    SubmissionRecord.issuer == principal.issuer,
                    SubmissionRecord.subject == principal.subject,
                )
            )
            if submission is None:
                raise ResourceNotFound
            return await self._submission_view(session, submission)

    async def claim_job(
        self, worker_id: str, lease_seconds: int, max_attempts: int = 20
    ) -> tuple[SubmissionRecord, EvaluationJobRecord] | None:
        now = utc_now()
        async with self.database.session() as session:
            async with session.begin():
                await session.execute(
                    update(EvaluationJobRecord)
                    .where(
                        EvaluationJobRecord.status == "running",
                        EvaluationJobRecord.lease_until < now,
                        EvaluationJobRecord.attempts >= max_attempts,
                    )
                    .values(
                        status="failed",
                        lease_until=None,
                        lease_owner=None,
                        last_error="attempts_exhausted_after_lease_expiry",
                    )
                )
                job = await session.scalar(
                    select(EvaluationJobRecord)
                    .where(
                        or_(
                            EvaluationJobRecord.status == "pending",
                            and_(
                                EvaluationJobRecord.status == "running",
                                EvaluationJobRecord.lease_until < now,
                            ),
                        ),
                        EvaluationJobRecord.available_at <= now,
                        EvaluationJobRecord.attempts < max_attempts,
                    )
                    .order_by(EvaluationJobRecord.available_at)
                    .with_for_update(skip_locked=True)
                )
                if job is None:
                    return None
                claimed = await session.execute(
                    update(EvaluationJobRecord)
                    .where(
                        EvaluationJobRecord.job_id == job.job_id,
                        or_(
                            EvaluationJobRecord.status == "pending",
                            and_(
                                EvaluationJobRecord.status == "running",
                                EvaluationJobRecord.lease_until < now,
                            ),
                        ),
                        EvaluationJobRecord.available_at <= now,
                        EvaluationJobRecord.attempts < max_attempts,
                    )
                    .values(
                        status="running",
                        attempts=EvaluationJobRecord.attempts + 1,
                        lease_until=now + timedelta(seconds=lease_seconds),
                        lease_owner=worker_id,
                    )
                    .execution_options(synchronize_session=False)
                )
                if claimed.rowcount != 1:
                    return None
                await session.refresh(job)
                submission = await session.get(SubmissionRecord, job.submission_id)
                if submission is None:
                    job.status = "failed"
                    job.last_error = "submission_missing"
                    return None
                await session.flush()
                return submission, job

    async def renew_job_lease(self, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        async with self.database.session() as session:
            async with session.begin():
                result = await session.execute(
                    update(EvaluationJobRecord)
                    .where(
                        EvaluationJobRecord.job_id == job_id,
                        EvaluationJobRecord.status == "running",
                        EvaluationJobRecord.lease_owner == worker_id,
                    )
                    .values(lease_until=utc_now() + timedelta(seconds=lease_seconds))
                )
                return result.rowcount == 1

    async def finish_job(self, job_id: str, worker_id: str, evaluation: EvaluationView) -> bool:
        async with self.database.session() as session:
            async with session.begin():
                job = await session.scalar(
                    select(EvaluationJobRecord).where(
                        EvaluationJobRecord.job_id == job_id,
                        EvaluationJobRecord.status == "running",
                        EvaluationJobRecord.lease_owner == worker_id,
                    )
                )
                if job is None:
                    return False
                existing = await session.get(EvaluationRecord, job.submission_id)
                if existing is None:
                    session.add(
                        EvaluationRecord(
                            submission_id=job.submission_id,
                            **evaluation.model_dump(),
                        )
                    )
                submission = await session.get(SubmissionRecord, job.submission_id)
                if submission is not None:
                    session.add(
                        LearnerEventRecord(
                            event_id=str(uuid4()),
                            issuer=submission.issuer,
                            subject=submission.subject,
                            session_id=submission.session_id,
                            submission_id=submission.submission_id,
                            event_type="evaluation_succeeded",
                            payload=evaluation.model_dump(mode="json"),
                            created_at=utc_now(),
                        )
                    )
                    status = "started"
                    if (
                        submission.purpose == "transfer"
                        and evaluation.outcome_verdict == "correct"
                        and evaluation.reasoning_verdict == "sound"
                        and submission.parent_submission_id
                    ):
                        parent = await session.get(
                            SubmissionRecord, submission.parent_submission_id
                        )
                        parent_eval = (
                            await session.get(EvaluationRecord, submission.parent_submission_id)
                            if parent
                            else None
                        )
                        if (
                            parent
                            and parent.session_id == submission.session_id
                            and parent.content_package_id == submission.content_package_id
                            and parent.content_version == submission.content_version
                            and parent.item_id != submission.item_id
                            and parent.purpose in {"assessment", "practice"}
                            and parent_eval
                            and parent_eval.outcome_verdict == "correct"
                            and parent_eval.reasoning_verdict == "sound"
                        ):
                            status = "mastered"
                    progress = await session.scalar(
                        select(LearnerProgressRecord).where(
                            LearnerProgressRecord.issuer == submission.issuer,
                            LearnerProgressRecord.subject == submission.subject,
                            LearnerProgressRecord.content_package_id
                            == submission.content_package_id,
                            LearnerProgressRecord.content_version == submission.content_version,
                            LearnerProgressRecord.item_id == submission.item_id,
                        )
                    )
                    if progress is None:
                        session.add(
                            LearnerProgressRecord(
                                issuer=submission.issuer,
                                subject=submission.subject,
                                content_package_id=submission.content_package_id,
                                content_version=submission.content_version,
                                item_id=submission.item_id,
                                status=status,
                                updated_at=utc_now(),
                            )
                        )
                    elif status == "mastered":
                        progress.status = status
                        progress.version += 1
                        progress.updated_at = utc_now()
                job.status = "succeeded"
                job.lease_until = None
                job.lease_owner = None
                job.last_error = None
                return True

    async def fail_job(self, job_id: str, worker_id: str, error: str, retry: bool) -> bool:
        async with self.database.session() as session:
            async with session.begin():
                job = await session.scalar(
                    select(EvaluationJobRecord).where(
                        EvaluationJobRecord.job_id == job_id,
                        EvaluationJobRecord.status == "running",
                        EvaluationJobRecord.lease_owner == worker_id,
                    )
                )
                if job is None:
                    return False
                job.status = "pending" if retry else "failed"
                job.available_at = utc_now() + timedelta(seconds=min(60, 2**job.attempts))
                job.lease_until = None
                job.lease_owner = None
                job.last_error = error[:2000]
                return True

    async def heartbeat(self, worker_id: str) -> None:
        async with self.database.session() as session:
            async with session.begin():
                record = await session.get(WorkerHeartbeatRecord, worker_id)
                if record is None:
                    session.add(WorkerHeartbeatRecord(worker_id=worker_id, updated_at=utc_now()))
                else:
                    record.updated_at = utc_now()

    @staticmethod
    def _session_view(record: SessionRecord) -> SessionView:
        return SessionView.model_validate(
            {
                "session_id": UUID(record.session_id),
                "content_package_id": record.content_package_id,
                "content_version": record.content_version,
                "ui_locale": record.ui_locale,
                "instructional_language": record.instructional_language,
                "created_at": as_utc(record.created_at),
            }
        )

    async def _submission_view(self, session, record: SubmissionRecord) -> SubmissionView:
        job = await session.scalar(
            select(EvaluationJobRecord).where(
                EvaluationJobRecord.submission_id == record.submission_id
            )
        )
        if job is None:
            raise ResourceNotFound
        evaluation = await session.get(EvaluationRecord, record.submission_id)
        return SubmissionView.model_validate(
            {
                "submission_id": UUID(record.submission_id),
                "session_id": UUID(record.session_id),
                "content_package_id": record.content_package_id,
                "content_version": record.content_version,
                "item_id": record.item_id,
                "answer": record.answer,
                "reasoning": record.reasoning,
                "purpose": record.purpose,
                "parent_submission_id": (
                    UUID(record.parent_submission_id) if record.parent_submission_id else None
                ),
                "created_at": as_utc(record.created_at),
                "job": {"job_id": UUID(job.job_id), "status": job.status},
                "evaluation": (
                    {
                        "outcome_verdict": evaluation.outcome_verdict,
                        "reasoning_verdict": evaluation.reasoning_verdict,
                        "diagnostic_status": evaluation.diagnostic_status,
                        "evidence_references": evaluation.evidence_references,
                        "misconception_id": evaluation.misconception_id,
                    }
                    if evaluation
                    else None
                ),
            }
        )
