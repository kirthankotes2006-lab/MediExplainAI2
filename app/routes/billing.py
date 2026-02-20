"""
API routes for billing anomaly detection and bill / policy analysis endpoints.
"""
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.schemas.billing_schema import (
    BillingRecord,
    BillingRecordCreate,
    BillingRecordResponse,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    MedicalBill,
)
from app.services.billing_service import billing_service, analyze_medical_bill
from app.services.llm_service_unified import generate_llm_explanation_unified
from app.services.qa_service import generate_qa_response
from app.services.pdf_parser_service import parse_medical_bill_pdf
from app.core.policy_model import InsurancePolicyModel
from app.core.policy_parser import parse_insurance_policy_pdf
from app.core.policy_state import CURRENT_POLICY


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/records", response_model=BillingRecordResponse, status_code=status.HTTP_201_CREATED)
def create_billing_record(record_data: BillingRecordCreate) -> BillingRecordResponse:
    """
    Create a new billing record.
    
    The system will automatically detect anomalies for the new record.
    """
    try:
        record = billing_service.create_record(record_data)
        anomalies = billing_service.get_record_anomalies(record.record_id)
        
        return BillingRecordResponse(
            record=record,
            anomalies=anomalies
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create billing record: {str(e)}"
        )


@router.get("/records", response_model=List[BillingRecord])
def get_all_billing_records() -> List[BillingRecord]:
    """
    Retrieve all billing records.
    """
    return billing_service.get_all_records()


@router.get("/records/{record_id}", response_model=BillingRecordResponse)
def get_billing_record(record_id: str) -> BillingRecordResponse:
    """
    Retrieve a specific billing record by ID.
    """
    record = billing_service.get_record(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Billing record {record_id} not found"
        )
    
    anomalies = billing_service.get_record_anomalies(record_id)
    
    return BillingRecordResponse(
        record=record,
        anomalies=anomalies
    )


@router.post("/anomalies/detect", response_model=AnomalyDetectionResponse)
def detect_anomalies(request: AnomalyDetectionRequest) -> AnomalyDetectionResponse:
    """
    Detect anomalies in billing records.
    
    Can analyze specific records or all records.
    Supports filtering by confidence threshold and severity levels.
    """
    try:
        return billing_service.detect_anomalies(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect anomalies: {str(e)}"
        )


@router.post("/bills/analyze")
def analyze_medical_bill_route(bill: MedicalBill) -> dict:
    """
    Analyze a medical bill for insurance coverage and cost efficiency.

    Wraps the `analyze_medical_bill` service in proper error handling so that:
    - Validation errors return HTTP 400
    - Unexpected errors return HTTP 500
    """
    try:
        result = analyze_medical_bill(bill)
        return result
    except ValueError as exc:
        logger.warning("Validation error while analyzing medical bill: %s", exc, extra={"bill_id": getattr(bill, "bill_id", None)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while analyzing medical bill", extra={"bill_id": getattr(bill, "bill_id", None)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze medical bill",
        ) from exc


def _bill_to_dict(bill: MedicalBill) -> Dict[str, Any]:
    """
    Convert MedicalBill to a plain dict, compatible with Pydantic v1/v2.
    """
    if hasattr(bill, "model_dump"):
        return bill.model_dump()  # type: ignore[call-arg]
    return bill.dict()  # type: ignore[call-arg]


def _policy_to_dict(policy: InsurancePolicyModel) -> Dict[str, Any]:
    """
    Convert InsurancePolicyModel to a plain dict.
    """
    return {
        "coverage_limits": dict(policy.coverage_limits),
        "exclusions": list(policy.exclusions),
        "non_payable_items": list(policy.non_payable_items),
        "co_payment_percentage": float(policy.co_payment_percentage),
    }


@router.post("/upload")
async def upload_medical_bill(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a medical bill PDF, parse it into a MedicalBill, analyze coverage and costs,
    and return a structured JSON response with an explanation.

    - File type must be PDF
    - If parsing fails -> HTTP 400
    - If unexpected error -> HTTP 500
    """
    if not file.filename.lower().endswith(".pdf") or file.content_type not in {
        "application/pdf",
        "application/x-pdf",
        "application/acrobat",
        "applications/pdf",
        "text/pdf",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    tmp_path: str | None = None

    try:
        # Save uploaded file to a temporary location
        suffix = os.path.splitext(file.filename)[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        # Parse PDF into MedicalBill
        bill = parse_medical_bill_pdf(tmp_path)

        # Analyze the parsed bill
        analysis = analyze_medical_bill(bill)
        explanation = generate_llm_explanation_unified(analysis)

        return {
            "filename": file.filename,
            "bill": _bill_to_dict(bill),
            "analysis": analysis,
            "explanation": explanation,
        }

    except ValueError as exc:
        logger.warning(
            "Validation/parsing error while processing uploaded PDF: %s",
            exc,
            extra={"uploaded_filename": file.filename},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        # Re-raise HTTPExceptions unchanged
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error while processing uploaded medical bill PDF",
            extra={"uploaded_filename": file.filename},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process uploaded medical bill",
        ) from exc
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning(
                    "Failed to remove temporary file %s", tmp_path, exc_info=True
                )


@router.post("/upload-policy")
async def upload_insurance_policy(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload an insurance policy PDF, parse it into an InsurancePolicyModel,
    store it in the global CURRENT_POLICY, and return a structured JSON response.

    - File type must be PDF
    - If parsing fails -> HTTP 400
    - If unexpected error -> HTTP 500
    """
    if not file.filename.lower().endswith(".pdf") or file.content_type not in {
        "application/pdf",
        "application/x-pdf",
        "application/acrobat",
        "applications/pdf",
        "text/pdf",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    tmp_path: Optional[str] = None

    try:
        # Save uploaded file to a temporary location
        suffix = os.path.splitext(file.filename)[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        # Parse PDF into InsurancePolicyModel
        policy = parse_insurance_policy_pdf(tmp_path)

        # Store in shared CURRENT_POLICY state
        from app.core import policy_state  # local import to avoid cycles

        policy_state.CURRENT_POLICY = policy

        return {
            "filename": file.filename,
            "policy": _policy_to_dict(policy),
            "message": "Policy uploaded and parsed successfully",
        }

    except ValueError as exc:
        logger.warning(
            "Validation/parsing error while processing uploaded policy PDF: %s",
            exc,
            extra={"uploaded_filename": file.filename},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        # Re-raise HTTPExceptions unchanged
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected error while processing uploaded insurance policy PDF",
            extra={"uploaded_filename": file.filename},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process uploaded insurance policy",
        ) from exc
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning(
                    "Failed to remove temporary file %s", tmp_path, exc_info=True
                )


@router.post("/download-report")
async def download_report(data: Dict[str, Any]):
    """
    Generate and download a PDF report of the bill analysis.
    Expects analysis data in the request body.
    """
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=(8.5*inch, 11*inch))
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph("MediExplain AI", title_style))
        elements.append(Paragraph("Medical Billing Analysis Report", styles['Heading2']))
        elements.append(Spacer(1, 0.3*inch))

        # Extract data from request
        analysis = data.get('analysis', {})
        explanation = data.get('explanation', 'No explanation available')
        # Sanitize explanation to remove markdown asterisks and ensure proper line breaks
        if isinstance(explanation, str):
            explanation = explanation.replace('**', '').replace('*', '')
            explanation = explanation.replace('\r\n', '\n').replace('\r', '\n')
            explanation = explanation.replace('\n', '<br/>')

        # Report content
        elements.append(Paragraph("Bill Analysis Summary", styles['Heading3']))
        elements.append(Spacer(1, 0.15*inch))
        elements.append(Paragraph(explanation, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))

        # Key metrics
        elements.append(Paragraph("Financial Summary", styles['Heading3']))
        elements.append(Spacer(1, 0.1*inch))
        
        total_bill = analysis.get('total_bill_amount', 0)
        final_claimable = analysis.get('final_claimable_amount', 0)
        co_payment = analysis.get('co_payment_deducted', 0)
        
        summary_text = f"""
        <b>Total Bill Amount:</b> ₹{total_bill:,.2f}<br/>
        <b>Final Claimable Amount:</b> ₹{final_claimable:,.2f}<br/>
        <b>Co-payment Deducted:</b> ₹{co_payment:,.2f}<br/>
        """
        elements.append(Paragraph(summary_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))

        # Coverage breakdown
        coverage_breakdown = analysis.get('coverage_breakdown', [])
        if coverage_breakdown:
            elements.append(Paragraph("Treatment Breakdown", styles['Heading3']))
            elements.append(Spacer(1, 0.1*inch))
            
            # Create table data
            table_data = [['Treatment', 'Billed', 'Coverage Limit', 'Claimable']]
            for item in coverage_breakdown:
                table_data.append([
                    item.get('treatment_name', 'N/A'),
                    f"₹{item.get('billed_cost', 0):,.0f}",
                    f"₹{item.get('coverage_limit', 0):,.0f}",
                    f"₹{item.get('claimable_amount', 0):,.0f}"
                ])
            
            table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))

        # Footer
        footer_text = "Generated by MediExplain AI - Your Medical Billing Assistant"
        elements.append(Paragraph(footer_text, styles['Normal']))

        doc.build(elements)
        buffer.seek(0)

        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=MediExplain_Report.pdf"}
        )
    except Exception as e:
        logger.exception("Error generating PDF report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report"
        ) from e


@router.get("/health")
def health_check():
    """
    Health check endpoint for the billing service.
    """
    return {
        "status": "healthy",
        "service": "billing_anomaly_detection",
        "records_count": len(billing_service.get_all_records())
    }


@router.post("/ask")
async def ask_question(payload: Dict[str, Any]):
    """
    Answer questions about medical bill analysis.

    Accepts a question and the analysis context, then generates a contextual
    answer using the LLM.

    Args:
        payload: Dictionary containing:
            - question: str - The user's question about their bill
            - analysis: dict - The billing analysis results

    Returns:
        Dictionary with the answer to the question
    """
    question = payload.get("question")
    context = payload.get("analysis")

    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required",
        )

    if not context:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis context is required",
        )

    try:
        answer = generate_qa_response(question, context)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error generating Q&A response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer",
        ) from e
