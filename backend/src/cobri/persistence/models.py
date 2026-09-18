"""Portable SQLAlchemy models for the Day 1 durable workflow."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_owner", "issuer", "subject"),)

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    content_package_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_version: Mapped[str] = mapped_column(String(128), nullable=False)
    ui_locale: Mapped[str] = mapped_column(String(2), nullable=False)
    instructional_language: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SubmissionRecord(Base):
    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_owner", "issuer", "subject"),)

    submission_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    content_package_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_version: Mapped[str] = mapped_column(String(128), nullable=False)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False, default="assessment")
    parent_submission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("issuer", "subject", "session_id", "idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    submission_id: Mapped[str] = mapped_column(String(36), nullable=False)


class EvaluationJobRecord(Base):
    __tablename__ = "evaluation_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    submission_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    outcome_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    reasoning_verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    diagnostic_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    misconception_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class WorkerHeartbeatRecord(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearnerEventRecord(Base):
    __tablename__ = "learner_events"
    __table_args__ = (Index("ix_learner_events_owner", "issuer", "subject", "created_at"),)

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    submission_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearnerProgressRecord(Base):
    __tablename__ = "learner_progress"
    __table_args__ = (
        UniqueConstraint("issuer", "subject", "content_package_id", "content_version", "item_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issuer: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    content_package_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_version: Mapped[str] = mapped_column(String(128), nullable=False)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="started")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmbeddingRecord(Base):
    __tablename__ = "content_embeddings"
    __table_args__ = (
        UniqueConstraint("content_package_id", "content_version", "item_id", "model_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_package_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_version: Mapped[str] = mapped_column(String(128), nullable=False)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(256), nullable=False)
    tokenizer_revision: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized: Mapped[bool] = mapped_column(nullable=False, default=True)
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)


class QuarantinedSourceRecord(Base):
    __tablename__ = "quarantined_sources"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="quarantined")
