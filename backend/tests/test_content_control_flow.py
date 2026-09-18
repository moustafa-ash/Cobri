from pathlib import Path

import pytest

from cobri.content.catalog import FileContentCatalog
from cobri.errors import ResourceNotFound


def test_draft_control_flow_package_is_rejected_at_runtime():
    catalog = FileContentCatalog(Path(__file__).parents[2] / "content-packages")

    with pytest.raises(ResourceNotFound):
        catalog.get_package("python-control-flow", "1.0.0-draft")
