"""
Core insurance policy configuration and helper utilities.

This module centralizes business rules around insurance coverage so they can
be reused across services and easily extended for future ML-based reasoning.
"""
from __future__ import annotations

from typing import Final, Optional


INSURANCE_POLICY: Final[dict] = {
    "coverage_limits": {
        "General Consultation": 2000,
        "Blood Test": 3000,
        "MRI Scan": 18000,
        "CT Scan": 15000,
        "ICU Charges": 10000,  # Per day, max 3 days
        "Minor Surgery": 50000,
        "Major Surgery": 200000,
        "Knee Replacement Surgery": 150000,
    },
    "exclusions": [
        "Cosmetic Surgery",
        "Fertility Treatment",
        "Experimental Procedures",
        "Experimental Treatment",
    ],
    "non_payable_items": [
        "Gloves",
        "Masks",
        "Sanitizer",
        "Administrative Charges",
        "Registration Fees",
        "Sanitization Charges",
    ],
    "co_payment_percentage": 15,
}


def _validate_name(name: str, *, field_label: str = "name") -> str:
    """
    Validate and normalize a string name.

    Raises:
        ValueError: If the input is empty or only whitespace.
    """
    if not isinstance(name, str):
        raise ValueError(f"{field_label} must be a string")

    normalized = name.strip()
    if not normalized:
        raise ValueError(f"{field_label} cannot be empty")

    return normalized


def is_treatment_excluded(name: str) -> bool:
    """
    Check if a treatment is in the exclusions list.

    Args:
        name: Treatment name.

    Returns:
        True if the treatment is excluded, False otherwise.

    Raises:
        ValueError: If the input is invalid.
    """
    normalized = _validate_name(name, field_label="treatment name").lower()
    exclusions = {item.lower() for item in INSURANCE_POLICY["exclusions"]}
    return normalized in exclusions


def is_treatment_covered(name: str) -> bool:
    """
    Check if a treatment is covered under the policy.

    A treatment is considered covered if it has a coverage limit defined
    and is not explicitly excluded.

    Args:
        name: Treatment name.

    Returns:
        True if the treatment is covered, False otherwise.

    Raises:
        ValueError: If the input is invalid.
    """
    normalized = _validate_name(name, field_label="treatment name").lower()

    coverage_limits = {
        k.lower(): v for k, v in INSURANCE_POLICY["coverage_limits"].items()
    }
    if normalized not in coverage_limits:
        return False

    if is_treatment_excluded(name):
        return False

    return True


def get_coverage_limit(name: str) -> Optional[float]:
    """
    Get the coverage limit for a treatment.

    Args:
        name: Treatment name.

    Returns:
        The coverage limit as a float if defined, otherwise None.

    Raises:
        ValueError: If the input is invalid.
    """
    normalized = _validate_name(name, field_label="treatment name").lower()

    coverage_limits = {
        k.lower(): float(v) for k, v in INSURANCE_POLICY["coverage_limits"].items()
    }
    return coverage_limits.get(normalized)


def is_non_payable_item(name: str) -> bool:
    """
    Check if an item is in the non-payable list.

    Args:
        name: Item name.

    Returns:
        True if the item is non-payable, False otherwise.

    Raises:
        ValueError: If the input is invalid.
    """
    normalized = _validate_name(name, field_label="item name").lower()
    non_payable_items = {
        item.lower() for item in INSURANCE_POLICY["non_payable_items"]
    }
    return normalized in non_payable_items


def get_co_payment_percentage() -> float:
    """
    Get the co-payment percentage defined in the policy.

    Returns:
        Co-payment percentage as a float.
    """
    return float(INSURANCE_POLICY["co_payment_percentage"])


__all__ = [
    "INSURANCE_POLICY",
    "is_treatment_excluded",
    "is_treatment_covered",
    "get_coverage_limit",
    "is_non_payable_item",
    "get_co_payment_percentage",
]

