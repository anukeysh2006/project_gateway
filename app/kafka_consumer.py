# app/kafka_consumer.py
import os
import json
import uuid
from bson import ObjectId
from confluent_kafka import Consumer, KafkaError
from datetime import datetime, timezone
from app.database import applications_collection

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP", "project-gateway-consumer-group")

consumer_conf = {
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    "group.id": GROUP_ID,
    "auto.offset.reset": "earliest",
}

consumer = Consumer(consumer_conf)
topics = ["supplier.application.submitted"]
consumer.subscribe(topics)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# Convert MongoDB document to JSON-serializable dict
def serialize_doc(doc):
    if doc is None:
        return None
    def convert(value):
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, list):
            return [convert(v) for v in value]
        elif isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        else:
            return value
    return convert(doc)

# Helper function to print stage info
def print_stage(stage_name, phase_id, db_record):
    print(f"\n========== Stage: {stage_name} ==========")
    print(f"Phase ID: {phase_id}")
    print("Database state after stage:")
    print(json.dumps(serialize_doc(db_record), indent=2))

def main_loop():
    print("[consumer] started, listening topics:", topics)
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print("[consumer] error:", msg.error())
                    continue

            try:
                event = json.loads(msg.value().decode("utf-8"))
            except Exception as e:
                print("[consumer] invalid JSON event:", e)
                continue

            etype = event.get("event_type", "")
            app_id = event.get("supplier_application_id")

            if etype == "application_submitted":
                print(f"[consumer] detected application submitted: {app_id}")

                doc = applications_collection.find_one({"supplier_application_id": app_id})
                if not doc:
                    print(f"[consumer] no document found for {app_id}")
                    continue

                if doc.get("status") != "PENDING_REVIEW":
                    print(f"[consumer] skipping, current status: {doc.get('status')}")
                    continue

                # 1️⃣ Supplier Application Submitted (manual payload)
                phase_id = f"{app_id}-supplier_application_submitted-{uuid.uuid4()}"
                print_stage("Supplier Application Submitted", phase_id, doc)

                # 2️⃣ Schedule Audit
                scheduled_dt = now_iso()
                applications_collection.update_one(
                    {"supplier_application_id": app_id},
                    {
                        "$set": {"status": "AUDIT_SCHEDULED", "audit_date": scheduled_dt, "updated_at": scheduled_dt},
                        "$push": {"history": {"timestamp": scheduled_dt, "from": "PENDING_REVIEW", "to": "AUDIT_SCHEDULED", "actor": "automated_consumer"}}
                    }
                )
                doc = applications_collection.find_one({"supplier_application_id": app_id})
                audit_scheduled_phase_id = f"{app_id}-audit_scheduled-{uuid.uuid4()}"
                print(f"[consumer] AUDIT_SCHEDULED triggered for {app_id}")
                print_stage("Audit Scheduled", audit_scheduled_phase_id, doc)

                # 3️⃣ Audit Passed
                passed_dt = now_iso()
                applications_collection.update_one(
                    {"supplier_application_id": app_id},
                    {
                        "$set": {"status": "AUDIT_PASSED", "audit_passed": True, "updated_at": passed_dt},
                        "$push": {"history": {"timestamp": passed_dt, "from": "AUDIT_SCHEDULED", "to": "AUDIT_PASSED", "actor": "auditor_api"}}
                    }
                )
                doc = applications_collection.find_one({"supplier_application_id": app_id})
                audit_result_phase_id = f"{app_id}-audit_result-{uuid.uuid4()}"
                print(f"[consumer] AUDIT_PASSED triggered for {app_id}")
                print_stage("Audit Completed", audit_result_phase_id, doc)

                # 4️⃣ Activate Supplier
                supplier_id = f"GATEWAY-SUP-{uuid.uuid4()}"
                active_dt = now_iso()
                applications_collection.update_one(
                    {"supplier_application_id": app_id},
                    {
                        "$set": {"status": "ACTIVE", "supplier_id": supplier_id, "updated_at": active_dt},
                        "$push": {"history": {"timestamp": active_dt, "from": "AUDIT_PASSED", "to": "ACTIVE", "actor": "activate_api"}}
                    }
                )
                doc = applications_collection.find_one({"supplier_application_id": app_id})
                supplier_activated_phase_id = f"{app_id}-supplier_activated-{uuid.uuid4()}"
                print(f"[consumer] ACTIVE triggered for {app_id}")
                print_stage("Supplier Activated", supplier_activated_phase_id, doc)

            else:
                print("[consumer] unhandled event type:", etype)

    except KeyboardInterrupt:
        print("[consumer] interrupted")
    finally:
        consumer.close()

if __name__ == "__main__":
    main_loop()
