#!/usr/bin/env python3
"""
Test script to verify token name resolution using only Solana RPC
"""
import sys
import os
import logging
import json
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our token modules
from token_finder import get_token_name
from external_integrations.solana_rpc import (
    get_token_name_and_symbol,
    get_token_metadata_account,
    get_account_info,
    get_token_info
)

def get_token_metadata_via_helius(token_address):
    """
    Directly query Helius or another public RPC to get token metadata
    """
    # Using a public API key for demonstration - replace with your own for production
    url = "https://api.mainnet-beta.solana.com"
    
    # First get the Metaplex metadata PDA
    try:
        # Metaplex metadata program ID
        metadata_program_id = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        
        # Get program accounts
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getProgramAccounts",
            "params": [
                metadata_program_id,
                {
                    "encoding": "base64",
                    "filters": [
                        {
                            "memcmp": {
                                "offset": 33,
                                "bytes": token_address
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return None

def test_token_address(token_address):
    """
    Test token resolution using different methods
    """
    print(f"\n===== TESTING PURE RPC RESOLUTION FOR {token_address} =====\n")
    
    # 1. Test direct token_finder function
    print("\n1. Using token_finder.get_token_name:")
    name, symbol = get_token_name(token_address, "solana")
    print(f"   Name: {name}")
    print(f"   Symbol: {symbol}")
    
    # 2. Test Solana RPC directly
    print("\n2. Using direct Solana RPC:")
    rpc_name, rpc_symbol = get_token_name_and_symbol(token_address)
    print(f"   Name: {rpc_name}")
    print(f"   Symbol: {rpc_symbol}")
    
    # 3. Test Metaplex metadata parsing
    print("\n3. Testing Metaplex metadata parsing:")
    metadata = get_token_metadata_account(token_address)
    if metadata:
        print(f"   Metadata: {json.dumps(metadata, indent=2)}")
    else:
        print("   No metadata found")
    
    # 4. Test basic token info
    print("\n4. Testing basic token info:")
    token_info = get_token_info(token_address)
    if token_info:
        print(f"   Token info: {json.dumps(token_info, indent=2)}")
    else:
        print("   No token info found")
    
    # 5. Try Helius API directly
    print("\n5. Testing with public Solana RPC:")
    helius_data = get_token_metadata_via_helius(token_address)
    if helius_data:
        print(f"   Found {len(helius_data.get('result', []))} metadata accounts")
    else:
        print("   No metadata found")
    
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
    
    # Test the specific token
    token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    test_token_address(token_address)
