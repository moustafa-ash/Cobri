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
from cobri.model_gateway.gateway import (
    ProviderUnavailable,
    StructuredModelGateway,
    evaluation_prompt,
)

CONTENT_ROOT = Path(__file__).parents[2] / "content-packages"


def load_cases(path: Path) -> list[dict]:
    cases = json.loads((path / "evaluation.json").read_text(encoding="utf-8"))
    if path.name == "v1":
        assert len(cases) == 120
        assert Counter(case["language"] for case in cases) == {"en": 60, "ar": 60}
        for language in ("en", "ar"):
            counts = Counter(case["category"] for case in cases if case["language"] == language)
            assert set(counts.values()) == {10}
        manifest = json.loads((path / "review-manifest.json").read_text(encoding="utf-8"))
        if manifest["dataset_digest"] != _digest(cases):
            raise ValueError("review manifest does not match the current dataset")
    for case in cases:
        Evaluation.model_validate(case["expected_verdict"])
    return cases


def _digest(value: object) -> str:
    import hashlib

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _review_approved(path: Path) -> bool:
    manifest = json.loads((path / "review-manifest.json").read_text(encoding="utf-8"))
    cases = json.loads((path / "evaluation.json").read_text(encoding="utf-8"))
    expected_items = set()
    for package_id, version in {
        (case["content_package_id"], case["content_version"]) for case in cases
    }:
        package = json.loads(
            (CONTENT_ROOT / package_id / version / "package.json").read_text(encoding="utf-8")
        )
        expected_items.update((package_id, version, item["item_id"]) for item in package["items"])
    actual_items = {
        (entry["package_id"], entry["version"], entry["item_id"])
        for entry in manifest["content_reviews"]
    }
    content_reviews_valid = True
    for review in manifest["content_reviews"]:
        package_path = CONTENT_ROOT / review["package_id"] / review["version"] / "package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))
        item = next(item for item in package["items"] if item["item_id"] == review["item_id"])
        content_reviews_valid &= (
            review["package_digest"] == _digest(package)
            and review["item_digest"] == _digest(item)
            and review["reviewer"] == "moustafa-ash"
            and review["status"] == "reviewed"
        )
    return (
        manifest["reviewer"] == "moustafa-ash"
        and manifest["status"] == "approved"
        and manifest["dataset_digest"] == _digest(cases)
        and actual_items == expected_items
        and len(manifest["case_reviews"]) == len(cases)
        and all(
            entry["status"] == "reviewed"
            and entry["reviewer"] == "moustafa-ash"
            and entry["digest"] == _digest(case)
            for entry, case in zip(manifest["case_reviews"], cases, strict=True)
        )
        and content_reviews_valid
    )


def report_metrics(rows: list[dict], cases: list[dict]) -> dict:
    """Report distinct metrics and block gates for signals this harness cannot observe."""
    completed = [row for row in rows if row["result"] is not None]
    cases_by_id = {case["case_id"]: case for case in cases}
    packages = {}
    for package_path in CONTENT_ROOT.glob("*/**/package.json"):
        package = json.loads(package_path.read_text(encoding="utf-8"))
        packages[(package["content_package_id"], package["content_version"])] = package

    def rate(numerator: int, denominator: int, threshold: float) -> dict:
        value = numerator / denominator if denominator else None
        gate = "blocked" if value is None else "pass" if value >= threshold else "fail"
        return {
            "value": value,
            "numerator": numerator,
            "denominator": denominator,
            "threshold": threshold,
            "gate": gate,
        }

    outcome = sum(
        row["result"]["outcome_verdict"] == row["expected"]["outcome_verdict"] for row in completed
    )
    reasoning = sum(
        row["result"]["reasoning_verdict"] == row["expected"]["reasoning_verdict"]
        for row in completed
    )
    supported = [row for row in completed if row["expected"]["diagnostic_status"] == "supported"]
    true_positive = sum(
        row["result"]["diagnostic_status"] == "supported"
        and row["result"]["misconception_id"] == row["expected"]["misconception_id"]
        for row in supported
    )
    false_positive_count = sum(
        row["result"]["diagnostic_status"] == "supported"
        and row["expected"]["diagnostic_status"] != "supported"
        for row in completed
    )
    grounded = 0
    for row in completed:
        case = cases_by_id[row["case_id"]]
        package = packages[(case["content_package_id"], case["content_version"])]
        item = next(item for item in package["items"] if item["item_id"] == case["item_id"])
        grounded += set(row["result"]["evidence_references"]).issubset(
            set(item["evidence_references"])
        )
    adversarial = [
        row for row in completed if cases_by_id[row["case_id"]]["category"] == "adversarial"
    ]
    safe = sum(row["result"] == row["expected"] for row in adversarial)
    latencies = sorted(row["latency_ms"] for row in rows)
    return {
        "outcome_accuracy": rate(outcome, len(completed), 0.90),
        "reasoning_classification": rate(reasoning, len(completed), 0.90),
        "diagnostic_precision": rate(true_positive, true_positive + false_positive_count, 0.90),
        "uncertainty_calibration": {
            "gate": "blocked",
            "reason": "confidence labels are not captured",
        },
        "evidence_grounding": rate(grounded, len(completed), 0.90),
        "safety": rate(safe, len(adversarial), 1.0),
        "latency_ms": {
            "p50": latencies[len(latencies) // 2] if latencies else None,
            "p95": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
            if latencies
            else None,
        },
        "quota_failures": {
            "count": sum(row.get("failure_category") == "quota" for row in rows),
            "gate": "report-only",
        },
        "supported_recall_at_3": {
            "gate": "blocked",
            "threshold": 0.95,
            "reason": "ranked retrieval traces are not captured by this provider harness",
        },
    }


async def run_provider(cases: list[dict], provider: str, output: Path, dataset_path: Path) -> dict:
    settings = Settings(_env_file=None)
    gateway = StructuredModelGateway(settings)
    model = settings.groq_model if provider == "groq" else settings.openrouter_model
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((dataset_path / "review-manifest.json").read_text(encoding="utf-8"))
    package_versions = {(case["content_package_id"], case["content_version"]) for case in cases}
    packages = {
        key: json.loads(
            (CONTENT_ROOT / key[0] / key[1] / "package.json").read_text(encoding="utf-8")
        )
        for key in package_versions
    }
    rubrics = {
        f"{package_id}:{version}:{item['item_id']}": _digest(item["rubric"])
        for (package_id, version), package in packages.items()
        for item in package["items"]
    }
    provenance = {
        "provider": provider,
        "model": model,
        "prompt_version": "cobri-evaluation-v1",
        "schema_digest": _digest(Evaluation.model_json_schema()),
        "rubric_digests": rubrics,
        "package_digests": {
            f"{key[0]}:{key[1]}": _digest(value) for key, value in packages.items()
        },
        "retrieval_index_version": "direct-reviewed-package-evidence-v1",
        "dataset_version": dataset_path.name,
        "dataset_digest": manifest["dataset_digest"],
    }
    results = []
    for case in cases:
        input_data = EvaluationInput(
            answer=case["input"]["answer"],
            reasoning=case["input"]["reasoning"],
            item_id=case["item_id"],
            content_package_id=case["content_package_id"],
            content_version=case["content_version"],
        )
        package = packages[(case["content_package_id"], case["content_version"])]
        item = next(item for item in package["items"] if item["item_id"] == case["item_id"])
        prompt = evaluation_prompt(
            input_data,
            {
                "sources": item["evidence"],
                "rubric": item["rubric"],
                "allowed_misconceptions": item["misconception_ids"],
                "language": case["language"],
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
                break
            except Exception as exc:  # provider boundary: classify, do not leak response data
                error = exc.category if isinstance(exc, ProviderUnavailable) else type(exc).__name__
                if attempts == 3:
                    break
        results.append(
            {
                "case_id": case["case_id"],
                "provider": provider,
                "model": model,
                "provenance": provenance,
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
    return {
        "provider": provider,
        "model": model,
        "cases": len(results),
        "completed": len(comparable),
        "metrics": report_metrics(results, cases),
        "provenance": provenance,
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
    if not _review_approved(args.dataset):
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "status": "blocked",
                    "reason": (
                        "Moustafa must approve every digest-bound content item and dataset case "
                        "first"
                    ),
                }
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
    report = asyncio.run(run_provider(cases, provider, output, args.dataset))
    print(json.dumps(report, ensure_ascii=False))
    required = (
        "outcome_accuracy",
        "reasoning_classification",
        "diagnostic_precision",
        "uncertainty_calibration",
        "evidence_grounding",
        "safety",
        "supported_recall_at_3",
    )
    gates = [report["metrics"][name]["gate"] for name in required]
    if "fail" in gates:
        return 1
    if "blocked" in gates:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
