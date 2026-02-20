"""
Service for parsing simple, structured medical bill PDFs into `MedicalBill` objects.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from app.schemas.billing_schema import MedicalBill


def _parse_medical_bill_payload(payload: dict) -> MedicalBill:
    """
    Helper to parse a MedicalBill from raw dict, compatible with Pydantic v1/v2.
    """
    try:
        # Pydantic v2
        return MedicalBill.model_validate(payload)  # type: ignore[attr-defined]
    except AttributeError:
        # Pydantic v1 fallback
        return MedicalBill.parse_obj(payload)  # type: ignore[call-arg]


def parse_medical_bill_pdf(file_path: str) -> MedicalBill:
    """
    Parse a structured medical bill PDF into a `MedicalBill` object.

    Supports multiple PDF formats:
    
    Format 1 (Line-based):
        Patient: Aditya
        Hospital: City Hospital
        Treatment: MRI Scan - 20000
        Other: Gloves - 500

    Format 2 (Table-based with headers):
        Patient: Aditya
        Hospital: City Hospital
        Item | Cost (₹)
        MRI Scan | 28000
        Gloves | 1200

    Args:
        file_path: Path to the PDF file.

    Returns:
        A populated `MedicalBill` instance.

    Raises:
        ValueError: If required fields (patient, hospital, at least one treatment)
                    are missing or parsing fails in a controlled way.
        RuntimeError: For unexpected parsing errors (I/O, malformed PDF, etc.).
    """
    try:
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValueError("file_path must be a non-empty string")

        try:
            reader = PdfReader(file_path)
        except PdfReadError as exc:
            raise ValueError("Invalid or corrupted PDF file") from exc
        text_chunks: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)

        full_text = "\n".join(text_chunks)
        if not full_text.strip():
            raise ValueError("PDF appears to be empty or text could not be extracted")

        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        patient_name: Optional[str] = None
        hospital_name: Optional[str] = None
        co_payment_percentage: Optional[float] = None
        treatments: list[dict] = []
        other_items: list[dict] = []
        
        # Known non-payable and treatment-like keywords for categorization
        non_payable_keywords = {'glove', 'mask', 'sanit', 'admin', 'registration', 'fee', 'charge'}
        treatment_keywords = {'mri', 'ct', 'scan', 'blood', 'test', 'surgery', 'consultation', 'icu', 'replacement', 'xray', 'ultrasound'}

        for i, line in enumerate(lines):
            lower = line.lower()

            # Patient line
            if lower.startswith("patient:"):
                patient_name = line.split(":", 1)[1].strip() or None
                continue

            # Hospital line
            if lower.startswith("hospital:"):
                hospital_name = line.split(":", 1)[1].strip() or None
                continue
            
            # Co-payment percentage line
            if lower.startswith("co-payment") or lower.startswith("copayment"):
                try:
                    # Extract number from lines like "Co-Payment: 15%" or "Co-Payment:\n15"
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if not content and i + 1 < len(lines):
                        # Try next line if current is empty
                        next_line = lines[i + 1].lower()
                        content = next_line.strip()
                    
                    # Parse percentage value
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*%?', content)
                    if match:
                        co_payment_percentage = float(match.group(1))
                except Exception as parse_err:
                    # Log but don't fail on co-payment parsing
                    pass
                continue

            # Treatment line: "Treatment: MRI Scan - 20000" (Format 1)
            if lower.startswith("treatment:"):
                content = line.split(":", 1)[1].strip()
                if " - " in content:
                    name_part, cost_part = content.split(" - ", 1)
                else:
                    name_part, cost_part = content, ""

                name = name_part.strip()
                try:
                    cost = Decimal(cost_part.replace(",", "").strip())
                except Exception:
                    raise ValueError(f"Invalid treatment cost format in line: {line!r}")

                if not name or cost <= 0:
                    raise ValueError(f"Invalid treatment entry in line: {line!r}")

                treatments.append({"name": name, "cost": cost})
                continue

            # Other item line: "Other: Gloves - 500" (Format 1)
            if lower.startswith("other:"):
                content = line.split(":", 1)[1].strip()
                if " - " in content:
                    name_part, cost_part = content.split(" - ", 1)
                else:
                    name_part, cost_part = content, ""

                name = name_part.strip()
                try:
                    cost = Decimal(cost_part.replace(",", "").strip())
                except Exception:
                    raise ValueError(f"Invalid other item cost format in line: {line!r}")

                if not name or cost <= 0:
                    raise ValueError(f"Invalid other item entry in line: {line!r}")

                other_items.append({"name": name, "cost": cost})
                continue
            
            # Format 2: Table-based parsing (Item | Cost or Item    Cost)
            # Look for pipe separator or significant whitespace
            if "|" in line or (len(line) > 20 and line.count(" ") > 2):
                # Skip header lines
                if any(h in lower for h in ['item', 'cost', 'description', 'amount', 'price']):
                    continue
                
                # Try pipe separator first
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        cost_str = parts[1].strip()
                    else:
                        continue
                else:
                    # Try to parse as: "ItemName    1200" (item at start, cost at end)
                    # Split by significant whitespace (3+ spaces)
                    import re
                    match = re.split(r'\s{3,}', line)
                    if len(match) >= 2:
                        name = match[0].strip()
                        cost_str = match[-1].strip()
                    else:
                        continue
                
                # Try to extract numeric cost
                import re
                cost_match = re.search(r'(\d+(?:,\d+)*(?:\.\d{2})?)', cost_str)
                if not cost_match:
                    continue
                
                try:
                    cost = Decimal(cost_match.group(1).replace(",", ""))
                    if cost <= 0:
                        continue
                    
                    # Categorize as treatment or other item
                    name_lower = name.lower()
                    
                    # Heuristic: if name contains non-payable keywords, it's an other item
                    is_non_payable = any(kw in name_lower for kw in non_payable_keywords)
                    
                    # If it contains treatment keywords or is a standard procedure, it's a treatment
                    is_treatment = any(kw in name_lower for kw in treatment_keywords)
                    
                    if is_non_payable or (not is_treatment and any(kw in name_lower for kw in ['administrative', 'registration', 'fee'])):
                        other_items.append({"name": name, "cost": cost})
                    else:
                        # Default to treatment if it looks like a medical service
                        treatments.append({"name": name, "cost": cost})
                except Exception:
                    continue

        # Validate required fields
        if not patient_name:
            raise ValueError("Patient name not found in PDF (expected line starting with 'Patient:')")
        if not hospital_name:
            raise ValueError("Hospital name not found in PDF (expected line starting with 'Hospital:')")
        if not treatments:
            raise ValueError("No treatments found in PDF (expected at least one 'Treatment:' line or table entry)")

        payload = {
            "bill_id": None,
            "patient_id": patient_name,
            "treatments": treatments,
            "other_items": other_items,
        }

        return _parse_medical_bill_payload(payload)

    except ValueError:
        # Bubble up validation errors as-is
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to parse medical bill PDF: {exc}") from exc


__all__ = ["parse_medical_bill_pdf"]
