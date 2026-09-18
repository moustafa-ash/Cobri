import json
from collections import Counter
from pathlib import Path


def test_v1_dataset_has_required_bilingual_allocation() -> None:
    path = Path(__file__).parent / "fixtures" / "evaluations" / "v1" / "evaluation.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert len(cases) == 120
    assert Counter(case["language"] for case in cases) == {"en": 60, "ar": 60}
    for language in ("en", "ar"):
        counts = Counter(case["category"] for case in cases if case["language"] == language)
        assert set(counts.values()) == {12}
