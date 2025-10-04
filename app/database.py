# app/database.py
from pymongo import MongoClient

# Local MongoDB URI
MONGO_URI = "mongodb://localhost:27017"

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Create/use database
db = client["project_gateway"]

# Collection for supplier applications
applications_collection = db["supplier_applications"]
#open docker desktop
#docker-compose up -d
#mongod
#uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
#python -m app.kafka_consumer