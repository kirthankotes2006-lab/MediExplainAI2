"""
Business logic for billing anomaly detection.
Designed to be easily extensible for ML model integration.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Union
from uuid import uuid4

from app.schemas.billing_schema import (
    BillingRecord,
    BillingRecordCreate,
    DetectedAnomaly,
    AnomalyType,
    AnomalySeverity,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    MedicalBill,
)
from app.core.insurance_policy import (
    is_treatment_excluded,
    is_treatment_covered,
    get_coverage_limit,
    is_non_payable_item,
    get_co_payment_percentage,
)
from app.core.policy_model import InsurancePolicyModel
from app.core.policy_state import CURRENT_POLICY
from app.services.cost_analysis_service import analyze_cost_efficiency


def _get_active_policy() -> Optional[InsurancePolicyModel]:
    """
    Return the currently loaded InsurancePolicyModel, if any.
    """
    return CURRENT_POLICY


def _is_treatment_excluded_policy(name: str) -> bool:
    """
    Policy-aware check for treatment exclusion.

    Uses CURRENT_POLICY if loaded; otherwise falls back to the
    hard-coded insurance_policy helpers.
    """
    policy = _get_active_policy()
    if policy:
        normalized = name.strip().lower()
        exclusions_ci = {n.lower() for n in policy.exclusions}
        return normalized in exclusions_ci
    return is_treatment_excluded(name)


def _is_treatment_covered_policy(name: str) -> bool:
    """
    Policy-aware check for treatment coverage.

    A treatment is considered covered if:
    - It has a coverage limit defined, and
    - It is not listed in the exclusions.
    """
    policy = _get_active_policy()
    if policy:
        normalized = name.strip().lower()
        exclusions_ci = {n.lower() for n in policy.exclusions}
        if normalized in exclusions_ci:
            return False
        coverage_ci = {n.lower() for n in policy.coverage_limits.keys()}
        return normalized in coverage_ci
    return is_treatment_covered(name)


def _get_coverage_limit_policy(name: str) -> Optional[float]:
    """
    Policy-aware coverage limit lookup.
    """
    policy = _get_active_policy()
    if policy:
        return policy.get_coverage_limit(name)
    return get_coverage_limit(name)


def _is_non_payable_item_policy(name: str) -> bool:
    """
    Policy-aware non-payable item check.
    """
    policy = _get_active_policy()
    if policy:
        normalized = name.strip().lower()
        non_payable_ci = {n.lower() for n in policy.non_payable_items}
        return normalized in non_payable_ci
    return is_non_payable_item(name)


def _get_co_payment_percentage_policy() -> float:
    """
    Policy-aware co-payment percentage.
    """
    policy = _get_active_policy()
    if policy:
        return float(policy.co_payment_percentage)
    return get_co_payment_percentage()


class BillingService:
    """
    Service layer for billing operations and anomaly detection.
    
    This class handles business logic and can be extended to integrate ML models.
    """
    
    def __init__(self):
        # In-memory storage for development
        # TODO: Replace with database integration
        self._records: dict[str, BillingRecord] = {}
        self._anomalies: dict[str, List[DetectedAnomaly]] = {}
    
    def create_record(self, record_data: BillingRecordCreate) -> BillingRecord:
        """
        Create a new billing record.
        
        Args:
            record_data: Billing record data
            
        Returns:
            Created billing record
        """
        record_id = f"BILL-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        
        record = BillingRecord(
            record_id=record_id,
            **record_data.model_dump(),
            date_billed=record_data.date_billed or datetime.now()
        )
        
        self._records[record_id] = record
        
        # Automatically detect anomalies for new records
        anomalies = self._detect_anomalies(record)
        self._anomalies[record_id] = anomalies
        
        return record    
    def get_record(self, record_id: str) -> Optional[BillingRecord]:
        """
        Retrieve a billing record by ID.
        
        Args:
            record_id: Record identifier
            
        Returns:
            Billing record or None if not found
        """
        return self._records.get(record_id)    
    def get_all_records(self) -> List[BillingRecord]:
        """
        Get all billing records.
        
        Returns:
            List of all billing records
        """
        return list(self._records.values())    
    def detect_anomalies(
        self,
        request: AnomalyDetectionRequest
    ) -> AnomalyDetectionResponse:
        """
        Detect anomalies in billing records.
        
        This method can be extended to integrate ML models for more sophisticated detection.
        
        Args:
            request: Detection request parameters
            
        Returns:
            Detection response with found anomalies
        """
        # Determine which records to analyze
        if request.record_ids:
            records_to_analyze = [
                self._records[rid] for rid in request.record_ids
                if rid in self._records
            ]
        else:
            records_to_analyze = list(self._records.values())
        
        # Detect anomalies
        all_anomalies: List[DetectedAnomaly] = []
        for record in records_to_analyze:
            anomalies = self._detect_anomalies(record, request.min_confidence)
            all_anomalies.extend(anomalies)
        
        # Apply severity filter if specified
        if request.severity_filter:
            all_anomalies = [
                a for a in all_anomalies
                if a.severity in request.severity_filter
            ]
        
        return AnomalyDetectionResponse(
            total_records_analyzed=len(records_to_analyze),
            anomalies_detected=len(all_anomalies),
            anomalies=all_anomalies
        )    
    def _detect_anomalies(
        self,
        record: BillingRecord,
        min_confidence: float = 0.5
    ) -> List[DetectedAnomaly]:
        """
        Internal method to detect anomalies in a single record.
        
        This is where ML model integration would be added.
        Currently uses rule-based detection as a placeholder.
        
        Args:
            record: Billing record to analyze
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of detected anomalies
        """
        anomalies: List[DetectedAnomaly] = []
        
        # Placeholder: Rule-based anomaly detection
        # TODO: Replace with ML model inference
        
        # Example: Detect unusually high amounts
        # This is a simple rule - ML models would provide more sophisticated detection
        typical_amounts = {
            "99213": Decimal("150.00"),  # Office visit
            "99214": Decimal("200.00"),  # Office visit, detailed
            "36415": Decimal("25.00"),  # Routine venipuncture
        }
        
        if record.service_code in typical_amounts:
            typical = typical_amounts[record.service_code]
            if record.amount > typical * Decimal("2.0"):  # 2x threshold
                anomaly = DetectedAnomaly(
                    anomaly_id=f"ANOM-{str(uuid4())[:8].upper()}",
                    record_id=record.record_id,
                    anomaly_type=AnomalyType.OVERCHARGE,
                    severity=AnomalySeverity.HIGH,
                    description=f"Amount ${record.amount} exceeds typical range for service code {record.service_code}",
                    confidence_score=0.75,  # Placeholder confidence
                    suggested_action="Review pricing against fee schedule"
                )
                anomalies.append(anomaly)
        
        # Example: Detect duplicate records (simplified)
        # ML models could detect more sophisticated duplicates
        for existing_record in self._records.values():
            if (
                existing_record.record_id != record.record_id
                and existing_record.patient_id == record.patient_id
                and existing_record.service_code == record.service_code
                and abs((existing_record.date_of_service - record.date_of_service).days) < 1
            ):
                anomaly = DetectedAnomaly(
                    anomaly_id=f"ANOM-{str(uuid4())[:8].upper()}",
                    record_id=record.record_id,
                    anomaly_type=AnomalyType.DUPLICATE,
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Possible duplicate of record {existing_record.record_id}",
                    confidence_score=0.65,
                    suggested_action="Verify if this is a legitimate duplicate service"
                )
                anomalies.append(anomaly)
                break  # Only flag once per record
        
        return anomalies    
    def get_record_anomalies(self, record_id: str) -> List[DetectedAnomaly]:
        """
        Get anomalies for a specific record.
        
        Args:
            record_id: Record identifier
            
        Returns:
            List of anomalies for the record
        """
        return self._anomalies.get(record_id, [])


def analyze_medical_bill(bill: MedicalBill) -> dict:
    """
    Analyze a medical bill for insurance coverage and cost efficiency.

    The analysis includes:
    - Total bill amount
    - Total claimable amount after co-payment
    - Co-payment deducted
    - Excluded items and non-payable items
    - Coverage breakdown for treatments
    - Cost-efficiency warnings for overpriced items

    Raises:
        ValueError: If the bill has no valid treatments for coverage analysis.
    """
    try:
        if not bill.treatments:
            raise ValueError("Medical bill must contain at least one treatment")

        total_bill_amount = Decimal("0")
        total_claimable_before_copay = Decimal("0")

        excluded_items: List[dict] = []
        non_payable_items: List[dict] = []
        coverage_breakdown: List[dict] = []
        cost_efficiency_warnings: List[dict] = []

        # Process treatments
        for treatment in bill.treatments:
            name = treatment.name
            cost = Decimal(treatment.cost)
            total_bill_amount += cost

            # Get mean cost and stats from cost analysis
            mean_cost = 0.0
            std_dev = 0.0
            historical_trend = []
            try:
                cost_analysis = analyze_cost_efficiency(name, float(cost))
                if cost_analysis:
                    mean_cost = cost_analysis.get("average_cost", 0.0)
                    std_dev = cost_analysis.get("std_dev", 0.0)
                    historical_trend = cost_analysis.get("historical_trend", [])
            except Exception:
                pass

            # Coverage & exclusions (policy-aware)
            if _is_treatment_excluded_policy(name):
                excluded_items.append(
                    {
                        "name": name,
                        "cost": float(cost),
                        "reason": "policy_exclusion",
                    }
                )
                coverage_breakdown.append(
                    {
                        "treatment_name": name,
                        "billed_cost": float(cost),
                        "coverage_limit": 0.0,
                        "claimable_amount": 0.0,
                        "mean_cost": mean_cost,
                        "std_dev": std_dev,
                        "historical_trend": historical_trend,
                    }
                )
            elif _is_treatment_covered_policy(name):
                coverage_limit_value = _get_coverage_limit_policy(name)
                coverage_limit = (
                    Decimal(str(coverage_limit_value))
                    if coverage_limit_value is not None
                    else Decimal("0")
                )
                claimable = min(cost, coverage_limit)
                total_claimable_before_copay += claimable

                coverage_breakdown.append(
                    {
                        "treatment_name": name,
                        "billed_cost": float(cost),
                        "coverage_limit": float(coverage_limit),
                        "claimable_amount": float(claimable),
                        "mean_cost": mean_cost,
                        "std_dev": std_dev,
                        "historical_trend": historical_trend,
                    }
                )
            else:
                # Not excluded and not covered -> patient pays fully
                coverage_breakdown.append(
                    {
                        "treatment_name": name,
                        "billed_cost": float(cost),
                        "coverage_limit": 0.0,
                        "claimable_amount": 0.0,
                        "mean_cost": mean_cost,
                        "std_dev": std_dev,
                        "historical_trend": historical_trend,
                    }
                )

            # Cost-efficiency analysis for treatment
            try:
                analysis = analyze_cost_efficiency(name, float(cost))
                if analysis and analysis.get("status") != "within_market_range":
                    analysis_with_context = {**analysis, "item_type": "treatment"}
                    cost_efficiency_warnings.append(analysis_with_context)
            except Exception:
                # Do not fail bill analysis due to cost-efficiency helper issues
                continue

        # Process other billable items
        for item in bill.other_items:
            name = item.name
            cost = Decimal(item.cost)
            total_bill_amount += cost

            # Track non-payable items
            if _is_non_payable_item_policy(name):
                non_payable_items.append(
                    {
                        "name": name,
                        "cost": float(cost),
                        "reason": "non_payable_item",
                    }
                )
            
            # Cost-efficiency analysis for other items (including non-payable ones)
            # This helps identify overcharges even on items that insurance won't cover
            try:
                analysis = analyze_cost_efficiency(name, float(cost))
                if analysis:
                    # Add severity indicator for anomalies
                    analysis_with_context = {**analysis, "item_type": "other_item"}
                    
                    # If item is non-payable AND overpriced, mark as high priority
                    if _is_non_payable_item_policy(name) and analysis.get("status") == "highly_overpriced":
                        analysis_with_context["priority"] = "high"
                        analysis_with_context["alert"] = f"⚠️ Non-payable item '{name}' is significantly overpriced (₹{cost} vs typical ₹{analysis['average_cost']:.0f})"
                    
                    if analysis.get("status") != "within_market_range":
                        cost_efficiency_warnings.append(analysis_with_context)
            except Exception:
                continue

        if total_claimable_before_copay <= 0:
            raise ValueError("No valid treatments for insurance coverage")

        # Apply co-payment deduction (policy-aware)
        co_payment_percentage = Decimal(str(_get_co_payment_percentage_policy())) / Decimal(
            "100"
        )
        co_payment_deducted = (
            total_claimable_before_copay * co_payment_percentage
        ).quantize(Decimal("0.01"))
        total_claimable_after_copay = (
            total_claimable_before_copay - co_payment_deducted
        ).quantize(Decimal("0.01"))

        return {
            "total_bill_amount": float(total_bill_amount),
            "total_claimable_amount": float(total_claimable_after_copay),
            "co_payment_deducted": float(co_payment_deducted),
            "excluded_items": excluded_items,
            "non_payable_items": non_payable_items,
            "coverage_breakdown": coverage_breakdown,
            "cost_efficiency_warnings": cost_efficiency_warnings,
        }

    except ValueError:
        # Bubble up validation errors for the caller to handle
        raise
    except Exception as exc:
        # Wrap unexpected errors to keep the interface stable
        raise RuntimeError(f"Error analyzing medical bill: {exc}") from exc


# Global service instance
# In production, this could be managed by dependency injection
billing_service = BillingService()
