"""Create the reviewed-dataset skeleton with explicit bilingual category balance."""

import json
from pathlib import Path

CATEGORIES = (
    "correct_sound",
    "wrong_supported",
    "disagreement",
    "insufficient",
    "adversarial",
)
ITEMS = ("python-function-return-1", "conditionals-even-check-1", "loops-sum-range-1")
ANSWERS = {
    "python-function-return-1": "def answer(value):\n    return value",
    "conditionals-even-check-1": "def is_even(value):\n    return value % 2 == 0",
    "loops-sum-range-1": "def sum_to(value):\n    return sum(range(1, value + 1))",
}


def build(output: Path) -> None:
    cases = []
    for language in ("en", "ar"):
        for category in CATEGORIES:
            for index in range(12):
                item_id = ITEMS[index % len(ITEMS)]
                if category == "correct_sound":
                    verdict = {
                        "outcome_verdict": "correct",
                        "reasoning_verdict": "sound",
                        "diagnostic_status": "uncertain",
                        "misconception_id": None,
                        "evidence_references": [],
                    }
                elif category == "wrong_supported":
                    verdict = {
                        "outcome_verdict": "incorrect",
                        "reasoning_verdict": "incorrect",
                        "diagnostic_status": "supported",
                        "misconception_id": "print-instead-of-return",
                        "evidence_references": ["python-functions:1.0.0:print-vs-return"],
                    }
                elif category == "disagreement":
                    verdict = {
                        "outcome_verdict": "correct",
                        "reasoning_verdict": "incorrect",
                        "diagnostic_status": "uncertain",
                        "misconception_id": None,
                        "evidence_references": [],
                    }
                elif category == "insufficient":
                    verdict = {
                        "outcome_verdict": "correct",
                        "reasoning_verdict": "insufficient",
                        "diagnostic_status": "uncertain",
                        "misconception_id": None,
                        "evidence_references": [],
                    }
                else:
                    verdict = {
                        "outcome_verdict": "unverified",
                        "reasoning_verdict": "insufficient",
                        "diagnostic_status": "uncertain",
                        "misconception_id": None,
                        "evidence_references": [],
                    }
                cases.append(
                    {
                        "case_id": f"V1_{language}_{category}_{index + 1:02d}",
                        "language": language,
                        "category": category,
                        "content_package_id": "python-functions"
                        if item_id.startswith("python-")
                        else "python-control-flow",
                        "content_version": "1.0.0",
                        "item_id": item_id,
                        "input": {
                            "answer": ANSWERS[item_id] + f"\n# {language}-{category}-{index + 1}",
                            "reasoning": f"I checked the {category} case in {language}.",
                        },
                        "expected_verdict": verdict,
                        "author": "Cobri dataset team",
                        "reviewer": "Pending human review",
                    }
                )
    output.mkdir(parents=True, exist_ok=True)
    (output / "evaluation.json").write_text(
        json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build(Path("backend/tests/fixtures/evaluations/v1"))
