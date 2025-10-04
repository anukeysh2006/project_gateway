# app/kafka_producer.py
import os
import json
from confluent_kafka import Producer
from datetime import datetime

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

producer_conf = {
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    # optional: 'client.id': 'project-gateway-producer'
}
producer = Producer(producer_conf)

def delivery_report(err, msg):
    if err is not None:
        print("Delivery failed:", err)
    else:
        # optional success log:
        print(f"Delivered message to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

def publish_event(topic: str, key: str, value: dict):
    """
    Publish a JSON event to Kafka. key should be supplier_application_id.
    """
    data = json.dumps(value).encode("utf-8")
    producer.produce(topic, key=key, value=data, callback=delivery_report)
    producer.flush()  # flush for deterministic delivery in dev
