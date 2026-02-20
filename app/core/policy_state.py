"""
Shared state for the currently active insurance policy.

This is kept in a small dedicated module so it can be imported from both
route handlers and services without introducing circular imports.
"""
from __future__ import annotations

from typing import Optional

from app.core.policy_model import InsurancePolicyModel


CURRENT_POLICY: Optional[InsurancePolicyModel] = None


__all__ = ["CURRENT_POLICY"]

