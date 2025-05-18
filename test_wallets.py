import requests
import sys
import json

# Define API endpoint
BASE_URL = "https://418b7862-b0d9-4a59-8a0a-b0cdf2b40a11.preview.emergentagent.com"

class WalletTester:
    def __init__(self):
        self.test_results = []
        self.tests_run = 0
        self.tests_passed = 0
    
    def run_test(self, name, method, endpoint, expected_status=200, headers=None, data=None, custom_validation=None):
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        url = f"{BASE_URL}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers)
            else:
                result = {
                    "name": name,
                    "success": False,
                    "error": f"Unsupported HTTP method: {method}"
                }
                self.test_results.append(result)
                print(f"❌ Failed - {result['error']}")
                return False, None
                
            # Check status code
            status_matches = response.status_code == expected_status
            
            # Try to parse response as JSON
            try:
                response_data = response.json()
            except:
                response_data = response.text
                
            # Custom validation logic if provided
            validation_success = True
            validation_message = ""
            
            if status_matches and custom_validation:
                validation_success, validation_message = custom_validation(response_data)
                
            # Determine if test passed
            test_passed = status_matches and validation_success
            
            # Record result
            result = {
                "name": name,
                "success": test_passed,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "validation_message": validation_message
            }
            
            self.test_results.append(result)
            
            # Print result
            if test_passed:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if validation_message:
                    print(f"   {validation_message}")
            else:
                if not status_matches:
                    print(f"❌ Failed - Expected status {expected_status}, got {response.status_code}")
                elif validation_message:
                    print(f"❌ Failed - {validation_message}")
                else:
                    print(f"❌ Failed - Test failed but no validation message provided")
                    
            return test_passed, response_data
            
        except Exception as e:
            result = {
                "name": name,
                "success": False,
                "error": str(e)
            }
            self.test_results.append(result)
            print(f"❌ Failed - {str(e)}")
            return False, None
    
    def test_base_wallet(self, wallet_address="0x671b746d2c5a34609cce723cbf8f475639bc0fa2"):
        """Test analysis for a specific wallet on Base blockchain"""
        def validate_wallet_response(data):
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
                
            # Verify blockchain is base
            if data["blockchain"] != "base":
                return False, f"Blockchain mismatch: {data['blockchain']} != base"
                
            # Verify expected data for this known wallet
            if data["best_trade_token"] != "PEPE":
                return False, f"Expected best_trade_token to be PEPE, but got: {data['best_trade_token']}"
                
            if data["worst_trade_token"] != "BRETT":
                return False, f"Expected worst_trade_token to be BRETT, but got: {data['worst_trade_token']}"
                
            return True, f"Response correctly shows expected data: best_trade_token={data['best_trade_token']}, worst_trade_token={data['worst_trade_token']}"
            
        return self.run_test(
            "Analyze Base Wallet (0x671b746d2c5a34609cce723cbf8f475639bc0fa2)",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"},
            custom_validation=validate_wallet_response
        )
    
    def test_solana_wallet(self, wallet_address="GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"):
        """Test analysis for a specific wallet on Solana blockchain"""
        def validate_wallet_response(data):
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
            
        return self.run_test(
            "Analyze Solana Wallet (GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr)",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            custom_validation=validate_wallet_response
        )
    
    def test_unknown_wallet(self, wallet_address="0x8c87af79c0b9bb8856a5ca09cb5a2a0a38b8f43e"):
        """Test analysis for an unknown wallet"""
        def validate_wallet_response(data):
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
                
            # Verify blockchain is base
            if data["blockchain"] != "base":
                return False, f"Blockchain mismatch: {data['blockchain']} != base"
                
            # Verify no data is shown for unknown wallet
            if data["best_trade_token"] or data["best_multiplier_token"] or data["worst_trade_token"]:
                return False, f"Expected empty token fields for unknown wallet, but got: best_trade_token={data['best_trade_token']}, best_multiplier_token={data['best_multiplier_token']}, worst_trade_token={data['worst_trade_token']}"
                
            if abs(data["best_trade_profit"]) > 0.000001 or abs(data["best_multiplier"]) > 0.000001 or abs(data["all_time_pnl"]) > 0.000001 or abs(data["worst_trade_loss"]) > 0.000001:
                return False, f"Expected zero values for unknown wallet, but got: best_trade_profit={data['best_trade_profit']}, best_multiplier={data['best_multiplier']}, all_time_pnl={data['all_time_pnl']}, worst_trade_loss={data['worst_trade_loss']}"
                
            return True, "Response correctly shows no data for unknown wallet"
            
        return self.run_test(
            "Analyze Unknown Wallet (0x8c87af79c0b9bb8856a5ca09cb5a2a0a38b8f43e)",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"},
            custom_validation=validate_wallet_response
        )
    
    def test_leaderboard(self, blockchain="base", stat_type="worst_trade"):
        """Test leaderboard for proper token display"""
        def validate_leaderboard_response(data):
            if not isinstance(data, list):
                return False, "Expected list response for leaderboard"
                
            if not data:
                return False, "Leaderboard should not be empty"
                
            # Check if token names are properly displayed
            for entry in data:
                if "token" not in entry or not entry["token"]:
                    return False, f"Missing or empty token name for entry: {entry}"
                    
            return True, f"Leaderboard shows proper token names for {len(data)} entries"
            
        return self.run_test(
            f"Leaderboard for {blockchain} - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}?blockchain={blockchain}",
            200,
            custom_validation=validate_leaderboard_response
        )
    
    def print_summary(self):
        """Print a summary of all test results"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        # Group by success/failure
        failed_tests = [test for test in self.test_results if not test["success"]]
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['name']}")
                if "validation_message" in test and test["validation_message"]:
                    print(f"    Reason: {test['validation_message']}")
                elif "error" in test:
                    print(f"    Error: {test['error']}")
                    
        print("\n" + "="*50)

def main():
    # Setup
    tester = WalletTester()
    
    # Run tests
    tester.test_base_wallet()
    tester.test_solana_wallet()
    tester.test_unknown_wallet()
    tester.test_leaderboard("base", "worst_trade")
    tester.test_leaderboard("solana", "worst_trade")
    
    # Print summary
    tester.print_summary()

if __name__ == "__main__":
    main()
