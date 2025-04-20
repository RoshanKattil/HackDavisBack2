#!/usr/bin/env python3

"""
init_db.py

Initialize the MongoDB for chain_custody_db from scratch,
using GeoJSON Point fields instead of simple lat/long,
and creating named indexes to avoid conflicts.
"""

from pymongo import MongoClient, ASCENDING, GEOSPHERE

def main():
    # Connect to local MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db_name = "chain_custody_db"

    # Drop the existing database (if any)
    client.drop_database(db_name)
    print(f"Dropped database {db_name}")

    # Re-create database and collections
    db = client[db_name]

    # 1. Materials collection
    materials = db["materials"]
    materials.create_index(
        [("materialId", ASCENDING)],
        name="materialId_1",
        unique=True
    )
    materials.create_index(
        [("location", GEOSPHERE)],
        name="location_2dsphere_idx"
    )
    print("Created 'materials' collection with indexes on materialId and geo location")

    # 2. Transfers collection (named to match app.py)
    transfers = db["transfers"]
    transfers.create_index(
        [("materialId", ASCENDING), ("timestamp", ASCENDING)],
        name="material_ts_idx"
    )
    print("Created 'transfers' collection with index material_ts_idx")

    # 3. Waste (hazardous) collection
    waste = db["waste"]
    waste.create_index(
        [("wasteId", ASCENDING)],
        name="wasteId_1",
        unique=True
    )
    print("Created 'waste' collection with unique index on wasteId")

    # 4. Waste history collection
    waste_history = db["waste_history"]
    waste_history.create_index(
        [("wasteId", ASCENDING), ("timestamp", ASCENDING)],
        name="waste_history_ts_idx"
    )
    # If you also store geo points for each step, you could add:
    # waste_history.create_index(
    #     [("from", GEOSPHERE), ("to", GEOSPHERE)],
    #     name="waste_history_geo_idx"
    # )
    print("Created 'waste_history' collection with index waste_history_ts_idx")

if __name__ == "__main__":
    main()
