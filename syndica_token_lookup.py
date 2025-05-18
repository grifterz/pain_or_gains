#!/usr/bin/env python3

import requests
import json
import base64
import base58
from typing import Dict, Any, Optional

# The token address to look up
TOKEN_ADDRESS = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"

# Syndica API key placeholder (replace with actual key)
SYNDICA_API_KEY = "YOUR_API_KEY"

# Syndica endpoint
SYNDICA_ENDPOINT = f"https://solana-mainnet.api.syndica.io/api-key/{SYNDICA_API_KEY}"

def check_health():
    """Verify Syndica connection is working"""
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "getHealth"
    }
    
    try:
        response = requests.post(SYNDICA_ENDPOINT, json=payload)
        print(f"Health check - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Health response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"Health check error: {str(e)}")
        return False

def get_token_info(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get token information using Syndica
    """
    try:
        # Get account info
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
        
        response = requests.post(SYNDICA_ENDPOINT, json=payload)
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
    Try to get token metadata using Metaplex metadata program via Syndica
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
        
        response = requests.post(SYNDICA_ENDPOINT, json=payload)
        print(f"\nMetadata lookup - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"]:
                print(f"Found metadata accounts: {len(data['result'])}")
                
                for account in data["result"]:
                    if "account" in account and "data" in account["account"]:
                        encoded_data = account["account"]["data"][0]
                        try:
                            # Decode the base64 data
                            binary_data = base64.b64decode(encoded_data)
                            print(f"Binary data length: {len(binary_data)} bytes")
                            
                            # Parse Metaplex metadata
                            # Byte 0: Metaplex metadata version (1 byte)
                            # Byte 1: Update authority enabled (1 byte)
                            # Bytes 2-33: Update authority (32 bytes)
                            # Bytes 34-65: Mint key (32 bytes)
                            # Bytes 66-97: Name (variable length, prefixed with 4-byte string length)
                            # After name: Symbol (variable length, prefixed with 4-byte string length)
                            # After symbol: URI (variable length, prefixed with 4-byte string length)
                            
                            if len(binary_data) < 70:
                                print("Metadata binary data too short")
                                continue
                            
                            # Get name length (4 bytes, little-endian)
                            name_len = int.from_bytes(binary_data[66:70], byteorder='little')
                            if 70 + name_len > len(binary_data):
                                print(f"Invalid name length: {name_len}")
                                continue
                            
                            # Extract name
                            name = binary_data[70:70+name_len].decode('utf-8').strip()
                            
                            # Get symbol length (4 bytes, little-endian)
                            symbol_offset = 70 + name_len
                            symbol_len = int.from_bytes(binary_data[symbol_offset:symbol_offset+4], byteorder='little')
                            if symbol_offset + 4 + symbol_len > len(binary_data):
                                print(f"Invalid symbol length: {symbol_len}")
                                continue
                            
                            # Extract symbol
                            symbol = binary_data[symbol_offset+4:symbol_offset+4+symbol_len].decode('utf-8').strip()
                            
                            print(f"Extracted name: {name}, symbol: {symbol}")
                            return {
                                "name": name,
                                "symbol": symbol
                            }
                        except Exception as parse_error:
                            print(f"Error parsing metadata: {str(parse_error)}")
                
                print("Failed to parse metadata from any account")
            else:
                print("No metadata accounts found")
        else:
            print(f"API error: {response.text}")
    
    except Exception as e:
        print(f"Error getting metadata: {str(e)}")
    
    return None

# Check if we need to update the API key first
print("NOTE: Before running this script, make sure to replace YOUR_API_KEY with a valid Syndica API key!")
print("      Edit the file to update the SYNDICA_API_KEY variable.")

# Only continue if the API key has been updated
if SYNDICA_API_KEY == "YOUR_API_KEY":
    print("\nPlease update the SYNDICA_API_KEY before running this script.")
    print("Exiting without making any API calls.")
    exit(1)

# Execute the lookup
print("\n=== SOLANA TOKEN LOOKUP USING SYNDICA API ===")
print(f"Token address: {TOKEN_ADDRESS}")

# Check API health first
if not check_health():
    print("Syndica API health check failed. Please check your API key and try again.")
    exit(1)

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
    print("Could not determine token information")

print("=========================================\n")
