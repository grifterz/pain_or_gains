
import requests
import sys
import time
from datetime import datetime

class MemeAnalyzerTester:
    def __init__(self, base_url="https://418b7862-b0d9-4a59-8a0a-b0cdf2b40a11.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, expected_data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            status_success = response.status_code == expected_status
            
            if status_success:
                print(f"✅ Status check passed: {response.status_code}")
                
                # If we have expected data to validate
                if expected_data:
                    response_data = response.json()
                    data_success = True
                    
                    for key, expected_value in expected_data.items():
                        if key not in response_data:
                            print(f"❌ Expected key '{key}' not found in response")
                            data_success = False
                        elif isinstance(expected_value, dict) and isinstance(response_data[key], dict):
                            # For nested dictionaries, check if all expected keys exist
                            for nested_key in expected_value:
                                if nested_key not in response_data[key]:
                                    print(f"❌ Expected nested key '{nested_key}' not found in response['{key}']")
                                    data_success = False
                        elif expected_value is not None and response_data[key] != expected_value:
                            print(f"❌ Value mismatch for '{key}': expected '{expected_value}', got '{response_data[key]}'")
                            data_success = False
                    
                    if data_success:
                        print("✅ Data validation passed")
                        self.tests_passed += 1
                    else:
                        print("❌ Data validation failed")
                else:
                    self.tests_passed += 1
            else:
                print(f"❌ Status check failed: Expected {expected_status}, got {response.status_code}")
                
            return status_success, response.json() if status_success else {}

        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200,
            expected_data={"message": None}  # We just check if the key exists
        )

    def test_analyze_base_wallet(self, wallet_address):
        """Test analyzing a Base wallet"""
        success, response = self.run_test(
            f"Analyze Base Wallet ({wallet_address})",
            "POST",
            "analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"},
            expected_data={
                "wallet_address": wallet_address,
                "blockchain": "base",
                "best_trade_profit": None,
                "best_trade_token": None,
                "best_multiplier": None,
                "best_multiplier_token": None,
                "all_time_pnl": None
            }
        )
        
        # Additional checks for the specific Base wallet
        if success and wallet_address == "0x671b746d2c5a34609cce723cbf8f475639bc0fa2":
            print("\nVerifying Base wallet specific token names:")
            
            # Check for ROOST token instead of e1abd0
            if response.get("best_trade_token") == "ROOST":
                print("✅ Best trade token shows as ROOST (not e1abd0 or BASED)")
                self.tests_passed += 1
            else:
                print(f"❌ Best trade token shows as {response.get('best_trade_token')} instead of ROOST")
                
            # Check for ROOST token for best multiplier
            if response.get("best_multiplier_token") == "ROOST":
                print("✅ Best multiplier token shows as ROOST")
                self.tests_passed += 1
            else:
                print(f"❌ Best multiplier token shows as {response.get('best_multiplier_token')} instead of ROOST")
                
            # Check for profit values
            if response.get("best_trade_profit") and abs(response.get("best_trade_profit") - 0.2) < 0.1:
                print(f"✅ Best trade profit is around 0.2 ETH: {response.get('best_trade_profit')}")
                self.tests_passed += 1
            else:
                print(f"❌ Best trade profit is not around 0.2 ETH: {response.get('best_trade_profit')}")
                
            if response.get("best_multiplier") and abs(response.get("best_multiplier") - 3.0) < 0.5:
                print(f"✅ Best multiplier is around 3.0x: {response.get('best_multiplier')}")
                self.tests_passed += 1
            else:
                print(f"❌ Best multiplier is not around 3.0x: {response.get('best_multiplier')}")
                
            if response.get("all_time_pnl") and abs(response.get("all_time_pnl") - 0.8) < 0.2:
                print(f"✅ All-time PnL is around 0.8 ETH: {response.get('all_time_pnl')}")
                self.tests_passed += 1
            else:
                print(f"❌ All-time PnL is not around 0.8 ETH: {response.get('all_time_pnl')}")
                
            self.tests_run += 5  # We added 5 additional checks
            
        return success, response
        
    def test_analyze_solana_wallet(self, wallet_address):
        """Test analyzing a Solana wallet"""
        success, response = self.run_test(
            f"Analyze Solana Wallet ({wallet_address})",
            "POST",
            "analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            expected_data={
                "wallet_address": wallet_address,
                "blockchain": "solana",
                "best_trade_profit": None,
                "best_trade_token": None,
                "best_multiplier": None,
                "best_multiplier_token": None,
                "all_time_pnl": None
            }
        )
        
        # Additional checks for the specific Solana wallet
        if success and wallet_address == "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr":
            print("\nVerifying Solana wallet specific token names:")
            
            # Check for JEWCOIN token instead of FHRQk2
            if response.get("best_trade_token") == "JEWCOIN":
                print("✅ Best trade token shows as JEWCOIN (not FHRQk2 or PUMP)")
                self.tests_passed += 1
            else:
                print(f"❌ Best trade token shows as {response.get('best_trade_token')} instead of JEWCOIN")
                
            # Check for JEWCOIN token for best multiplier
            if response.get("best_multiplier_token") == "JEWCOIN":
                print("✅ Best multiplier token shows as JEWCOIN")
                self.tests_passed += 1
            else:
                print(f"❌ Best multiplier token shows as {response.get('best_multiplier_token')} instead of JEWCOIN")
                
            # Check for profit values
            if response.get("best_trade_profit") and abs(response.get("best_trade_profit") - 0.2) < 0.1:
                print(f"✅ Best trade profit is around 0.2 SOL: {response.get('best_trade_profit')}")
                self.tests_passed += 1
            else:
                print(f"❌ Best trade profit is not around 0.2 SOL: {response.get('best_trade_profit')}")
                
            if response.get("best_multiplier") and abs(response.get("best_multiplier") - 3.0) < 0.5:
                print(f"✅ Best multiplier is around 3.0x: {response.get('best_multiplier')}")
                self.tests_passed += 1
            else:
                print(f"❌ Best multiplier is not around 3.0x: {response.get('best_multiplier')}")
                
            if response.get("all_time_pnl") and abs(response.get("all_time_pnl") - 0.6) < 0.2:
                print(f"✅ All-time PnL is around 0.6 SOL: {response.get('all_time_pnl')}")
                self.tests_passed += 1
            else:
                print(f"❌ All-time PnL is not around 0.6 SOL: {response.get('all_time_pnl')}")
                
            # Check for PUNKFLOOR token in the response
            tokens_in_response = [
                response.get("best_trade_token", ""),
                response.get("best_multiplier_token", ""),
                response.get("worst_trade_token", "")
            ]
            
            if "PUNKFLOOR" in tokens_in_response:
                print("✅ PUNKFLOOR token is present in the response")
                self.tests_passed += 1
            else:
                print("❌ PUNKFLOOR token is not present in the response")
                
            self.tests_run += 6  # We added 6 additional checks
            
        return success, response
        
    def test_analyze_random_wallet(self, wallet_address):
        """Test analyzing a random wallet with no data"""
        return self.run_test(
            f"Analyze Random Wallet ({wallet_address})",
            "POST",
            "analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"},
            expected_data={
                "wallet_address": wallet_address,
                "blockchain": "base",
                "best_trade_profit": 0.0,
                "best_trade_token": "",
                "best_multiplier": 0.0,
                "best_multiplier_token": "",
                "all_time_pnl": 0.0
            }
        )

    def test_leaderboard(self, stat_type, blockchain):
        """Test getting leaderboard data"""
        success, response = self.run_test(
            f"Leaderboard ({blockchain} - {stat_type})",
            "GET",
            f"leaderboard/{stat_type}?blockchain={blockchain}",
            200
        )
        
        # Check if leaderboard entries have proper token names instead of address fragments
        if success and len(response) > 0:
            print(f"\nChecking token names in {blockchain} leaderboard for {stat_type}:")
            
            # Skip all_time_pnl as it doesn't have token names
            if stat_type != "all_time_pnl":
                has_proper_names = True
                for entry in response:
                    token = entry.get("token", "")
                    
                    # Check if token is a proper name and not an address fragment
                    if token and len(token) > 0:
                        # Address fragments typically start with 0x or are 6 characters of hex
                        is_address_fragment = token.startswith("0x") or (len(token) <= 6 and all(c in "0123456789abcdefABCDEF" for c in token))
                        
                        if is_address_fragment:
                            print(f"❌ Found address fragment as token name: {token}")
                            has_proper_names = False
                        else:
                            print(f"✅ Found proper token name: {token}")
                
                if has_proper_names:
                    print(f"✅ All tokens in {blockchain} {stat_type} leaderboard have proper names")
                    self.tests_passed += 1
                else:
                    print(f"❌ Some tokens in {blockchain} {stat_type} leaderboard still use address fragments")
                
                self.tests_run += 1
        
        return success, response

def main():
    # Setup
    tester = MemeAnalyzerTester()
    
    # Test wallets from the requirements
    base_wallet = "0x671b746d2c5a34609cce723cbf8f475639bc0fa2"
    solana_wallet = "GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"
    random_wallet = "0x8c87af79c0b9bb8856a5ca09cb5a2a0a38b8f43e"
    
    # Run tests
    print("\n===== Testing Pain or Gains Memecoin Analytics API =====\n")
    
    # Test root endpoint
    tester.test_root_endpoint()
    
    # Test wallet analysis
    print("\n----- Testing Wallet Analysis -----")
    tester.test_analyze_base_wallet(base_wallet)
    tester.test_analyze_solana_wallet(solana_wallet)
    tester.test_analyze_random_wallet(random_wallet)
    
    # Test leaderboard
    print("\n----- Testing Leaderboard -----")
    for blockchain in ["base", "solana"]:
        for stat_type in ["best_trade", "best_multiplier", "all_time_pnl", "worst_trade"]:
            tester.test_leaderboard(stat_type, blockchain)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
