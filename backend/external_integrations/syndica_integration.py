"""
Syndica RPC Integration for Solana token metadata resolution
"""
import requests
import base64
import logging
import json
import os
import time
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for token info to reduce API calls
TOKEN_CACHE = {}
CACHE_TTL = 3600  # 1 hour in seconds

def get_syndica_endpoint():
    """
    Get the Syndica RPC endpoint URL with API key
    """
    # Get API key from environment variable
    syndica_api_key = os.environ.get("SOLANA_API_KEY", "")
    
    if not syndica_api_key:
        logger.warning("No Syndica API key found in environment variables")
        return None
        
    # Construct the Syndica endpoint
    return f"https://solana-mainnet.api.syndica.io/api-key/{syndica_api_key}"

def check_health() -> bool:
    """
    Verify Syndica connection is working
    """
    endpoint = get_syndica_endpoint()
    if not endpoint:
        logger.error("Cannot check Syndica health: No API endpoint available")
        return False
        
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "getHealth"
    }
    
    try:
        response = requests.post(endpoint, json=payload)
        logger.info(f"Syndica health check - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Syndica health response: {data}")
            return True
        else:
            logger.warning(f"Syndica health check failed: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Syndica health check error: {str(e)}")
        return False

def get_token_info(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get token information using Syndica RPC
    """
    endpoint = get_syndica_endpoint()
    if not endpoint:
        logger.error("Cannot get token info: No Syndica API endpoint available")
        return None
        
    # Check cache first
    cache_key = f"syndica:token_info:{token_address}"
    now = time.time()
    if cache_key in TOKEN_CACHE and (now - TOKEN_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached token info for {token_address}")
        return TOKEN_CACHE[cache_key]['data']
    
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
        
        response = requests.post(endpoint, json=payload)
        logger.info(f"Syndica account info - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"] and data["result"]["value"]:
                logger.info(f"Syndica account exists, checking data...")
                
                # Check if this is a token mint
                if "parsed" in data["result"]["value"]["data"]:
                    parsed_data = data["result"]["value"]["data"]["parsed"]
                    
                    if parsed_data["type"] == "mint":
                        info = parsed_data["info"]
                        token_info = {
                            "decimals": info.get("decimals", 0),
                            "isInitialized": info.get("isInitialized", False),
                            "mintAuthority": info.get("mintAuthority", ""),
                            "supply": info.get("supply", "0"),
                        }
                        
                        # Cache the result
                        TOKEN_CACHE[cache_key] = {
                            'data': token_info,
                            'timestamp': now
                        }
                        
                        return token_info
                    else:
                        logger.warning(f"Account is not a token mint. Type: {parsed_data['type']}")
                else:
                    logger.warning("Account data is not in parsed format")
            else:
                logger.warning("Syndica account not found or no data")
        else:
            logger.warning(f"Syndica API error: {response.text}")
    
    except Exception as e:
        logger.error(f"Error getting token info from Syndica: {str(e)}")
    
    return None

def get_token_metadata(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get token metadata using Metaplex metadata program via Syndica
    """
    endpoint = get_syndica_endpoint()
    if not endpoint:
        logger.error("Cannot get token metadata: No Syndica API endpoint available")
        return None
    
    # Check cache first
    cache_key = f"syndica:token_metadata:{token_address}"
    now = time.time()
    if cache_key in TOKEN_CACHE and (now - TOKEN_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached token metadata for {token_address}")
        return TOKEN_CACHE[cache_key]['data']
    
    try:
        # Metaplex metadata program ID
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
        
        response = requests.post(endpoint, json=payload)
        logger.info(f"Syndica metadata lookup - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"]:
                logger.info(f"Found metadata accounts: {len(data['result'])}")
                
                for account in data["result"]:
                    if "account" in account and "data" in account["account"]:
                        encoded_data = account["account"]["data"][0]
                        try:
                            # Decode the base64 data
                            binary_data = base64.b64decode(encoded_data)
                            logger.info(f"Binary data length: {len(binary_data)} bytes")
                            
                            # Parse Metaplex metadata
                            if len(binary_data) < 70:
                                logger.warning("Metadata binary data too short")
                                continue
                            
                            # Get name length (4 bytes, little-endian)
                            name_len = int.from_bytes(binary_data[66:70], byteorder='little')
                            if 70 + name_len > len(binary_data):
                                logger.warning(f"Invalid name length: {name_len}")
                                continue
                            
                            # Extract name
                            name = binary_data[70:70+name_len].decode('utf-8').strip()
                            
                            # Get symbol length (4 bytes, little-endian)
                            symbol_offset = 70 + name_len
                            symbol_len = int.from_bytes(binary_data[symbol_offset:symbol_offset+4], byteorder='little')
                            if symbol_offset + 4 + symbol_len > len(binary_data):
                                logger.warning(f"Invalid symbol length: {symbol_len}")
                                continue
                            
                            # Extract symbol
                            symbol = binary_data[symbol_offset+4:symbol_offset+4+symbol_len].decode('utf-8').strip()
                            
                            logger.info(f"Extracted name: {name}, symbol: {symbol}")
                            metadata = {
                                "name": name,
                                "symbol": symbol
                            }
                            
                            # Cache the result
                            TOKEN_CACHE[cache_key] = {
                                'data': metadata,
                                'timestamp': now
                            }
                            
                            return metadata
                        except Exception as parse_error:
                            logger.error(f"Error parsing metadata: {str(parse_error)}")
                
                logger.warning("Failed to parse metadata from any account")
            else:
                logger.warning("No metadata accounts found")
        else:
            logger.warning(f"Syndica API error: {response.text}")
    
    except Exception as e:
        logger.error(f"Error getting metadata from Syndica: {str(e)}")
    
    return None

def get_token_name_and_symbol(token_address: str) -> Tuple[str, str]:
    """
    Get token name and symbol using Syndica RPC
    Returns a tuple of (name, symbol)
    """
    logger.info(f"Getting token name and symbol for {token_address} using Syndica")
    
    # First try to get metadata (includes name and symbol)
    metadata = get_token_metadata(token_address)
    if metadata and metadata.get("name") and metadata.get("symbol"):
        logger.info(f"Found token metadata: {metadata}")
        return metadata["name"], metadata["symbol"]
    
    # If metadata is not available, try to get basic token info
    token_info = get_token_info(token_address)
    if token_info:
        logger.info(f"Found basic token info: {token_info}")
        # We only have decimals and supply, so use token address as fallback
        return token_address[:10] + "...", token_address[:6]
    
    # Default fallback
    logger.warning(f"Could not get token info for {token_address}")
    return token_address[:10] + "...", token_address[:6]

# Test function
if __name__ == "__main__":
    token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    print(f"Testing Syndica integration with token: {token_address}")
    
    if check_health():
        print("Syndica API connection is healthy")
        
        name, symbol = get_token_name_and_symbol(token_address)
        print(f"Token Name: {name}")
        print(f"Token Symbol: {symbol}")
    else:
        print("Syndica API connection failed health check")
