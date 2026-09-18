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
from cobri.content.catalog import FileContentCatalog
from cobri.evaluations.contracts import Evaluation, EvaluationInput
from cobri.model_gateway.gateway import StructuredModelGateway, evaluation_prompt


def _value(row: dict, field: str):
    value = row.get(field)
    if isinstance(value, list):
        return tuple(sorted(value))
    return value


def _accuracy(rows: list[dict], field: str) -> float:
    return sum(
        _value(row["result"], field) == _value(row["expected"], field) for row in rows
    ) / len(rows)


def _macro_f1(rows: list[dict], field: str) -> float:
    labels = {_value(row["result"], field) for row in rows} | {
        _value(row["expected"], field) for row in rows
    }
    scores = []
    for label in labels:
        true_positive = sum(
            _value(row["result"], field) == label == _value(row["expected"], field) for row in rows
        )
        false_positive = sum(
            _value(row["result"], field) == label and _value(row["expected"], field) != label
            for row in rows
        )
        false_negative = sum(
            _value(row["result"], field) != label and _value(row["expected"], field) == label
            for row in rows
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0
        )
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return sum(scores) / len(scores) if scores else 0.0


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
    settings = Settings()
    gateway = StructuredModelGateway(settings)
    catalog = FileContentCatalog(settings.content_root)
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
        item = catalog.get_item(
            case["content_package_id"], case["content_version"], case["item_id"]
        )
        prompt = evaluation_prompt(
            input_data,
            {
                "sources": [source.model_dump() for source in item.evidence],
                "rubric": [criterion.model_dump() for criterion in item.rubric],
                "allowed_misconceptions": item.misconception_ids,
            },
        )
        started = perf_counter()
        attempts = 0
        error = None
        actual = None
        while attempts < 3:
            attempts += 1
            try:
                actual = await gateway.evaluate_provider(provider, prompt)
                error = None
                break
            except Exception as exc:  # provider boundary: classify, do not leak response data
                error = type(exc).__name__
                if attempts == 3:
                    break
        results.append(
            {
                "case_id": case["case_id"],
                "language": case["language"],
                "category": case["category"],
                "content_package_id": case["content_package_id"],
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
    fields = (
        "outcome_verdict",
        "reasoning_verdict",
        "diagnostic_status",
        "misconception_id",
        "evidence_references",
    )
    metrics = {
        f"{field}_accuracy": _accuracy(comparable, field) if comparable else 0.0 for field in fields
    }
    metrics.update(
        {
            f"{field}_macro_f1": _macro_f1(comparable, field) if comparable else 0.0
            for field in fields
        }
    )
    adversarial = [row for row in results if row["category"] == "adversarial"]
    unsupported_citations = sum(
        bool(
            set(row["result"]["evidence_references"]) - set(row["expected"]["evidence_references"])
        )
        for row in comparable
    )
    false_misconceptions = sum(
        row["result"]["misconception_id"] is not None
        and row["expected"]["misconception_id"] is None
        for row in comparable
    )
    summary = {
        "provider": provider,
        "model": model,
        "cases": len(results),
        "completed": len(comparable),
        "failed": len(results) - len(comparable),
        "denominators": {
            "languages": dict(Counter(case["language"] for case in cases)),
            "categories": dict(Counter(case["category"] for case in cases)),
            "packages": dict(Counter(case["content_package_id"] for case in cases)),
        },
        "exact_match": matched / len(comparable) if comparable else 0.0,
        "metrics": metrics,
        "unsupported_citations": unsupported_citations,
        "false_misconceptions": false_misconceptions,
        "adversarial_safety": {
            "completed": sum(row["result"] is not None for row in adversarial),
            "total": len(adversarial),
            "pass": len(adversarial) > 0 and all(row["result"] is not None for row in adversarial),
        },
        "cost_usd": None,
        "cost_cap_usd": 1.0,
        "cost_status": "provider_usage_not_exposed",
        "output": str(output),
        "quality": "pending_human_review",
    }
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


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
    settings = Settings()
    provider = args.mode.removesuffix("-only")
    key_name = f"COBRI_{provider.upper()}_API_KEY"
    if not getattr(settings, f"{provider}_api_key"):
        print(json.dumps({"mode": args.mode, "status": "blocked", "reason": f"missing {key_name}"}))
        return 2
    settings = Settings()
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
