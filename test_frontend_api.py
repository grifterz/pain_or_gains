#!/usr/bin/env python3
"""
Test the frontend API calls to verify token name resolution
"""
import os
import sys
import requests
import json
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_backend_url():
    """
    Get the backend URL from frontend .env file
    """
    # Try to read from .env file
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    url = line.strip().split("=", 1)[1].strip('"\'')
                    return url
    
    # Fallback to localhost
    return "http://localhost:8001"

def test_wallet_api():
    """
    Test wallet API endpoints
    """
    print("\n=== TESTING WALLET API ===\n")
    
    # Get base URL
    base_url = get_backend_url()
    parsed_url = urlparse(base_url)
    
    # Ensure the path has /api prefix
    if not parsed_url.path.startswith("/api"):
        api_path = "/api"
    else:
        api_path = parsed_url.path
    
    # Test wallets
    test_wallets = {
        "solana": [
            "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr",
            "HN7cABqLq46Es1jh92dQQpRbDCu5Dt7RpkeU3YwjUG4e"
        ],
        "base": [
            "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28",
            "0x1a0A4e99A0E1D96887041497B6C846d8C21886E5"
        ]
    }
    
    for blockchain, wallets in test_wallets.items():
        for wallet in wallets:
            # Construct URL
            url = f"{base_url.rstrip('/')}{api_path}/wallet/{wallet}?blockchain={blockchain}"
            
            try:
                # Make request
                print(f"Testing: {url}")
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success! Got data for {blockchain} wallet {wallet}")
                    
                    # Check for token data
                    if "positions" in data and data["positions"]:
                        for pos in data["positions"]:
                            token_addr = pos.get("token_address", "")
                            token_name = pos.get("token_name", "")
                            token_symbol = pos.get("token_symbol", "")
                            print(f"   Token: {token_addr}")
                            print(f"   Name: {token_name}")
                            print(f"   Symbol: {token_symbol}")
                    else:
                        print("   No positions found")
                else:
                    print(f"❌ Failed with status {response.status_code}: {response.text}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")

def test_leaderboard_api():
    """
    Test leaderboard API endpoints
    """
    print("\n=== TESTING LEADERBOARD API ===\n")
    
    # Get base URL
    base_url = get_backend_url()
    parsed_url = urlparse(base_url)
    
    # Ensure the path has /api prefix
    if not parsed_url.path.startswith("/api"):
        api_path = "/api"
    else:
        api_path = parsed_url.path
    
    # Test metrics
    metrics = ["best_trade", "worst_trade", "best_multiplier", "all_time_pnl"]
    
    for blockchain in ["solana", "base"]:
        for metric in metrics:
            # Construct URL
            url = f"{base_url.rstrip('/')}{api_path}/leaderboard?blockchain={blockchain}&metric={metric}"
            
            try:
                # Make request
                print(f"Testing: {url}")
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success! Got {blockchain} leaderboard for {metric}")
                    
                    # Check first few results
                    for i, entry in enumerate(data[:3]):
                        wallet = entry.get("wallet", "")
                        token_addr = entry.get("token_address", "")
                        token_name = entry.get("token_name", "")
                        token_symbol = entry.get("token_symbol", "")
                        value = entry.get("value", 0)
                        
                        print(f"   #{i+1}: Wallet: {wallet}")
                        print(f"       Token: {token_addr}")
                        print(f"       Name: {token_name}")
                        print(f"       Symbol: {token_symbol}")
                        print(f"       Value: {value}")
                else:
                    print(f"❌ Failed with status {response.status_code}: {response.text}")
            
            except Exception as e:
                print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print(f"Testing API at {get_backend_url()}")
    
    test_wallet_api()
    test_leaderboard_api()
