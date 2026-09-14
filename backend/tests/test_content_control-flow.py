import pytest
from cobri.content.ports import FileContentCatalog, ContentPackageNotFoundError


def test_draft_control_flow_package_is_rejected_at_runtime():
    catalog = FileContentCatalog("content-packages")
    
    with pytest.raises(ContentPackageNotFoundError):
        catalog.get_package("python-control-flow", "1.0.0-draft")