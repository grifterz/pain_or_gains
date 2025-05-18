"""
Token finder module that retrieves real token names from blockchain explorers
"""
import requests
import re
import logging
import json
import time
import os
import sys
from typing import Tuple, Dict, Any, Optional

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our Syndica integration
from external_integrations.syndica_integration import get_token_name_and_symbol as syndica_get_token_name

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for API endpoints
SOLSCAN_API = "https://public-api.solscan.io"
SOLSCAN_API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NDc1OTMxODMyMzAsImVtYWlsIjoicGlrZWRhcnJlbjcxMEBnbWFpbC5jb20iLCJhY3Rpb24iOiJ0b2tlbi1hcGkiLCJhcGlWZXJzaW9uIjoidjIiLCJpYXQiOjE3NDc1OTMxODN9.H3_JHdgBk25jDpM8JEBzKhXURa3he49xU-eKpQMyomk"
BASESCAN_API = "https://api.basescan.org"
BASESCAN_API_KEY = "CQYEHTMRFY24DXPFGIWUYBFYGSYJH1V1EZ"  # Example API key

# Cache for token info to reduce API calls
TOKEN_CACHE = {}
CACHE_TTL = 3600  # 1 hour in seconds

# Fallback token info for specific addresses - only used if API calls fail
BASE_TOKEN_FALLBACKS = {
    "0xe1abd004250ac8d1f199421d647e01d094faa180": {"name": "Roost", "symbol": "ROOST"},
    "0xcaa6d4049e667ffd88457a1733d255eed02996bb": {"name": "Memecoin", "symbol": "MEME"},
    "0x692c1564c82e6a3509ee189d1b666df9a309b420": {"name": "Based", "symbol": "BASED"},
    "0xc53fc22033a4bcb15b5405c38e67e378c960ee6b": {"name": "Degen", "symbol": "DEGEN"}
}

def get_solana_token_info(token_address) -> Dict[str, Any]:
    """
    Fetch Solana token info from Solscan API using the provided API token
    """
    # Check cache first
    cache_key = f"solana:{token_address}"
    now = time.time()
    if cache_key in TOKEN_CACHE and (now - TOKEN_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached info for {token_address}")
        return TOKEN_CACHE[cache_key]['data']
    
    try:
        # Use authenticated Solscan API
        url = f"{SOLSCAN_API}/token/meta?tokenAddress={token_address}"
        headers = {
            "accept": "application/json",
            "token": SOLSCAN_API_TOKEN
        }
        
        logger.info(f"Fetching Solana token info with API token for {token_address}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"API response for {token_address}: {data}")
            
            if data:
                name = data.get("name", "")
                symbol = data.get("symbol", "")
                decimals = data.get("decimals", 9)
                
                if name or symbol:
                    token_info = {
                        "name": name if name else symbol,
                        "symbol": symbol if symbol else name,
                        "decimals": decimals
                    }
                    
                    # Cache the result
                    TOKEN_CACHE[cache_key] = {
                        'data': token_info,
                        'timestamp': now
                    }
                    
                    logger.info(f"Successfully fetched info for {token_address}: name={name}, symbol={symbol}")
                    return token_info
                else:
                    logger.warning(f"Solscan API returned empty name/symbol for {token_address}")
            else:
                logger.warning(f"Solscan API returned empty data for {token_address}")
        else:
            logger.warning(f"Solscan API call failed with status {response.status_code}: {response.text}")
    
    except Exception as e:
        logger.error(f"Error fetching Solana token info: {str(e)}")
    
    # Return fallback or default info
    default_info = {
        "name": token_address[:10] + "...",
        "symbol": token_address[:6],
        "decimals": 9
    }
    
    # Cache the default result
    TOKEN_CACHE[cache_key] = {
        'data': default_info,
        'timestamp': now
    }
    
    return default_info

def get_base_token_info(token_address) -> Dict[str, Any]:
    """
    Fetch Base/Ethereum token info from BaseScan API
    """
    # Normalize address to lowercase
    token_address = token_address.lower()
    
    # Check cache first
    cache_key = f"base:{token_address}"
    now = time.time()
    if cache_key in TOKEN_CACHE and (now - TOKEN_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached info for {token_address}")
        return TOKEN_CACHE[cache_key]['data']
    
    try:
        # First try Basescan token info API
        url = f"{BASESCAN_API}/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={BASESCAN_API_KEY}"
        
        logger.info(f"Fetching Base token info from API for {token_address}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "1" and data.get("result"):
                token_info = data.get("result", [])
                if isinstance(token_info, list) and token_info:
                    token_info = token_info[0]
                
                name = token_info.get("name", "")
                symbol = token_info.get("symbol", "")
                decimals = int(token_info.get("decimals", 18))
                
                if name or symbol:
                    result = {
                        "name": name if name else symbol,
                        "symbol": symbol if symbol else name,
                        "decimals": decimals
                    }
                    
                    # Cache the result
                    TOKEN_CACHE[cache_key] = {
                        'data': result,
                        'timestamp': now
                    }
                    
                    logger.info(f"Successfully fetched info for {token_address}: name={name}, symbol={symbol}")
                    return result
                else:
                    logger.warning(f"Basescan API returned empty name/symbol for {token_address}")
            else:
                logger.warning(f"Basescan API returned non-success status: {data.get('message', 'Unknown error')}")
        else:
            logger.warning(f"Basescan API call failed with status {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching Base token info: {str(e)}")
    
    # Return fallback if available, otherwise use token address
    if token_address in BASE_TOKEN_FALLBACKS:
        result = BASE_TOKEN_FALLBACKS[token_address]
    else:
        result = {
            "name": token_address[:10] + "...",
            "symbol": token_address[2:8],
            "decimals": 18
        }
    
    # Cache the result
    TOKEN_CACHE[cache_key] = {
        'data': result,
        'timestamp': now
    }
    
    return result

def get_token_name(token_address, blockchain) -> Tuple[str, str]:
    """
    Get token name and symbol (synchronous version)
    """
    try:
        if blockchain.lower() == "solana":
            # First try Syndica RPC API for Solana tokens
            try:
                logger.info(f"Trying Syndica RPC for token {token_address}")
                name, symbol = syndica_get_token_name(token_address)
                logger.info(f"Syndica returned name={name}, symbol={symbol} for {token_address}")
                
                # If both name and symbol are available, return them
                if name and symbol and name != token_address[:10] + "..." and symbol != token_address[:6]:
                    return name, symbol
                else:
                    logger.warning(f"Syndica fallback used for token {token_address}")
            except Exception as e:
                logger.error(f"Error using Syndica for token {token_address}: {str(e)}")
            
            # If Syndica fails, fall back to Solscan
            logger.info(f"Falling back to Solscan for token {token_address}")
            token_info = get_solana_token_info(token_address)
            return token_info["name"], token_info["symbol"]
        elif blockchain.lower() == "base":
            token_info = get_base_token_info(token_address)
            return token_info["name"], token_info["symbol"]
        else:
            return token_address[:10] + "...", token_address[:6]
            
    except Exception as e:
        logger.error(f"Error in get_token_name: {str(e)}")
        
        # Emergency fallbacks
        if blockchain.lower() == "solana":
            return token_address[:10] + "...", token_address[:6]
        else:  # base
            return token_address[:10] + "...", token_address[2:8]

# Test function
if __name__ == "__main__":
    # Test some tokens
    test_tokens = [
        ("5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump", "solana"),
        ("FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump", "solana"),
        ("3yCDp1E5yzA1qoNQuDjNr5iXyj1CSHjf3dktHpnypump", "solana"),
        ("56UtHy4oBGeLNEenvvXJhhAwDwhNc2bbZgAPUZaFpump", "solana"),
        ("0xe1abd004250ac8d1f199421d647e01d094faa180", "base"),
        ("0xcaa6d4049e667ffd88457a1733d255eed02996bb", "base"),
        ("0x692c1564c82e6a3509ee189d1b666df9a309b420", "base"),
        ("0xc53fc22033a4bcb15b5405c38e67e378c960ee6b", "base")
    ]
    
    # Run tests
    for token_address, blockchain in test_tokens:
        name, symbol = get_token_name(token_address, blockchain)
        print(f"{blockchain.capitalize()} token {token_address}: name={name}, symbol={symbol}")
