import os
import asyncio
import json
from uuid import uuid4
import pytest

from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore
from cobri.identity.auth import Principal
from cobri.tutoring.contracts import SessionCreate
from cobri.assessments.contracts import SubmissionCreate


@pytest.mark.anyio
async def test_competing_workers_lease_claiming():
    """
    Verifies that when two workers try to claim a job concurrently,
    only ONE worker gets the lease and the second receives None.
    """
    db_url = os.environ.get(
        "COBRI_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cobri_db"
    )
    database = Database(db_url)
    store = DatabaseStore(database)
    principal = Principal(issuer="test_issuer", subject="test_subject")

    try:
        # 1. Create a session
        session_view = await store.create_session(
            principal=principal,
            request=SessionCreate(
                content_package_id="python-control-flow",
                content_version="1.0.0",
                ui_locale="en",
                instructional_language="en",
            ),
        )

        # 2. Construct valid SubmissionCreate request
        submission_req = SubmissionCreate(
            item_id="item_01",
            answer=json.dumps({"code": "x = 1"}),
            reasoning="Testing concurrency",
            purpose="assessment",
        )

        await store.accept_submission(
            principal=principal,
            session_id=session_view.session_id,
            request=submission_req,
            idempotency_key=str(uuid4()),
        )

        # 3. Simulate concurrent job claims by two workers
        results = await asyncio.gather(
            store.claim_job(worker_id="worker_A", lease_seconds=10),
            store.claim_job(worker_id="worker_B", lease_seconds=10),
        )

        # 4. Assert mutual exclusion
        successful_claims = [r for r in results if r is not None]
        assert len(successful_claims) == 1

        claimed_submission, claimed_job = successful_claims[0]
        assert claimed_job.status == "running"
        assert claimed_job.lease_owner in ["worker_A", "worker_B"]

    finally:
        if hasattr(database, "engine"):
            await database.engine.dispose()