#!/usr/bin/env python3
"""
Test script to verify live token resolution for THE PENGU KILLER token
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
from external_integrations.solana_rpc import get_token_name_and_symbol

def test_pengu_token_live():
    """
    Test the PENGU KILLER token resolution using direct RPC
    """
    # Target token address
    token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    
    print("\n===== TESTING PENGU KILLER TOKEN (LIVE RESOLUTION) =====\n")
    
    # 1. Test direct Solana RPC integration
    print("1. Testing direct Solana RPC integration:")
    name, symbol = get_token_name_and_symbol(token_address)
    print(f"   Name: {name}")
    print(f"   Symbol: {symbol}")
    
    # 2. Test the main token_finder function
    print("\n2. Testing token_finder module:")
    name, symbol = get_token_name(token_address, "solana")
    print(f"   Name: {name}")
    print(f"   Symbol: {symbol}")
    
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
    test_pengu_token_live()
