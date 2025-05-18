from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import json
import os
import re
import uuid
import requests
import random
from datetime import datetime
import sys

# Import our token finder and blockchain fetcher
sys.path.append("/app/backend")
from token_finder import get_token_name
from blockchain_fetcher import fetch_wallet_transactions

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
transactions_collection = db["transactions"]
positions_collection = db["positions"]
wallets_collection = db["wallets"]

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

async def store_transactions(wallet_address: str, blockchain: str, transactions: List[Dict[str, Any]]):
    """
    Store wallet transactions in MongoDB
    """
    if not transactions:
        return
    
    logger.info(f"Storing {len(transactions)} transactions for {blockchain} wallet: {wallet_address}")
    
    # Store each transaction
    for tx in transactions:
        # Use tx_hash as a unique identifier
        await transactions_collection.update_one(
            {"tx_hash": tx["tx_hash"], "wallet_address": wallet_address},
            {"$set": tx},
            upsert=True
        )
    
    # Update wallet record
    await wallets_collection.update_one(
        {"address": wallet_address, "blockchain": blockchain},
        {
            "$set": {
                "last_updated": datetime.now(),
                "transaction_count": len(transactions)
            }
        },
        upsert=True
    )

async def get_stored_transactions(wallet_address: str, blockchain: str) -> List[Dict[str, Any]]:
    """
    Get stored transactions for a wallet from MongoDB
    """
    cursor = transactions_collection.find({"wallet_address": wallet_address})
    return await cursor.to_list(length=1000)  # Limit to 1000 transactions

async def analyze_transactions(transactions):
    """
    Analyze token trades to calculate statistics
    """
    if not transactions:
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
    token_metadata = {}
    
    for tx in transactions:
        token = tx["token_symbol"]
        if token not in token_transactions:
            token_transactions[token] = []
            token_metadata[token] = {
                "address": tx["token_address"],
                "name": tx["token_name"],
                "symbol": tx["token_symbol"]
            }
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
    
    # Get token metadata for statistics
    stats = {
        "best_trade_profit": best_trade_profit,
        "best_trade_token": best_trade_token,
        "best_multiplier": best_multiplier,
        "best_multiplier_token": best_multiplier_token,
        "all_time_pnl": all_time_pnl,
        "worst_trade_loss": worst_trade_loss,
        "worst_trade_token": worst_trade_token,
        "token_metadata": token_metadata
    }
    
    return stats

# API routes
@api_router.get("/")
async def root():
    return {"message": "Pain or Gains API - Memecoin Analysis Tool"}

@api_router.post("/analyze")
async def analyze_wallet(search_query: SearchQuery) -> TradeStats:
    """
    Analyze a wallet's token trades and return statistics
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
        # Check if we have cached wallet data
        wallet_doc = await wallets_collection.find_one({"address": wallet_address, "blockchain": blockchain})
        
        # Get transactions - either from cache or fetch new ones
        if wallet_doc and "last_updated" in wallet_doc:
            last_updated = wallet_doc["last_updated"]
            if (datetime.now() - last_updated).total_seconds() < 3600:  # 1 hour cache
                logger.info(f"Using cached transactions for {wallet_address}")
                transactions = await get_stored_transactions(wallet_address, blockchain)
            else:
                # Refresh if data is over an hour old
                logger.info(f"Refreshing transactions for {wallet_address}")
                transactions = fetch_wallet_transactions(wallet_address, blockchain)
                await store_transactions(wallet_address, blockchain, transactions)
        else:
            # Fetch new transactions
            logger.info(f"Fetching new transactions for {wallet_address}")
            transactions = fetch_wallet_transactions(wallet_address, blockchain)
            await store_transactions(wallet_address, blockchain, transactions)
        
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
        stats = await analyze_transactions(transactions)
        
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

@api_router.get("/wallet/{wallet_address}")
async def get_wallet_details(wallet_address: str, blockchain: str = Query(...)):
    """
    Get wallet details with token positions
    """
    try:
        logger.info(f"Getting details for {blockchain} wallet: {wallet_address}")
        
        # Extra validation check to catch invalid addresses
        if blockchain == "solana" and not is_valid_solana_address(wallet_address):
            raise HTTPException(status_code=400, detail="Invalid Solana wallet address")
        elif blockchain == "base" and not is_valid_eth_address(wallet_address):
            raise HTTPException(status_code=400, detail="Invalid Ethereum/Base wallet address")
        
        # Check if we have cached wallet data
        wallet_doc = await wallets_collection.find_one({"address": wallet_address, "blockchain": blockchain})
        
        # Get transactions - either from cache or fetch new ones
        if wallet_doc and "last_updated" in wallet_doc:
            last_updated = wallet_doc["last_updated"]
            if (datetime.now() - last_updated).total_seconds() < 3600:  # 1 hour cache
                logger.info(f"Using cached transactions for {wallet_address}")
                transactions = await get_stored_transactions(wallet_address, blockchain)
            else:
                # Refresh if data is over an hour old
                logger.info(f"Refreshing transactions for {wallet_address}")
                transactions = fetch_wallet_transactions(wallet_address, blockchain)
                await store_transactions(wallet_address, blockchain, transactions)
        else:
            # Fetch new transactions
            logger.info(f"Fetching new transactions for {wallet_address}")
            transactions = fetch_wallet_transactions(wallet_address, blockchain)
            await store_transactions(wallet_address, blockchain, transactions)
        
        # Process transactions to get token positions
        positions = []
        token_data = {}
        
        for tx in transactions:
            token_address = tx["token_address"]
            token_name = tx["token_name"]
            token_symbol = tx["token_symbol"]
            
            if token_address not in token_data:
                token_data[token_address] = {
                    "token_address": token_address,
                    "token_name": token_name,
                    "token_symbol": token_symbol,
                    "balance": 0,
                    "value": 0,
                    "cost_basis": 0,
                    "last_price": 0
                }
            
            # Update token data based on transaction type
            if tx["type"] == "buy":
                token_data[token_address]["balance"] += tx["amount"]
                token_data[token_address]["cost_basis"] += (tx["amount"] * tx["price"])
            elif tx["type"] == "sell":
                token_data[token_address]["balance"] -= tx["amount"]
            
            # Update last price
            if tx["price"] > 0:
                token_data[token_address]["last_price"] = tx["price"]
        
        # Calculate current value and create positions list
        for token_address, data in token_data.items():
            if data["balance"] > 0:
                data["value"] = data["balance"] * data["last_price"]
                positions.append(data)
        
        # Get trade stats
        stats = await analyze_transactions(transactions)
        
        # Remove token_metadata from stats for cleaner response
        if "token_metadata" in stats:
            del stats["token_metadata"]
        
        return {
            "wallet_address": wallet_address,
            "blockchain": blockchain,
            "positions": positions,
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error getting wallet details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting wallet details: {str(e)}")

@api_router.get("/leaderboard")
async def get_leaderboard(blockchain: str = Query(...), metric: str = Query(...)):
    """
    Get leaderboard data for a specific statistic
    """
    try:
        if blockchain not in ["solana", "base"]:
            raise HTTPException(status_code=400, detail="Invalid blockchain")
        
        stat_map = {
            "best_trade": ("best_trade_profit", -1, "best_trade_token"),
            "best_multiplier": ("best_multiplier", -1, "best_multiplier_token"),
            "all_time_pnl": ("all_time_pnl", -1, None),
            "worst_trade": ("worst_trade_loss", 1, "worst_trade_token")  # For worst trade, lower (more negative) is higher rank
        }
        
        if metric not in stat_map:
            raise HTTPException(status_code=400, detail="Invalid metric")
            
        field, sort_order, token_field = stat_map[metric]
        
        # Get top wallets from our database
        pipeline = [
            {"$match": {"blockchain": blockchain}},
            {"$sort": {field: sort_order}},
            {"$limit": 10}
        ]
        
        cursor = collection.aggregate(pipeline)
        leaderboard_entries = await cursor.to_list(length=10)
        
        # Format the results
        formatted_entries = []
        for entry in leaderboard_entries:
            token_symbol = entry.get(token_field, "")
            
            # Get token info if available
            token_address = ""
            token_name = ""
            
            # Look up in transactions collection
            if token_symbol:
                tx_query = {"token_symbol": token_symbol, "wallet_address": entry["wallet_address"]}
                tx = await transactions_collection.find_one(tx_query)
                if tx:
                    token_address = tx.get("token_address", "")
                    token_name = tx.get("token_name", "")
            
            formatted_entries.append({
                "wallet": entry["wallet_address"],
                "blockchain": entry["blockchain"],
                "token_address": token_address,
                "token_name": token_name,
                "token_symbol": token_symbol,
                "value": entry.get(field, 0)
            })
        
        return formatted_entries
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting leaderboard: {str(e)}")

# Mount the API router
app.mount("/api", api_router)

# Root endpoint
@app.get("/")
async def app_root():
    return {"message": "Pain or Gains API - Memecoin Analysis Tool. Access API at /api"}

# MongoDB connection events
@app.on_event("startup")
async def startup_db_client():
    await db.command("ping")
    logger.info("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
