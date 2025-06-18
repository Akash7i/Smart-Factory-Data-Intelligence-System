from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['smart_factory']
collection = db['machine_data']

# EDM machine IDs
machine_ids = [f"M{i}" for i in range(1, 11)]

# Clear old data for all machines (optional)
collection.delete_many({'machine_id': {'$in': machine_ids}})
print("🗑️ Cleared existing data for M1 to M10")

# Insert 50 sample records for each machine
for machine_id in machine_ids:
    base_time = datetime.now() - timedelta(minutes=49)
    data = []
    for i in range(50):
        entry = {
            'machine_id': machine_id,
            'timestamp': base_time + timedelta(minutes=i),
            'temperature': round(random.uniform(70, 120), 2)
        }
        data.append(entry)
    
    collection.insert_many(data)
    print(f"✅ Inserted 50 sample data points for {machine_id}")
