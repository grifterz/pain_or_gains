"""
Helper module to create demo transactions for the memecoin analyzer
"""
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Known token addresses for our wallets
WALLET_TOKENS = {
    "0x671b746d2c5a34609cce723cbf8f475639bc0fa2": [
        "0xe1abd004250ac8d1f199421d647e01d094faa180",
        "0xcaa6d4049e667ffd88457a1733d255eed02996bb",
        "0x692c1564c82e6a3509ee189d1b666df9a309b420",
        "0xc53fc22033a4bcb15b5405c38e67e378c960ee6b"
    ],
    "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr": [
        "FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump",
        "3yCDp1E5yzA1qoNQuDjNr5iXyj1CSHjf3dktHpnypump",
        "56UtHy4oBGeLNEenvvXJhhAwDwhNc2bbZgAPUZaFpump",
        "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    ]
}

# Added more test wallet addresses
WALLET_TOKENS["0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28"] = [
    "0xe1abd004250ac8d1f199421d647e01d094faa180",
    "0xcaa6d4049e667ffd88457a1733d255eed02996bb"
]

WALLET_TOKENS["0x1a0A4e99A0E1D96887041497B6C846d8C21886E5"] = [
    "0x692c1564c82e6a3509ee189d1b666df9a309b420",
    "0xc53fc22033a4bcb15b5405c38e67e378c960ee6b"
]

WALLET_TOKENS["HN7cABqLq46Es1jh92dQQpRbDCu5Dt7RpkeU3YwjUG4e"] = [
    "FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump",
    "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
]

def create_synthetic_transactions(
    wallet_address: str,
    blockchain: str,
    token_info_func
) -> List[Dict[str, Any]]:
    """
    Create synthetic transactions for demonstration with CORRECT token names from token_info_func
    """
    transactions = []
    now = int(datetime.now().timestamp())
    token_addresses = WALLET_TOKENS.get(wallet_address, [])
    
    if not token_addresses:
        # Default tokens if wallet not recognized
        if blockchain == "solana":
            token_addresses = ["FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump", 
                             "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"]
        else:
            token_addresses = ["0xe1abd004250ac8d1f199421d647e01d094faa180",
                             "0xcaa6d4049e667ffd88457a1733d255eed02996bb"]
    
    # Create buy/sell pairs for each token
    for token_address in token_addresses:
        # Get real token name from blockchain explorer
        token_name, token_symbol = token_info_func(token_address, blockchain)
        logger.info(f"Using token {token_name} ({token_symbol}) for {token_address}")
        
        # Random amounts and prices
        base_amount = random.uniform(100, 10000)
        base_buy_price = random.uniform(0.0001, 0.001)
        multiplier = random.uniform(1.5, 5.0)
        sell_price = base_buy_price * multiplier
        
        # Buy transaction
        buy_timestamp = now - random.randint(7, 30) * 86400  # 7-30 days ago
        
        transactions.append({
            "tx_hash": f"synthetic-buy-{token_address}-{buy_timestamp}",
            "wallet_address": wallet_address,
            "token_address": token_address,
            "token_symbol": token_symbol,
            "token_name": token_name,
            "amount": base_amount,
            "price": base_buy_price,
            "timestamp": buy_timestamp,
            "type": "buy"
        })
        
        # Sell transaction - sell 50% of position
        sell_timestamp = buy_timestamp + random.randint(1, 7) * 86400  # 1-7 days after buy
        
        transactions.append({
            "tx_hash": f"synthetic-sell-{token_address}-{sell_timestamp}",
            "wallet_address": wallet_address,
            "token_address": token_address,
            "token_symbol": token_symbol,
            "token_name": token_name,
            "amount": base_amount * 0.5,
            "price": sell_price,
            "timestamp": sell_timestamp,
            "type": "sell"
        })
        
        # Maybe add another buy
        if random.random() > 0.5:
            second_buy_timestamp = sell_timestamp + random.randint(1, 3) * 86400
            second_buy_price = sell_price * random.uniform(0.7, 1.2)
            second_amount = base_amount * random.uniform(0.2, 0.8)
            
            transactions.append({
                "tx_hash": f"synthetic-buy2-{token_address}-{second_buy_timestamp}",
                "wallet_address": wallet_address,
                "token_address": token_address,
                "token_symbol": token_symbol,
                "token_name": token_name,
                "amount": second_amount,
                "price": second_buy_price,
                "timestamp": second_buy_timestamp,
                "type": "buy"
            })
    
    # Sort transactions by timestamp
    transactions.sort(key=lambda x: x["timestamp"])
    return transactions
