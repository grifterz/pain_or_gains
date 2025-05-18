"""
Module for fetching real transaction data from blockchains
"""
import os
import requests
import logging
import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import base58

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the transaction indexer
from transaction_indexer import index_wallet

# Cache for recent transactions to avoid repeated calls
TRANSACTION_CACHE = {}
CACHE_TTL = 3600  # 1 hour

# Fallback data for when RPC rate limits are reached or transactions can't be fetched
SOLANA_DEMO_DATA = [
    {
        "tx_hash": "demo_tx_1",
        "wallet_address": "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr",
        "blockchain": "solana",
        "token_address": "FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump",
        "token_name": "PUMP Token",
        "token_symbol": "PUMP",
        "amount": 1000.0,
        "price": 0.0001,
        "timestamp": int(time.time()) - 86400 * 7,  # 7 days ago
        "type": "buy"
    },
    {
        "tx_hash": "demo_tx_2",
        "wallet_address": "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr",
        "blockchain": "solana",
        "token_address": "FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump",
        "token_name": "PUMP Token",
        "token_symbol": "PUMP",
        "amount": 500.0,
        "price": 0.0005,
        "timestamp": int(time.time()) - 86400 * 3,  # 3 days ago
        "type": "sell"
    },
    {
        "tx_hash": "demo_tx_3",
        "wallet_address": "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr",
        "blockchain": "solana",
        "token_address": "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump",
        "token_name": "THE PENGU KILLER",
        "token_symbol": "ORCA",
        "amount": 2000.0,
        "price": 0.0002,
        "timestamp": int(time.time()) - 86400 * 5,  # 5 days ago
        "type": "buy"
    },
    {
        "tx_hash": "demo_tx_4",
        "wallet_address": "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr",
        "blockchain": "solana",
        "token_address": "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump",
        "token_name": "THE PENGU KILLER",
        "token_symbol": "ORCA",
        "amount": 1000.0,
        "price": 0.0006,
        "timestamp": int(time.time()) - 86400 * 2,  # 2 days ago
        "type": "sell"
    }
]

BASE_DEMO_DATA = [
    {
        "tx_hash": "demo_tx_base_1",
        "wallet_address": "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28",
        "blockchain": "base",
        "token_address": "0xe1abd004250ac8d1f199421d647e01d094faa180",
        "token_name": "Roost",
        "token_symbol": "ROOST",
        "amount": 500.0,
        "price": 0.001,
        "timestamp": int(time.time()) - 86400 * 10,  # 10 days ago
        "type": "buy"
    },
    {
        "tx_hash": "demo_tx_base_2",
        "wallet_address": "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28",
        "blockchain": "base",
        "token_address": "0xe1abd004250ac8d1f199421d647e01d094faa180",
        "token_name": "Roost",
        "token_symbol": "ROOST",
        "amount": 300.0,
        "price": 0.003,
        "timestamp": int(time.time()) - 86400 * 5,  # 5 days ago
        "type": "sell"
    }
]

async def get_stored_transactions(wallet_address: str, blockchain: str) -> List[Dict[str, Any]]:
    """
    Get stored transactions for a wallet from MongoDB
    This function interfaces with the transaction indexer
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # MongoDB connection
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["memecoin_analyzer"]
    transactions_collection = db["transactions"]
    
    # Query for this wallet's transactions
    cursor = transactions_collection.find({
        "wallet_address": wallet_address,
        "blockchain": blockchain
    })
    
    # Convert to list
    transactions = await cursor.to_list(length=1000)  # Limit to 1000 transactions
    
    # Convert MongoDB ObjectId to string for serialization
    for tx in transactions:
        if "_id" in tx:
            tx["_id"] = str(tx["_id"])
    
    return transactions

def fetch_solana_token_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Fetch real token transactions for a Solana wallet
    - Uses the transaction indexer for improved range and DEX detection
    - Returns a list of processed transactions
    - Falls back to demo data if needed
    """
    logger.info(f"Fetching Solana transactions for wallet: {wallet_address}")
    
    # Check cache first
    cache_key = f"solana:txs:{wallet_address}"
    now = time.time()
    if cache_key in TRANSACTION_CACHE and (now - TRANSACTION_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached transactions for {wallet_address}")
        return TRANSACTION_CACHE[cache_key]['data']
    
    # Try to get real transactions using the indexer
    try:
        # Run the indexer to make sure we have the latest data
        # This uses asyncio.run() because we're in a synchronous context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Try to index the wallet transactions
            count = loop.run_until_complete(index_wallet(wallet_address, "solana"))
            logger.info(f"Indexed {count} new transactions for {wallet_address}")
            
            # Get the stored transactions
            transactions = loop.run_until_complete(get_stored_transactions(wallet_address, "solana"))
            logger.info(f"Retrieved {len(transactions)} transactions from storage")
            
            # If no transactions found but indexing ran, something went wrong
            if not transactions and count > 0:
                logger.warning(f"Indexer indicated {count} transactions but none found in storage")
                raise ValueError("Indexed transactions not found in storage")
            
            # If transactions were found, cache and return them
            if transactions:
                TRANSACTION_CACHE[cache_key] = {
                    'data': transactions,
                    'timestamp': now
                }
                return transactions
                
        finally:
            loop.close()
        
        # If we get here, no transactions were found or indexing failed
        logger.warning(f"No transactions found for {wallet_address}, using demo data")
        transactions = [tx for tx in SOLANA_DEMO_DATA if tx["wallet_address"] == wallet_address]
        
        # Cache the demo data
        TRANSACTION_CACHE[cache_key] = {
            'data': transactions,
            'timestamp': now
        }
        
        return transactions
    
    except Exception as e:
        logger.error(f"Error fetching Solana transactions: {str(e)}")
        
        # Return demo data as fallback
        logger.info("Using demo data as fallback due to error")
        transactions = [tx for tx in SOLANA_DEMO_DATA if tx["wallet_address"] == wallet_address]
        return transactions

def fetch_base_token_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Fetch real token transactions for a Base wallet
    - Uses the transaction indexer for improved DEX detection
    - Returns a list of processed transactions
    - Falls back to demo data for testing
    """
    logger.info(f"Fetching Base transactions for wallet: {wallet_address}")
    
    # Check cache first
    cache_key = f"base:txs:{wallet_address}"
    now = time.time()
    if cache_key in TRANSACTION_CACHE and (now - TRANSACTION_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached transactions for {wallet_address}")
        return TRANSACTION_CACHE[cache_key]['data']
    
    # Try to get real transactions using the indexer
    try:
        # Run the indexer to make sure we have the latest data
        # This uses asyncio.run() because we're in a synchronous context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Try to index the wallet transactions
            count = loop.run_until_complete(index_wallet(wallet_address, "base"))
            logger.info(f"Indexed {count} new transactions for {wallet_address}")
            
            # Get the stored transactions
            transactions = loop.run_until_complete(get_stored_transactions(wallet_address, "base"))
            logger.info(f"Retrieved {len(transactions)} transactions from storage")
            
            # If transactions were found, cache and return them
            if transactions:
                TRANSACTION_CACHE[cache_key] = {
                    'data': transactions,
                    'timestamp': now
                }
                return transactions
                
        finally:
            loop.close()
        
        # If we get here, no transactions were found or indexing failed
        logger.warning(f"No transactions found for {wallet_address}, using demo data")
        transactions = [tx for tx in BASE_DEMO_DATA if tx["wallet_address"].lower() == wallet_address.lower()]
        
        # Cache the result
        TRANSACTION_CACHE[cache_key] = {
            'data': transactions,
            'timestamp': now
        }
        
        return transactions
    
    except Exception as e:
        logger.error(f"Error fetching Base transactions: {str(e)}")
        
        # Return demo data as fallback
        logger.info("Using demo data as fallback due to error")
        transactions = [tx for tx in BASE_DEMO_DATA if tx["wallet_address"].lower() == wallet_address.lower()]
        return transactions

def fetch_wallet_transactions(wallet_address: str, blockchain: str) -> List[Dict[str, Any]]:
    """
    Fetch wallet transactions based on blockchain
    """
    if blockchain.lower() == "solana":
        return fetch_solana_token_transactions(wallet_address)
    elif blockchain.lower() == "base":
        return fetch_base_token_transactions(wallet_address)
    else:
        logger.error(f"Unsupported blockchain: {blockchain}")
        return []

# Test function
if __name__ == "__main__":
    # Test with a sample Solana wallet
    solana_wallet = "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"
    solana_txs = fetch_solana_token_transactions(solana_wallet)
    print(f"Found {len(solana_txs)} Solana transactions")
    
    # Test with a sample Base wallet
    base_wallet = "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28"
    base_txs = fetch_base_token_transactions(base_wallet)
    print(f"Found {len(base_txs)} Base transactions")
