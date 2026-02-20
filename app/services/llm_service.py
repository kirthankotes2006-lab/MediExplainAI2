"""
LLM Service for generating natural language explanations of billing analysis.

Uses OpenAI API to provide clear, patient-friendly explanations of medical bill
analysis results.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

from openai import OpenAI, APIError, APIConnectionError


logger = logging.getLogger(__name__)


def _get_openai_client() -> Optional[OpenAI]:
    """
    Initialize and return an OpenAI client if API key is available.

    Returns:
        OpenAI client instance if API key is set, otherwise None.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY environment variable not set")
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None


def generate_llm_explanation(analysis: Dict[str, Any]) -> str:
    """
    Generate a natural language explanation of medical bill analysis using LLM.

    Uses OpenAI API to create patient-friendly, transparent explanations of
    billing analysis results including exclusions, non-payable items, cost
    deviations, and anomalies.

    Args:
        analysis: Dictionary containing analysis results with keys:
            - total_bill_amount: float - Total billed amount
            - total_claimable_amount: float - Amount insurance will cover
            - co_payment_deducted: float - Co-payment amount
            - excluded_items: List[dict] - Items excluded from coverage
            - non_payable_items: List[dict] - Items insurance won't pay
            - coverage_breakdown: List[dict] - Breakdown of covered items
            - cost_efficiency_warnings: List[dict] - Potential overpricing flags

    Returns:
        String containing a natural language explanation of the billing analysis.
        Falls back to a basic template explanation if LLM is unavailable.
    """
    client = _get_openai_client()

    # Calculate cost deviation percentage if possible
    cost_deviation_pct = 0.0
    if analysis.get("total_bill_amount", 0) > 0:
        claimable = analysis.get("total_claimable_amount", 0)
        total = analysis.get("total_bill_amount", 0)
        cost_deviation_pct = ((total - claimable) / total) * 100 if total > 0 else 0

    # Check for statistical anomalies
    has_anomalies = len(analysis.get("cost_efficiency_warnings", [])) > 0

    # Prepare context for the LLM
    context = f"""
Total Bill: ${analysis.get('total_bill_amount', 0):,.2f}
Claimable Amount: ${analysis.get('total_claimable_amount', 0):,.2f}
Co-Payment: ${analysis.get('co_payment_deducted', 0):,.2f}
Cost Deviation: {cost_deviation_pct:.1f}%
Statistical Anomalies: {'Yes' if has_anomalies else 'No'}

Excluded Items ({len(analysis.get('excluded_items', []))}):
{_format_items(analysis.get('excluded_items', []))}

Non-Payable Items ({len(analysis.get('non_payable_items', []))}):
{_format_items(analysis.get('non_payable_items', []))}

Cost Efficiency Warnings ({len(analysis.get('cost_efficiency_warnings', []))}):
{_format_items(analysis.get('cost_efficiency_warnings', []))}

Coverage Breakdown ({len(analysis.get('coverage_breakdown', []))}):
{_format_items(analysis.get('coverage_breakdown', []))}
    """.strip()

    if not client:
        return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)

    try:
        system_prompt = (
            "You are a healthcare insurance assistant. Explain billing analysis in simple language. "
            "Be clear, transparent, and non-accusatory. Provide a concise but comprehensive explanation "
            "that helps patients understand their medical bill and insurance coverage."
        )

        user_prompt = (
            f"Please explain this medical bill analysis to a patient in a friendly and clear manner:\n\n{context}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        # Extract text from response
        if response.choices and len(response.choices) > 0:
            explanation = response.choices[0].message.content
            logger.info("Successfully generated LLM explanation")
            return explanation
        else:
            logger.warning("Empty response from LLM, using fallback")
            return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)

    except (APIError, APIConnectionError) as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            logger.warning("OpenAI API quota exceeded, using fallback explanation")
        else:
            logger.warning(f"LLM API error, using fallback: {e}")
        return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)
    except Exception as e:
        logger.error(f"Unexpected error generating LLM explanation: {e}")
        return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)


def _format_items(items: list) -> str:
    """Format a list of items for display."""
    if not items:
        return "None"
    
    formatted = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name", item.get("item_name", "Unknown"))
            cost = item.get("cost", 0)
            formatted.append(f"  • {name}: ${cost:,.2f}")
        else:
            formatted.append(f"  • {item}")
    
    return "\n".join(formatted) if formatted else "None"


def _generate_fallback_explanation(
    analysis: Dict[str, Any], 
    cost_deviation_pct: float, 
    has_anomalies: bool
) -> str:
    """
    Generate a fallback explanation when LLM is unavailable.

    Args:
        analysis: The billing analysis results
        cost_deviation_pct: Cost deviation percentage
        has_anomalies: Whether anomalies were detected

    Returns:
        A formatted string explanation of the billing analysis
    """
    total_bill = analysis.get("total_bill_amount", 0)
    claimable = analysis.get("total_claimable_amount", 0)
    copay = analysis.get("co_payment_deducted", 0)
    excluded_count = len(analysis.get("excluded_items", []))
    non_payable_count = len(analysis.get("non_payable_items", []))
    warning_count = len(analysis.get("cost_efficiency_warnings", []))

    explanation = f"""
**Medical Bill Analysis Summary**

Your total bill was **${total_bill:,.2f}**. After reviewing your insurance coverage:

• **Insurance will cover:** ${claimable:,.2f}
• **Your co-payment:** ${copay:,.2f}
• **Difference from claimable:** {cost_deviation_pct:.1f}%

**Coverage Details:**
• Excluded items: {excluded_count} treatment(s) not covered by your policy
• Non-payable items: {non_payable_count} item(s) your insurance doesn't pay for
• Potential cost concerns: {warning_count} item(s) with unusual pricing

{"⚠️ **Alert:** Your bill contains items with pricing that appears higher than market rates. Please review the itemized breakdown." if has_anomalies else "✓ Your bill appears to be within normal cost ranges."}

Please contact your insurance provider or hospital for clarification on any excluded or non-payable items.
    """.strip()

    return explanation
