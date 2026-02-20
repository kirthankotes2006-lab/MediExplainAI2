"""
Local reference cost database and lookup helpers.

Keeps typical cost ranges for common items/procedures so that services
and ML components can reason about outliers and anomalies.
"""
from __future__ import annotations

from typing import Final, Optional


LOCAL_COST_DATABASE: Final[dict[str, dict[str, float]]] = {
    "MRI Scan": {
        "average_cost": 9000,
        "min_cost": 7000,
        "max_cost": 15000,
    },
    "Blood Test": {
        "average_cost": 1000,
        "min_cost": 600,
        "max_cost": 1800,
    },
    "ICU Charges": {
        "average_cost": 8000,  # Per day
        "min_cost": 5000,      # Per day
        "max_cost": 12000,     # Per day
    },
    "CT Scan": {
        "average_cost": 8000,
        "min_cost": 6000,
        "max_cost": 12000,
    },
    "Gloves": {
        "average_cost": 100,
        "min_cost": 50,
        "max_cost": 200,
    },
    "Administrative Charges": {
        "average_cost": 500,
        "min_cost": 200,
        "max_cost": 800,
    },
    "General Consultation": {
        "average_cost": 1200,
        "min_cost": 800,
        "max_cost": 1800,
    },
    "Knee Replacement Surgery": {
        "average_cost": 100000,
        "min_cost": 80000,
        "max_cost": 150000,
    },
    "Minor Surgery": {
        "average_cost": 30000,
        "min_cost": 15000,
        "max_cost": 60000,
    },
}


def _validate_item_name(item_name: str) -> str:
    """
    Validate and normalize an item name.

    Raises:
        ValueError: If the name is not a non-empty string.
    """
    if not isinstance(item_name, str):
        raise ValueError("item_name must be a string")

    normalized = item_name.strip()
    if not normalized:
        raise ValueError("item_name cannot be empty")

    return normalized


def get_local_cost_info(item_name: str) -> Optional[dict]:
    """
    Retrieve cost information for a given item from the local database.

    Lookup is case-insensitive.

    Args:
        item_name: Name of the procedure or item.

    Returns:
        A cost info dictionary (containing average/min/max cost) if found,
        otherwise None.

    Raises:
        ValueError: If item_name is invalid.
    """
    normalized = _validate_item_name(item_name).lower()

    # Build a case-insensitive index on demand (small dataset)
    ci_index: dict[str, dict[str, float]] = {
        name.lower(): info for name, info in LOCAL_COST_DATABASE.items()
    }

    cost_info = ci_index.get(normalized)
    # Return as-is; callers should treat result as read-only
    return cost_info


__all__ = [
    "LOCAL_COST_DATABASE",
    "get_local_cost_info",
]

