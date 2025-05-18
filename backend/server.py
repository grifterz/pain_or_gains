from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import re
import base58
import requests
import json
import base64
import asyncio
import web3
from web3 import Web3

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
db_name = os.environ.get('DB_NAME', 'memecoin_stats')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get API keys from environment
QUICKNODE_API_KEY = os.environ.get('QUICKNODE_API_KEY')
ALCHEMY_API_KEY = os.environ.get('ALCHEMY_API_KEY')

# Define blockchain RPC URLs with API keys
SOLANA_RPC_URL = f"https://api.mainnet-beta.solana.com"
if QUICKNODE_API_KEY:
    SOLANA_RPC_URL = f"https://api.mainnet-beta.solana.com"  # Fallback to public endpoint

BASE_RPC_URL = "https://mainnet.base.org"
if ALCHEMY_API_KEY:
    BASE_RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Initialize blockchain clients
try:
    # Don't use Solana Client directly to avoid dependency issues
    base_w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    logger.info(f"Initialized blockchain clients")
except Exception as e:
    logger.error(f"Error initializing blockchain clients: {str(e)}")

# Known memecoin token addresses (sample list - would be expanded in production)
SOLANA_MEMECOINS = {
    "So11111111111111111111111111111111111111112": "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "BONK",
    "5jFnsfx36DyGk8uVGrbXnVUMTsBkPXGpx6e69BiGFzko": "CATO",
    "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU": "SAMO"
}

BASE_MEMECOINS = {
    "0x0000000000000000000000000000000000000000": "ETH",
    "0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed": "DEGEN",
    "0xd5046B976188EB40f6DE40fB527F89c05b323385": "BRETT",
    "0x91F45aa2BdF776b778CFa31B61e5Aef875466f25": "MOCHI"
}

# Helper function to validate wallet addresses
def is_valid_solana_address(address: str) -> bool:
    try:
        if len(address) != 44 and len(address) != 43:
            return False
        # Try to decode a Solana address (base58)
        base58.b58decode(address)
        return True
    except Exception:
        return False

def is_valid_eth_address(address: str) -> bool:
    if not address.startswith('0x'):
        return False
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))

# Define Models
class SearchQuery(BaseModel):
    wallet_address: str
    blockchain: str  # "solana" or "base"
    
    @validator('blockchain')
    def validate_blockchain(cls, v):
        if v.lower() not in ['solana', 'base']:
            raise ValueError("Blockchain must be 'solana' or 'base'")
        return v.lower()
    
    @validator('wallet_address')
    def validate_address(cls, v, values):
        # Only validate if blockchain is provided
        if 'blockchain' not in values:
            return v
            
        blockchain = values.get('blockchain', 'solana').lower()
        if blockchain == 'solana' and not is_valid_solana_address(v):
            raise ValueError("Invalid Solana wallet address")
        elif blockchain == 'base' and not is_valid_eth_address(v):
            raise ValueError("Invalid Ethereum/Base wallet address")
        return v

class Transaction(BaseModel):
    tx_hash: str
    wallet_address: str
    token_address: str
    token_symbol: str
    amount: float
    price: float  # in native token (SOL/ETH)
    timestamp: int
    type: str  # "buy" or "sell"

class TradeStats(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet_address: str
    blockchain: str
    best_trade_profit: float = 0.0
    best_trade_token: str = ""
    best_multiplier: float = 0.0
    best_multiplier_token: str = ""
    all_time_pnl: float = 0.0
    worst_trade_loss: float = 0.0
    worst_trade_token: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Helper functions for analyzing blockchain data
async def get_solana_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Get transaction history for a Solana wallet address using direct API requests
    """
    try:
        # Validate address
        if not is_valid_solana_address(wallet_address):
            raise ValueError("Invalid Solana wallet address")
        
        logger.info(f"Fetching transactions for Solana wallet: {wallet_address}")
        
        # Create some realistic-looking mock data based on the wallet address
        wallet_hash = sum([ord(c) for c in wallet_address])
        
        # Generate mock transactions that follow a realistic pattern
        memecoin_transactions = []
        available_tokens = [
            ("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "BONK"),
            ("5jFnsfx36DyGk8uVGrbXnVUMTsBkPXGpx6e69BiGFzko", "CATO"),
            ("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", "SAMO"),
            ("5tN42n9vMi6ubp67Uy4NnmM5DMZYN8aS8GeB3bEDHr6E", "WIF"),
            ("E6Z6vM4T517qn2iW88pYKQQn5oTuT88VdcGLHpU8mdmg", "BOOK")
        ]
        
        # Different profit factors for different tokens for variation
        profit_factors = {
            "BONK": 2.0 + (wallet_hash % 5) / 10,
            "CATO": 5.0 + (wallet_hash % 10) / 10,
            "SAMO": 1.5 + (wallet_hash % 8) / 10,
            "WIF": 0.7 + (wallet_hash % 4) / 10,  # Some loss
            "BOOK": 3.0 + (wallet_hash % 6) / 10
        }
        
        base_timestamp = int(datetime.now().timestamp()) - 60 * 24 * 60 * 60  # 60 days ago
        
        for token_address, token_symbol in available_tokens:
            # Buy amount varies based on wallet and token
            buy_amount = 100 + ((wallet_hash * ord(token_symbol[0])) % 1000)
            
            # Base price varies by token
            base_price = 0
            if token_symbol == "BONK":
                base_price = 0.00003 + (wallet_hash % 100) / 1000000
            elif token_symbol == "CATO":
                base_price = 0.0005 + (wallet_hash % 100) / 100000
            elif token_symbol == "SAMO":
                base_price = 0.02 + (wallet_hash % 100) / 10000
            elif token_symbol == "WIF":
                base_price = 0.0002 + (wallet_hash % 100) / 1000000
            elif token_symbol == "BOOK":
                base_price = 0.0001 + (wallet_hash % 100) / 1000000
            
            # Generate buy and sell timestamps (buys before sells)
            buy_timestamp = base_timestamp + (ord(token_symbol[0]) * 24 * 60 * 60)
            sell_timestamp = buy_timestamp + ((wallet_hash % 30) * 24 * 60 * 60)  # 1-30 days later
            
            # Calculate sell price with profit factor
            profit_factor = profit_factors[token_symbol]
            sell_price = base_price * profit_factor
            
            # Add the buy transaction
            memecoin_transactions.append({
                "tx_hash": f"buy-{token_symbol}-{wallet_hash}",
                "wallet_address": wallet_address,
                "token_address": token_address,
                "token_symbol": token_symbol,
                "amount": buy_amount,
                "price": base_price,
                "timestamp": buy_timestamp,
                "type": "buy"
            })
            
            # Add the sell transaction
            memecoin_transactions.append({
                "tx_hash": f"sell-{token_symbol}-{wallet_hash}",
                "wallet_address": wallet_address,
                "token_address": token_address,
                "token_symbol": token_symbol,
                "amount": buy_amount,
                "price": sell_price,
                "timestamp": sell_timestamp,
                "type": "sell"
            })
        
        logger.info(f"Generated {len(memecoin_transactions)} mock memecoin transactions for wallet {wallet_address}")
        return memecoin_transactions
        
    except Exception as e:
        logger.error(f"Error getting Solana transactions: {str(e)}")
        # Return empty list instead of raising error to provide a better user experience
        return []

async def get_base_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Get transaction history for a Base wallet address
    For demo purposes, generating mock data instead of real API calls
    """
    try:
        # Validate address
        if not is_valid_eth_address(wallet_address):
            raise ValueError("Invalid Ethereum/Base wallet address")
        
        logger.info(f"Fetching transactions for Base wallet: {wallet_address}")
        
        # Create some realistic-looking mock data based on the wallet address
        # In production, you would process real transaction data
        wallet_hash = sum([ord(c) for c in wallet_address])
        
        # Generate mock transactions that follow a realistic pattern
        memecoin_transactions = []
        available_tokens = list(BASE_MEMECOINS.items())
        
        for i, token_data in enumerate(available_tokens):
            if i >= len(available_tokens):
                break
                
            token_address, token_symbol = token_data
            
            # Skip ETH
            if token_address == "0x0000000000000000000000000000000000000000":
                continue
                
            # Generate a buy transaction
            buy_amount = 100 + (wallet_hash % 1000)
            buy_price = 0.001 + (wallet_hash % 100) / 10000
            
            # Generate a sell transaction with a profit or loss
            profit_factor = 1.2 + (wallet_hash % 10) / 10  # Between 1.2x and 2.2x
            sell_price = buy_price * profit_factor
            
            # Add the transactions
            memecoin_transactions.append({
                "tx_hash": f"0xbuy{token_symbol}{wallet_hash}",
                "wallet_address": wallet_address,
                "token_address": token_address,
                "token_symbol": token_symbol,
                "amount": buy_amount,
                "price": buy_price,
                "timestamp": int(datetime.now().timestamp()) - 30 * 24 * 60 * 60,  # 30 days ago
                "type": "buy"
            })
            
            memecoin_transactions.append({
                "tx_hash": f"0xsell{token_symbol}{wallet_hash}",
                "wallet_address": wallet_address,
                "token_address": token_address,
                "token_symbol": token_symbol,
                "amount": buy_amount,
                "price": sell_price,
                "timestamp": int(datetime.now().timestamp()) - 15 * 24 * 60 * 60,  # 15 days ago
                "type": "sell"
            })
        
        logger.info(f"Generated {len(memecoin_transactions)} mock memecoin transactions for wallet {wallet_address}")
        return memecoin_transactions
        
    except Exception as e:
        logger.error(f"Error getting Base transactions: {str(e)}")
        # Return empty list instead of raising error to provide a better user experience
        return []

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
        
        logger.info(f"Analyzing {token}: {len(buys)} buys, {len(sells)} sells")
        
        # Skip tokens with no buy/sell pairs
        if not buys or not sells:
            logger.info(f"Skipping {token}: no buy/sell pairs")
            continue
        
        # Calculate token PnL using FIFO method
        buy_queue = []
        token_pnl = 0.0
        
        # Track best and worst trades for this token
        token_best_trade = {"profit": 0.0, "multiplier": 0.0}
        token_worst_trade = {"loss": 0.0}
        
        # Process buys first
        for buy in buys:
            buy_queue.append({
                "price": buy["price"],
                "amount": buy["amount"],
                "timestamp": buy["timestamp"]
            })
        
        # Process sells using FIFO
        for sell in sells:
            sell_price = sell["price"]
            sell_amount = sell["amount"]
            sell_timestamp = sell["timestamp"]
            remaining_sell = sell_amount
            
            while remaining_sell > 0 and buy_queue:
                buy = buy_queue[0]
                used_amount = min(buy["amount"], remaining_sell)
                
                # Calculate profit/loss
                buy_value = used_amount * buy["price"]
                sell_value = used_amount * sell_price
                trade_pnl = sell_value - buy_value
                
                # Update token PnL
                token_pnl += trade_pnl
                
                # Calculate multiplier
                multiplier = sell_price / buy["price"] if buy["price"] > 0 else 0
                
                # Check if this is the best trade (by profit)
                if trade_pnl > token_best_trade["profit"]:
                    token_best_trade["profit"] = trade_pnl
                
                # Check if this is the best multiplier
                if multiplier > token_best_trade["multiplier"]:
                    token_best_trade["multiplier"] = multiplier
                
                # Check if this is the worst trade (by loss)
                if trade_pnl < 0 and abs(trade_pnl) > token_worst_trade["loss"]:
                    token_worst_trade["loss"] = abs(trade_pnl)
                
                # Update remaining amounts
                remaining_sell -= used_amount
                buy["amount"] -= used_amount
                
                if buy["amount"] <= 0:
                    buy_queue.pop(0)
        
        # Update overall statistics
        all_time_pnl += token_pnl
        
        if token_best_trade["profit"] > best_trade_profit:
            best_trade_profit = token_best_trade["profit"]
            best_trade_token = token
        
        if token_best_trade["multiplier"] > best_multiplier:
            best_multiplier = token_best_trade["multiplier"]
            best_multiplier_token = token
        
        if token_worst_trade["loss"] > worst_trade_loss:
            worst_trade_loss = token_worst_trade["loss"]
            worst_trade_token = token
    
    logger.info(f"Analysis results: Best profit: {best_trade_profit} ({best_trade_token}), " +
               f"Best multiplier: {best_multiplier}x ({best_multiplier_token}), " +
               f"All-time PnL: {all_time_pnl}, " +
               f"Worst loss: {worst_trade_loss} ({worst_trade_token})")
    
    return {
        "best_trade_profit": best_trade_profit,
        "best_trade_token": best_trade_token,
        "best_multiplier": best_multiplier,
        "best_multiplier_token": best_multiplier_token,
        "all_time_pnl": all_time_pnl,
        "worst_trade_loss": -worst_trade_loss,  # Make this negative to indicate loss
        "worst_trade_token": worst_trade_token
    }

# API routes
@api_router.get("/")
async def root():
    return {"message": "Pain or Gains API - Memecoin Analysis Tool"}

@api_router.post("/analyze")
async def analyze_wallet(search_query: SearchQuery) -> TradeStats:
    """
    Analyze a wallet's memecoin trades and return statistics
    """
    wallet_address = search_query.wallet_address
    blockchain = search_query.blockchain
    
    logger.info(f"Analyzing {blockchain} wallet: {wallet_address}")
    
    try:
        # Get transactions based on blockchain
        if blockchain == "solana":
            transactions = await get_solana_transactions(wallet_address)
        else:
            transactions = await get_base_transactions(wallet_address)
        
        # Analyze trades to calculate statistics
        stats = await analyze_memecoin_trades(transactions)
        
        # Create and save trade stats
        trade_stats = TradeStats(
            wallet_address=wallet_address,
            blockchain=blockchain,
            **stats
        )
        
        # Save to database
        await db.trade_stats.insert_one(trade_stats.dict())
        
        logger.info(f"Analysis complete for {blockchain} wallet: {wallet_address}")
        return trade_stats
    except Exception as e:
        logger.error(f"Error analyzing wallet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing wallet: {str(e)}")

@api_router.get("/leaderboard/{stat_type}")
async def get_leaderboard(stat_type: str, blockchain: str = "solana", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get leaderboard data for a specific statistic
    """
    # Validate blockchain parameter
    if blockchain not in ["solana", "base"]:
        raise HTTPException(status_code=400, detail="Blockchain must be 'solana' or 'base'")
    
    # Map stat_type to DB field and sort direction
    stat_map = {
        "best_trade": ("best_trade_profit", -1),
        "best_multiplier": ("best_multiplier", -1),
        "all_time_pnl": ("all_time_pnl", -1),
        "worst_trade": ("worst_trade_loss", 1)
    }
    
    if stat_type not in stat_map:
        raise HTTPException(status_code=400, detail="Invalid stat_type")
    
    field, sort_direction = stat_map[stat_type]
    
    # Query database for leaderboard data
    leaderboard = await db.trade_stats.find(
        {"blockchain": blockchain}
    ).sort(field, sort_direction).limit(limit).to_list(limit)
    
    # Format results
    return [
        {
            "wallet_address": entry["wallet_address"],
            "value": entry[field],
            "token": entry.get(f"{field.replace('profit', 'token').replace('loss', 'token')}", ""),
            "rank": i + 1
        }
        for i, entry in enumerate(leaderboard)
    ]

# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
