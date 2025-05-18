#!/usr/bin/env python3

import requests
import json

# The token address to look up
TOKEN_ADDRESS = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"

# Solscan API token
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3NDc1OTMxODMyMzAsImVtYWlsIjoicGlrZWRhcnJlbjcxMEBnbWFpbC5jb20iLCJhY3Rpb24iOiJ0b2tlbi1hcGkiLCJhcGlWZXJzaW9uIjoidjIiLCJpYXQiOjE3NDc1OTMxODN9.H3_JHdgBk25jDpM8JEBzKhXURa3he49xU-eKpQMyomk"

# Try different Solscan API endpoints
endpoints = [
    f"https://public-api.solscan.io/token/meta?tokenAddress={TOKEN_ADDRESS}",
    f"https://api.solscan.io/token/meta?tokenAddress={TOKEN_ADDRESS}",
    f"https://api-v2.solscan.io/token/meta?tokenAddress={TOKEN_ADDRESS}"
]

print("\n=== Trying different Solscan API endpoints ===")

for endpoint in endpoints:
    print(f"\nEndpoint: {endpoint}")
    
    # Try with just the accept header
    headers = {"accept": "application/json"}
    try:
        response = requests.get(endpoint, headers=headers)
        print(f"  Without token - Status: {response.status_code}")
        if response.status_code == 200 and response.text:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"  Error without token: {str(e)}")
    
    # Try with the API token
    headers = {
        "accept": "application/json",
        "token": API_TOKEN
    }
    try:
        response = requests.get(endpoint, headers=headers)
        print(f"  With token - Status: {response.status_code}")
        if response.status_code == 200 and response.text:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
    except Exception as e:
        print(f"  Error with token: {str(e)}")

# Try the SolScan legacy API
legacy_endpoint = f"https://public-api.solscan.io/account/{TOKEN_ADDRESS}"
print(f"\nLegacy endpoint: {legacy_endpoint}")
try:
    response = requests.get(legacy_endpoint, headers={"accept": "application/json"})
    print(f"  Status: {response.status_code}")
    if response.status_code == 200 and response.text:
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"  Error: {str(e)}")

# Try to get token info from account transactions
transactions_endpoint = f"https://public-api.solscan.io/account/transactions?account={TOKEN_ADDRESS}&limit=10"
print(f"\nTransactions endpoint: {transactions_endpoint}")
try:
    response = requests.get(transactions_endpoint, headers={"accept": "application/json"})
    print(f"  Status: {response.status_code}")
    if response.status_code == 200 and response.text:
        data = response.json()
        txs = data.get("data", [])
        if txs:
            print(f"  Found {len(txs)} transactions")
            for i, tx in enumerate(txs[:3]):  # Show first 3 transactions
                print(f"  Transaction {i+1}: {tx.get('txHash', 'Unknown')}")
except Exception as e:
    print(f"  Error: {str(e)}")

print("\n--- Based on the results, this token appears to be ---")
print("Name: Unknown (API limitations)")
print("Symbol: Unknown (API limitations)")
print("Address:", TOKEN_ADDRESS)
print("============================================\n")
