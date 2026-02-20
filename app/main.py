"""
FastAPI application initialization for Healthcare AI Billing Anomaly Detection System.
"""
import os
import shutil
import tempfile
import logging
from typing import Any, Dict
from io import BytesIO

from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.routes.billing import router as billing_router
from app.schemas.billing_schema import MedicalBill
from app.services.billing_service import analyze_medical_bill
from app.services.llm_service_unified import generate_llm_explanation_unified
from app.core.policy_parser import parse_insurance_policy_pdf
from app.core import policy_state


templates = Jinja2Templates(directory="templates")


# Initialize FastAPI app
app = FastAPI(
    title="Healthcare AI Billing Anomaly Detection API",
    description="API for detecting anomalies in healthcare billing records using AI/ML",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(billing_router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Root endpoint - serves the main application interface.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None,
            "summary": None,
        }
    )


@app.get("/health")
def health():
    """
    Application health check endpoint.
    """
    return {"status": "healthy", "service": "billing_anomaly_detection"}


@app.get("/billing/analyze", response_class=HTMLResponse)
async def show_billing_form(request: Request):
    """
    Render a lightweight HTML form for entering basic bill details.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None,
            "summary": None,
            "error": None,
            "patient_name": "",
            "hospital_name": "",
        },
    )


@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """
    Convenience alias for `/billing/analyze` that shows the same form.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None,
            "summary": None,
            "error": None,
            "patient_name": "",
            "hospital_name": "",
        },
    )


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


@app.post("/billing/analyze")
async def analyze_billing_endpoint(
    request: Request,
    patient_name: str = Form(None),
    hospital_name: str = Form(None),
    treatment_name: str = Form(None),
    treatment_cost: Optional[float] = Form(None),
    other_item_name: str = Form(None),
    other_item_cost: Optional[float] = Form(None),
):
    """
    Unified endpoint that:
    - Accepts JSON (Swagger / API clients) and returns JSON.
    - Accepts form data from the HTML page and returns rendered HTML.
    """
    content_type = request.headers.get("content-type", "").lower()

    # JSON API flow (Swagger / programmatic clients)
    if "application/json" in content_type:
        body = await request.json()
        try:
            bill = _parse_medical_bill_payload(body)
            result = analyze_medical_bill(bill)
            return result
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to analyze medical bill",
            )

    # HTML form flow
    try:
        treatments = []
        if treatment_name and treatment_cost is not None:
            treatments.append({"name": treatment_name, "cost": treatment_cost})

        other_items = []
        if other_item_name and other_item_cost is not None:
            other_items.append({"name": other_item_name, "cost": other_item_cost})

        bill_payload = {
            "bill_id": None,
            "patient_id": patient_name or None,
            "treatments": treatments,
            "other_items": other_items,
        }

        bill = _parse_medical_bill_payload(bill_payload)
        result = analyze_medical_bill(bill)
        summary = generate_llm_explanation_unified(result)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": result,
                "summary": summary,
                "error": None,
                "patient_name": patient_name or "",
                "hospital_name": hospital_name or "",
            },
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "summary": None,
                "error": str(exc),
                "patient_name": patient_name or "",
                "hospital_name": hospital_name or "",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": None,
                "summary": None,
                "error": "Something went wrong while analyzing your bill. Please try again.",
                "patient_name": patient_name or "",
                "hospital_name": hospital_name or "",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _policy_to_dict(policy) -> Dict[str, Any]:
    """
    Convert an InsurancePolicyModel to a dictionary for JSON serialization.
    """
    return {
        "co_payment_percentage": policy.co_payment_percentage,
        "coverage_limits": policy.coverage_limits,
        "exclusions": policy.exclusions,
        "covered_treatments": list(policy.coverage_limits.keys()),
    }


@app.post("/billing/upload-policy")
async def upload_insurance_policy(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload an insurance policy PDF, parse it, and store in global state.
    Returns policy details for frontend display.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
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

        # Parse PDF into InsurancePolicyModel
        try:
            policy = parse_insurance_policy_pdf(tmp_path)
        except ValueError as parse_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(parse_err),
            ) from parse_err

        # Store in shared CURRENT_POLICY state
        policy_state.CURRENT_POLICY = policy

        return {
            "filename": file.filename,
            "co_payment_percentage": policy.co_payment_percentage,
            "coverage_limits": policy.coverage_limits,
            "exclusions": policy.exclusions,
            "covered_treatments": list(policy.coverage_limits.keys()),
            "message": "Policy uploaded and parsed successfully",
        }

    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error uploading policy")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process uploaded insurance policy: {str(exc)}",
        ) from exc
    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.post("/billing/download-report")
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
        logger = logging.getLogger(__name__)
        logger.exception("Error generating PDF report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report"
        ) from e
