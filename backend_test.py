import requests
import unittest
import json
import sys
from datetime import datetime

class MemecoinsAPITester:
    def __init__(self, base_url="https://994f8226-f44b-42aa-9a0f-715c84fc22e4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, custom_validation=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            status_success = response.status_code == expected_status
            
            # Try to parse response as JSON
            try:
                response_data = response.json()
            except:
                response_data = {}
                
            # Run custom validation if provided
            validation_success = True
            validation_message = ""
            if status_success and custom_validation:
                validation_success, validation_message = custom_validation(response_data)
            
            success = status_success and validation_success
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if validation_message:
                    print(f"   {validation_message}")
            else:
                if not status_success:
                    print(f"❌ Failed - Expected status {expected_status}, got {response.status_code}")
                    try:
                        print(f"Response: {response.text}")
                    except:
                        pass
                if not validation_success and validation_message:
                    print(f"❌ Failed - {validation_message}")
            
            # Store test result
            self.test_results.append({
                "name": name,
                "success": success,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "validation_message": validation_message
            })
            
            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "api",
            200,
            custom_validation=lambda data: (
                "message" in data and "Pain or Gains API" in data["message"],
                f"Response contains expected message: {data.get('message', 'No message')}"
            )
        )

    def test_wallet_with_no_memecoin_activity(self, wallet_address="7EqvJ1KaFzV9FrcvZezSKob3VfsBuN6mEMcCkSTJw48G"):
        """Test analyzing a wallet with no memecoin activity"""
        def validate_no_activity_response(data):
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
                
            # Verify no token data (should be empty for a wallet with no activity)
            if any([
                data["best_trade_token"], 
                data["best_multiplier_token"], 
                data["worst_trade_token"],
                abs(data["best_trade_profit"]) > 0.000001,
                abs(data["best_multiplier"]) > 0.000001,
                abs(data["all_time_pnl"]) > 0.000001,
                abs(data["worst_trade_loss"]) > 0.000001
            ]):
                return False, "Expected empty stats for wallet with no memecoin activity, but found data"
                
            return True, "Response correctly shows no memecoin activity for this wallet"
            
        return self.run_test(
            "Analyze Wallet With No Memecoin Activity",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            custom_validation=validate_no_activity_response
        )

    def test_wallet_with_memecoin_activity(self, wallet_address="8kzcTCwWTmsYTkNPbsMiQGE9sBJqXY5X38UHgtQ8cEwN"):
        """Test analyzing a wallet with memecoin activity"""
        def validate_active_wallet_response(data):
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
                
            # Verify we have actual data (at least one token field should be populated)
            has_token_data = any([
                data["best_trade_token"], 
                data["best_multiplier_token"], 
                data["worst_trade_token"]
            ])
            
            has_value_data = any([
                abs(data["best_trade_profit"]) > 0.000001,
                abs(data["best_multiplier"]) > 0.000001,
                abs(data["all_time_pnl"]) > 0.000001,
                abs(data["worst_trade_loss"]) > 0.000001
            ])
            
            if not (has_token_data and has_value_data):
                return False, "Expected real data for active wallet, but found empty stats"
                
            return True, "Response contains valid memecoin activity data for this wallet"
            
        return self.run_test(
            "Analyze Wallet With Memecoin Activity",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            custom_validation=validate_active_wallet_response
        )
    
    def test_invalid_wallet_address(self):
        """Test with invalid wallet address format"""
        def validate_invalid_response(data):
            # The API should return a 400 status for invalid addresses
            # But if it returns 200, it should at least have empty token fields
            if data.get("best_trade_token") or data.get("best_multiplier_token") or data.get("worst_trade_token"):
                return False, "Expected empty token fields for invalid address, but got data"
            return True, "Invalid address correctly returned empty token fields"
            
        return self.run_test(
            "Invalid Wallet Address Format",
            "POST",
            "api/analyze",
            400,  # Expecting 400 for invalid format
            data={"wallet_address": "invalid-address", "blockchain": "solana"},
            custom_validation=validate_invalid_response
        )
    
    def test_leaderboard_entries(self, stat_type="best_trade"):
        """Test that leaderboard only shows wallets with real memecoin activity"""
        def validate_leaderboard_entries(data):
            if not isinstance(data, list):
                return False, "Expected list response for leaderboard"
                
            # For the specific test case, we expect empty leaderboard
            if not data:
                return True, "Leaderboard is correctly empty (no wallets with real activity)"
                
            # If there are entries, verify they have real data
            required_fields = ["wallet_address", "value", "token", "rank"]
            for entry in data:
                missing_fields = [field for field in required_fields if field not in entry]
                if missing_fields:
                    return False, f"Leaderboard entry missing fields: {', '.join(missing_fields)}"
                
                # Verify each entry has a non-zero value and a token
                if abs(entry["value"]) < 0.000001 or not entry["token"]:
                    return False, f"Leaderboard contains entry with no real data: {entry}"
                    
            return True, f"Leaderboard contains {len(data)} valid entries with real memecoin activity"
            
        return self.run_test(
            f"Leaderboard Entries - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}",
            200,
            params={"blockchain": "solana", "limit": 10},
            custom_validation=validate_leaderboard_entries
        )
    
    def test_all_leaderboard_tabs(self):
        """Test all four leaderboard statistic tabs"""
        all_passed = True
        results = {}
        
        for stat_type in ["best_trade", "best_multiplier", "all_time_pnl", "worst_trade"]:
            success, data = self.test_leaderboard_entries(stat_type)
            results[stat_type] = {"success": success, "data": data}
            all_passed = all_passed and success
        
        # Additional validation to ensure different tabs show different data
        if all_passed and all(len(results[stat]["data"]) > 0 for stat in results):
            # Compare entries across tabs
            different_entries = set()
            for stat_type, result in results.items():
                for entry in result["data"]:
                    different_entries.add(f"{entry['wallet_address']}-{entry['value']}")
            
            if len(different_entries) <= 1:
                print("❌ Failed - All leaderboard tabs show identical data")
                all_passed = False
        
        return all_passed, results
        
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

def test_specific_base_wallet(tester, wallet_address="0x671b746d2c5a34609cce723cbf8f475639bc0fa2"):
    """Test the specific Base wallet from the requirements"""
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
            
        # Verify blockchain is base
        if data["blockchain"] != "base":
            return False, f"Blockchain mismatch: {data['blockchain']} != base"
            
        # Verify no data is shown (all values should be zero or empty)
        if data["best_trade_token"] or data["best_multiplier_token"] or data["worst_trade_token"]:
            return False, f"Expected empty token fields for wallet with no activity, but got: best_trade_token={data['best_trade_token']}, best_multiplier_token={data['best_multiplier_token']}, worst_trade_token={data['worst_trade_token']}"
            
        if abs(data["best_trade_profit"]) > 0.000001 or abs(data["best_multiplier"]) > 0.000001 or abs(data["all_time_pnl"]) > 0.000001 or abs(data["worst_trade_loss"]) > 0.000001:
            return False, f"Expected zero values for wallet with no activity, but got: best_trade_profit={data['best_trade_profit']}, best_multiplier={data['best_multiplier']}, all_time_pnl={data['all_time_pnl']}, worst_trade_loss={data['worst_trade_loss']}"
            
        return True, "Response correctly shows no data for wallet with no activity"
        
    return tester.run_test(
        "Analyze Specific Base Wallet",
        "POST",
        "api/analyze",
        200,
        data={"wallet_address": wallet_address, "blockchain": "base"},
        custom_validation=validate_specific_wallet_response
    )

def main():
    # Setup
    tester = MemecoinsAPITester()
    
    # Run tests
    tester.test_root_endpoint()
    
    # Test the specific Base wallet from the requirements
    specific_wallet_success, specific_wallet_data = test_specific_base_wallet(tester)
    
    # Test wallet with no memecoin activity
    no_activity_success, no_activity_data = tester.test_wallet_with_no_memecoin_activity()
    
    # Test wallet with memecoin activity
    activity_success, activity_data = tester.test_wallet_with_memecoin_activity()
    
    # Test invalid wallet address format
    tester.test_invalid_wallet_address()
    
    # Test all leaderboard tabs
    tester.test_all_leaderboard_tabs()
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())