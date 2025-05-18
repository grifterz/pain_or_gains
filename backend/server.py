from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
import logging
import json
import os
import re
import uuid
import requests
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "0Ik6_-2dWBj1BCXGcJNY5LFJrYVJ0OMf")

# Initialize FastAPI app
app = FastAPI()
api_router = FastAPI(prefix="/api")

# Add CORS middleware
api_router.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client["memecoin_analyzer"]
collection = db["wallet_analyses"]

# Define schemas
class SearchQuery(BaseModel):
    wallet_address: str
    blockchain: str
    
    @validator('blockchain')
    def blockchain_must_be_valid(cls, v):
        if v.lower() not in ["solana", "base"]:
            raise ValueError("Blockchain must be 'solana' or 'base'")
        return v.lower()

class TradeStats(BaseModel):
    id: str
    wallet_address: str
    blockchain: str
    best_trade_profit: float
    best_trade_token: str = ""
    best_multiplier: float
    best_multiplier_token: str = ""
    all_time_pnl: float
    worst_trade_loss: float
    worst_trade_token: str = ""
    timestamp: datetime

# Helper function to validate wallet addresses
def is_valid_solana_address(address: str) -> bool:
    try:
        # Solana addresses must be 32-44 bytes long in base58 encoding
        return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address))
    except:
        return False

def is_valid_eth_address(address: str) -> bool:
    try:
        # Ethereum addresses must be 42 characters long (0x + 40 hex characters)
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))
    except:
        return False

async def get_solana_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Get real transaction history for a Solana wallet address using public RPC API
    """
    try:
        # Validate address
        if not is_valid_solana_address(wallet_address):
            raise ValueError("Invalid Solana wallet address")
        
        logger.info(f"Fetching real transactions for Solana wallet: {wallet_address}")
        
        # Get token accounts for the wallet
        token_accounts_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }
        
        response = requests.post(SOLANA_RPC_URL, json=token_accounts_payload)
        data = response.json()
        
        if 'error' in data:
            logger.error(f"Error from Solana RPC: {data['error']}")
            return []
        
        token_accounts = data.get('result', {}).get('value', [])
        
        # Get transaction history for each token account
        transactions = []
        for account in token_accounts:
            try:
                account_pubkey = account.get('pubkey')
                mint = account.get('account', {}).get('data', {}).get('parsed', {}).get('info', {}).get('mint')
                
                # Try to get token info from metadata
                try:
                    token_data_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTokenSupply",
                        "params": [mint]
                    }
                    token_response = requests.post(SOLANA_RPC_URL, json=token_data_payload)
                    token_data = token_response.json()
                    
                    # Use first 6 chars of mint as symbol if we can't get a better name
                    token_symbol = mint[:6]
                    
                    # Try to get a proper symbol through metadata
                    try:
                        # This is just a simplistic way to get token info
                        # In a production environment, you'd use a better token metadata service
                        if 'result' in token_data and 'symbol' in token_data.get('result', {}):
                            token_symbol = token_data['result']['symbol']
                    except:
                        pass
                except Exception as e:
                    logger.error(f"Error getting token info: {str(e)}")
                    token_symbol = mint[:6]  # Use first 6 chars as fallback
                
                # Get transactions for this token account
                tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignaturesForAddress",
                    "params": [
                        account_pubkey,
                        {"limit": 100}
                    ]
                }
                
                tx_response = requests.post(SOLANA_RPC_URL, json=tx_payload)
                tx_data = tx_response.json()
                
                if 'error' in tx_data:
                    logger.error(f"Error from Solana RPC: {tx_data['error']}")
                    continue
                
                signatures = [item.get('signature') for item in tx_data.get('result', [])]
                
                # Get transaction details for each signature
                for signature in signatures:
                    tx_detail_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [
                            signature,
                            {"encoding": "jsonParsed"}
                        ]
                    }
                    
                    tx_detail_response = requests.post(SOLANA_RPC_URL, json=tx_detail_payload)
                    tx_detail = tx_detail_response.json()
                    
                    if 'error' in tx_detail:
                        logger.error(f"Error from Solana RPC: {tx_detail['error']}")
                        continue
                    
                    tx_result = tx_detail.get('result', {})
                    
                    # Attempt to determine if this is a buy or sell
                    tx_type = "unknown"
                    price = 0.0
                    amount = 0.0
                    
                    # Parse transaction to determine type and details
                    # This is simplified and would need more complex logic for accuracy
                    try:
                        pre_token_balance = tx_result.get('meta', {}).get('preTokenBalances', [])
                        post_token_balance = tx_result.get('meta', {}).get('postTokenBalances', [])
                        
                        if pre_token_balance and post_token_balance:
                            # Try to identify if token balance increased (buy) or decreased (sell)
                            for post_bal in post_token_balance:
                                if post_bal.get('mint') == mint:
                                    post_amount = int(post_bal.get('uiTokenAmount', {}).get('amount', 0))
                                    
                                    # Find matching pre-balance
                                    pre_amount = 0
                                    for pre_bal in pre_token_balance:
                                        if pre_bal.get('mint') == mint:
                                            pre_amount = int(pre_bal.get('uiTokenAmount', {}).get('amount', 0))
                                    
                                    # Determine type based on balance change
                                    if post_amount > pre_amount:
                                        tx_type = "buy"
                                        amount = (post_amount - pre_amount) / 10**9  # Convert from lamports
                                        # Estimated price based on SOL transfer
                                        sol_change = tx_result.get('meta', {}).get('postBalances', [0])[0] - tx_result.get('meta', {}).get('preBalances', [0])[0]
                                        if sol_change != 0:
                                            price = abs(sol_change / 10**9) / amount
                                    elif post_amount < pre_amount:
                                        tx_type = "sell"
                                        amount = (pre_amount - post_amount) / 10**9  # Convert from lamports
                                        # Estimated price based on SOL transfer
                                        sol_change = tx_result.get('meta', {}).get('postBalances', [0])[0] - tx_result.get('meta', {}).get('preBalances', [0])[0]
                                        if sol_change != 0:
                                            price = abs(sol_change / 10**9) / amount
                    except Exception as e:
                        logger.error(f"Error parsing transaction: {str(e)}")
                    
                    # Only add if we could determine a clear buy or sell
                    if tx_type in ["buy", "sell"] and price > 0 and amount > 0:
                        transactions.append({
                            "tx_hash": signature,
                            "wallet_address": wallet_address,
                            "token_address": mint,
                            "token_symbol": token_symbol,
                            "amount": amount,
                            "price": price,
                            "timestamp": tx_result.get('blockTime', 0),
                            "type": tx_type
                        })
            except Exception as e:
                logger.error(f"Error processing token account: {str(e)}")
                continue
                
        return transactions
        
    except Exception as e:
        logger.error(f"Error getting Solana transactions: {str(e)}")
        return []  # No fallback to sample data anymore

async def get_base_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Get real transaction history for a Base wallet address using Alchemy API
    """
    try:
        # Validate address
        if not is_valid_eth_address(wallet_address):
            raise ValueError("Invalid Ethereum/Base wallet address")
        
        logger.info(f"Fetching real transactions for Base wallet: {wallet_address}")
        
        if not ALCHEMY_API_KEY:
            logger.error("Alchemy API key not provided")
            return []
        
        # Using Alchemy API for Base blockchain
        alchemy_url = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        
        # Get token balances for the wallet
        token_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTokenBalances",
            "params": [wallet_address, "erc20"]
        }
        
        token_response = requests.post(alchemy_url, json=token_payload)
        token_data = token_response.json()
        
        if 'error' in token_data:
            logger.error(f"Error from Alchemy API: {token_data['error']}")
            return []
        
        token_addresses = []
        for balance in token_data.get('result', {}).get('tokenBalances', []):
            token_addresses.append(balance.get('contractAddress'))
        
        # Process all tokens, not just memecoins
        all_transactions = []
        
        # Get transfers for each token
        for token_address in token_addresses:
            # Try to get token info using Alchemy's getTokenMetadata
            token_meta_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "alchemy_getTokenMetadata",
                "params": [token_address]
            }
            
            token_meta_response = requests.post(alchemy_url, json=token_meta_payload)
            token_meta_data = token_meta_response.json()
            
            if 'result' in token_meta_data and token_meta_data['result'].get('symbol'):
                token_symbol = token_meta_data['result'].get('symbol')
            else:
                # Use first 6 chars of address if we can't get the symbol
                token_symbol = token_address[2:8]
            
            # Get transfers for this token
            transfers_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "alchemy_getAssetTransfers",
                "params": [
                    {
                        "fromBlock": "0x0",  # From genesis block (all history)
                        "toBlock": "latest",
                        "category": ["erc20"],
                        "contractAddresses": [token_address],
                        "withMetadata": True,
                        "excludeZeroValue": True,
                        "maxCount": "0x64",  # Increase to 100 transfers (0x64 = 100 in hex)
                        "order": "desc"  # Most recent first
                    }
                ]
            }
            
            transfers_response = requests.post(alchemy_url, json=transfers_payload)
            transfers_data = transfers_response.json()
            
            if 'error' in transfers_data:
                logger.error(f"Error from Alchemy API: {transfers_data['error']}")
                continue
            
            transfers = transfers_data.get('result', {}).get('transfers', [])
            
            # Process transfers to identify buys and sells
            for transfer in transfers:
                try:
                    tx_hash = transfer.get('hash')
                    timestamp = int(transfer.get('metadata', {}).get('blockTimestamp', "0").replace("-", "").replace(":", "").replace("+", "").replace("T", "").replace("Z", ""))
                    
                    # Get detailed transaction receipt to determine if this is a buy or sell
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash]
                    }
                    
                    tx_response = requests.post(alchemy_url, json=tx_payload)
                    tx_data = tx_response.json()
                    
                    if 'error' in tx_data:
                        logger.error(f"Error from Alchemy API: {tx_data['error']}")
                        continue
                    
                    receipt = tx_data.get('result', {})
                    logs = receipt.get('logs', [])
                    
                    # Get transaction details
                    tx_details_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getTransactionByHash",
                        "params": [tx_hash]
                    }
                    
                    tx_details_response = requests.post(alchemy_url, json=tx_details_payload)
                    tx_details_data = tx_details_response.json()
                    
                    if 'error' in tx_details_data:
                        logger.error(f"Error from Alchemy API: {tx_details_data['error']}")
                        continue
                    
                    tx_details = tx_details_data.get('result', {})
                    
                    # Try to determine if this is a buy or sell - much less restrictive logic
                    tx_type = "unknown"
                    amount = float(transfer.get('value', 0))
                    price = 0.0
                    
                    # Determine if this is a buy or sell based on the direction of the transfer
                    wallet_address_lower = wallet_address.lower()
                    from_address = transfer.get('from', "").lower()
                    to_address = transfer.get('to', "").lower()
                    
                    # For any transaction involving the wallet, consider it a potentially valid trade
                    if wallet_address_lower == from_address:
                        # Wallet is sending tokens - likely a sell
                        tx_type = "sell"
                    elif wallet_address_lower == to_address:
                        # Wallet is receiving tokens - likely a buy
                        tx_type = "buy"
                    
                    # Try to determine price
                    if tx_type in ["buy", "sell"]:
                        # Look for ETH value in the transaction
                        eth_value = int(tx_details.get('value', "0x0"), 16) / 10**18
                        gas_price = int(tx_details.get('gasPrice', "0x0"), 16) / 10**9
                        gas_used = int(receipt.get('gasUsed', "0x0"), 16)
                        gas_cost = gas_price * gas_used / 10**9
                        
                        # If there's ETH value, use it to estimate price
                        if eth_value > 0 and amount > 0:
                            price = eth_value / amount
                        # Otherwise try to derive from gas cost (very rough approximation)
                        elif gas_cost > 0 and amount > 0:
                            price = gas_cost / amount
                    
                    # Only add transactions where we could determine a type and price
                    if tx_type in ["buy", "sell"] and amount > 0:
                        # If price is zero, set a minimal price to avoid division by zero later
                        if price <= 0:
                            price = 0.0000001  # Minimal price as placeholder
                        
                        all_transactions.append({
                            "tx_hash": tx_hash,
                            "wallet_address": wallet_address,
                            "token_address": token_address,
                            "token_symbol": token_symbol,
                            "amount": amount,
                            "price": price,
                            "timestamp": int(datetime.strptime(transfer.get('metadata', {}).get('blockTimestamp', "2023-01-01T00:00:00Z"), "%Y-%m-%dT%H:%M:%SZ").timestamp()),
                            "type": tx_type
                        })
                except Exception as e:
                    logger.error(f"Error processing transfer: {str(e)}")
                    continue
        
        return all_transactions
                
    except Exception as e:
        logger.error(f"Error getting Base transactions: {str(e)}")
        return []  # No fallback to sample data anymore

async def analyze_memecoin_trades(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze memecoin trades to calculate statistics
    """
    if not transactions:
        logger.info("No transactions found for analysis")
        return {
            "best_trade_profit": 0.0,
            "best_trade_token": "",
            "best_multiplier": 0.0,
            "best_multiplier_token": "",
            "all_time_pnl": 0.0,
            "worst_trade_loss": 0.0,
            "worst_trade_token": ""
        }
    
    # Group transactions by token
    token_transactions = {}
    for tx in transactions:
        token = tx["token_symbol"]
        if token not in token_transactions:
            token_transactions[token] = []
        token_transactions[token].append(tx)
    
    # Calculate statistics
    best_trade_profit = 0.0
    best_trade_token = ""
    best_multiplier = 0.0
    best_multiplier_token = ""
    all_time_pnl = 0.0
    worst_trade_loss = 0.0
    worst_trade_token = ""
    
    # Process each token separately
    for token, txs in token_transactions.items():
        # Sort transactions by timestamp
        sorted_txs = sorted(txs, key=lambda x: x["timestamp"])
        
        # Separate buys and sells
        buys = [tx for tx in sorted_txs if tx["type"] == "buy"]
        sells = [tx for tx in sorted_txs if tx["type"] == "sell"]
        
        # Skip tokens with no buy/sell pairs
        if not buys or not sells:
            continue
        
        # Calculate trades
        token_pnl = 0.0
        token_best_trade = 0.0
        token_worst_trade = 0.0
        token_best_multiplier = 0.0
        
        # Process buys and sells to pair them into trades
        remaining_buys = []
        for buy in buys:
            remaining_buys.append({
                "price": buy["price"],
                "amount": buy["amount"],
                "timestamp": buy["timestamp"]
            })
        
        for sell in sells:
            sell_price = sell["price"]
            sell_amount = sell["amount"]
            sell_timestamp = sell["timestamp"]
            
            # Match with available buys (oldest first)
            while sell_amount > 0 and remaining_buys:
                buy = remaining_buys[0]
                
                # Determine matched amount
                matched_amount = min(buy["amount"], sell_amount)
                
                # Calculate PnL for this matched portion
                buy_value = matched_amount * buy["price"]
                sell_value = matched_amount * sell_price
                trade_pnl = sell_value - buy_value
                
                # Update token PnL
                token_pnl += trade_pnl
                
                # Check if this is the best or worst trade
                if trade_pnl > token_best_trade:
                    token_best_trade = trade_pnl
                
                if trade_pnl < token_worst_trade:
                    token_worst_trade = trade_pnl
                
                # Calculate multiplier (avoid division by zero)
                if buy_value > 0:
                    multiplier = sell_value / buy_value
                    if multiplier > token_best_multiplier:
                        token_best_multiplier = multiplier
                
                # Update remaining amounts
                buy["amount"] -= matched_amount
                sell_amount -= matched_amount
                
                # Remove buy if fully used
                if buy["amount"] <= 0:
                    remaining_buys.pop(0)
        
        # Update global stats if token has noteworthy stats
        if token_best_trade > best_trade_profit:
            best_trade_profit = token_best_trade
            best_trade_token = token
        
        if token_worst_trade < worst_trade_loss:
            worst_trade_loss = token_worst_trade
            worst_trade_token = token
        
        if token_best_multiplier > best_multiplier:
            best_multiplier = token_best_multiplier
            best_multiplier_token = token
        
        # Add to total PnL
        all_time_pnl += token_pnl
    
    return {
        "best_trade_profit": best_trade_profit,
        "best_trade_token": best_trade_token,
        "best_multiplier": best_multiplier,
        "best_multiplier_token": best_multiplier_token,
        "all_time_pnl": all_time_pnl,
        "worst_trade_loss": worst_trade_loss,
        "worst_trade_token": worst_trade_token
    }

# API routes
@api_router.get("/")
async def root():
    return {"message": "Pain or Gains API - Memecoin Analysis Tool"}

@api_router.post("/analyze")
async def analyze_wallet(search_query: SearchQuery) -> TradeStats:
    """
    Analyze a wallet's memecoin trades and return statistics using ONLY real blockchain data
    """
    wallet_address = search_query.wallet_address
    blockchain = search_query.blockchain
    
    logger.info(f"Analyzing {blockchain} wallet: {wallet_address}")
    
    # Extra validation check to catch invalid addresses
    if blockchain == "solana" and not is_valid_solana_address(wallet_address):
        raise HTTPException(status_code=400, detail="Invalid Solana wallet address")
    elif blockchain == "base" and not is_valid_eth_address(wallet_address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum/Base wallet address")
    
    try:
        # Get transactions based on blockchain
        if blockchain == "solana":
            transactions = await get_solana_transactions(wallet_address)
        else:  # blockchain == "base"
            transactions = await get_base_transactions(wallet_address)
        
        # Log the actual transactions found
        logger.info(f"Found {len(transactions)} transactions for {blockchain} wallet: {wallet_address}")
        for tx in transactions[:5]:  # Log first 5 transactions for debugging
            logger.info(f"Transaction: {tx['token_symbol']} {tx['type']} {tx['amount']} at {tx['price']}")
        
        # Don't show any results if no transactions found
        if not transactions:
            logger.info(f"No transactions found for {blockchain} wallet: {wallet_address}")
            return TradeStats(
                id=str(uuid.uuid4()),
                wallet_address=wallet_address,
                blockchain=blockchain,
                best_trade_profit=0.0,
                best_trade_token="",
                best_multiplier=0.0,
                best_multiplier_token="",
                all_time_pnl=0.0,
                worst_trade_loss=0.0,
                worst_trade_token="",
                timestamp=datetime.now()
            )
        
        # Analyze trades
        stats = await analyze_memecoin_trades(transactions)
        
        # Create response
        result = TradeStats(
            id=str(uuid.uuid4()),
            wallet_address=wallet_address,
            blockchain=blockchain,
            best_trade_profit=stats["best_trade_profit"],
            best_trade_token=stats["best_trade_token"],
            best_multiplier=stats["best_multiplier"],
            best_multiplier_token=stats["best_multiplier_token"],
            all_time_pnl=stats["all_time_pnl"],
            worst_trade_loss=stats["worst_trade_loss"],
            worst_trade_token=stats["worst_trade_token"],
            timestamp=datetime.now()
        )
        
        # Store in MongoDB
        await collection.insert_one(result.dict())
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing wallet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing wallet: {str(e)}")

@api_router.get("/leaderboard/{stat_type}")
async def get_leaderboard(stat_type: str, blockchain: str = Query(...)):
    """
    Get leaderboard data for a specific statistic
    """
    try:
        if blockchain not in ["solana", "base"]:
            raise HTTPException(status_code=400, detail="Invalid blockchain")
        
        stat_map = {
            "best_trade": ("best_trade_profit", -1),
            "best_multiplier": ("best_multiplier", -1),
            "all_time_pnl": ("all_time_pnl", -1),
            "worst_trade": ("worst_trade_loss", 1)  # For worst trade, lower (more negative) is higher rank
        }
        
        if stat_type not in stat_map:
            raise HTTPException(status_code=400, detail="Invalid stat_type")
            
        field, sort_order = stat_map[stat_type]
        
        # Clear the collection of duplicates before returning the leaderboard
        # This aggregation gets the latest analysis for each wallet
        pipeline = [
            {"$match": {"blockchain": blockchain}},
            {"$sort": {"timestamp": -1}},  # Sort by most recent timestamp
            {"$group": {
                "_id": "$wallet_address",
                "doc": {"$first": "$$ROOT"}  # Keep only the most recent document
            }},
            {"$replaceRoot": {"newRoot": "$doc"}}
        ]
        
        # Execute the aggregation and store results in a list
        results = []
        async for doc in collection.aggregate(pipeline):
            # Only include entries with data
            if doc[field] != 0:
                results.append(doc)
                
        # Sort the results by the appropriate field
        results.sort(key=lambda x: x[field], reverse=(sort_order == -1))
        
        # Limit to top 10
        results = results[:10]
        
        # Format the response
        leaderboard = []
        rank = 1
        
        for doc in results:
            value = doc[field]
            
            # Get the correct token based on stat type
            if stat_type == "best_trade":
                token = doc.get("best_trade_token", "")
            elif stat_type == "worst_trade":
                token = doc.get("worst_trade_token", "")
            elif stat_type == "best_multiplier":
                token = doc.get("best_multiplier_token", "")
            elif stat_type == "all_time_pnl":
                token = value  # For PnL, just duplicate the value
                
            leaderboard.append({
                "wallet_address": doc["wallet_address"],
                "value": value,
                "token": token,
                "rank": rank
            })
            rank += 1
            
        return leaderboard
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting leaderboard: {str(e)}")

# Mount the API router
app.mount("/api", api_router)

# MongoDB connection events
@app.on_event("startup")
async def startup_db_client():
    await db.command("ping")
    logger.info("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
