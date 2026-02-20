"""
Pydantic schemas for billing anomaly detection.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class AnomalyType(str, Enum):
    """Types of billing anomalies that can be detected."""
    OVERCHARGE = "overcharge"
    DUPLICATE = "duplicate"
    UNUSUAL_PATTERN = "unusual_pattern"
    FRAUDULENT = "fraudulent"
    CODING_ERROR = "coding_error"


class AnomalySeverity(str, Enum):
    """Severity levels for detected anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BillingRecord(BaseModel):
    """Schema for a single billing record."""
    record_id: str = Field(..., description="Unique identifier for the billing record")
    patient_id: str = Field(..., description="Patient identifier")
    provider_id: str = Field(..., description="Healthcare provider identifier")
    service_code: str = Field(..., description="Medical service/procedure code")
    service_description: Optional[str] = Field(None, description="Description of the service")
    amount: Decimal = Field(..., description="Billing amount", gt=0)
    date_of_service: datetime = Field(..., description="Date when service was provided")
    date_billed: Optional[datetime] = Field(None, description="Date when billing occurred")
    diagnosis_code: Optional[str] = Field(None, description="Diagnosis code (ICD-10)")
    insurance_claim_id: Optional[str] = Field(None, description="Insurance claim identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "BILL-2024-001",
                "patient_id": "PAT-12345",
                "provider_id": "PROV-67890",
                "service_code": "99213",
                "service_description": "Office visit, established patient",
                "amount": "150.00",
                "date_of_service": "2024-02-15T10:30:00",
                "date_billed": "2024-02-16T09:00:00",
                "diagnosis_code": "E11.9",
                "insurance_claim_id": "CLM-98765"
            }
        }


class DetectedAnomaly(BaseModel):
    """Schema for a detected billing anomaly."""
    anomaly_id: str = Field(..., description="Unique identifier for the anomaly")
    record_id: str = Field(..., description="Associated billing record ID")
    anomaly_type: AnomalyType = Field(..., description="Type of anomaly detected")
    severity: AnomalySeverity = Field(..., description="Severity level")
    description: str = Field(..., description="Human-readable description of the anomaly")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="ML model confidence score (0-1)")
    detected_at: datetime = Field(default_factory=datetime.now, description="Timestamp when anomaly was detected")
    suggested_action: Optional[str] = Field(None, description="Recommended action to take")

    class Config:
        json_schema_extra = {
            "example": {
                "anomaly_id": "ANOM-001",
                "record_id": "BILL-2024-001",
                "anomaly_type": "overcharge",
                "severity": "high",
                "description": "Amount exceeds typical range for this service code",
                "confidence_score": 0.87,
                "detected_at": "2024-02-20T14:30:00",
                "suggested_action": "Review pricing against fee schedule"
            }
        }


class BillingRecordCreate(BaseModel):
    """Schema for creating a new billing record."""
    patient_id: str
    provider_id: str
    service_code: str
    service_description: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    date_of_service: datetime
    date_billed: Optional[datetime] = None
    diagnosis_code: Optional[str] = None
    insurance_claim_id: Optional[str] = None


class BillingRecordResponse(BaseModel):
    """Response schema for billing record operations."""
    record: BillingRecord
    anomalies: List[DetectedAnomaly] = Field(default_factory=list, description="Detected anomalies for this record")


class AnomalyDetectionRequest(BaseModel):
    """Request schema for anomaly detection."""
    record_ids: Optional[List[str]] = Field(None, description="Specific record IDs to analyze. If None, analyzes all records.")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    severity_filter: Optional[List[AnomalySeverity]] = Field(None, description="Filter by severity levels")


class AnomalyDetectionResponse(BaseModel):
    """Response schema for anomaly detection."""
    total_records_analyzed: int
    anomalies_detected: int
    anomalies: List[DetectedAnomaly]
    analysis_timestamp: datetime = Field(default_factory=datetime.now)


class TreatmentItem(BaseModel):
    """Single treatment/procedure on a medical bill."""

    name: str = Field(..., description="Treatment or procedure name")
    cost: Decimal = Field(..., gt=0, description="Billed cost for this treatment")


class OtherItem(BaseModel):
    """Additional billable items (e.g., supplies, miscellaneous charges)."""

    name: str = Field(..., description="Item name")
    cost: Decimal = Field(..., gt=0, description="Billed cost for this item")


class MedicalBill(BaseModel):
    """
    Aggregated medical bill for a patient, including treatments and other items.
    Designed for insurance coverage and cost-efficiency analysis.
    """

    bill_id: Optional[str] = Field(
        None, description="Unique identifier for the medical bill"
    )
    patient_id: Optional[str] = Field(
        None, description="Patient identifier associated with this bill"
    )
    treatments: List[TreatmentItem] = Field(
        ..., min_items=1, description="List of medical treatments/procedures"
    )
    other_items: List[OtherItem] = Field(
        default_factory=list,
        description="Other billable items such as supplies or admin charges",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the bill was created in the system",
    )

