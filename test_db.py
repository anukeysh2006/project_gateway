from app.database import applications_collection

# Test insertion
test_doc = {"test": "MongoDB connection successful"}
result = applications_collection.insert_one(test_doc)
print("Inserted document ID:", result.inserted_id)
