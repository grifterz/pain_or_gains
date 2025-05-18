from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from solana.rpc.api import Client as SolanaClient
from web3 import Web3
import requests

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# Define blockchain RPC URLs (using public endpoints for now)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
BASE_RPC_URL = "https://mainnet.base.org"

# Initialize blockchain clients
solana_client = SolanaClient(SOLANA_RPC_URL)
base_w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# Define Models
class SearchQuery(BaseModel):
    wallet_address: str
    blockchain: str  # "solana" or "base"

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
async def get_solana_memecoin_trades(wallet_address: str) -> Dict[str, Any]:
    """
    Get memecoin trades for a Solana wallet address
    Note: In a real implementation, this would query the Solana blockchain
    and analyze the transactions to identify memecoin trades
    """
    # Mock implementation with simulated data
    # In a real-world scenario, we would query the Solana blockchain API 
    # and analyze the transactions to calculate these metrics
    
    # For demo purposes, we'll create some mock data based on the wallet address
    # In a production app, this would use proper token identifiers, price history, etc.
    wallet_hash = sum([ord(c) for c in wallet_address])
    
    best_trade_profit = (wallet_hash % 100) * 10.5
    best_multiplier = (wallet_hash % 20) + 1.5
    all_time_pnl = (wallet_hash % 200) - 50
    worst_trade_loss = (wallet_hash % 50) * -1
    
    return {
        "best_trade_profit": best_trade_profit,
        "best_trade_token": "BONK",
        "best_multiplier": best_multiplier,
        "best_multiplier_token": "CATO",
        "all_time_pnl": all_time_pnl,
        "worst_trade_loss": worst_trade_loss,
        "worst_trade_token": "DOGGO"
    }

async def get_base_memecoin_trades(wallet_address: str) -> Dict[str, Any]:
    """
    Get memecoin trades for a Base wallet address
    Note: In a real implementation, this would query the Base blockchain
    and analyze the transactions to identify memecoin trades
    """
    # Mock implementation with simulated data
    # In a real-world scenario, we would query the Base blockchain API 
    # and analyze the transactions to calculate these metrics
    
    # For demo purposes, we'll create some mock data based on the wallet address
    # In a production app, this would use proper token identifiers, price history, etc.
    wallet_hash = sum([ord(c) for c in wallet_address])
    
    best_trade_profit = (wallet_hash % 150) * 8.3
    best_multiplier = (wallet_hash % 15) + 2.5
    all_time_pnl = (wallet_hash % 300) - 100
    worst_trade_loss = (wallet_hash % 70) * -1
    
    return {
        "best_trade_profit": best_trade_profit,
        "best_trade_token": "BRETT",
        "best_multiplier": best_multiplier,
        "best_multiplier_token": "DEGEN",
        "all_time_pnl": all_time_pnl,
        "worst_trade_loss": worst_trade_loss,
        "worst_trade_token": "MOCHI"
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
    blockchain = search_query.blockchain.lower()
    
    # Validate blockchain parameter
    if blockchain not in ["solana", "base"]:
        raise HTTPException(status_code=400, detail="Blockchain must be 'solana' or 'base'")
    
    # Analyze trades based on blockchain
    if blockchain == "solana":
        trade_data = await get_solana_memecoin_trades(wallet_address)
    else:
        trade_data = await get_base_memecoin_trades(wallet_address)
    
    # Create and save trade stats
    trade_stats = TradeStats(
        wallet_address=wallet_address,
        blockchain=blockchain,
        **trade_data
    )
    
    # Save to database
    await db.trade_stats.insert_one(trade_stats.dict())
    
    return trade_stats

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
