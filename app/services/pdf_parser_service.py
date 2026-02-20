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

    Expected PDF structure (line-based, order can vary):

        Patient: Aditya
        Hospital: City Hospital

        Treatment: MRI Scan - 20000
        Treatment: Blood Test - 900
        Other: Gloves - 500

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
        treatments: list[dict] = []
        other_items: list[dict] = []

        for line in lines:
            lower = line.lower()

            # Patient line
            if lower.startswith("patient:"):
                patient_name = line.split(":", 1)[1].strip() or None
                continue

            # Hospital line
            if lower.startswith("hospital:"):
                hospital_name = line.split(":", 1)[1].strip() or None
                continue

            # Treatment line: "Treatment: MRI Scan - 20000"
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

            # Other item line: "Other: Gloves - 500"
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

        # Validate required fields
        if not patient_name:
            raise ValueError("Patient name not found in PDF (expected line starting with 'Patient:')")
        if not hospital_name:
            raise ValueError("Hospital name not found in PDF (expected line starting with 'Hospital:')")
        if not treatments:
            raise ValueError("No treatments found in PDF (expected at least one 'Treatment:' line)")

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
