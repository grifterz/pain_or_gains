#!/usr/bin/env python3
"""
Test script to verify real transaction fetching
"""
import os
import sys
import json
import logging
from datetime import datetime
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our modules
from blockchain_fetcher import fetch_wallet_transactions

async def test_wallet_analysis():
    """
    Test fetching real transactions for sample wallets
    """
    # Test wallets
    solana_wallet = "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"
    base_wallet = "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28"
    
    # Test Solana wallet
    print(f"\n=== TESTING SOLANA WALLET: {solana_wallet} ===\n")
    solana_txs = fetch_wallet_transactions(solana_wallet, "solana")
    
    print(f"Found {len(solana_txs)} transactions for Solana wallet")
    if solana_txs:
        # Show some example transactions
        print("\nExample transactions:")
        for tx in solana_txs[:3]:
            print(f"TX Hash: {tx['tx_hash']}")
            print(f"Token: {tx['token_name']} ({tx['token_symbol']})")
            print(f"Type: {tx['type']}")
            print(f"Amount: {tx['amount']}")
            print(f"Price: {tx['price']}")
            print(f"Timestamp: {datetime.fromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 40)
    
    # Test Base wallet
    print(f"\n=== TESTING BASE WALLET: {base_wallet} ===\n")
    base_txs = fetch_wallet_transactions(base_wallet, "base")
    
    print(f"Found {len(base_txs)} transactions for Base wallet")
    if base_txs:
        # Show some example transactions
        print("\nExample transactions:")
        for tx in base_txs[:3]:
            print(f"TX Hash: {tx['tx_hash']}")
            print(f"Token: {tx['token_name']} ({tx['token_symbol']})")
            print(f"Type: {tx['type']}")
            print(f"Amount: {tx['amount']}")
            print(f"Price: {tx['price']}")
            print(f"Timestamp: {datetime.fromtimestamp(tx['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 40)

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
    asyncio.run(test_wallet_analysis())
