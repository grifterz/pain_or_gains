#!/usr/bin/env python3
"""
Test script to verify live token name resolution without hardcoded fallbacks
"""
import sys
import os
import logging
import requests
import base64
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")

# Import our token modules
from token_finder import get_token_name
from external_integrations.syndica_integration import (
    get_token_name_and_symbol,
    get_metadata_from_solscan
)

def test_solscan_direct(token_address):
    """
    Test direct Solscan scraping for a token
    """
    print(f"\n=== DIRECT SOLSCAN SCRAPING FOR {token_address} ===")
    
    try:
        url = f"https://solscan.io/token/{token_address}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        print(f"Requesting: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            html = response.text
            
            # Just extract the title to see what Solscan shows
            title_match = response.text.split("<title>")[1].split("</title>")[0] if "<title>" in response.text else "No title found"
            print(f"Page title: {title_match}")
            
            # Extract some of the HTML for debugging
            html_excerpt = html[:500] + "..." if len(html) > 500 else html
            print(f"HTML excerpt: {html_excerpt}")
            
            # Try our metadata extraction function
            metadata = get_metadata_from_solscan(token_address)
            if metadata:
                print(f"Extracted metadata: {metadata}")
            else:
                print("Failed to extract metadata")
                
        else:
            print(f"Failed with status code: {response.status_code}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

def test_live_token_resolution(token_address):
    """
    Test live token name resolution for a specific token
    """
    print(f"\n=== LIVE TOKEN RESOLUTION FOR {token_address} ===")
    
    # Test our syndica integration directly
    print("\n1. Testing Syndica integration:")
    syndica_name, syndica_symbol = get_token_name_and_symbol(token_address)
    print(f"   Name: {syndica_name}")
    print(f"   Symbol: {syndica_symbol}")
    
    # Test our token_finder module 
    print("\n2. Testing token_finder module:")
    name, symbol = get_token_name(token_address, "solana")
    print(f"   Name: {name}")
    print(f"   Symbol: {symbol}")

def test_solscan_api(token_address):
    """
    Test Solscan API for token info
    """
    print(f"\n=== SOLSCAN API FOR {token_address} ===")
    
    try:
        url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
        headers = {
            "accept": "application/json",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NDc1OTMxODMyMzAsImVtYWlsIjoicGlrZWRhcnJlbjcxMEBnbWFpbC5jb20iLCJhY3Rpb24iOiJ0b2tlbi1hcGkiLCJhcGlWZXJzaW9uIjoidjIiLCJpYXQiOjE3NDc1OTMxODN9.H3_JHdgBk25jDpM8JEBzKhXURa3he49xU-eKpQMyomk"
        }
        
        print(f"Requesting: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"API response: {json.dumps(data, indent=2)}")
        else:
            print(f"Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Load environment variables from .env file
    env_path = "/app/backend/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip("'\"")
    
    # Token to test
    token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
    
    # Run direct Solscan test first
    test_solscan_direct(token_address)
    
    # Test Solscan API
    test_solscan_api(token_address)
    
    # Test live resolution
    test_live_token_resolution(token_address)
