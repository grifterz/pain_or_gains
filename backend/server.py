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
from solana.rpc.api import Client as SolanaClient
from web3 import Web3
import asyncio

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
    SOLANA_RPC_URL = f"https://mainnet.solana.quicknode.pro/{QUICKNODE_API_KEY}/"

BASE_RPC_URL = "https://mainnet.base.org"
if ALCHEMY_API_KEY:
    BASE_RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Initialize blockchain clients
solana_client = SolanaClient(SOLANA_RPC_URL)
base_w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

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
    
    @validator('wallet_address')
    def validate_address(cls, v, values):
        blockchain = values.get('blockchain', 'solana').lower()
        if blockchain == 'solana' and not is_valid_solana_address(v):
            raise ValueError("Invalid Solana wallet address")
        elif blockchain == 'base' and not is_valid_eth_address(v):
            raise ValueError("Invalid Ethereum/Base wallet address")
        return v
    
    @validator('blockchain')
    def validate_blockchain(cls, v):
        if v.lower() not in ['solana', 'base']:
            raise ValueError("Blockchain must be 'solana' or 'base'")
        return v.lower()

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
    Get transaction history for a Solana wallet address
    """
    try:
        # Validate address
        if not is_valid_solana_address(wallet_address):
            raise ValueError("Invalid Solana wallet address")
            
        # Get transaction signatures for the wallet
        signatures_response = solana_client.get_signatures_for_address(wallet_address)
        
        transactions = []
        memecoin_transactions = []
        
        # Process each transaction to identify memecoin transactions
        for sig_info in signatures_response.get('result', []):
            try:
                tx_hash = sig_info.get('signature')
                tx_info = solana_client.get_transaction(tx_hash)
                
                if not tx_info.get('result'):
                    continue
                
                # Get transaction details
                tx_data = tx_info.get('result', {})
                tx_meta = tx_data.get('meta', {})
                
                # Skip failed transactions
                if tx_meta.get('err'):
                    continue
                
                # Look for token transfers in pre and post token balances
                pre_token_balances = tx_meta.get('preTokenBalances', [])
                post_token_balances = tx_meta.get('postTokenBalances', [])
                
                # Skip if no token activity
                if not pre_token_balances and not post_token_balances:
                    continue
                
                # Check for memecoin token transfers
                for post_balance in post_token_balances:
                    mint = post_balance.get('mint')
                    
                    # Skip if not a known memecoin
                    if mint not in SOLANA_MEMECOINS:
                        continue
                    
                    # Find corresponding pre-balance to determine if buy or sell
                    pre_balance = next((b for b in pre_token_balances if b.get('mint') == mint), None)
                    
                    if not pre_balance:
                        # Token didn't exist before - this is a buy
                        amount = float(post_balance.get('uiTokenAmount', {}).get('uiAmount', 0))
                        tx_type = "buy"
                    else:
                        # Compare pre and post amounts
                        pre_amount = float(pre_balance.get('uiTokenAmount', {}).get('uiAmount', 0))
                        post_amount = float(post_balance.get('uiTokenAmount', {}).get('uiAmount', 0))
                        
                        if post_amount > pre_amount:
                            amount = post_amount - pre_amount
                            tx_type = "buy"
                        else:
                            amount = pre_amount - post_amount
                            tx_type = "sell"
                    
                    # Skip tiny transactions
                    if amount < 0.00001:
                        continue
                    
                    # Get price estimate from transaction value
                    # This is a simplified approach - in production you would use more precise methods
                    sol_change = abs(tx_meta.get('postBalances', [0])[0] - tx_meta.get('preBalances', [0])[0]) / 1_000_000_000
                    price = sol_change / amount if amount > 0 else 0
                    
                    # Create transaction record
                    memecoin_transactions.append({
                        "tx_hash": tx_hash,
                        "wallet_address": wallet_address,
                        "token_address": mint,
                        "token_symbol": SOLANA_MEMECOINS.get(mint, "Unknown"),
                        "amount": amount,
                        "price": price,  # Price in SOL
                        "timestamp": tx_data.get('blockTime', 0),
                        "type": tx_type
                    })
            except Exception as e:
                logger.error(f"Error processing Solana transaction {sig_info.get('signature')}: {str(e)}")
        
        return memecoin_transactions
    
    except Exception as e:
        logger.error(f"Error getting Solana transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching Solana transactions: {str(e)}")

async def get_base_transactions(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Get transaction history for a Base wallet address
    """
    try:
        # Validate address
        if not is_valid_eth_address(wallet_address):
            raise ValueError("Invalid Ethereum/Base wallet address")
        
        memecoin_transactions = []
        
        # Using Alchemy API for token transfers
        url = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        
        # First, get token balances to identify which memecoins the wallet has held
        token_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTokenBalances",
            "params": [wallet_address, "erc20"]
        }
        
        token_response = requests.post(url, json=token_payload)
        token_data = token_response.json()
        
        # Get token addresses from the response
        token_addresses = []
        for token in token_data.get('result', {}).get('tokenBalances', []):
            contract_address = token.get('contractAddress')
            token_addresses.append(contract_address)
        
        # Add known memecoins even if not in current balances
        for token_address in BASE_MEMECOINS.keys():
            if token_address not in token_addresses and token_address != "0x0000000000000000000000000000000000000000":  # Skip ETH
                token_addresses.append(token_address)
        
        # For each token, get transfer history
        for token_address in token_addresses:
            if token_address == "0x0000000000000000000000000000000000000000":
                continue  # Skip ETH for now
                
            # Get token transfers
            transfers_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "alchemy_getAssetTransfers",
                "params": [
                    {
                        "fromBlock": "0x0",
                        "toBlock": "latest",
                        "category": ["erc20"],
                        "contractAddresses": [token_address],
                        "withMetadata": True,
                        "excludeZeroValue": True,
                        "maxCount": "0x64"  # Limit to 100 transfers
                    }
                ]
            }
            
            transfers_response = requests.post(url, json=transfers_payload)
            transfers_data = transfers_response.json()
            
            for transfer in transfers_data.get('result', {}).get('transfers', []):
                tx_hash = transfer.get('hash')
                from_address = transfer.get('from')
                to_address = transfer.get('to')
                amount = float(transfer.get('value', 0))
                token_symbol = transfer.get('asset', BASE_MEMECOINS.get(token_address, "Unknown"))
                block_num = int(transfer.get('blockNum', "0x0"), 16)
                
                # Get block timestamp
                block_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getBlockByNumber",
                    "params": [hex(block_num), False]
                }
                
                block_response = requests.post(url, json=block_payload)
                block_data = block_response.json()
                timestamp = int(block_data.get('result', {}).get('timestamp', "0x0"), 16)
                
                # Determine if buy or sell
                tx_type = "buy" if to_address.lower() == wallet_address.lower() else "sell"
                
                # Get transaction to estimate price
                tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getTransactionByHash",
                    "params": [tx_hash]
                }
                
                tx_response = requests.post(url, json=tx_payload)
                tx_data = tx_response.json()
                
                # Simplified price estimation (in production, use a price API or DEX data)
                value_wei = int(tx_data.get('result', {}).get('value', "0x0"), 16)
                value_eth = value_wei / 1e18
                price = value_eth / amount if amount > 0 else 0
                
                memecoin_transactions.append({
                    "tx_hash": tx_hash,
                    "wallet_address": wallet_address,
                    "token_address": token_address,
                    "token_symbol": token_symbol,
                    "amount": amount,
                    "price": price,  # Price in ETH
                    "timestamp": timestamp,
                    "type": tx_type
                })
        
        return memecoin_transactions
    
    except Exception as e:
        logger.error(f"Error getting Base transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching Base transactions: {str(e)}")

async def analyze_memecoin_trades(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze memecoin trades to calculate statistics
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
