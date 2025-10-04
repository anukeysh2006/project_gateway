# app/models.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SupplierApplication(BaseModel):
    supplier_application_id: Optional[str] = None
    supplier_application_phase_id: Optional[str] = None
    audit_scheduled_phase_id: Optional[str] = None
    audit_result_phase_id: Optional[str] = None
    supplier_activation_phase_id: Optional[str] = None
    company_name: str
    certifications: List[str]
    component_types: List[str]
    status: str = "PENDING_REVIEW"
    audit_date: Optional[datetime] = None
    audit_passed: Optional[bool] = None
    supplier_id: Optional[str] = None
