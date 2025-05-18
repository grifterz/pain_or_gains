#!/usr/bin/env python3
"""
Test script to verify the Syndica integration works correctly
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our Syndica integration
from external_integrations.syndica_integration import (
    check_health,
    get_token_info,
    get_token_metadata,
    get_token_name_and_symbol
)

# Import the updated token_finder
from token_finder import get_token_name

# The token address to test
TEST_TOKEN = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"

def test_syndica_direct():
    """
    Test the Syndica integration directly
    """
    print("\n=== TESTING SYNDICA INTEGRATION DIRECTLY ===")
    
    # Check Syndica API health
    print("\nChecking Syndica API health...")
    if check_health():
        print("✅ Syndica API connection is healthy")
    else:
        print("❌ Syndica API connection failed health check")
        return
    
    # Get token info
    print("\nGetting token info...")
    token_info = get_token_info(TEST_TOKEN)
    if token_info:
        print(f"✅ Token info found: {token_info}")
    else:
        print("❌ Failed to get token info")
    
    # Get token metadata
    print("\nGetting token metadata...")
    token_metadata = get_token_metadata(TEST_TOKEN)
    if token_metadata:
        print(f"✅ Token metadata found: {token_metadata}")
        print(f"   Name: {token_metadata.get('name')}")
        print(f"   Symbol: {token_metadata.get('symbol')}")
    else:
        print("❌ Failed to get token metadata")
    
    # Get token name and symbol (combined function)
    print("\nGetting token name and symbol...")
    name, symbol = get_token_name_and_symbol(TEST_TOKEN)
    print(f"✅ Name: {name}")
    print(f"✅ Symbol: {symbol}")

def test_token_finder():
    """
    Test the token_finder module with Syndica integration
    """
    print("\n=== TESTING TOKEN_FINDER MODULE WITH SYNDICA ===")
    
    # Use the token_finder to get token name and symbol
    print(f"\nGetting token name and symbol for {TEST_TOKEN}...")
    name, symbol = get_token_name(TEST_TOKEN, "solana")
    print(f"✅ Token Name: {name}")
    print(f"✅ Token Symbol: {symbol}")

if __name__ == "__main__":
    # Make sure environment variable is set
    if not os.environ.get("SOLANA_API_KEY"):
        api_key = os.environ.get("SOLANA_API_KEY", "")
        print(f"⚠️ Warning: SOLANA_API_KEY environment variable may not be set correctly.")
        print(f"   Current value: {api_key if api_key else 'Not set'}")
        
        # Load from .env file
        print("   Trying to load from .env file...")
        env_path = "/app/backend/.env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("SOLANA_API_KEY="):
                        key = line.strip().split("=", 1)[1]
                        if key:
                            os.environ["SOLANA_API_KEY"] = key.strip('"\'')
                            print(f"   Loaded API key from .env file")
    
    # Run the tests
    test_syndica_direct()
    test_token_finder()
