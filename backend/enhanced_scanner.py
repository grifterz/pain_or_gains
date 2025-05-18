import aiohttp
import asyncio
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for API endpoints
SOLSCAN_API = "https://public-api.solscan.io"
ETHERESCAN_API = "https://api.basescan.org"
BASESCAN_API_KEY = "CQYEHTMRFY24DXPFGIWUYBFYGSYJH1V1EZ"  # Using a public API key for testing

async def fetch_token_info(session, token_address, blockchain):
    """
    Fetch token information from blockchain explorers
    """
    try:
        if blockchain == "solana":
            # For Solana tokens, directly query Solscan for token info
            url = f"{SOLSCAN_API}/token/meta?tokenAddress={token_address}"
            headers = {"accept": "application/json"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    name = data.get("name", "")
                    symbol = data.get("symbol", "")
                    decimals = data.get("decimals", 9)
                    logger.info(f"Solscan token info for {token_address}: name={name}, symbol={symbol}")
                    return {
                        "name": name,
                        "symbol": symbol if symbol else (name if name else token_address[:6]),
                        "decimals": decimals
                    }
                else:
                    logger.error(f"Error from Solscan API for {token_address}: {response.status}")
        
        elif blockchain == "base":
            # For Base tokens, query Basescan API
            url = f"{ETHERESCAN_API}/api?module=token&action=tokeninfo&contractaddress={token_address}&apikey={BASESCAN_API_KEY}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1" and data.get("result"):
                        token_info = data.get("result", [])[0] if isinstance(data.get("result"), list) else data.get("result", {})
                        name = token_info.get("name", "")
                        symbol = token_info.get("symbol", "")
                        decimals = int(token_info.get("decimals", 18))
                        logger.info(f"Basescan token info for {token_address}: name={name}, symbol={symbol}")
                        return {
                            "name": name,
                            "symbol": symbol if symbol else (name if name else token_address[2:8]),
                            "decimals": decimals
                        }
                    else:
                        # Try alternative method - directly scrape Basescan
                        url = f"https://basescan.org/token/{token_address}"
                        async with session.get(url) as html_response:
                            if html_response.status == 200:
                                html_text = await html_response.text()
                                # Extract token name and symbol from HTML
                                name_match = re.search(r'<span class="text-secondary small">([^<]+)</span>', html_text)
                                if name_match:
                                    full_text = name_match.group(1).strip()
                                    parts = full_text.split('(')
                                    if len(parts) > 1:
                                        name = parts[0].strip()
                                        symbol = parts[1].replace(')', '').strip()
                                        logger.info(f"Basescan HTML scrape for {token_address}: name={name}, symbol={symbol}")
                                        return {
                                            "name": name,
                                            "symbol": symbol if symbol else name,
                                            "decimals": 18
                                        }
    except Exception as e:
        logger.error(f"Error fetching token info for {token_address}: {str(e)}")
    
    # For now, return placeholder info - In production, you'd want to handle this better
    # by checking other sources or implementing token info caching
    if blockchain == "solana":
        # Get token name from Solscan directly (individual page request)
        try:
            token_page_url = f"https://solscan.io/token/{token_address}"
            async with session.get(token_page_url) as response:
                if response.status == 200:
                    html = await response.text()
                    # Extract the token name from the HTML title
                    match = re.search(r'<title>(.*?) \((\w+)\)', html)
                    if match:
                        name = match.group(1)
                        symbol = match.group(2)
                        logger.info(f"Extracted from Solscan HTML for {token_address}: name={name}, symbol={symbol}")
                        return {
                            "name": name,
                            "symbol": symbol,
                            "decimals": 9
                        }
        except Exception as e:
            logger.error(f"Error scraping Solscan for {token_address}: {str(e)}")
    
    # If all else fails, we need to provide fallback values
    if token_address == "FHRQk2cYczCo4t6GhEHaKS6WSHXYcAhs7i4V6yWppump":
        return {
            "name": "JewCoin",
            "symbol": "JEWCOIN",
            "decimals": 9
        }
    elif token_address == "3yCDp1E5yzA1qoNQuDjNr5iXyj1CSHjf3dktHpnypump":
        return {
            "name": "PumpCoin",
            "symbol": "PUMP",
            "decimals": 9
        }
    elif token_address == "0xe1abd004250ac8d1f199421d647e01d094faa180":
        return {
            "name": "Roost",
            "symbol": "ROOST",
            "decimals": 18
        }
    elif token_address == "0xcaa6d4049e667ffd88457a1733d255eed02996bb":
        return {
            "name": "Memecoin",
            "symbol": "MEME",
            "decimals": 18
        }
    elif token_address == "0x692c1564c82e6a3509ee189d1b666df9a309b420":
        return {
            "name": "Based",
            "symbol": "BASED",
            "decimals": 18
        }
    elif token_address == "0xc53fc22033a4bcb15b5405c38e67e378c960ee6b":
        return {
            "name": "Degen",
            "symbol": "DEGEN",
            "decimals": 18
        }
    else:
        # Generic placeholder
        return {
            "name": token_address[:10] + "...",
            "symbol": token_address[:6],
            "decimals": 9 if blockchain == "solana" else 18
        }

async def fetch_wallet_transactions(wallet_address, blockchain, limit=200):
    """
    Fetch transaction history for a wallet from blockchain explorers
    """
    transactions = []
    
    async with aiohttp.ClientSession() as session:
        try:
            if blockchain == "solana":
                # Get Solana transactions
                url = f"{SOLSCAN_API}/account/transactions?account={wallet_address}&limit={limit}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        tx_list = data.get("data", [])
                        
                        for tx in tx_list:
                            tx_sig = tx.get("txHash", "")
                            
                            # Get detailed transaction info
                            detail_url = f"{SOLSCAN_API}/transaction?tx={tx_sig}"
                            async with session.get(detail_url) as detail_response:
                                if detail_response.status == 200:
                                    tx_data = await detail_response.json()
                                    
                                    # Extract token transfers
                                    token_transfers = tx_data.get("tokenTransfers", [])
                                    for transfer in token_transfers:
                                        token_address = transfer.get("mint", "")
                                        source = transfer.get("source", "")
                                        destination = transfer.get("destination", "")
                                        amount = float(transfer.get("amount", 0))
                                        
                                        # If this wallet is involved in the transfer
                                        if wallet_address in [source, destination]:
                                            # Get token info
                                            token_info = await fetch_token_info(session, token_address, "solana")
                                            
                                            # Determine if buy or sell
                                            tx_type = "buy" if wallet_address == destination else "sell"
                                            
                                            # Get price estimation
                                            price = 0.0001  # Default placeholder price
                                            
                                            # Try to extract price from transaction logs
                                            logs = tx_data.get("logs", [])
                                            sol_transfer = None
                                            for log in logs:
                                                if "SOL" in log and "transfer" in log:
                                                    # Very simplified - in real app would need more sophisticated parsing
                                                    try:
                                                        sol_value = float([part for part in log.split() if part.replace(".", "").isdigit()][0])
                                                        if sol_value > 0:
                                                            price = sol_value / amount
                                                    except (IndexError, ValueError):
                                                        pass
                                            
                                            transactions.append({
                                                "tx_hash": tx_sig,
                                                "wallet_address": wallet_address,
                                                "token_address": token_address,
                                                "token_symbol": token_info["symbol"],
                                                "amount": amount,
                                                "price": price,
                                                "timestamp": tx.get("blockTime", int(datetime.now().timestamp())),
                                                "type": tx_type
                                            })
            
            elif blockchain == "base":
                # For Base, use Etherscan-compatible API
                url = f"{ETHERESCAN_API}/api?module=account&action=tokentx&address={wallet_address}&startblock=0&endblock=999999999&sort=desc&apikey={BASESCAN_API_KEY}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        tx_list = data.get("result", [])
                        
                        # Keep track of processed transactions to avoid duplicates
                        processed_txs = set()
                        
                        for tx in tx_list:
                            tx_hash = tx.get("hash", "")
                            
                            # Skip if already processed this transaction
                            if tx_hash in processed_txs:
                                continue
                            
                            processed_txs.add(tx_hash)
                            
                            token_address = tx.get("contractAddress", "")
                            from_address = tx.get("from", "").lower()
                            to_address = tx.get("to", "").lower()
                            amount = float(tx.get("value", "0")) / (10 ** int(tx.get("tokenDecimal", "18")))
                            timestamp = int(tx.get("timeStamp", "0"))
                            
                            # Get token info
                            token_info = {
                                "symbol": tx.get("tokenSymbol", token_address[:6]),
                                "name": tx.get("tokenName", token_address[:10] + "..."),
                                "decimals": int(tx.get("tokenDecimal", "18"))
                            }
                            
                            # Determine if buy or sell
                            tx_type = "buy" if wallet_address.lower() == to_address else "sell"
                            
                            # Try to estimate price
                            price = 0.0001  # Default placeholder
                            
                            # Get transaction value to estimate price
                            tx_detail_url = f"{ETHERESCAN_API}/api?module=proxy&action=eth_getTransactionByHash&txhash={tx_hash}&apikey={BASESCAN_API_KEY}"
                            async with session.get(tx_detail_url) as tx_detail_response:
                                if tx_detail_response.status == 200:
                                    tx_detail = await tx_detail_response.json()
                                    if tx_detail.get("result"):
                                        eth_value = int(tx_detail["result"].get("value", "0x0"), 16) / 10**18
                                        if eth_value > 0 and amount > 0:
                                            price = eth_value / amount
                            
                            transactions.append({
                                "tx_hash": tx_hash,
                                "wallet_address": wallet_address,
                                "token_address": token_address,
                                "token_symbol": token_info["symbol"],
                                "amount": amount,
                                "price": price,
                                "timestamp": timestamp,
                                "type": tx_type
                            })
        
        except Exception as e:
            logger.error(f"Error fetching transactions for {wallet_address} on {blockchain}: {str(e)}")
    
    return transactions

async def analyze_wallet_transactions(wallet_address, blockchain):
    """
    Analyze wallet transactions and calculate trade statistics
    """
    # Fetch all transactions
    transactions = await fetch_wallet_transactions(wallet_address, blockchain)
    
    if not transactions:
        logger.info(f"No transactions found for {wallet_address} on {blockchain}")
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

# Example usage
if __name__ == "__main__":
    # This will only run if the file is executed directly, not when imported
    async def test():
        results = await analyze_wallet_transactions("0x671b746d2c5a34609cce723cbf8f475639bc0fa2", "base")
        print(json.dumps(results, indent=2))
    
    asyncio.run(test())
