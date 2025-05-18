#!/usr/bin/env python3
"""
Test script to verify the correct token name for the PENGU KILLER token
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our token modules
from token_finder import get_token_name
from external_integrations.syndica_integration import (
    get_token_name_and_symbol,
    get_pump_token_info,
    get_metadata_from_solscan
)

def test_pengu_token():
    """
    Test the PENGU KILLER token resolution
    """
    # Target token address
    token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    
    print("\n===== TESTING PENGU KILLER TOKEN =====\n")
    
    # 1. Check hardcoded fallback
    print("1. Checking hardcoded fallbacks:")
    pump_tokens = get_pump_token_info()
    if token_address in pump_tokens:
        fallback = pump_tokens[token_address]
        print(f"   Fallback name: {fallback['name']}")
        print(f"   Fallback symbol: {fallback['symbol']}")
    else:
        print("   No fallback found for this token")
    
    # 2. Check Solscan scraping
    print("\n2. Testing Solscan scraping:")
    solscan_data = get_metadata_from_solscan(token_address)
    if solscan_data:
        print(f"   Solscan name: {solscan_data.get('name', 'Not found')}")
        print(f"   Solscan symbol: {solscan_data.get('symbol', 'Not found')}")
    else:
        print("   Failed to get data from Solscan scraping")
    
    # 3. Test direct Syndica integration
    print("\n3. Testing Syndica integration:")
    syndica_name, syndica_symbol = get_token_name_and_symbol(token_address)
    print(f"   Syndica name: {syndica_name}")
    print(f"   Syndica symbol: {syndica_symbol}")
    
    # 4. Test the main token_finder function
    print("\n4. Testing token_finder module:")
    name, symbol = get_token_name(token_address, "solana")
    print(f"   Final name: {name}")
    print(f"   Final symbol: {symbol}")
    
    print("\n===== TEST COMPLETE =====")

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
    test_pengu_token()
