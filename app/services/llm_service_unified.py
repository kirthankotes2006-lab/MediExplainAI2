"""
Unified LLM Service supporting both OpenAI and Google Gemini APIs.

Provides automatic fallback between providers and graceful degradation.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional, Literal

import requests
from openai import OpenAI, APIError, APIConnectionError


logger = logging.getLogger(__name__)


def _get_openai_client() -> Optional[OpenAI]:
    """Initialize and return an OpenAI client if API key is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None


def _get_active_llm_provider() -> Literal["openai", "gemini", "none"]:
    """Determine which LLM provider is active based on available API keys."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return "none"


def generate_llm_explanation_unified(analysis: Dict[str, Any]) -> str:
    """
    Generate a natural language explanation of medical bill analysis using available LLM.

    Tries OpenAI first, then Gemini, then falls back to template.

    Args:
        analysis: Dictionary containing analysis results

    Returns:
        String containing a natural language explanation of the billing analysis.
    """
    provider = _get_active_llm_provider()
    
    if provider == "openai":
        return _generate_with_openai(analysis)
    elif provider == "gemini":
        return _generate_with_gemini(analysis)
    else:
        cost_deviation_pct = _calculate_cost_deviation(analysis)
        has_anomalies = len(analysis.get("cost_efficiency_warnings", [])) > 0
        return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)


def _generate_with_openai(analysis: Dict[str, Any]) -> str:
    """Generate explanation using OpenAI API."""
    client = _get_openai_client()
    if not client:
        logger.warning("OpenAI client not available")
        return _fallback_from_analysis(analysis)

    cost_deviation_pct = _calculate_cost_deviation(analysis)
    has_anomalies = len(analysis.get("cost_efficiency_warnings", [])) > 0
    context = _format_context_for_llm(analysis)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a healthcare insurance assistant. Explain billing analysis in simple language. "
                        "Be clear, transparent, and non-accusatory. Provide a concise but comprehensive explanation "
                        "that helps patients understand their medical bill and insurance coverage."
                    ),
                },
                {"role": "user", "content": f"Please explain this medical bill analysis to a patient:\n\n{context}"},
            ],
        )

        if response.choices and len(response.choices) > 0:
            explanation = response.choices[0].message.content
            logger.info("Successfully generated explanation with OpenAI")
            # Replace $ with ₹ for Indian currency
            explanation = explanation.replace('$', '₹')
            return explanation

    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            logger.warning("OpenAI API quota exceeded, trying Gemini")
            # Try Gemini as fallback
            gemini_result = _generate_with_gemini(analysis)
            if gemini_result != _fallback_from_analysis(analysis):
                return gemini_result
        else:
            logger.warning(f"OpenAI API error: {e}")

    return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)


def _generate_with_gemini(analysis: Dict[str, Any]) -> str:
    """Generate explanation using Google Gemini API via REST."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("Gemini API key not configured")
        return _fallback_from_analysis(analysis)

    cost_deviation_pct = _calculate_cost_deviation(analysis)
    has_anomalies = len(analysis.get("cost_efficiency_warnings", [])) > 0
    context = _format_context_for_llm(analysis)

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"""You are a healthcare insurance assistant. Explain this medical bill analysis in simple language. 
Be clear, transparent, and non-accusatory.

Analysis:
{context}

Please provide a concise but comprehensive explanation that helps patients understand their bill and insurance coverage."""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.7,
            }
        }

        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0].get("content", {})
                if "parts" in content and len(content["parts"]) > 0:
                    explanation = content["parts"][0].get("text", "")
                    if explanation:
                        logger.info("Successfully generated explanation with Gemini")
                        # Replace $ with ₹ for Indian currency
                        explanation = explanation.replace('$', '₹')
                        return explanation
        else:
            logger.warning(f"Gemini API error: {response.status_code} - {response.text}")

    except requests.exceptions.Timeout:
        logger.warning("Gemini API request timeout")
    except Exception as e:
        logger.warning(f"Gemini API error: {e}")

    return _generate_fallback_explanation(analysis, cost_deviation_pct, has_anomalies)


def _calculate_cost_deviation(analysis: Dict[str, Any]) -> float:
    """Calculate cost deviation percentage."""
    if analysis.get("total_bill_amount", 0) > 0:
        claimable = analysis.get("total_claimable_amount", 0)
        total = analysis.get("total_bill_amount", 0)
        return ((total - claimable) / total) * 100 if total > 0 else 0
    return 0.0


def _format_context_for_llm(analysis: Dict[str, Any]) -> str:
    """Format analysis into readable context for LLM."""
    total_bill = analysis.get("total_bill_amount", 0)
    claimable = analysis.get("total_claimable_amount", 0)
    copay = analysis.get("co_payment_deducted", 0)
    excluded_items = analysis.get("excluded_items", [])
    non_payable_items = analysis.get("non_payable_items", [])
    warnings = analysis.get("cost_efficiency_warnings", [])

    context = f"""
Total Bill: ₹{total_bill:,.2f}
Claimable Amount: ₹{claimable:,.2f}
Co-Payment: ₹{copay:,.2f}

Excluded Items ({len(excluded_items)}):
{_format_items(excluded_items)}

Non-Payable Items ({len(non_payable_items)}):
{_format_items(non_payable_items)}

Cost Efficiency Warnings ({len(warnings)}):
{_format_items(warnings)}
    """.strip()

    return context


def _format_items(items: list) -> str:
    """Format items list for display."""
    if not items:
        return "None"
    
    formatted = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name", item.get("item_name", "Unknown"))
            cost = item.get("cost", 0)
            formatted.append(f"  • {name}: ₹{cost:,.2f}")
        else:
            formatted.append(f"  • {item}")
    
    return "\n".join(formatted) if formatted else "None"


def _fallback_from_analysis(analysis: Dict[str, Any]) -> str:
    """Quick fallback when no LLM is available."""
    return _generate_fallback_explanation(
        analysis,
        _calculate_cost_deviation(analysis),
        len(analysis.get("cost_efficiency_warnings", [])) > 0
    )


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

Your total bill was **₹{total_bill:,.2f}**. After reviewing your insurance coverage:

• **Insurance will cover:** ₹{claimable:,.2f}
• **Your co-payment:** ₹{copay:,.2f}
• **Difference from claimable:** {cost_deviation_pct:.1f}%

**Coverage Details:**
• Excluded items: {excluded_count} treatment(s) not covered by your policy
• Non-payable items: {non_payable_count} item(s) your insurance doesn't pay for
• Potential cost concerns: {warning_count} item(s) with unusual pricing

{"⚠️ **Alert:** Your bill contains items with pricing that appears higher than market rates. Please review the itemized breakdown." if has_anomalies else "✓ Your bill appears to be within normal cost ranges."}

Please contact your insurance provider or hospital for clarification on any excluded or non-payable items.
    """.strip()

    return explanation
