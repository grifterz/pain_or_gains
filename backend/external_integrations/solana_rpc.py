"""
Direct Solana RPC integration for token metadata resolution
"""
import requests
import base64
import logging
import json
import os
import time
import base58
import binascii
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for token info to reduce API calls
TOKEN_CACHE = {}
CACHE_TTL = 3600  # 1 hour in seconds

def get_solana_rpc_endpoint():
    """
    Get the Solana RPC endpoint with API key if available
    """
    # Default public endpoint as a fallback
    DEFAULT_ENDPOINT = "https://api.mainnet-beta.solana.com"
    
    # Try to get Syndica API key from environment
    syndica_api_key = os.environ.get("SOLANA_API_KEY", "")
    if syndica_api_key:
        return f"https://solana-mainnet.api.syndica.io/api-key/{syndica_api_key}"
    
    # Use Helius RPC if available (better rate limits than public endpoint)
    helius_api_key = os.environ.get("HELIUS_API_KEY", "")
    if helius_api_key:
        return f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    
    # Default fallback to public endpoint
    return DEFAULT_ENDPOINT

def get_account_info(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get account info from Solana RPC
    """
    endpoint = get_solana_rpc_endpoint()
    
    # Check cache first
    cache_key = f"solana_rpc:account:{token_address}"
    now = time.time()
    if cache_key in TOKEN_CACHE and (now - TOKEN_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached account info for {token_address}")
        return TOKEN_CACHE[cache_key]['data']
    
    try:
        # Prepare RPC request
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
        
        # Make request
        logger.info(f"Getting account info for {token_address}")
        response = requests.post(endpoint, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result and result["result"] and result["result"]["value"]:
                account_info = result["result"]["value"]
                
                # Cache the result
                TOKEN_CACHE[cache_key] = {
                    'data': account_info,
                    'timestamp': now
                }
                
                return account_info
            else:
                logger.warning(f"Account not found or no data for {token_address}")
        else:
            logger.warning(f"RPC request failed with status {response.status_code}: {response.text}")
    
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
    
    return None

def get_token_metadata_pda(token_address: str) -> Optional[str]:
    """
    Calculate the Metaplex metadata PDA address for a token
    """
    try:
        # Metaplex metadata program ID
        metadata_program_id = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        
        # Seeds for the PDA
        seeds = [
            b"metadata",
            bytes(metadata_program_id, 'utf-8'),
            base58.b58decode(token_address)
        ]
        
        # Calculate metadata address
        metadata_address, _bump = _find_program_address(seeds, metadata_program_id)
        return metadata_address
    
    except Exception as e:
        logger.error(f"Error calculating metadata PDA: {str(e)}")
        return None

def _find_program_address(seeds, program_id):
    """
    Find a program derived address
    Note: This is a simplified version; in production you'd use the solana-py library
    """
    nonce = 255
    while nonce > 0:
        try:
            # Concatenate all seeds with nonce byte
            all_seeds = []
            for seed in seeds:
                all_seeds.extend(seed)
            all_seeds.append(nonce)
            
            # Create a buffer of the seed data
            seed_bytes = bytes(all_seeds)
            
            # Calculate the address using sha256(seeds || program_id)
            # Note: This is a simplified algorithm, solana-py does this correctly
            address = "placeholder"  # Would be calculated from seed_bytes and program_id
            
            return address, nonce
        except Exception as e:
            nonce -= 1
    
    raise ValueError("Unable to find a valid program address")

def get_token_metadata_account(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get token metadata account from Solana RPC
    """
    endpoint = get_solana_rpc_endpoint()
    
    # Check cache first
    cache_key = f"solana_rpc:metadata:{token_address}"
    now = time.time()
    if cache_key in TOKEN_CACHE and (now - TOKEN_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached metadata for {token_address}")
        return TOKEN_CACHE[cache_key]['data']
    
    try:
        # Metaplex metadata program ID
        metadata_program_id = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
        
        # Prepare RPC request to find metadata accounts
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
        
        # Make request
        logger.info(f"Getting metadata accounts for {token_address}")
        response = requests.post(endpoint, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result and result["result"]:
                # Process metadata accounts
                for account in result["result"]:
                    if "account" in account and "data" in account["account"]:
                        encoded_data = account["account"]["data"][0]
                        try:
                            # Decode base64 data
                            binary_data = base64.b64decode(encoded_data)
                            
                            # Parse the binary data (Metaplex metadata layout)
                            if len(binary_data) < 70:
                                logger.warning("Metadata binary data too short")
                                continue
                            
                            # Extract name
                            name_len = int.from_bytes(binary_data[66:70], byteorder='little')
                            if 70 + name_len > len(binary_data):
                                logger.warning(f"Invalid name length: {name_len}")
                                continue
                            
                            name = binary_data[70:70+name_len].decode('utf-8').strip()
                            
                            # Extract symbol
                            symbol_offset = 70 + name_len
                            symbol_len = int.from_bytes(binary_data[symbol_offset:symbol_offset+4], byteorder='little')
                            if symbol_offset + 4 + symbol_len > len(binary_data):
                                logger.warning(f"Invalid symbol length: {symbol_len}")
                                continue
                            
                            symbol = binary_data[symbol_offset+4:symbol_offset+4+symbol_len].decode('utf-8').strip()
                            
                            # Create metadata result
                            metadata = {
                                "name": name,
                                "symbol": symbol
                            }
                            
                            # Try to extract URI for additional metadata
                            try:
                                uri_offset = symbol_offset + 4 + symbol_len
                                uri_len = int.from_bytes(binary_data[uri_offset:uri_offset+4], byteorder='little')
                                if uri_offset + 4 + uri_len <= len(binary_data):
                                    uri = binary_data[uri_offset+4:uri_offset+4+uri_len].decode('utf-8').strip()
                                    metadata["uri"] = uri
                            except Exception as uri_err:
                                logger.warning(f"Error extracting metadata URI: {uri_err}")
                            
                            # Cache the result
                            TOKEN_CACHE[cache_key] = {
                                'data': metadata,
                                'timestamp': now
                            }
                            
                            return metadata
                        except Exception as e:
                            logger.error(f"Error parsing metadata: {str(e)}")
                
                logger.warning(f"No valid metadata found for {token_address}")
            else:
                logger.warning(f"No metadata accounts found for {token_address}")
        else:
            logger.warning(f"RPC request failed with status {response.status_code}: {response.text}")
    
    except Exception as e:
        logger.error(f"Error getting token metadata: {str(e)}")
    
    return None

def get_token_info(token_address: str) -> Optional[Dict[str, Any]]:
    """
    Get token information using Solana RPC
    """
    account_info = get_account_info(token_address)
    
    if account_info:
        try:
            # Check if this is a token mint account
            if account_info.get("data") and "parsed" in account_info["data"]:
                parsed_data = account_info["data"]["parsed"]
                
                if parsed_data.get("type") == "mint":
                    return {
                        "decimals": parsed_data["info"].get("decimals", 0),
                        "supply": parsed_data["info"].get("supply", "0")
                    }
        except Exception as e:
            logger.error(f"Error parsing token info: {str(e)}")
    
    return None

def get_token_name_and_symbol(token_address: str) -> Tuple[str, str]:
    """
    Get token name and symbol from Solana blockchain
    Returns a tuple of (name, symbol)
    """
    logger.info(f"Getting token name and symbol for {token_address}")
    
    # First try to get metadata
    metadata = get_token_metadata_account(token_address)
    if metadata and metadata.get("name") and metadata.get("symbol"):
        logger.info(f"Got metadata for {token_address}: {metadata}")
        return metadata["name"], metadata["symbol"]
    
    # If metadata is not found, try to get basic token info
    token_info = get_token_info(token_address)
    if token_info:
        logger.info(f"Got token info for {token_address}: {token_info}")
        # Just use the token address as a fallback
        return token_address[:10] + "...", token_address[:6]
    
    # Default fallback
    logger.warning(f"Could not get token info for {token_address}")
    return token_address[:10] + "...", token_address[:6]

# Test function
if __name__ == "__main__":
    token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    print(f"Testing with token address: {token_address}")
    
    name, symbol = get_token_name_and_symbol(token_address)
    print(f"Token Name: {name}")
    print(f"Token Symbol: {symbol}")
