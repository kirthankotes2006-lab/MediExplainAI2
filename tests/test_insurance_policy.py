import pytest

from app.core.insurance_policy import (
    is_treatment_excluded,
    is_treatment_covered,
    get_coverage_limit,
    is_non_payable_item,
    get_co_payment_percentage,
)


def test_is_treatment_excluded():
    assert is_treatment_excluded("Cosmetic Surgery") is True
    assert is_treatment_excluded("cosmetic surgery") is True
    assert is_treatment_excluded("General Consultation") is False


def test_is_treatment_covered():
    assert is_treatment_covered("General Consultation") is True
    assert is_treatment_covered("Unknown Treatment") is False


def test_get_coverage_limit():
    assert get_coverage_limit("General Consultation") == 2000.0
    assert get_coverage_limit("Blood Test") == 1500.0
    assert get_coverage_limit("Unknown Treatment") is None


def test_is_non_payable_item():
    assert is_non_payable_item("Gloves") is True
    assert is_non_payable_item("gloves") is True
    assert is_non_payable_item("MRI Scan") is False


def test_get_co_payment_percentage():
    assert get_co_payment_percentage() == 10.0


@pytest.mark.parametrize("value", ["", "   ", None])
def test_invalid_treatment_name_raises(value):
    with pytest.raises(ValueError):
        # type: ignore[arg-type]
        is_treatment_covered(value)

