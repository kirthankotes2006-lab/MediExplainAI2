import pytest

from app.core.cost_database import (
    LOCAL_COST_DATABASE,
    get_local_cost_info,
)


def test_get_local_cost_info_found():
    """Test retrieving cost info for items that exist in the database."""
    mri_info = get_local_cost_info("MRI Scan")
    assert mri_info is not None
    assert mri_info["average_cost"] == 9000
    assert mri_info["min_cost"] == 7000
    assert mri_info["max_cost"] == 11000

    blood_test_info = get_local_cost_info("Blood Test")
    assert blood_test_info is not None
    assert blood_test_info["average_cost"] == 800
    assert blood_test_info["min_cost"] == 500
    assert blood_test_info["max_cost"] == 1200

    gloves_info = get_local_cost_info("Gloves")
    assert gloves_info is not None
    assert gloves_info["average_cost"] == 100


def test_get_local_cost_info_case_insensitive():
    """Test that lookup is case-insensitive."""
    assert get_local_cost_info("mri scan") == get_local_cost_info("MRI Scan")
    assert get_local_cost_info("BLOOD TEST") == get_local_cost_info("Blood Test")
    assert get_local_cost_info("gloves") == get_local_cost_info("Gloves")


def test_get_local_cost_info_not_found():
    """Test that None is returned for items not in the database."""
    assert get_local_cost_info("Unknown Item") is None
    assert get_local_cost_info("X-Ray") is None
    assert get_local_cost_info("Non-existent Procedure") is None


@pytest.mark.parametrize("invalid_input", ["", "   ", None, 123])
def test_get_local_cost_info_invalid_input(invalid_input):
    """Test that ValueError is raised for invalid inputs."""
    with pytest.raises(ValueError):
        get_local_cost_info(invalid_input)  # type: ignore[arg-type]


def test_local_cost_database_structure():
    """Test that LOCAL_COST_DATABASE has the expected structure."""
    assert isinstance(LOCAL_COST_DATABASE, dict)
    assert "MRI Scan" in LOCAL_COST_DATABASE
    assert "Blood Test" in LOCAL_COST_DATABASE
    assert "Gloves" in LOCAL_COST_DATABASE

    # Verify each entry has the required keys
    for item_name, cost_info in LOCAL_COST_DATABASE.items():
        assert "average_cost" in cost_info
        assert "min_cost" in cost_info
        assert "max_cost" in cost_info
        assert isinstance(cost_info["average_cost"], (int, float))
        assert isinstance(cost_info["min_cost"], (int, float))
        assert isinstance(cost_info["max_cost"], (int, float))
