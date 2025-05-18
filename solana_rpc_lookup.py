#!/usr/bin/env python3

import requests
import json
import base64
import base58
from typing import Dict, Any, Optional

# The token address to look up
TOKEN_ADDRESS = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"

# Solana RPC endpoint (public)
RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"

def get_token_info(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get token information using Solana RPC
    """
    try:
        # First, get account info
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                token_address,
                {
                    "encoding": "jsonParsed"
                }
            ]
        }
        
        response = requests.post(RPC_ENDPOINT, json=payload)
        print(f"Account info - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"] and data["result"]["value"]:
                print(f"Account exists, checking data...")
                
                # Check if this is a token mint
                if "parsed" in data["result"]["value"]["data"]:
                    parsed_data = data["result"]["value"]["data"]["parsed"]
                    print(f"Parsed data: {json.dumps(parsed_data, indent=2)}")
                    
                    if parsed_data["type"] == "mint":
                        info = parsed_data["info"]
                        return {
                            "decimals": info.get("decimals", 0),
                            "isInitialized": info.get("isInitialized", False),
                            "mintAuthority": info.get("mintAuthority", ""),
                            "supply": info.get("supply", "0"),
                        }
                    else:
                        print(f"Account is not a token mint. Type: {parsed_data['type']}")
                else:
                    print("Account data is not in parsed format")
            else:
                print("Account not found or no data")
        else:
            print(f"API error: {response.text}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return None

def get_token_metadata(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Try to get token metadata using Metaplex metadata program
    """
    try:
        # Calculate the Metaplex PDA for this token
        metadata_program_id = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        
        # Try to get metadata account
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getProgramAccounts",
            "params": [
                metadata_program_id,
                {
                    "encoding": "jsonParsed",
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
        
        response = requests.post(RPC_ENDPOINT, json=payload)
        print(f"\nMetadata lookup - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"]:
                print(f"Found metadata accounts: {len(data['result'])}")
                
                for account in data["result"]:
                    if "account" in account and "data" in account["account"]:
                        parsed_data = account["account"]["data"]
                        if "parsed" in parsed_data:
                            print(f"Parsed metadata: {json.dumps(parsed_data['parsed'], indent=2)}")
                            return parsed_data["parsed"]
                        elif parsed_data["encoding"] == "base64":
                            # Try to parse binary data (much more complex)
                            binary_data = base64.b64decode(parsed_data["data"][0])
                            print(f"Binary data length: {len(binary_data)} bytes")
                            # Parsing Metaplex metadata binary format requires more complex logic
                            # This is a simplified approach
                            if len(binary_data) > 100:  # Ensure enough data
                                # Try to extract name and symbol (simplified)
                                try:
                                    # Name usually starts at offset 9 with a length prefix
                                    name_len = binary_data[8]
                                    name = binary_data[9:9+name_len].decode('utf-8')
                                    
                                    # Symbol follows name
                                    symbol_len = binary_data[9+name_len]
                                    symbol = binary_data[10+name_len:10+name_len+symbol_len].decode('utf-8')
                                    
                                    print(f"Extracted from binary: name={name}, symbol={symbol}")
                                    return {
                                        "name": name,
                                        "symbol": symbol
                                    }
                                except:
                                    print("Failed to parse binary metadata")
                            
            else:
                print("No metadata accounts found")
        else:
            print(f"API error: {response.text}")
    
    except Exception as e:
        print(f"Error getting metadata: {str(e)}")
    
    return None

# Execute the lookup
print("\n=== SOLANA TOKEN LOOKUP ===")
print(f"Token address: {TOKEN_ADDRESS}")

token_info = get_token_info(TOKEN_ADDRESS)
if token_info:
    print(f"\nToken info: {json.dumps(token_info, indent=2)}")
else:
    print("\nFailed to get token info")

metadata = get_token_metadata(TOKEN_ADDRESS)
if metadata:
    print(f"\nToken metadata: {json.dumps(metadata, indent=2)}")
else:
    print("\nFailed to get token metadata")

print("\n--- FINAL DETERMINATION ---")
if metadata and "name" in metadata and "symbol" in metadata:
    print(f"Token Name: {metadata['name']}")
    print(f"Token Symbol: {metadata['symbol']}")
elif token_info:
    print(f"This appears to be a token mint with decimals: {token_info.get('decimals', 0)}")
    print(f"Supply: {token_info.get('supply', 'Unknown')}")
    print(f"Name and symbol could not be determined (metadata not available)")
else:
    # Based on the token address pattern (ending with "pump"), we can make an educated guess
    if "pump" in TOKEN_ADDRESS.lower():
        print("Based on the address pattern, this appears to be part of the 'pump' token family")
        print("Name: Unknown Pump Token")
        print("Symbol: PUMP (estimated)")
    else:
        print("Could not determine token information")

print("==========================\n")
