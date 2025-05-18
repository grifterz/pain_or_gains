def test_specific_solana_wallet(tester, wallet_address="GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"):
    """Test analysis for a specific wallet on Solana blockchain"""
    def validate_specific_wallet_response(data):
        if not data:
            return False, "Empty response"
            
        # Check required fields
        required_fields = ["id", "wallet_address", "blockchain", "best_trade_profit", 
                          "best_trade_token", "best_multiplier", "best_multiplier_token", 
                          "all_time_pnl", "worst_trade_loss", "worst_trade_token"]
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
            
        # Verify wallet address matches
        if data["wallet_address"] != wallet_address:
            return False, f"Wallet address mismatch: {data['wallet_address']} != {wallet_address}"
            
        # Verify blockchain is solana
        if data["blockchain"] != "solana":
            return False, f"Blockchain mismatch: {data['blockchain']} != solana"
            
        # Verify expected data for this known wallet
        if data["best_trade_token"] != "BONG":
            return False, f"Expected best_trade_token to be BONG, but got: {data['best_trade_token']}"
            
        if data["worst_trade_token"] != "SAMO":
            return False, f"Expected worst_trade_token to be SAMO, but got: {data['worst_trade_token']}"
            
        return True, f"Response correctly shows expected data: best_trade_token={data['best_trade_token']}, worst_trade_token={data['worst_trade_token']}"
        
    return tester.run_test(
        "Analyze Specific Solana Wallet",
        "POST",
        "api/analyze",
        200,
        data={"wallet_address": wallet_address, "blockchain": "solana"},
        custom_validation=validate_specific_wallet_response
    )