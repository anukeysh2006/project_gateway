#!/usr/bin/env python3
"""
auto_onboard.py
Submit a supplier application and print structured DB state for each stage.
"""

import requests
import time
import argparse
import json
import uuid
from datetime import datetime, timezone

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def generate_phase_id(base, phase_name):
    return f"{base}-{phase_name.replace(' ', '_').lower()}-{uuid.uuid4()}"

def submit_application(base_url, company_name, certs, components):
    url = f"{base_url}/supplier/apply"
    payload = {
        "company_name": company_name,
        "certifications": certs,
        "component_types": components
    }
    r = requests.post(url, json=payload)
    r.raise_for_status()
    return r.json()

def get_application(base_url, app_id):
    url = f"{base_url}/supplier/{app_id}"
    r = requests.get(url)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def put_audit_result(base_url, app_id, passed: bool):
    url = f"{base_url}/supplier/audit_result/{app_id}"
    r = requests.put(url, json={"audit_passed": bool(passed)})
    r.raise_for_status()
    return r.json()

def put_activate(base_url, app_id):
    url = f"{base_url}/supplier/activate/{app_id}"
    r = requests.put(url)
    r.raise_for_status()
    return r.json()

def wait_for_status(base_url, app_id, expected_status, timeout=60, poll_interval=0.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = get_application(base_url, app_id)
        if doc and doc.get("status") == expected_status:
            return doc
        time.sleep(poll_interval)
    raise TimeoutError(f"Timeout waiting for status {expected_status} for {app_id}")

def print_stage(stage_name, doc, phase_field, phase_id):
    print(f"\n{'='*10} Stage: {stage_name} {'='*10}")
    print(f"Phase ID: {phase_id}")
    doc_copy = dict(doc)
    doc_copy[phase_field] = phase_id
    print("Database state after stage:")
    print(json.dumps(doc_copy, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--company", default="Auto Supplier Ltd")
    parser.add_argument("--certs", default="ISO9001")
    parser.add_argument("--components", default="motors,sensors")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    certs = [c.strip() for c in args.certs.split(",") if c.strip()]
    components = [c.strip() for c in args.components.split(",") if c.strip()]

    print("Submitting supplier application...")
    resp = submit_application(base_url, args.company, certs, components)
    app_id = resp.get("supplier_application_id")

    # Stage 1: Submitted (PENDING_REVIEW)
    doc = get_application(base_url, app_id)
    application_phase_id = generate_phase_id(app_id, "supplier_application_submitted")
    print_stage("Supplier Application Submitted", doc, "supplier_application_phase_id", application_phase_id)

    # Stage 2: Wait for AUDIT_SCHEDULED
    doc = wait_for_status(base_url, app_id, "AUDIT_SCHEDULED", timeout=args.timeout)
    audit_scheduled_phase_id = generate_phase_id(app_id, "audit_scheduled")
    print_stage("Audit Scheduled", doc, "audit_scheduled_phase_id", audit_scheduled_phase_id)

    # Stage 3: Audit Completed
    put_audit_result(base_url, app_id, True)
    doc = wait_for_status(base_url, app_id, "AUDIT_PASSED", timeout=args.timeout)
    audit_result_phase_id = generate_phase_id(app_id, "audit_result")
    print_stage("Audit Completed", doc, "audit_result_phase_id", audit_result_phase_id)

    # Stage 4: Supplier Activated
    put_activate(base_url, app_id)
    doc = wait_for_status(base_url, app_id, "ACTIVE", timeout=args.timeout)
    supplier_activation_phase_id = generate_phase_id(app_id, "supplier_activated")
    print_stage("Supplier Activated", doc, "supplier_activation_phase_id", supplier_activation_phase_id)

if __name__ == "__main__":
    main()
