"""
Q&A Service for answering questions about medical bill analysis.

Uses OpenAI API to provide contextual answers based on the billing analysis.
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


def generate_qa_response(question: str, context: Dict[str, Any]) -> str:
    """
    Generate an answer to a question about the billing analysis.

    Provides contextual answers based on the analysis results. Answers are
    limited to information contained in the analysis to avoid hallucination.

    Args:
        question: The user's question about their bill or analysis
        context: The billing analysis dictionary containing:
            - total_bill_amount: float
            - total_claimable_amount: float
            - co_payment_deducted: float
            - excluded_items: List[dict]
            - non_payable_items: List[dict]
            - coverage_breakdown: List[dict]
            - cost_efficiency_warnings: List[dict]

    Returns:
        String containing the answer to the question based on the analysis.
        Returns an error message if the LLM service is unavailable.
    """
    client = _get_openai_client()

    if not client:
        return "Unable to answer questions at this time. OpenAI API key not configured."

    try:
        # Format context for the LLM
        context_str = _format_context_for_qa(context)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful healthcare insurance assistant. "
                        "Answer questions based ONLY on the medical bill analysis provided. "
                        "If the question cannot be answered from the provided analysis, "
                        "politely explain that the information is not available in the analysis. "
                        "Be concise and clear in your responses."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Medical Bill Analysis:\n{context_str}\n\nQuestion: {question}",
                },
            ],
            temperature=0.3,
            max_tokens=500,
        )

        answer = response.choices[0].message.content
        logger.info("Successfully generated Q&A response")
        return answer

    except (APIError, APIConnectionError) as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            logger.warning("OpenAI API quota exceeded")
            return "I'm currently unable to answer questions due to API quota limits. Please try again later or contact support."
        else:
            logger.warning(f"Q&A API error: {e}")
            return f"Error answering question: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in Q&A service: {e}")
        return "An unexpected error occurred while processing your question. Please try again."


def _format_context_for_qa(context: Dict[str, Any]) -> str:
    """
    Format the analysis context into a readable string for the LLM.

    Args:
        context: The billing analysis dictionary

    Returns:
        Formatted string representation of the analysis
    """
    total_bill = context.get("total_bill_amount", 0)
    claimable = context.get("total_claimable_amount", 0)
    copay = context.get("co_payment_deducted", 0)
    excluded_items = context.get("excluded_items", [])
    non_payable_items = context.get("non_payable_items", [])
    coverage_breakdown = context.get("coverage_breakdown", [])
    warnings = context.get("cost_efficiency_warnings", [])

    context_str = f"""
Total Bill Amount: ${total_bill:,.2f}
Claimable Amount: ${claimable:,.2f}
Co-Payment: ${copay:,.2f}

Excluded Items ({len(excluded_items)}):
{_format_items_for_qa(excluded_items)}

Non-Payable Items ({len(non_payable_items)}):
{_format_items_for_qa(non_payable_items)}

Covered Items ({len(coverage_breakdown)}):
{_format_items_for_qa(coverage_breakdown)}

Cost Efficiency Warnings ({len(warnings)}):
{_format_items_for_qa(warnings)}
    """.strip()

    return context_str


def _format_items_for_qa(items: list) -> str:
    """Format items for Q&A context."""
    if not items:
        return "None"

    formatted = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name", item.get("item_name", "Unknown"))
            cost = item.get("cost", 0)
            reason = item.get("reason", "")
            status = item.get("status", "")

            if reason:
                formatted.append(f"• {name}: ${cost:,.2f} ({reason})")
            elif status:
                formatted.append(f"• {name}: ${cost:,.2f} ({status})")
            else:
                formatted.append(f"• {name}: ${cost:,.2f}")
        else:
            formatted.append(f"• {item}")

    return "\n".join(formatted) if formatted else "None"
