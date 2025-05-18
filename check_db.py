#!/usr/bin/env python3
"""
Script to check MongoDB database content
"""
import os
import sys
import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def check_database():
    """Check MongoDB collections"""
    # MongoDB connection
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["memecoin_analyzer"]
    
    # Check transactions collection
    tx_count = await db.transactions.count_documents({})
    print(f"Transactions collection: {tx_count} documents")
    
    # Get a sample transaction
    sample_tx = await db.transactions.find_one({})
    if sample_tx:
        # Convert ObjectId to string for JSON serialization
        if "_id" in sample_tx:
            sample_tx["_id"] = str(sample_tx["_id"])
        print("Sample transaction:")
        print(json.dumps(sample_tx, indent=2))
    
    # Check wallets collection
    wallet_count = await db.wallets.count_documents({})
    print(f"Wallets collection: {wallet_count} documents")
    
    # Check indexer_state collection
    state_count = await db.indexer_state.count_documents({})
    print(f"Indexer state collection: {state_count} documents")
    
    # Get a sample state
    sample_state = await db.indexer_state.find_one({})
    if sample_state:
        # Convert ObjectId to string for JSON serialization
        if "_id" in sample_state:
            sample_state["_id"] = str(sample_state["_id"])
        print("Sample indexer state:")
        print(json.dumps(sample_state, indent=2))

if __name__ == "__main__":
    # Load environment variables from .env file
    env_path = "/app/backend/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip("'\"")
    
    # Run the check
    asyncio.run(check_database())
