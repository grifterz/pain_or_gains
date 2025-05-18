#!/usr/bin/env python3
"""
Comprehensive test script for token name resolution
"""
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import the token_finder
from token_finder import get_token_name
from external_integrations.syndica_integration import get_pump_token_info

def test_solana_pump_tokens():
    """
    Test all known pump tokens
    """
    print("\n=== TESTING SOLANA PUMP TOKENS ===")
    
    # Get all pump tokens from the hardcoded list
    pump_tokens = get_pump_token_info()
    
    for token_address, token_info in pump_tokens.items():
        expected_name = token_info["name"]
        expected_symbol = token_info["symbol"]
        
        # Test name resolution
        name, symbol = get_token_name(token_address, "solana")
        
        # Check if it matches expected values
        if name == expected_name and symbol == expected_symbol:
            result = "✅ PASS"
        else:
            result = "❌ FAIL"
        
        print(f"{result} {token_address}: got={name} ({symbol}), expected={expected_name} ({expected_symbol})")

def test_base_tokens():
    """
    Test Base blockchain tokens
    """
    print("\n=== TESTING BASE TOKENS ===")
    
    base_tokens = [
        "0xe1abd004250ac8d1f199421d647e01d094faa180",  # Roost
        "0xcaa6d4049e667ffd88457a1733d255eed02996bb",  # Memecoin
        "0x692c1564c82e6a3509ee189d1b666df9a309b420",  # Based
        "0xc53fc22033a4bcb15b5405c38e67e378c960ee6b"   # Degen
    ]
    
    for token_address in base_tokens:
        # Test name resolution
        name, symbol = get_token_name(token_address, "base")
        print(f"{token_address}: name={name}, symbol={symbol}")

def test_specific_token(token_address, blockchain):
    """
    Test a specific token
    """
    print(f"\n=== TESTING SPECIFIC TOKEN: {token_address} on {blockchain} ===")
    
    # Test name resolution
    name, symbol = get_token_name(token_address, blockchain)
    print(f"Token Name: {name}")
    print(f"Token Symbol: {symbol}")

if __name__ == "__main__":
    # Test all pump tokens
    test_solana_pump_tokens()
    
    # Test base tokens
    test_base_tokens()
    
    # Test a specific token if provided as command-line argument
    if len(sys.argv) > 2:
        token_address = sys.argv[1]
        blockchain = sys.argv[2]
        test_specific_token(token_address, blockchain)
