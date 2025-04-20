from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGODB_URI"))
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGODB_URI)
db = client["chain_custody_db"]

# Completely clear both collections:
db.materials.delete_many({})
db.transfers.delete_many({})

print("Cleared materials and transfers.")
