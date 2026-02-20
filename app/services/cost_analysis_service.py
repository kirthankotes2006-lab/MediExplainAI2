"""
Cost analysis service for comparing billed costs against market rates.

This service analyzes billing costs against the local cost database to identify
potential overpricing and cost efficiency issues.
"""
from __future__ import annotations

from typing import Optional

from app.core.cost_database import get_local_cost_info


def analyze_cost_efficiency(item_name: str, billed_cost: float) -> Optional[dict]:
    """
    Analyze cost efficiency by comparing billed cost against market rates.

    Args:
        item_name: Name of the item or procedure being analyzed.
        billed_cost: The cost that was billed for this item.

    Returns:
        A dictionary containing cost analysis results with keys:
        - item_name: The item name
        - billed_cost: The billed cost
        - average_cost: Market average cost
        - min_cost: Market minimum cost
        - max_cost: Market maximum cost
        - status: One of "highly_overpriced", "slightly_overpriced", or "within_market_range"
        
        Returns None if the item is not found in the cost database.

    Raises:
        ValueError: If billed_cost is <= 0 or item_name is invalid.
    """
    try:
        # Validate billed_cost
        if not isinstance(billed_cost, (int, float)):
            raise ValueError("billed_cost must be a number")
        
        if billed_cost <= 0:
            raise ValueError("billed_cost must be greater than 0")
        
        # Get local cost info (this will raise ValueError if item_name is invalid)
        cost_info = get_local_cost_info(item_name)
        
        # If item not found in database, return None
        if cost_info is None:
            return None
        
        # Extract cost values
        average_cost = float(cost_info["average_cost"])
        min_cost = float(cost_info["min_cost"])
        max_cost = float(cost_info["max_cost"])
        
        # Determine status based on comparison
        if billed_cost > max_cost:
            status = "highly_overpriced"
        elif billed_cost > average_cost:
            status = "slightly_overpriced"
        else:
            status = "within_market_range"
        
        # Return structured analysis result
        return {
            "item_name": item_name,
            "billed_cost": float(billed_cost),
            "average_cost": average_cost,
            "min_cost": min_cost,
            "max_cost": max_cost,
            "status": status,
        }
    
    except ValueError:
        # Re-raise ValueError as-is (for invalid inputs)
        raise
    except Exception as e:
        # Wrap any unexpected errors
        raise RuntimeError(f"Error analyzing cost efficiency: {str(e)}") from e


__all__ = [
    "analyze_cost_efficiency",
]
