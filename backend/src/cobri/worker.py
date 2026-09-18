"""Database-polling evaluation worker."""

import asyncio
import logging
from dataclasses import dataclass, field

from cobri.assessments.contracts import EvaluationView
from cobri.config import Settings
from cobri.content.catalog import FileContentCatalog
from cobri.errors import IntegrationContractError
from cobri.evaluations.contracts import DiagnosticStatus, EvaluationInput
from cobri.model_gateway.fixture import FixtureEvaluator
from cobri.model_gateway.gateway import (
    ProviderUnavailable,
    StructuredModelGateway,
    evaluation_prompt,
)
from cobri.observability import OperationalMetrics
from cobri.persistence.database import Database
from cobri.persistence.repositories import DatabaseStore
from cobri.sandbox.docker_runner import DockerSandbox

logger = logging.getLogger(__name__)


@dataclass
class EvaluationWorker:
    settings: Settings
    store: DatabaseStore
    catalog: FileContentCatalog
    metrics: OperationalMetrics = field(default_factory=OperationalMetrics)

    async def run_once(self, worker_id: str = "local-worker") -> bool:
        await self.store.heartbeat(worker_id)
        claimed = await self.store.claim_job(
            worker_id,
            self.settings.worker_lease_seconds,
            self.settings.worker_max_attempts,
        )
        if claimed is None:
            return False
        self.metrics.increment("jobs_claimed")
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
            evaluation = await self._evaluate_with_lease(input_data, item, job.job_id, worker_id)
            self._validate_evaluation(evaluation, item)
            finished = await self.store.finish_job(
                job.job_id, worker_id, EvaluationView.from_evaluation(evaluation)
            )
            if finished:
                self.metrics.increment("jobs_succeeded")
        except Exception as exc:
            retry = job.attempts < self.settings.worker_max_attempts
            logger.warning("evaluation job %s failed: %s", job.job_id, type(exc).__name__)
            failed = await self.store.fail_job(job.job_id, worker_id, type(exc).__name__, retry)
            if failed:
                self.metrics.increment("jobs_retried" if retry else "jobs_failed")
        return True

    async def _evaluate(self, input_data: EvaluationInput, item):
        if self.settings.sandbox_enabled:
            sandbox = DockerSandbox(
                self.settings.sandbox_image, self.settings.sandbox_timeout_seconds
            )
            result = await asyncio.to_thread(sandbox.run, input_data.answer, item.tests)
            input_data = input_data.model_copy(update={"sandbox_passed": result.passed})
        if self.settings.evaluation_mode == "provider":
            if not self.settings.model_configured:
                raise ProviderUnavailable("provider evaluation mode has no configured provider")
            gateway = StructuredModelGateway(self.settings)
            evaluation = await gateway.evaluate(
                evaluation_prompt(
                    input_data,
                    {
                        "sources": [source.model_dump() for source in item.evidence],
                        "rubric": [criterion.model_dump() for criterion in item.rubric],
                        "allowed_misconceptions": item.misconception_ids,
                    },
                )
            )
            if input_data.sandbox_passed is not None:
                evaluation = evaluation.model_copy(
                    update={
                        "outcome_verdict": ("correct" if input_data.sandbox_passed else "incorrect")
                    }
                )
            return evaluation
        return FixtureEvaluator().evaluate(input_data, item)

    async def _evaluate_with_lease(self, input_data, item, job_id: str, worker_id: str):
        task = asyncio.create_task(self._evaluate(input_data, item))
        renewal_interval = max(1.0, self.settings.worker_lease_seconds / 3)
        while True:
            try:
                return await asyncio.wait_for(asyncio.shield(task), timeout=renewal_interval)
            except TimeoutError:
                renewed = await self.store.renew_job_lease(
                    job_id, worker_id, self.settings.worker_lease_seconds
                )
                if not renewed:
                    task.cancel()
                    raise RuntimeError("evaluation job lease was lost") from None

    @staticmethod
    def _validate_evaluation(evaluation, item) -> None:
        if not set(evaluation.evidence_references).issubset(item.evidence_references):
            raise IntegrationContractError("evaluation cited evidence outside the selected item")
        if evaluation.misconception_id not in [None, *item.misconception_ids]:
            raise IntegrationContractError("evaluation named an unsupported misconception")
        if (
            evaluation.diagnostic_status.value == "supported"
            and evaluation.misconception_id is not None
            and not evaluation.evidence_references
        ):
            raise IntegrationContractError("supported diagnoses must cite evidence")
        if (
            evaluation.diagnostic_status is DiagnosticStatus.UNCERTAIN
            and evaluation.misconception_id is not None
        ):
            raise IntegrationContractError("uncertain evaluations cannot name a misconception")


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
