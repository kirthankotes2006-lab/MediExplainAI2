"""
Medicine and treatment price database with alternatives.
Provides market comparison data for commonly used medicines and procedures.
"""
from typing import Dict, List, Optional
from decimal import Decimal


# Sample medicine database with generic and brand alternatives
MEDICINE_DATABASE: Dict[str, List[Dict]] = {
    # Antibiotics
    "Amoxicillin": [
        {"brand": "Amoxicillin (Generic)", "price": 45, "dosage": "500mg", "qty": 10},
        {"brand": "Augmentin", "price": 120, "dosage": "500mg", "qty": 10},
        {"brand": "Moxikind", "price": 95, "dosage": "500mg", "qty": 10},
    ],
    "Azithromycin": [
        {"brand": "Azithromycin (Generic)", "price": 60, "dosage": "500mg", "qty": 3},
        {"brand": "Zithromax", "price": 180, "dosage": "500mg", "qty": 3},
        {"brand": "Aziblast", "price": 90, "dosage": "500mg", "qty": 3},
    ],
    "Ciprofloxacin": [
        {"brand": "Ciprofloxacin (Generic)", "price": 50, "dosage": "500mg", "qty": 10},
        {"brand": "Cipro", "price": 200, "dosage": "500mg", "qty": 10},
        {"brand": "Ciprolet", "price": 85, "dosage": "500mg", "qty": 10},
    ],
    
    # Pain relievers
    "Paracetamol": [
        {"brand": "Paracetamol (Generic)", "price": 20, "dosage": "500mg", "qty": 15},
        {"brand": "Crocin", "price": 65, "dosage": "500mg", "qty": 15},
        {"brand": "Dolo", "price": 55, "dosage": "500mg", "qty": 15},
    ],
    "Ibuprofen": [
        {"brand": "Ibuprofen (Generic)", "price": 30, "dosage": "400mg", "qty": 10},
        {"brand": "Brufen", "price": 85, "dosage": "400mg", "qty": 10},
        {"brand": "Combiflam", "price": 75, "dosage": "400mg", "qty": 10},
    ],
    "Aspirin": [
        {"brand": "Aspirin (Generic)", "price": 25, "dosage": "500mg", "qty": 15},
        {"brand": "Asthalin", "price": 50, "dosage": "500mg", "qty": 15},
        {"brand": "Disprin", "price": 60, "dosage": "500mg", "qty": 15},
    ],
    
    # Anti-inflammatory
    "Diclofenac": [
        {"brand": "Diclofenac (Generic)", "price": 35, "dosage": "50mg", "qty": 10},
        {"brand": "Voveran", "price": 90, "dosage": "50mg", "qty": 10},
        {"brand": "Diclogesic", "price": 75, "dosage": "50mg", "qty": 10},
    ],
    
    # Cough & Cold
    "Cough Syrup": [
        {"brand": "Cough Syrup (Generic)", "price": 40, "dosage": "100ml", "qty": 1},
        {"brand": "Ascoril", "price": 85, "dosage": "100ml", "qty": 1},
        {"brand": "Strepsils", "price": 70, "dosage": "100ml", "qty": 1},
    ],
    "Cough Drop": [
        {"brand": "Cough Drop (Generic)", "price": 20, "dosage": "Strip", "qty": 10},
        {"brand": "Halls", "price": 50, "dosage": "Strip", "qty": 10},
        {"brand": "Strepsils", "price": 45, "dosage": "Strip", "qty": 10},
    ],
    
    # Vitamins & Supplements
    "Vitamin C": [
        {"brand": "Vitamin C (Generic)", "price": 25, "dosage": "500mg", "qty": 30},
        {"brand": "Celin", "price": 70, "dosage": "500mg", "qty": 30},
        {"brand": "Limcee", "price": 65, "dosage": "500mg", "qty": 30},
    ],
    "Vitamin D3": [
        {"brand": "Vitamin D3 (Generic)", "price": 40, "dosage": "1000IU", "qty": 30},
        {"brand": "D-Rise", "price": 110, "dosage": "1000IU", "qty": 30},
        {"brand": "Osteocare", "price": 100, "dosage": "1000IU", "qty": 30},
    ],
    "Multivitamin": [
        {"brand": "Multivitamin (Generic)", "price": 50, "dosage": "Tablet", "qty": 30},
        {"brand": "Supradyn", "price": 150, "dosage": "Tablet", "qty": 30},
        {"brand": "Stresstabs", "price": 130, "dosage": "Tablet", "qty": 30},
    ],
    
    # Antacid
    "Antacid": [
        {"brand": "Antacid (Generic)", "price": 30, "dosage": "100ml", "qty": 1},
        {"brand": "Gelusil", "price": 80, "dosage": "100ml", "qty": 1},
        {"brand": "Digene", "price": 75, "dosage": "100ml", "qty": 1},
    ],
    
    # Allergy/Cold
    "Cetirizine": [
        {"brand": "Cetirizine (Generic)", "price": 20, "dosage": "10mg", "qty": 10},
        {"brand": "Alerid", "price": 60, "dosage": "10mg", "qty": 10},
        {"brand": "Xyzal", "price": 85, "dosage": "10mg", "qty": 10},
    ],
}

# Procedure and service price comparisons
PROCEDURE_COMPARISON: Dict[str, List[Dict]] = {
    "MRI Brain": [
        {"provider": "Apollo Hospitals", "price": 8500, "time": "30 mins"},
        {"provider": "City Hospital", "price": 7500, "time": "30 mins"},
        {"provider": "Diagnostic Lab (XYZ)", "price": 6000, "time": "30 mins"},
    ],
    "MRI Spine": [
        {"provider": "Apollo Hospitals", "price": 9000, "time": "30 mins"},
        {"provider": "City Hospital", "price": 8000, "time": "30 mins"},
        {"provider": "Diagnostic Lab (XYZ)", "price": 7000, "time": "30 mins"},
    ],
    "CT Scan": [
        {"provider": "Apollo Hospitals", "price": 5000, "time": "15 mins"},
        {"provider": "City Hospital", "price": 4000, "time": "15 mins"},
        {"provider": "Diagnostic Lab (XYZ)", "price": 3500, "time": "15 mins"},
    ],
    "Blood Test": [
        {"provider": "Pathlab Plus", "price": 500, "time": "24 hrs"},
        {"provider": "City Hospital", "price": 800, "time": "24 hrs"},
        {"provider": "Apollo Lab", "price": 1000, "time": "24 hrs"},
    ],
    "X-Ray": [
        {"provider": "City Hospital", "price": 300, "time": "10 mins"},
        {"provider": "Diagnostic Lab (XYZ)", "price": 250, "time": "10 mins"},
        {"provider": "Apollo Hospitals", "price": 400, "time": "10 mins"},
    ],
    "Ultrasound": [
        {"provider": "City Hospital", "price": 500, "time": "20 mins"},
        {"provider": "Diagnostic Lab (XYZ)", "price": 400, "time": "20 mins"},
        {"provider": "Apollo Hospitals", "price": 700, "time": "20 mins"},
    ],
}


def get_medicine_alternatives(medicine_name: str) -> Optional[List[Dict]]:
    """
    Get alternative medicines with prices for a given medicine.
    
    Args:
        medicine_name: Name of the medicine to find alternatives for
        
    Returns:
        List of alternative medicines with prices, or None if not found
    """
    # Try exact match first
    if medicine_name in MEDICINE_DATABASE:
        return MEDICINE_DATABASE[medicine_name]
    
    # Try case-insensitive partial match
    medicine_name_lower = medicine_name.lower()
    for db_name, alternatives in MEDICINE_DATABASE.items():
        if medicine_name_lower in db_name.lower() or db_name.lower() in medicine_name_lower:
            return alternatives
    
    return None


def get_procedure_alternatives(procedure_name: str) -> Optional[List[Dict]]:
    """
    Get alternative providers with prices for a given procedure.
    
    Args:
        procedure_name: Name of the procedure to find alternatives for
        
    Returns:
        List of providers with prices, or None if not found
    """
    # Try exact match first
    if procedure_name in PROCEDURE_COMPARISON:
        return PROCEDURE_COMPARISON[procedure_name]
    
    # Try case-insensitive partial match
    procedure_name_lower = procedure_name.lower()
    for db_name, providers in PROCEDURE_COMPARISON.items():
        if procedure_name_lower in db_name.lower() or db_name.lower() in procedure_name_lower:
            return providers
    
    return None


def calculate_savings(item_name: str, billed_price: float, item_type: str = "medicine") -> Dict:
    """
    Calculate potential savings by comparing with alternatives.
    
    Args:
        item_name: Name of the medicine or procedure
        billed_price: Price billed by the hospital
        item_type: "medicine" or "procedure"
        
    Returns:
        Dictionary with savings information
    """
    if item_type == "medicine":
        alternatives = get_medicine_alternatives(item_name)
    else:
        alternatives = get_procedure_alternatives(item_name)
    
    if not alternatives:
        return {}
    
    # Find the cheapest alternative
    cheapest = min(alternatives, key=lambda x: x.get("price", float("inf")))
    cheapest_price = cheapest.get("price", billed_price)
    
    # Find average price
    avg_price = sum(alt.get("price", 0) for alt in alternatives) / len(alternatives)
    
    # Calculate savings
    savings_amount = billed_price - cheapest_price
    savings_percent = (savings_amount / billed_price * 100) if billed_price > 0 else 0
    
    return {
        "item_name": item_name,
        "billed_price": billed_price,
        "cheapest_price": cheapest_price,
        "cheapest_option": cheapest.get("brand", cheapest.get("provider", "Unknown")),
        "average_price": round(avg_price, 2),
        "savings_amount": round(savings_amount, 2),
        "savings_percent": round(savings_percent, 1),
        "all_alternatives": alternatives,
        "is_overpriced": savings_percent > 20,  # More than 20% overpriced
    }
