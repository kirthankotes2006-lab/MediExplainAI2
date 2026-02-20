"""
Core domain model for representing an insurance policy in a structured way.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InsurancePolicyModel:
    """
    In-memory representation of an insurance policy.

    This model is intentionally lightweight and independent of FastAPI/Pydantic
    so it can be reused in services and, later, ML models.
    """

    coverage_limits: Dict[str, float] = field(default_factory=dict)
    exclusions: List[str] = field(default_factory=list)
    non_payable_items: List[str] = field(default_factory=list)
    co_payment_percentage: float = 0.0

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a treatment or item name for case-insensitive lookups.

        Raises:
            ValueError: If the name is not a non-empty string.
        """
        if not isinstance(name, str):
            raise ValueError("treatment_name must be a string")
        normalized = name.strip()
        if not normalized:
            raise ValueError("treatment_name cannot be empty")
        return normalized

    def validate_treatment(self, treatment_name: str) -> bool:
        """
        Check if a treatment is valid for coverage evaluation.

        A treatment is considered valid if:
        - It has a coverage limit defined, and
        - It is not listed in the exclusions.

        Args:
            treatment_name: Name of the treatment/procedure.

        Returns:
            True if the treatment is valid for coverage, False otherwise.
        """
        normalized = self._normalize_name(treatment_name).lower()

        exclusions_ci = {name.lower() for name in self.exclusions}
        if normalized in exclusions_ci:
            return False

        coverage_ci = {name.lower() for name in self.coverage_limits.keys()}
        return normalized in coverage_ci

    def get_coverage_limit(self, treatment_name: str) -> Optional[float]:
        """
        Get the coverage limit for a treatment, if defined.

        Args:
            treatment_name: Name of the treatment/procedure.

        Returns:
            The coverage limit as a float if present, otherwise None.
        """
        normalized = self._normalize_name(treatment_name).lower()
        for name, limit in self.coverage_limits.items():
            if name.lower() == normalized:
                return float(limit)
        return None


__all__ = ["InsurancePolicyModel"]

