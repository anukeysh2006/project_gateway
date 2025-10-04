# app/main.py
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from app.database import applications_collection
from app.kafka_producer import publish_event

app = FastAPI(title="Project Gateway - Supplier Onboarding")

def iso_now():
    return datetime.utcnow().isoformat() + "Z"

class SupplierApplicationRequest(BaseModel):
    company_name: str
    certifications: List[str] = []
    component_types: List[str] = []

class AuditResultRequest(BaseModel):
    audit_passed: bool

@app.post("/supplier/apply")
def submit_supplier_application(body: SupplierApplicationRequest):
    supplier_application_id = f"GATEWAY-APP-{uuid4()}"
    now = iso_now()
    doc = {
        "supplier_application_id": supplier_application_id,
        "company_name": body.company_name,
        "certifications": body.certifications,
        "component_types": body.component_types,
        "status": "PENDING_REVIEW",
        "history": [{"timestamp": now, "from": None, "to": "PENDING_REVIEW", "actor": "submit_api"}],
        "created_at": now,
        "updated_at": now
    }
    applications_collection.insert_one(doc)

    event = {
        "event_type": "application_submitted",
        "supplier_application_id": supplier_application_id,
        "payload": {
            "supplier_application_phase_id": f"{supplier_application_id}-supplier_application_phase_id",
            "company_name": body.company_name,
            "certifications": body.certifications,
            "component_types": body.component_types
        },
        "timestamp": now
    }
    publish_event("supplier.application.submitted", supplier_application_id, event)
    return {"supplier_application_id": supplier_application_id, "status": "PENDING_REVIEW"}

@app.put("/supplier/schedule_audit/{application_id}")
def schedule_audit(application_id: str = Path(...), audit_date: Optional[str] = None):
    doc = applications_collection.find_one({"supplier_application_id": application_id})
    if not doc:
        raise HTTPException(404, "Application not found")
    if doc.get("status") != "PENDING_REVIEW":
        raise HTTPException(400, f"Cannot schedule audit when status is {doc.get('status')}")

    scheduled = audit_date or iso_now()
    applications_collection.update_one(
        {"supplier_application_id": application_id},
        {"$set": {"status": "AUDIT_SCHEDULED", "audit_date": scheduled, "updated_at": iso_now()},
         "$push": {"history": {"timestamp": iso_now(), "from": "PENDING_REVIEW", "to": "AUDIT_SCHEDULED", "actor": "schedule_api"}}}
    )
    event = {
        "event_type": "application_audit_scheduled",
        "supplier_application_id": application_id,
        "payload": {
            "audit_scheduled_phase_id": f"{application_id}-audit_scheduled_phase_id",
            "supplier_application_phase_id": doc.get("supplier_application_phase_id"),
            "company_name": doc.get("company_name"),
            "certifications": doc.get("certifications"),
            "component_types": doc.get("component_types"),
            "scheduled_date": scheduled
        },
        "timestamp": iso_now()
    }
    publish_event("supplier.application.audit_scheduled", application_id, event)
    return {"message": "Audit scheduled", "audit_date": scheduled}

@app.put("/supplier/audit_result/{application_id}")
def submit_audit_result(application_id: str, body: AuditResultRequest):
    doc = applications_collection.find_one({"supplier_application_id": application_id})
    if not doc:
        raise HTTPException(404, "Application not found")
    if doc.get("status") != "AUDIT_SCHEDULED":
        raise HTTPException(400, f"Cannot submit audit result when status is {doc.get('status')}")

    new_status = "AUDIT_PASSED" if body.audit_passed else "PENDING_REVIEW"
    applications_collection.update_one(
        {"supplier_application_id": application_id},
        {"$set": {"status": new_status, "audit_passed": bool(body.audit_passed), "updated_at": iso_now()},
         "$push": {"history": {"timestamp": iso_now(), "from": "AUDIT_SCHEDULED", "to": new_status, "actor": "auditor_api"}}}
    )
    event = {
        "event_type": "application_audit_result",
        "supplier_application_id": application_id,
        "payload": {
            "audit_result_phase_id": f"{application_id}-audit_result_phase_id",
            "audit_scheduled_phase_id": doc.get("audit_scheduled_phase_id"),
            "supplier_application_phase_id": doc.get("supplier_application_phase_id"),
            "company_name": doc.get("company_name"),
            "certifications": doc.get("certifications"),
            "component_types": doc.get("component_types"),
            "audit_passed": body.audit_passed
        },
        "timestamp": iso_now()
    }
    publish_event("supplier.application.audit_result", application_id, event)
    return {"message": "Audit result recorded", "audit_passed": body.audit_passed}

@app.put("/supplier/activate/{application_id}")
def activate_supplier(application_id: str):
    doc = applications_collection.find_one({"supplier_application_id": application_id})
    if not doc:
        raise HTTPException(404, "Application not found")
    if doc.get("status") != "AUDIT_PASSED":
        raise HTTPException(400, f"Cannot activate when status is {doc.get('status')}")

    supplier_id = f"GATEWAY-SUP-{uuid4()}"
    applications_collection.update_one(
        {"supplier_application_id": application_id},
        {"$set": {"status": "ACTIVE", "supplier_id": supplier_id, "updated_at": iso_now()},
         "$push": {"history": {"timestamp": iso_now(), "from": "AUDIT_PASSED", "to": "ACTIVE", "actor": "activate_api"}}}
    )
    event = {
        "event_type": "application_activated",
        "supplier_application_id": application_id,
        "payload": {
            "supplier_activation_phase_id": f"{application_id}-supplier_activation_phase_id",
            "audit_result_phase_id": doc.get("audit_result_phase_id"),
            "audit_scheduled_phase_id": doc.get("audit_scheduled_phase_id"),
            "supplier_application_phase_id": doc.get("supplier_application_phase_id"),
            "company_name": doc.get("company_name"),
            "certifications": doc.get("certifications"),
            "component_types": doc.get("component_types"),
            "supplier_id": supplier_id
        },
        "timestamp": iso_now()
    }
    publish_event("supplier.application.activated", application_id, event)
    return {"message": "Supplier activated", "supplier_id": supplier_id}

@app.get("/supplier/{application_id}")
def get_application(application_id: str):
    doc = applications_collection.find_one({"supplier_application_id": application_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Application not found")
    return doc
