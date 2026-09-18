"""Validate the dataset or run one explicitly selected provider."""

import argparse
import asyncio
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from cobri.config import Settings
from cobri.evaluations.contracts import Evaluation, EvaluationInput
from cobri.model_gateway.gateway import StructuredModelGateway


def load_cases(path: Path) -> list[dict]:
    cases = json.loads((path / "evaluation.json").read_text(encoding="utf-8"))
    if path.name == "v1":
        assert len(cases) == 120
        assert Counter(case["language"] for case in cases) == {"en": 60, "ar": 60}
        for language in ("en", "ar"):
            counts = Counter(case["category"] for case in cases if case["language"] == language)
            assert set(counts.values()) == {12}
    for case in cases:
        Evaluation.model_validate(case["expected_verdict"])
    return cases


async def run_provider(cases: list[dict], provider: str, output: Path) -> dict:
    settings = Settings(_env_file=None)
    gateway = StructuredModelGateway(settings)
    model = settings.groq_model if provider == "groq" else settings.openrouter_model
    output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for case in cases:
        input_data = EvaluationInput(
            answer=case["input"]["answer"],
            reasoning=case["input"]["reasoning"],
            item_id=case["item_id"],
            content_package_id=case["content_package_id"],
            content_version=case["content_version"],
        )
        prompt = json.dumps({"case": case["input"], "item_id": case["item_id"]})
        started = perf_counter()
        attempts = 0
        error = None
        actual = None
        while attempts < 3:
            attempts += 1
            try:
                actual = await gateway.evaluate_provider(provider, prompt)
                break
            except Exception as exc:  # provider boundary: classify, do not leak response data
                error = type(exc).__name__
                if attempts == 3:
                    break
        results.append(
            {
                "case_id": case["case_id"],
                "provider": provider,
                "model": model,
                "latency_ms": round((perf_counter() - started) * 1000),
                "attempts": attempts,
                "failure_category": error,
                "result": actual.model_dump(mode="json") if actual else None,
                "expected": case["expected_verdict"],
                "input": input_data.model_dump(mode="json"),
            }
        )
    output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in results), encoding="utf-8"
    )
    comparable = [row for row in results if row["result"] is not None]
    matched = sum(row["result"] == row["expected"] for row in comparable)
    return {
        "provider": provider,
        "model": model,
        "cases": len(results),
        "completed": len(comparable),
        "exact_match": matched / len(comparable) if comparable else 0.0,
        "output": str(output),
        "quality": "pending_human_review",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("deterministic", "groq-only", "openrouter-only"), required=True
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    if args.mode == "deterministic":
        print(
            json.dumps(
                {
                    "mode": "deterministic",
                    "cases": len(cases),
                    "status": "validated",
                    "denominators": {
                        "languages": dict(Counter(case["language"] for case in cases)),
                        "categories": dict(Counter(case["category"] for case in cases)),
                    },
                    "safety": "not_claimed",
                    "quality": "not_claimed",
                }
            )
        )
        return 0
    if os.getenv("COBRI_RUN_LIVE_PROVIDERS") != "1":
        print(
            json.dumps(
                {"mode": args.mode, "status": "blocked", "reason": "set COBRI_RUN_LIVE_PROVIDERS=1"}
            )
        )
        return 2
    provider = args.mode.removesuffix("-only")
    key_name = f"COBRI_{provider.upper()}_API_KEY"
    if not os.getenv(key_name):
        print(json.dumps({"mode": args.mode, "status": "blocked", "reason": f"missing {key_name}"}))
        return 2
    settings = Settings(_env_file=None)
    if provider == "openrouter" and settings.openrouter_model == "openrouter/free":
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "status": "blocked",
                    "reason": "fixed OpenRouter model required",
                }
            )
        )
        return 2
    output = args.output or (
        Path(".data")
        / "evaluations"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        / f"{provider}.jsonl"
    )
    print(json.dumps(asyncio.run(run_provider(cases, provider, output)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
