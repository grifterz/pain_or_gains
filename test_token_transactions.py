import sys
import json
from backend.server import create_synthetic_transactions, WALLET_TOKENS

def test_create_synthetic_transactions():
    """Test that create_synthetic_transactions creates both buy and sell transactions for all tokens"""
    wallet_address = "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"
    blockchain = "solana"
    
    # Print initial token list
    print(f"Initial tokens for {wallet_address}: {WALLET_TOKENS.get(wallet_address, [])}")
    
    # Create transactions
    transactions = create_synthetic_transactions(wallet_address, blockchain)
    
    # Print updated token list
    print(f"Updated tokens for {wallet_address}: {WALLET_TOKENS.get(wallet_address, [])}")
    
    # Group transactions by token and type
    token_transactions = {}
    for tx in transactions:
        token = tx["token_symbol"]
        tx_type = tx["type"]
        
        if token not in token_transactions:
            token_transactions[token] = {"buy": 0, "sell": 0}
        
        token_transactions[token][tx_type] += 1
    
    # Print transaction counts by token and type
    print("\nTransaction counts by token and type:")
    for token, counts in token_transactions.items():
        print(f"{token}: {counts['buy']} buy, {counts['sell']} sell")
    
    # Check if all tokens have both buy and sell transactions
    all_complete = True
    for token, counts in token_transactions.items():
        if counts["buy"] == 0 or counts["sell"] == 0:
            print(f"❌ {token} is missing {'buy' if counts['buy'] == 0 else 'sell'} transactions")
            all_complete = False
    
    if all_complete:
        print("✅ All tokens have both buy and sell transactions")
    else:
        print("❌ Some tokens are missing buy or sell transactions")
    
    # Print all transactions for PUNKFLOOR
    print("\nAll transactions for PUNKFLOOR:")
    punkfloor_txs = [tx for tx in transactions if tx["token_symbol"] == "PUNKFLOOR"]
    for tx in punkfloor_txs:
        print(json.dumps(tx, indent=2, default=str))

if __name__ == "__main__":
    test_create_synthetic_transactions()