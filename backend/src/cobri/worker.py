"""Database-polling evaluation worker."""

import asyncio
import logging
from dataclasses import dataclass

from cobri.assessments.contracts import EvaluationView
from cobri.config import Settings
from cobri.content.catalog import FileContentCatalog
from cobri.evaluations.contracts import EvaluationInput
from cobri.model_gateway.fixture import FixtureEvaluator
from cobri.model_gateway.gateway import (
    StructuredModelGateway,
    evaluation_prompt,
)
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore
from cobri.sandbox.docker_runner import DockerSandbox, SandboxUnavailable

logger = logging.getLogger(__name__)


@dataclass
class EvaluationWorker:
    settings: Settings
    store: DatabaseStore
    catalog: FileContentCatalog

    async def run_once(self, worker_id: str = "local-worker") -> bool:
        await self.store.heartbeat(worker_id)
        claimed = await self.store.claim_job(
            worker_id,
            self.settings.worker_lease_seconds,
            self.settings.worker_max_attempts,
        )
        if claimed is None:
            return False
        submission, job = claimed
        try:
            item = self.catalog.get_item(
                submission.content_package_id,
                submission.content_version,
                submission.item_id,
            )
            input_data = EvaluationInput(
                answer=submission.answer,
                reasoning=submission.reasoning,
                item_id=submission.item_id,
                content_package_id=submission.content_package_id,
                content_version=submission.content_version,
            )
            evaluation = await self._evaluate(input_data, item)
            await self.store.finish_job(job.job_id, EvaluationView.from_evaluation(evaluation))
        except Exception as exc:
            retry = job.attempts < self.settings.worker_max_attempts
            logger.warning("evaluation job %s failed: %s", job.job_id, type(exc).__name__)
            await self.store.fail_job(job.job_id, type(exc).__name__, retry)
        return True

    async def _evaluate(self, input_data: EvaluationInput, item):
        if self.settings.sandbox_enabled:
            sandbox = DockerSandbox(
                self.settings.sandbox_image, self.settings.sandbox_timeout_seconds
            )
            result = sandbox.run(input_data.answer, item.tests)
            if result.timed_out:
                raise SandboxUnavailable("sandbox execution timed out")
            if result.passed:
                input_data = input_data.model_copy(update={"answer": item.expected_code})
            else:
                input_data = input_data.model_copy(update={"answer": "__sandbox_failed__"})
        if self.settings.model_configured:
            gateway = StructuredModelGateway(self.settings)
            return await gateway.evaluate(
                evaluation_prompt(input_data, "\n".join(item.evidence_references))
            )
        return FixtureEvaluator().evaluate(input_data, item)


async def run_worker(settings: Settings) -> None:
    database = Database(settings.database_url)
    catalog = FileContentCatalog(settings.content_root)
    store = DatabaseStore(database)
    worker = EvaluationWorker(settings, store, catalog)
    try:
        while True:
            await worker.run_once()
            await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        await database.dispose()


def main() -> None:
    asyncio.run(run_worker(Settings()))


if __name__ == "__main__":
    main()
