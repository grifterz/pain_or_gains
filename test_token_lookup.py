#!/usr/bin/env python3

import sys
sys.path.append('/app/backend')
from token_finder import get_token_name

# The token address to look up
TOKEN_ADDRESS = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"
BLOCKCHAIN = "solana"

# Look up the token
name, symbol = get_token_name(TOKEN_ADDRESS, BLOCKCHAIN)

print(f"\n================================================")
print(f"TOKEN LOOKUP RESULTS:")
print(f"================================================")
print(f"Token Address: {TOKEN_ADDRESS}")
print(f"Blockchain: {BLOCKCHAIN}")
print(f"Name: {name}")
print(f"Symbol: {symbol}")
print(f"================================================\n")
