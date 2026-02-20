"""
Parser for reading an insurance policy PDF into an `InsurancePolicyModel`.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from app.core.policy_model import InsurancePolicyModel


def _extract_text(file_path: str) -> List[str]:
    """
    Extract non-empty, stripped lines of text from a PDF.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("file_path must be a non-empty string")

    try:
        reader = PdfReader(file_path)
    except PdfReadError as exc:
        raise ValueError("Invalid or corrupted PDF file") from exc
    lines: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line:
                lines.append(line)
    if not lines:
        raise ValueError("Policy PDF appears to be empty or text could not be extracted")
    return lines


def parse_insurance_policy_pdf(file_path: str) -> InsurancePolicyModel:
    """
    Parse an insurance policy PDF into an `InsurancePolicyModel`.

    Expected (flexible) structure, line-oriented, for example:

        Coverage Limits:
        MRI Scan - 10000
        Blood Test - 1500

        Exclusions:
        Cosmetic Surgery
        Experimental Treatment

        Non Payable Items:
        Gloves
        Sanitizer

        CoPayment: 10%

    Args:
        file_path: Path to the policy PDF.

    Returns:
        An `InsurancePolicyModel` instance populated from the PDF.

    Raises:
        ValueError: If the PDF content does not match the expected format.
        RuntimeError: For unexpected parsing errors (I/O, malformed PDF, etc.).
    """
    try:
        lines = _extract_text(file_path)

        coverage_limits: Dict[str, float] = {}
        exclusions: List[str] = []
        non_payable_items: List[str] = []
        co_payment_percentage: Optional[float] = None

        current_section: Optional[str] = None

        for line in lines:
            lower = line.lower()

            # Section headers
            if "coverage" in lower and ("limit" in lower or ":" in lower):
                current_section = "coverage_limits"
                continue
            if "exclusions" in lower:
                current_section = "exclusions"
                continue
            if "non payable items" in lower or "non-payable items" in lower or "non payable" in lower:
                current_section = "non_payable_items"
                continue
            if "copayment" in lower or "co-payment" in lower or "co payment" in lower:
                # Handle CoPayment lines like "CoPayment: 10%" or "CoPayment - 10"
                parts = line.split(":", 1)
                if len(parts) == 1:
                    parts = line.split("-", 1)
                if len(parts) == 2:
                    value_part = parts[1].strip()
                else:
                    raise ValueError(f"Invalid co-payment line format: {line!r}")

                value_part = value_part.replace("%", "").strip()
                try:
                    co_payment_percentage = float(value_part)
                except Exception:
                    raise ValueError(f"Invalid co-payment percentage value in line: {line!r}")
                continue

            # Content lines by section
            if current_section == "coverage_limits":
                # Skip empty lines or headers
                if not line or line.lower() in ["coverage limits", "coverage"]:
                    continue
                # Expect formats like "MRI Scan - 10000" or "MRI Scan: 10000"
                if "-" in line:
                    name_part, value_part = line.split("-", 1)
                elif ":" in line:
                    name_part, value_part = line.split(":", 1)
                else:
                    continue  # Skip lines that don't match format

                name = name_part.strip()
                value_str = value_part.replace(",", "").strip()
                try:
                    coverage_limits[name] = float(value_str)
                except Exception:
                    pass  # Skip lines that can't be parsed as numbers
            elif current_section == "exclusions":
                if line and line.lower() not in ["exclusions"]:
                    exclusions.append(line.strip())
            elif current_section == "non_payable_items":
                if line and line.lower() not in ["non payable items", "non-payable items", "non payable"]:
                    non_payable_items.append(line.strip())

        # Validate extracted data
        if not coverage_limits:
            raise ValueError("No coverage limits found in policy PDF")
        if co_payment_percentage is None:
            raise ValueError("Co-payment percentage not found in policy PDF")
        if co_payment_percentage < 0 or co_payment_percentage > 100:
            raise ValueError("Co-payment percentage must be between 0 and 100")

        return InsurancePolicyModel(
            coverage_limits=coverage_limits,
            exclusions=exclusions,
            non_payable_items=non_payable_items,
            co_payment_percentage=co_payment_percentage,
        )

    except ValueError:
        # Validation / format errors should propagate as ValueError
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to parse insurance policy PDF: {exc}") from exc


__all__ = ["parse_insurance_policy_pdf"]
