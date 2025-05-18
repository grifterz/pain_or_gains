#!/usr/bin/env python3
"""
Direct test of the token name resolution using MongoDB
"""
import os
import sys
import logging
import time
import pymongo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import token finder
from token_finder import get_token_name

def test_token_lookup():
    """
    Test token name resolution directly and store in MongoDB
    """
    # Connect to MongoDB
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/")
    client = pymongo.MongoClient(mongo_url)
    db = client["memecoins"]
    results_collection = db["token_resolution_tests"]
    
    # Tokens to test
    test_tokens = [
        ("5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump", "solana"),
        ("FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump", "solana"),
        ("3yCDp1E5yzA1qoNQuDjNr5iXyj1CSHjf3dktHpnypump", "solana"),
        ("56UtHy4oBGeLNEenvvXJhhAwDwhNc2bbZgAPUZaFpump", "solana"),
        ("0xe1abd004250ac8d1f199421d647e01d094faa180", "base"),
        ("0xcaa6d4049e667ffd88457a1733d255eed02996bb", "base"),
        ("0x692c1564c82e6a3509ee189d1b666df9a309b420", "base"),
        ("0xc53fc22033a4bcb15b5405c38e67e378c960ee6b", "base")
    ]
    
    # Clear existing test results
    results_collection.delete_many({})
    
    # Store test results
    print("\n=== TESTING TOKEN NAME RESOLUTION ===\n")
    for token_address, blockchain in test_tokens:
        try:
            # Get token name and symbol
            name, symbol = get_token_name(token_address, blockchain)
            
            # Store result in MongoDB
            result = {
                "token_address": token_address,
                "blockchain": blockchain,
                "name": name,
                "symbol": symbol,
                "timestamp": time.time()
            }
            results_collection.insert_one(result)
            
            print(f"✅ {blockchain.capitalize()} token {token_address}: name={name}, symbol={symbol}")
        except Exception as e:
            print(f"❌ Error looking up {blockchain} token {token_address}: {str(e)}")
    
    # Print all results
    print("\n=== MONGODB STORED RESULTS ===\n")
    cursor = results_collection.find({})
    for doc in cursor:
        print(f"Token: {doc['token_address']}, Name: {doc['name']}, Symbol: {doc['symbol']}")

if __name__ == "__main__":
    # Load environment variables from .env file
    env_path = "/app/backend/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip("'\"")
    
    # Run the test
    test_token_lookup()
