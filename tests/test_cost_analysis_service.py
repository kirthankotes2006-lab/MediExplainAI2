import pytest

from app.services.cost_analysis_service import analyze_cost_efficiency


def test_analyze_cost_efficiency_highly_overpriced():
    """Test detection of highly overpriced items (above max_cost)."""
    result = analyze_cost_efficiency("MRI Scan", 12000)
    
    assert result is not None
    assert result["item_name"] == "MRI Scan"
    assert result["billed_cost"] == 12000.0
    assert result["average_cost"] == 9000.0
    assert result["min_cost"] == 7000.0
    assert result["max_cost"] == 11000.0
    assert result["status"] == "highly_overpriced"


def test_analyze_cost_efficiency_slightly_overpriced():
    """Test detection of slightly overpriced items (above average but <= max)."""
    result = analyze_cost_efficiency("Blood Test", 1000)
    
    assert result is not None
    assert result["item_name"] == "Blood Test"
    assert result["billed_cost"] == 1000.0
    assert result["average_cost"] == 800.0
    assert result["status"] == "slightly_overpriced"


def test_analyze_cost_efficiency_within_market_range():
    """Test items within market range (<= average_cost)."""
    result = analyze_cost_efficiency("Gloves", 75)
    
    assert result is not None
    assert result["item_name"] == "Gloves"
    assert result["billed_cost"] == 75.0
    assert result["average_cost"] == 100.0
    assert result["status"] == "within_market_range"
    
    # Test at average cost boundary
    result2 = analyze_cost_efficiency("Blood Test", 800)
    assert result2 is not None
    assert result2["status"] == "within_market_range"


def test_analyze_cost_efficiency_at_boundaries():
    """Test behavior at cost boundaries."""
    # Exactly at max_cost should be slightly_overpriced (not highly)
    result = analyze_cost_efficiency("MRI Scan", 11000)
    assert result is not None
    assert result["status"] == "slightly_overpriced"
    
    # Just above max_cost should be highly_overpriced
    result2 = analyze_cost_efficiency("MRI Scan", 11001)
    assert result2 is not None
    assert result2["status"] == "highly_overpriced"
    
    # Exactly at average_cost should be within_market_range
    result3 = analyze_cost_efficiency("Blood Test", 800)
    assert result3 is not None
    assert result3["status"] == "within_market_range"


def test_analyze_cost_efficiency_item_not_found():
    """Test that None is returned for items not in the database."""
    result = analyze_cost_efficiency("Unknown Item", 1000)
    assert result is None


def test_analyze_cost_efficiency_case_insensitive():
    """Test that item lookup is case-insensitive."""
    result1 = analyze_cost_efficiency("MRI Scan", 12000)
    result2 = analyze_cost_efficiency("mri scan", 12000)
    
    assert result1 is not None
    assert result2 is not None
    # Check that cost values match (item_name preserves original case)
    assert result1["billed_cost"] == result2["billed_cost"]
    assert result1["average_cost"] == result2["average_cost"]
    assert result1["min_cost"] == result2["min_cost"]
    assert result1["max_cost"] == result2["max_cost"]
    assert result1["status"] == result2["status"]


@pytest.mark.parametrize("invalid_cost", [0, -1, -100, 0.0, -0.5])
def test_analyze_cost_efficiency_invalid_billed_cost(invalid_cost):
    """Test that ValueError is raised for invalid billed_cost (<= 0)."""
    with pytest.raises(ValueError, match="billed_cost must be greater than 0"):
        analyze_cost_efficiency("MRI Scan", invalid_cost)


def test_analyze_cost_efficiency_invalid_item_name():
    """Test that ValueError is raised for invalid item_name."""
    with pytest.raises(ValueError):
        analyze_cost_efficiency("", 1000)
    
    with pytest.raises(ValueError):
        analyze_cost_efficiency("   ", 1000)


def test_analyze_cost_efficiency_non_numeric_cost():
    """Test that ValueError is raised for non-numeric billed_cost."""
    with pytest.raises(ValueError, match="billed_cost must be a number"):
        analyze_cost_efficiency("MRI Scan", "not a number")  # type: ignore[arg-type]
    
    with pytest.raises(ValueError, match="billed_cost must be a number"):
        analyze_cost_efficiency("MRI Scan", None)  # type: ignore[arg-type]
