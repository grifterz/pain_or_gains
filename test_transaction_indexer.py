#!/usr/bin/env python3
"""
Test script for the transaction indexer
"""
import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our modules
from transaction_indexer import index_wallet, TransactionIndexer

async def test_indexer():
    """Test the transaction indexer with sample wallets"""
    # Test wallets
    solana_wallet = "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"
    base_wallet = "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28"
    
    # Create indexer
    indexer = TransactionIndexer()
    
    # Test Solana wallet
    print(f"\n=== TESTING SOLANA WALLET INDEXING FOR {solana_wallet} ===\n")
    
    try:
        # Index the wallet
        count = await index_wallet(solana_wallet, "solana", full_sync=True)
        print(f"Indexed {count} transactions for Solana wallet {solana_wallet}")
        
        # Get indexer state
        state = await indexer.get_indexer_state(solana_wallet, "solana")
        print(f"Indexer state: {state}")
        
        # Get latest transactions
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client["memecoin_analyzer"]
        transactions_collection = db["transactions"]
        
        # Get a few transactions to display
        cursor = transactions_collection.find({
            "wallet_address": solana_wallet,
            "blockchain": "solana"
        }).sort("timestamp", -1).limit(5)
        
        transactions = await cursor.to_list(length=5)
        
        print(f"Found {len(transactions)} recent transactions for {solana_wallet}")
        for tx in transactions:
            print(f"Transaction: {tx['tx_hash']}")
            print(f"Token: {tx['token_name']} ({tx['token_symbol']})")
            print(f"Type: {tx['type']}")
            print(f"Amount: {tx['amount']}")
            print(f"Price: {tx['price']}")
            print(f"Timestamp: {datetime.fromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            if 'dex' in tx and tx['dex']:
                print(f"DEX: {tx['dex']}")
            print("-" * 40)
    
    except Exception as e:
        print(f"Error testing Solana indexer: {str(e)}")
    
    # Test Base wallet
    print(f"\n=== TESTING BASE WALLET INDEXING FOR {base_wallet} ===\n")
    
    try:
        # Index the wallet
        count = await index_wallet(base_wallet, "base", full_sync=True)
        print(f"Indexed {count} transactions for Base wallet {base_wallet}")
        
        # Get indexer state
        state = await indexer.get_indexer_state(base_wallet, "base")
        print(f"Indexer state: {state}")
        
        # Get latest transactions
        cursor = transactions_collection.find({
            "wallet_address": base_wallet.lower(),
            "blockchain": "base"
        }).sort("timestamp", -1).limit(5)
        
        transactions = await cursor.to_list(length=5)
        
        print(f"Found {len(transactions)} recent transactions for {base_wallet}")
        for tx in transactions:
            print(f"Transaction: {tx['tx_hash']}")
            print(f"Token: {tx['token_name']} ({tx['token_symbol']})")
            print(f"Type: {tx['type']}")
            print(f"Amount: {tx['amount']}")
            print(f"Price: {tx['price']}")
            print(f"Timestamp: {datetime.fromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            if 'dex' in tx and tx['dex']:
                print(f"DEX: {tx['dex']}")
            print("-" * 40)
    
    except Exception as e:
        print(f"Error testing Base indexer: {str(e)}")

if __name__ == "__main__":
    # Load environment variables from .env file
    env_path = "/app/backend/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip("'\"")
    
    # Run the tests
    asyncio.run(test_indexer())
