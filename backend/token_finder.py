"""
Token finder module to provide names for specific token addresses
"""

# Base token name mappings (address -> name, symbol)
BASE_TOKEN_INFO = {
    "0xe1abd004250ac8d1f199421d647e01d094faa180": {"name": "Roost", "symbol": "ROOST"},
    "0xcaa6d4049e667ffd88457a1733d255eed02996bb": {"name": "Memecoin", "symbol": "MEME"},
    "0x692c1564c82e6a3509ee189d1b666df9a309b420": {"name": "Based", "symbol": "BASED"},
    "0xc53fc22033a4bcb15b5405c38e67e378c960ee6b": {"name": "Degen", "symbol": "DEGEN"}
}

# Solana token name mappings (address -> name, symbol)
SOLANA_TOKEN_INFO = {
    "FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump": {"name": "JewCoin", "symbol": "JEWCOIN"},
    "3yCDp1E5yzA1qoNQuDjNr5iXyj1CSHjf3dktHpnypump": {"name": "PumpCoin", "symbol": "PUMP"}
}

def get_token_name(token_address, blockchain):
    """
    Get token name and symbol for a specific token address
    """
    if blockchain.lower() == "base":
        token_info = BASE_TOKEN_INFO.get(token_address.lower(), {})
        if not token_info:
            token_info = BASE_TOKEN_INFO.get(token_address, {})
        
        if token_info:
            return token_info["name"], token_info["symbol"]
        else:
            return token_address[2:8], token_address[2:8]
            
    elif blockchain.lower() == "solana":
        token_info = SOLANA_TOKEN_INFO.get(token_address, {})
        
        if token_info:
            return token_info["name"], token_info["symbol"]
        else:
            return token_address[:6], token_address[:6]
            
    return "Unknown", "UNK"
