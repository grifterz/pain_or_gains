import sys
import json
from backend.server import create_synthetic_transactions, analyze_transactions, WALLET_TOKENS

def test_full_flow():
    """Test the full flow from creating transactions to analyzing them"""
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
    
    # Analyze transactions
    analysis = analyze_transactions(transactions)
    
    # Print analysis results
    print("\nAnalysis results:")
    print(json.dumps(analysis, indent=2))
    
    # Check if PUNKFLOOR is in the analysis results
    if "PUNKFLOOR" in str(analysis):
        print("✅ PUNKFLOOR found in analysis results")
    else:
        print("❌ PUNKFLOOR not found in analysis results")
    
    # Check if PUMP is in the analysis results
    if "PUMP" in str(analysis):
        print("✅ PUMP found in analysis results")
    else:
        print("❌ PUMP not found in analysis results")
    
    # Check if JEWCOIN is in the analysis results
    if "JEWCOIN" in str(analysis):
        print("✅ JEWCOIN found in analysis results")
    else:
        print("❌ JEWCOIN not found in analysis results")

if __name__ == "__main__":
    test_full_flow()