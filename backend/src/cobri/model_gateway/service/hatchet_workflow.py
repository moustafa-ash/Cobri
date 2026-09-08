from hatchet_sdk import Context
import hatchet as hatchet
from Cobri.backend.src.cobri.model_gateway.model.model_contracts import Submission, Evaluation, OutcomeVerdict
from Cobri.backend.src.cobri.model_gateway.validators.PythonValidator import PythonOutcomeEvaluator
from Cobri.backend.src.cobri.model_gateway.validators.llms_reasoning_evaluator import LLMReasoningEvaluator
from Cobri.backend.src.cobri.model_gateway.service.Evaluatingoutcomeservice import EvaluationCompositeService

@hatchet.workflow(on_events=["submission:created"], timeout="60s")
class EvaluateSubmissionWorkflow:

    @hatchet.step()
    async def evaluate_code(self, context: Context) -> dict:
        """Step 1: Run code through the deterministic outcome evaluator."""
        input_data = context.workflow_input()
        submission = Submission(**input_data)
        
        outcome_evaluator = PythonOutcomeEvaluator()
        outcome = await outcome_evaluator.evaluate_outcome(submission.code)
        
        return {"outcome_verdict": outcome.value}

    @hatchet.step(parents=["evaluate_code"])
    async def evaluate_reasoning(self, context: Context) -> dict:
        """Step 2: Pass explanation and code outcome to the LLM reasoning agent."""
        input_data = context.workflow_input()
        submission = Submission(**input_data)
        
        # Get outcome from previous step
        code_step_result = context.step_output("evaluate_code")
        outcome = OutcomeVerdict(code_step_result["outcome_verdict"])
        
        # Call reasoning evaluator agent
        reasoning_evaluator = LLMReasoningEvaluator(gateway_client=...)
        reasoning_verdict, diagnostic_status, misconception_id = (
            await reasoning_evaluator.evaluate_reasoning(submission.explanation, outcome)
        )
        
        return {
            "reasoning_verdict": reasoning_verdict.value,
            "diagnostic_status": diagnostic_status.value,
            "misconception_id": misconception_id
        }

    @hatchet.step(parents=["evaluate_code", "evaluate_reasoning"])
    async def combine_and_persist(self, context: Context) -> dict:
        """Step 3: Combine verdicts using Composite Service and persist."""
        code_res = context.step_output("evaluate_code")
        reasoning_res = context.step_output("evaluate_reasoning")
        
        # Merge using composite orchestrator rules
        # (e.g. enforcing invariant that failed code overrides sound reasoning)
        final_evaluation = EvaluationCompositeService.reconcile(code_res, reasoning_res)
        
        # Store in database & update session state
        # ...
        return final_evaluation.model_dump()