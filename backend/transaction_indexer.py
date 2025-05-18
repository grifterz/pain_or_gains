"""
Transaction Indexer for Blockchain Data

This module provides a background process for indexing and caching blockchain transactions,
supporting both Solana and Base chains.

Features:
- Paginated fetching of historical transactions to increase coverage
- Specialized DEX transaction parsing for accurate token swap detection
- Persistent storage of indexed transactions in MongoDB
- Rate-limit friendly request throttling
"""
import os
import sys
import time
import logging
import asyncio
import json
import base58
import base64
import requests
import pymongo
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the path for imports
sys.path.append("/app/backend")
from token_finder import get_token_name

# Environment variables
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

# MongoDB client
client = AsyncIOMotorClient(MONGO_URL)
db = client["memecoin_analyzer"]
transactions_collection = db["transactions"]
wallets_collection = db["wallets"]
indexer_state_collection = db["indexer_state"]

# Known DEX Program IDs
SOLANA_DEX_PROGRAMS = {
    "jupiterV3": "JUP3c2Uh3WA4Ng34tw6kPd2G4C5BB21Xo36Je1s32Ph",  # Jupiter Aggregator
    "jupiterV4": "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",  # Jupiter V4
    "raydium": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM
    "raydiumV2": "9HzJyW1qZsEiSfMUf6L2jo3CcTKAyBmSyKdwQeYisHrC"  # Raydium CLMM
}

BASE_DEX_ROUTERS = {
    "uniswapV3": "0x2626664c2603336E57B271c5C0b26F421741e481",  # Uniswap V3 Router on Base
    "baseswap": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86"  # Baseswap Router
}

# Max items per API request
MAX_ITEMS_PER_REQUEST = 100  # Most APIs limit to 100 items per request
MAX_REQUESTS_PER_MINUTE = 10  # Rate limit ourselves to avoid 429 errors
MAX_TRANSACTIONS_PER_WALLET = 1000  # Reasonable limit for free APIs

@dataclass
class IndexerState:
    """State tracking for the indexer"""
    wallet_address: str
    blockchain: str
    last_signature: Optional[str] = None  # For Solana pagination
    last_block: Optional[int] = None  # For Base pagination
    last_updated: datetime = datetime.now()
    is_fully_indexed: bool = False

class TransactionIndexer:
    """Indexes and processes blockchain transactions"""
    
    def __init__(self):
        """Initialize the indexer"""
        self.rpc_calls_this_minute = 0
        self.minute_start_time = time.time()
        self.sol_token_cache = {}  # Cache of known SPL tokens
    
    def get_solana_rpc_endpoint(self) -> str:
        """Get the Solana RPC endpoint with API key if available"""
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

    def get_base_rpc_endpoint(self) -> str:
        """Get the Base RPC endpoint with API key if available"""
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
    
    async def get_indexer_state(self, wallet_address: str, blockchain: str) -> IndexerState:
        """Get current indexer state for a wallet"""
        state_doc = await indexer_state_collection.find_one({
            "wallet_address": wallet_address,
            "blockchain": blockchain
        })
        
        if state_doc:
            return IndexerState(
                wallet_address=state_doc["wallet_address"],
                blockchain=state_doc["blockchain"],
                last_signature=state_doc.get("last_signature"),
                last_block=state_doc.get("last_block"),
                last_updated=state_doc.get("last_updated", datetime.now()),
                is_fully_indexed=state_doc.get("is_fully_indexed", False)
            )
        
        return IndexerState(wallet_address=wallet_address, blockchain=blockchain)
    
    async def save_indexer_state(self, state: IndexerState):
        """Save indexer state to database"""
        await indexer_state_collection.update_one(
            {"wallet_address": state.wallet_address, "blockchain": state.blockchain},
            {"$set": {
                "last_signature": state.last_signature,
                "last_block": state.last_block,
                "last_updated": state.last_updated,
                "is_fully_indexed": state.is_fully_indexed
            }},
            upsert=True
        )
    
    async def rate_limit_check(self):
        """Check if we need to pause for rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.minute_start_time
        
        # Reset counter if a minute has passed
        if elapsed > 60:
            self.rpc_calls_this_minute = 0
            self.minute_start_time = current_time
            return
        
        # If we're at the limit, sleep until the minute is up
        if self.rpc_calls_this_minute >= MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - elapsed
            logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
            self.rpc_calls_this_minute = 0
            self.minute_start_time = time.time()
    
    async def fetch_solana_signatures(self, wallet_address: str, before: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch Solana transaction signatures for a wallet
        Using pagination to get more historical transactions
        """
        await self.rate_limit_check()
        
        endpoint = self.get_solana_rpc_endpoint()
        self.rpc_calls_this_minute += 1
        
        params = {
            "limit": MAX_ITEMS_PER_REQUEST
        }
        
        if before:
            params["before"] = before
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet_address,
                params
            ]
        }
        
        try:
            response = requests.post(endpoint, json=payload)
            if response.status_code == 200:
                data = response.json()
                if "result" in data and data["result"]:
                    return data["result"]
            else:
                logger.error(f"Error fetching Solana signatures: {response.text}")
        except Exception as e:
            logger.error(f"Exception fetching Solana signatures: {str(e)}")
        
        return []
    
    async def is_token_account(self, account: str) -> bool:
        """Check if an account is a SPL token account"""
        if account in self.sol_token_cache:
            return self.sol_token_cache[account]
            
        await self.rate_limit_check()
        
        endpoint = self.get_solana_rpc_endpoint()
        self.rpc_calls_this_minute += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                account,
                {"encoding": "jsonParsed"}
            ]
        }
        
        try:
            response = requests.post(endpoint, json=payload)
            if response.status_code == 200:
                data = response.json()
                if "result" in data and data["result"] and data["result"]["value"]:
                    is_token = "parsed" in data["result"]["value"]["data"] and data["result"]["value"]["data"]["parsed"]["type"] == "mint"
                    self.sol_token_cache[account] = is_token
                    return is_token
            else:
                logger.error(f"Error checking token account: {response.text}")
        except Exception as e:
            logger.error(f"Exception checking token account: {str(e)}")
        
        return False
    
    async def fetch_solana_transaction(self, signature: str) -> Optional[Dict[str, Any]]:
        """Fetch a single Solana transaction with all details"""
        await self.rate_limit_check()
        
        endpoint = self.get_solana_rpc_endpoint()
        self.rpc_calls_this_minute += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }
        
        try:
            response = requests.post(endpoint, json=payload)
            if response.status_code == 200:
                data = response.json()
                if "result" in data and data["result"]:
                    return data["result"]
            else:
                logger.error(f"Error fetching transaction {signature}: {response.text}")
        except Exception as e:
            logger.error(f"Exception fetching transaction {signature}: {str(e)}")
        
        return None
    
    async def process_solana_transaction(self, 
                                         tx_data: Dict[str, Any], 
                                         wallet_address: str) -> List[Dict[str, Any]]:
        """
        Process a Solana transaction with enhanced DEX detection
        Returns a list of processed token transfers/swaps
        """
        if not tx_data:
            return []
            
        processed_txs = []
        timestamp = tx_data.get("blockTime", int(time.time()))
        tx_hash = tx_data.get("transaction", {}).get("signatures", [""])[0]
        
        try:
            # Skip if no metadata
            if not tx_data.get("meta"):
                return []
                
            # Check for DEX programs in the transaction
            instructions = []
            dex_program = None
            
            # Extract instructions
            if "message" in tx_data.get("transaction", {}):
                message = tx_data["transaction"]["message"]
                
                if "instructions" in message:
                    instructions = message["instructions"]
                    
                    # Check if any instruction is from a known DEX
                    for instr in instructions:
                        if "programId" in instr:
                            program_id = instr.get("programId")
                            if program_id in SOLANA_DEX_PROGRAMS.values():
                                dex_program = program_id
                                break
            
            # First check for token balance changes
            has_token_changes = False
            if "preTokenBalances" in tx_data["meta"] and "postTokenBalances" in tx_data["meta"]:
                has_token_changes = True
                
                # Process token balance changes (transfers)
                pre_balances = {b.get("mint") + ":" + b.get("owner"): b for b in tx_data["meta"]["preTokenBalances"] if "mint" in b and "owner" in b}
                post_balances = {b.get("mint") + ":" + b.get("owner"): b for b in tx_data["meta"]["postTokenBalances"] if "mint" in b and "owner" in b}
                
                # Find tokens where our wallet's balance changed
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
                    
                    # Try to infer price for swaps
                    price = 0
                    counterparty_mint = None
                    
                    # For DEX swaps, look for the other token in the pair
                    if dex_program:
                        # Find other token that changed in the opposite direction
                        for other_mint in set(m.split(':')[0] for m in pre_balances.keys()):
                            if other_mint != mint and await self.is_token_account(other_mint):
                                other_pre_key = other_mint + ":" + wallet_address
                                other_post_key = other_mint + ":" + wallet_address
                                
                                other_pre_amount = 0
                                if other_pre_key in pre_balances:
                                    other_pre_amount = float(pre_balances[other_pre_key].get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                                
                                other_post_amount = 0
                                if other_post_key in post_balances:
                                    other_post_amount = float(post_balances[other_post_key].get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                                
                                # If other token changed in opposite direction, it's likely the counterparty
                                if (tx_type == "buy" and other_post_amount < other_pre_amount) or \
                                   (tx_type == "sell" and other_post_amount > other_pre_amount):
                                    other_change = abs(other_post_amount - other_pre_amount)
                                    price = other_change / amount
                                    counterparty_mint = other_mint
                                    break
                    
                    # Get token details
                    name, symbol = get_token_name(mint, "solana")
                    
                    # Create transaction record
                    processed_txs.append({
                        "tx_hash": tx_hash,
                        "wallet_address": wallet_address,
                        "blockchain": "solana",
                        "token_address": mint,
                        "token_name": name,
                        "token_symbol": symbol,
                        "amount": amount,
                        "price": price,
                        "timestamp": timestamp,
                        "type": tx_type,
                        "dex": list(SOLANA_DEX_PROGRAMS.keys())[list(SOLANA_DEX_PROGRAMS.values()).index(dex_program)] if dex_program else None
                    })
                    
                    # If we found a counterparty, add the other side of the swap
                    if counterparty_mint:
                        counter_name, counter_symbol = get_token_name(counterparty_mint, "solana")
                        logger.info(f"Found swap counterparty: {counter_symbol} for {symbol}")
            
            # If no token balance changes but inner instructions exist, might still be a DEX swap
            elif dex_program and "innerInstructions" in tx_data["meta"]:
                logger.info(f"Found DEX program {dex_program} with inner instructions")
                # TODO: Parse Jupiter/Raydium-specific inner instructions for swap details
        
        except Exception as e:
            logger.error(f"Error processing Solana transaction {tx_hash}: {str(e)}")
        
        return processed_txs
    
    async def store_transactions(self, transactions: List[Dict[str, Any]]):
        """Store transactions in MongoDB"""
        if not transactions:
            return
            
        bulk_ops = []
        for tx in transactions:
            # Create an upsert operation for each transaction
            bulk_ops.append(
                pymongo.UpdateOne(
                    {"tx_hash": tx["tx_hash"], "wallet_address": tx["wallet_address"]},
                    {"$set": tx},
                    upsert=True
                )
            )
            
        if bulk_ops:
            await transactions_collection.bulk_write(bulk_ops)
    
    async def index_solana_wallet(self, wallet_address: str, full_sync: bool = False) -> int:
        """
        Index transactions for a Solana wallet
        Returns the number of new transactions found
        """
        state = await self.get_indexer_state(wallet_address, "solana")
        
        # If fully indexed and not forced full sync, and last update was recent, skip
        if state.is_fully_indexed and not full_sync and state.last_updated > datetime.now() - timedelta(hours=1):
            logger.info(f"Wallet {wallet_address} already fully indexed and recently updated")
            return 0
        
        before = state.last_signature if not full_sync else None
        processed_count = 0
        total_signatures = 0
        has_more = True
        
        while has_more:
            # Get transaction signatures
            logger.info(f"Fetching Solana signatures for {wallet_address}" + (f" before {before}" if before else ""))
            signatures = await self.fetch_solana_signatures(wallet_address, before)
            
            if not signatures:
                has_more = False
                break
                
            total_signatures += len(signatures)
            logger.info(f"Found {len(signatures)} signatures, total so far: {total_signatures}")
            
            # Process each transaction
            for sig_info in signatures:
                signature = sig_info["signature"]
                
                # Get transaction details
                tx_data = await self.fetch_solana_transaction(signature)
                if not tx_data:
                    continue
                
                # Process transaction
                processed_txs = await self.process_solana_transaction(tx_data, wallet_address)
                
                # Store processed transactions
                if processed_txs:
                    await self.store_transactions(processed_txs)
                    processed_count += len(processed_txs)
                
            # Update pagination cursor for next batch
            if signatures:
                before = signatures[-1]["signature"]
                state.last_signature = before
                await self.save_indexer_state(state)
            
            # If we've reached our limit, stop
            if total_signatures >= MAX_TRANSACTIONS_PER_WALLET:
                logger.info(f"Reached maximum number of transactions ({MAX_TRANSACTIONS_PER_WALLET}) for {wallet_address}")
                break
                
            # Sleep a bit to avoid hammering the API
            await asyncio.sleep(1)
        
        # Mark as fully indexed
        state.is_fully_indexed = True
        state.last_updated = datetime.now()
        await self.save_indexer_state(state)
        
        return processed_count
    
    async def fetch_base_transactions(self, wallet_address: str, start_block: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch Base/Ethereum transactions for a wallet
        Uses Etherscan-compatible API from Basescan
        """
        basescan_api_key = os.environ.get("BASESCAN_API_KEY", "CQYEHTMRFY24DXPFGIWUYBFYGSYJH1V1EZ")
        basescan_url = f"https://api.basescan.org/api"
        
        # Normalize address to lowercase
        wallet_address = wallet_address.lower()
        
        # Parameters
        params = {
            "module": "account",
            "action": "tokentx",
            "address": wallet_address,
            "apikey": basescan_api_key,
            "sort": "desc"
        }
        
        if start_block:
            params["startblock"] = start_block
            
        try:
            self.rpc_calls_this_minute += 1
            response = requests.get(basescan_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "1" and "result" in data:
                    return data["result"]
                else:
                    logger.warning(f"No Base transactions for {wallet_address}: {data.get('message', 'No error message')}")
            else:
                logger.error(f"Error fetching Base transactions: {response.text}")
        except Exception as e:
            logger.error(f"Exception fetching Base transactions: {str(e)}")
            
        return []
    
    async def process_base_transactions(self, transactions: List[Dict[str, Any]], wallet_address: str) -> List[Dict[str, Any]]:
        """
        Process Base blockchain transactions
        Includes DEX swap detection for UniswapV3 and Baseswap
        """
        processed_txs = []
        dex_txs = {}  # Group by tx_hash for DEX detection
        
        for tx in transactions:
            try:
                from_address = tx.get("from", "").lower()
                to_address = tx.get("to", "").lower()
                
                # Skip if not involving our wallet
                if from_address != wallet_address.lower() and to_address != wallet_address.lower():
                    continue
                
                token_address = tx.get("contractAddress", "").lower()
                token_name = tx.get("tokenName", "")
                token_symbol = tx.get("tokenSymbol", "")
                
                # Determine if buy or sell
                if to_address == wallet_address.lower():
                    tx_type = "buy"
                else:
                    tx_type = "sell"
                
                # Calculate amount in human-readable format
                token_decimals = int(tx.get("tokenDecimal", 18))
                amount = float(tx.get("value", "0")) / (10 ** token_decimals)
                
                # Get timestamp
                timestamp = int(tx.get("timeStamp", "0"))
                tx_hash = tx.get("hash", "")
                
                # Check if this is a DEX transaction
                dex_name = None
                price = 0
                
                # Group by tx_hash to identify DEX swaps (same tx_hash = likely a swap)
                if tx_hash not in dex_txs:
                    dex_txs[tx_hash] = []
                dex_txs[tx_hash].append({
                    "token_address": token_address,
                    "amount": amount,
                    "type": tx_type
                })
                
                # Check if the contract is a known DEX
                if to_address in BASE_DEX_ROUTERS.values():
                    dex_idx = list(BASE_DEX_ROUTERS.values()).index(to_address)
                    dex_name = list(BASE_DEX_ROUTERS.keys())[dex_idx]
                
                processed_txs.append({
                    "tx_hash": tx_hash,
                    "wallet_address": wallet_address,
                    "blockchain": "base",
                    "token_address": token_address,
                    "token_name": token_name,
                    "token_symbol": token_symbol,
                    "amount": amount,
                    "price": price,  # Will update after processing all txs in this hash
                    "timestamp": timestamp,
                    "type": tx_type,
                    "dex": dex_name
                })
            
            except Exception as e:
                logger.error(f"Error processing Base transaction: {str(e)}")
        
        # Second pass: Match DEX swaps and calculate prices
        for tx_hash, tx_group in dex_txs.items():
            if len(tx_group) == 2:  # A swap has exactly 2 token transfers
                # Find buy and sell
                buys = [tx for tx in tx_group if tx["type"] == "buy"]
                sells = [tx for tx in tx_group if tx["type"] == "sell"]
                
                if len(buys) == 1 and len(sells) == 1:
                    buy = buys[0]
                    sell = sells[0]
                    
                    # Calculate price in both directions
                    if buy["amount"] > 0:
                        buy_price = sell["amount"] / buy["amount"]
                        # Update the processed transaction
                        for tx in processed_txs:
                            if tx["tx_hash"] == tx_hash and tx["token_address"] == buy["token_address"]:
                                tx["price"] = buy_price
                                logger.info(f"Updated DEX swap price: {buy_price} for token {tx['token_address']}")
                    
                    if sell["amount"] > 0:
                        sell_price = buy["amount"] / sell["amount"]
                        # Update the processed transaction  
                        for tx in processed_txs:
                            if tx["tx_hash"] == tx_hash and tx["token_address"] == sell["token_address"]:
                                tx["price"] = sell_price
                                logger.info(f"Updated DEX swap price: {sell_price} for token {tx['token_address']}")
        
        return processed_txs
    
    async def index_base_wallet(self, wallet_address: str, full_sync: bool = False) -> int:
        """
        Index transactions for a Base wallet
        Returns the number of new transactions found
        """
        state = await self.get_indexer_state(wallet_address, "base")
        
        # If fully indexed and not forced full sync, and last update was recent, skip
        if state.is_fully_indexed and not full_sync and state.last_updated > datetime.now() - timedelta(hours=1):
            logger.info(f"Wallet {wallet_address} already fully indexed and recently updated")
            return 0
        
        start_block = None if full_sync else state.last_block
        processed_count = 0
        
        # Fetch transactions
        logger.info(f"Fetching Base transactions for {wallet_address}")
        transactions = await self.fetch_base_transactions(wallet_address, start_block)
        
        if transactions:
            logger.info(f"Found {len(transactions)} Base transactions")
            
            # Process transactions
            processed_txs = await self.process_base_transactions(transactions, wallet_address)
            
            # Store processed transactions
            if processed_txs:
                await self.store_transactions(processed_txs)
                processed_count = len(processed_txs)
                
            # Update last block for pagination
            if transactions:
                # Find the highest block number
                highest_block = max(int(tx.get("blockNumber", 0)) for tx in transactions)
                state.last_block = highest_block
        
        # Mark as fully indexed
        state.is_fully_indexed = True 
        state.last_updated = datetime.now()
        await self.save_indexer_state(state)
        
        return processed_count
    
    async def index_wallet(self, wallet_address: str, blockchain: str, full_sync: bool = False) -> int:
        """Index transactions for a wallet"""
        if blockchain.lower() == "solana":
            return await self.index_solana_wallet(wallet_address, full_sync)
        elif blockchain.lower() == "base":
            return await self.index_base_wallet(wallet_address, full_sync)
        else:
            logger.error(f"Unsupported blockchain: {blockchain}")
            return 0

# Async function to run the indexer
async def index_wallet(wallet_address: str, blockchain: str, full_sync: bool = False) -> int:
    """Run the indexer for a wallet"""
    indexer = TransactionIndexer()
    return await indexer.index_wallet(wallet_address, blockchain, full_sync)

# Run as a script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index blockchain transactions")
    parser.add_argument("wallet", help="Wallet address to index")
    parser.add_argument("blockchain", choices=["solana", "base"], help="Blockchain to index")
    parser.add_argument("--full", action="store_true", help="Force full sync")
    
    args = parser.parse_args()
    
    async def main():
        count = await index_wallet(args.wallet, args.blockchain, args.full)
        print(f"Indexed {count} transactions for {args.blockchain} wallet {args.wallet}")
    
    asyncio.run(main())
