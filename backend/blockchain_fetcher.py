"""
Module for fetching real transaction data from blockchains
"""
import os
import requests
import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import base58

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for recent transactions to avoid repeated calls
TRANSACTION_CACHE = {}
CACHE_TTL = 3600  # 1 hour

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

def get_base_rpc_endpoint():
    """
    Get the Base RPC endpoint with API key if available
    """
    # Default public endpoint
    DEFAULT_ENDPOINT = "https://mainnet.base.org"
    
    # Try to get Alchemy API key from environment
    alchemy_api_key = os.environ.get("ALCHEMY_API_KEY", "")
    if alchemy_api_key:
        return f"https://base-mainnet.g.alchemy.com/v2/{alchemy_api_key}"
    
    # Use Infura if available
    infura_api_key = os.environ.get("INFURA_API_KEY", "")
    if infura_api_key:
        return f"https://base-mainnet.infura.io/v3/{infura_api_key}"
    
    # Default fallback
    return DEFAULT_ENDPOINT

def fetch_solana_token_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Fetch real token transactions for a Solana wallet
    - This focuses on token transfers and swaps
    - Returns a list of processed transactions
    """
    logger.info(f"Fetching Solana transactions for wallet: {wallet_address}")
    
    # Check cache first
    cache_key = f"solana:txs:{wallet_address}"
    now = time.time()
    if cache_key in TRANSACTION_CACHE and (now - TRANSACTION_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached transactions for {wallet_address}")
        return TRANSACTION_CACHE[cache_key]['data']
    
    # Get RPC endpoint
    rpc_endpoint = get_solana_rpc_endpoint()
    
    try:
        # 1. Get signatures for the wallet
        signatures_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet_address,
                {"limit": 50}  # Limit to recent transactions
            ]
        }
        
        signatures_response = requests.post(rpc_endpoint, json=signatures_payload)
        if signatures_response.status_code != 200:
            logger.error(f"Error fetching signatures: {signatures_response.text}")
            return []
        
        signatures_data = signatures_response.json()
        if "result" not in signatures_data or not signatures_data["result"]:
            logger.warning(f"No transactions found for wallet: {wallet_address}")
            return []
        
        signatures = [sig_info["signature"] for sig_info in signatures_data["result"]]
        logger.info(f"Found {len(signatures)} signatures for wallet {wallet_address}")
        
        # 2. Get transaction details for each signature
        processed_transactions = []
        
        for signature in signatures:
            try:
                # Get transaction data
                tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        signature,
                        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                    ]
                }
                
                tx_response = requests.post(rpc_endpoint, json=tx_payload)
                if tx_response.status_code != 200:
                    logger.warning(f"Error fetching transaction {signature}: {tx_response.text}")
                    continue
                
                tx_data = tx_response.json()
                if "result" not in tx_data or not tx_data["result"]:
                    logger.warning(f"No data for transaction {signature}")
                    continue
                
                # Process the transaction to extract token transfers
                tx_result = tx_data["result"]
                processed_tx = process_solana_transaction(tx_result, wallet_address)
                
                if processed_tx:
                    processed_transactions.extend(processed_tx)
            
            except Exception as e:
                logger.error(f"Error processing transaction {signature}: {str(e)}")
                continue
        
        # If we found transactions, cache them
        if processed_transactions:
            TRANSACTION_CACHE[cache_key] = {
                'data': processed_transactions,
                'timestamp': now
            }
            
        logger.info(f"Processed {len(processed_transactions)} token transactions for {wallet_address}")
        return processed_transactions
    
    except Exception as e:
        logger.error(f"Error fetching Solana transactions: {str(e)}")
        return []

def process_solana_transaction(tx_data: Dict[str, Any], wallet_address: str) -> List[Dict[str, Any]]:
    """
    Process a Solana transaction to extract token transfers and swaps
    - Focuses on SPL token transfers and DEX swaps
    - Identifies buys and sells based on token balance changes
    """
    processed_txs = []
    
    try:
        # Skip if no token balances
        if not tx_data.get("meta") or "preTokenBalances" not in tx_data["meta"] or "postTokenBalances" not in tx_data["meta"]:
            return []
        
        # Get pre/post token balances
        pre_balances = {b.get("mint") + ":" + b.get("owner"): b for b in tx_data["meta"]["preTokenBalances"] if "mint" in b and "owner" in b}
        post_balances = {b.get("mint") + ":" + b.get("owner"): b for b in tx_data["meta"]["postTokenBalances"] if "mint" in b and "owner" in b}
        
        timestamp = tx_data.get("blockTime", int(time.time()))
        tx_hash = tx_data.get("transaction", {}).get("signatures", [""])[0]
        
        # Check for token transfers involving our wallet
        all_mints = set()
        for key in set(list(pre_balances.keys()) + list(post_balances.keys())):
            if ":" + wallet_address in key:
                mint = key.split(":")[0]
                all_mints.add(mint)
        
        # Process each token mint
        for mint in all_mints:
            pre_key = mint + ":" + wallet_address
            post_key = mint + ":" + wallet_address
            
            pre_amount = 0
            if pre_key in pre_balances:
                pre_amount = float(pre_balances[pre_key].get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
            
            post_amount = 0
            if post_key in post_balances:
                post_amount = float(post_balances[post_key].get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
            
            # Skip if no change
            if pre_amount == post_amount:
                continue
            
            # Determine if buy or sell
            if post_amount > pre_amount:
                tx_type = "buy"
                amount = post_amount - pre_amount
            else:
                tx_type = "sell"
                amount = pre_amount - post_amount
            
            # Look for payment info in the other token balances
            payment_amount = 0
            payment_token = "SOL"  # Default to SOL
            
            # TODO: Extract SOL payment from transaction logs
            # For now, we'll estimate based on common DEX pools
            
            # Create transaction record
            from token_finder import get_token_name
            name, symbol = get_token_name(mint, "solana")
            
            processed_txs.append({
                "tx_hash": tx_hash,
                "wallet_address": wallet_address,
                "token_address": mint,
                "token_name": name,
                "token_symbol": symbol,
                "amount": amount,
                "price": payment_amount / amount if amount > 0 and payment_amount > 0 else 0,
                "timestamp": timestamp,
                "type": tx_type
            })
    
    except Exception as e:
        logger.error(f"Error processing Solana transaction: {str(e)}")
    
    return processed_txs

def fetch_base_token_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Fetch real token transactions for a Base wallet
    - Focuses on ERC20 token transfers and swaps
    - Returns a list of processed transactions
    """
    logger.info(f"Fetching Base transactions for wallet: {wallet_address}")
    
    # Check cache first
    cache_key = f"base:txs:{wallet_address}"
    now = time.time()
    if cache_key in TRANSACTION_CACHE and (now - TRANSACTION_CACHE[cache_key]['timestamp'] < CACHE_TTL):
        logger.info(f"Using cached transactions for {wallet_address}")
        return TRANSACTION_CACHE[cache_key]['data']
    
    # Normalize address to lowercase
    wallet_address = wallet_address.lower()
    
    # Get RPC endpoint
    rpc_endpoint = get_base_rpc_endpoint()
    
    try:
        # For Base/EVM chains, we'll use a different approach to get token transfers
        # We can use the Etherscan-compatible API from Basescan
        
        basescan_api_key = os.environ.get("BASESCAN_API_KEY", "CQYEHTMRFY24DXPFGIWUYBFYGSYJH1V1EZ")
        basescan_url = f"https://api.basescan.org/api?module=account&action=tokentx&address={wallet_address}&apikey={basescan_api_key}"
        
        response = requests.get(basescan_url)
        if response.status_code != 200:
            logger.error(f"Error fetching Base token transfers: {response.text}")
            return []
        
        data = response.json()
        if data.get("status") != "1" or "result" not in data:
            logger.warning(f"No token transfers found for wallet: {wallet_address}")
            return []
        
        # Process token transfers
        transfers = data["result"]
        processed_transactions = []
        
        for transfer in transfers:
            try:
                token_address = transfer.get("contractAddress", "").lower()
                from_address = transfer.get("from", "").lower()
                to_address = transfer.get("to", "").lower()
                
                # Skip if not involving our wallet
                if from_address != wallet_address and to_address != wallet_address:
                    continue
                
                # Determine if buy or sell
                if to_address == wallet_address:
                    tx_type = "buy"
                else:
                    tx_type = "sell"
                
                # Get token details
                token_name = transfer.get("tokenName", "")
                token_symbol = transfer.get("tokenSymbol", "")
                token_decimals = int(transfer.get("tokenDecimal", 18))
                
                # Calculate amount in human-readable format
                amount = float(transfer.get("value", "0")) / (10 ** token_decimals)
                
                # Get timestamp
                timestamp = int(transfer.get("timeStamp", "0"))
                
                # Create transaction record
                processed_transactions.append({
                    "tx_hash": transfer.get("hash", ""),
                    "wallet_address": wallet_address,
                    "token_address": token_address,
                    "token_name": token_name,
                    "token_symbol": token_symbol,
                    "amount": amount,
                    "price": 0,  # We don't have price info from this API
                    "timestamp": timestamp,
                    "type": tx_type
                })
            
            except Exception as e:
                logger.error(f"Error processing Base transfer: {str(e)}")
                continue
        
        # If we found transactions, cache them
        if processed_transactions:
            TRANSACTION_CACHE[cache_key] = {
                'data': processed_transactions,
                'timestamp': now
            }
            
        logger.info(f"Processed {len(processed_transactions)} token transactions for {wallet_address}")
        return processed_transactions
    
    except Exception as e:
        logger.error(f"Error fetching Base transactions: {str(e)}")
        return []

def fetch_wallet_transactions(wallet_address: str, blockchain: str) -> List[Dict[str, Any]]:
    """
    Fetch wallet transactions based on blockchain
    """
    if blockchain.lower() == "solana":
        return fetch_solana_token_transactions(wallet_address)
    elif blockchain.lower() == "base":
        return fetch_base_token_transactions(wallet_address)
    else:
        logger.error(f"Unsupported blockchain: {blockchain}")
        return []

# Test function
if __name__ == "__main__":
    # Test with a sample Solana wallet
    solana_wallet = "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"
    solana_txs = fetch_solana_token_transactions(solana_wallet)
    print(f"Found {len(solana_txs)} Solana transactions")
    
    # Test with a sample Base wallet
    base_wallet = "0x2D1C5E86eF58644b2B2B09921AFE9ddf4E99eF28"
    base_txs = fetch_base_token_transactions(base_wallet)
    print(f"Found {len(base_txs)} Base transactions")
