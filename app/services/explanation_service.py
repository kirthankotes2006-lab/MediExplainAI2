"""
Explanation service for turning structured bill analysis into
patient-friendly, empowering language.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union


def _format_money(amount: Optional[Union[float, int]]) -> str:
    """Format numeric values as currency-like strings."""
    if amount is None:
        return "0.00"
    return f"{float(amount):,.2f}"


def generate_summary(result: Dict[str, Any]) -> str:
    """
    Convert a structured medical bill analysis into a patient-friendly explanation.

    The expected `result` structure matches the output of `analyze_medical_bill`:
    - total_bill_amount: float
    - total_claimable_amount: float
    - co_payment_deducted: float
    - excluded_items: List[dict]
    - non_payable_items: List[dict]
    - coverage_breakdown: List[dict]
    - cost_efficiency_warnings: List[dict]
    """
    total_bill = result.get("total_bill_amount", 0.0)
    total_claimable = result.get("total_claimable_amount", 0.0)
    co_payment = result.get("co_payment_deducted", 0.0)

    excluded_items: List[dict] = result.get("excluded_items", []) or []
    non_payable_items: List[dict] = result.get("non_payable_items", []) or []
    cost_warnings: List[dict] = result.get("cost_efficiency_warnings", []) or []

    lines: List[str] = []

    # Overview
    lines.append("Here is a clear summary of your medical bill and how your insurance may support you:")
    lines.append("")
    lines.append(f"- Total billed amount: ₹{_format_money(total_bill)}")
    lines.append(f"- Estimated amount your insurer could pay after co-payment: ₹{_format_money(total_claimable)}")
    lines.append(f"- Your share due to co-payment: approximately ₹{_format_money(co_payment)}")

    # Exclusions
    if excluded_items:
        names = ", ".join(item.get("name", "Unknown item") for item in excluded_items)
        lines.append("")
        lines.append("Some treatments are not covered under your current policy and may need to be paid fully by you:")
        lines.append(f"- Excluded items: {names}")
    else:
        lines.append("")
        lines.append("Good news: based on this analysis, we did not find any treatments marked as policy exclusions.")

    # Non-payable items
    if non_payable_items:
        names = ", ".join(item.get("name", "Unknown item") for item in non_payable_items)
        lines.append("")
        lines.append("Certain items are considered non-payable (for example, basic supplies or administrative charges):")
        lines.append(f"- Non-payable items: {names}")
        lines.append("These typically need to be covered by you and are standard across many insurance policies.")
    else:
        lines.append("")
        lines.append("We did not flag any standard non-payable items like basic supplies or admin charges in this bill.")

    # Cost awareness advisory
    lines.append("")
    lines.append("Cost awareness and advisory:")

    if cost_warnings:
        overpriced_items: List[str] = []
        for w in cost_warnings:
            item_name = w.get("item_name", "Unknown item")
            status = w.get("status", "overpriced")
            overpriced_items.append(f"{item_name} ({status.replace('_', ' ')})")

        lines.append("Our cost comparison suggests that some items may be priced higher than typical market rates:")
        lines.append(f"- Potentially overpriced: {', '.join(overpriced_items)}")
        lines.append(
            "You may want to ask your provider for a breakdown of these charges or if alternative options are available."
        )
        lines.append(
            "If feasible, consider checking prices at nearby hospitals, diagnostic centers, or labs for similar services, "
            "as some providers may offer significantly lower rates for the same treatment."
        )
    else:
        lines.append(
            "Based on our reference data, the costs in this bill appear to be within a normal market range for similar services."
        )

    lines.append(
        "Remember, this explanation is meant to empower you: you have the right to understand every charge, "
        "ask your insurer or hospital for clarifications, and explore more affordable options when possible."
    )

    return "\n".join(lines)


__all__ = ["generate_summary"]

