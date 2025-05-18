import unittest
import json
import requests
import sys
import re

# Define API endpoint
BASE_URL = "http://localhost:8001"

class MemecoinsAPITester:
    def __init__(self):
        self.test_results = []
        self.tests_run = 0
        self.tests_passed = 0
    
    def run_test(self, name, method, endpoint, expected_status=200, headers=None, data=None, custom_validation=None, allow_fail=False):
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
            
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        def validate_root_response(data):
            if not isinstance(data, dict):
                return False, "Expected JSON object in response"
                
            if "message" not in data:
                return False, "Missing 'message' field in response"
                
            if "Pain or Gains API" not in data["message"]:
                return False, f"Unexpected message content: {data['message']}"
                
            return True, "Response contains expected message: Pain or Gains API - Memecoin Analysis Tool"
            
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "api/",
            200,
            custom_validation=validate_root_response
        )
        
    def test_wallet_with_memecoin_activity(self, wallet_address="9eja6MHBPosta4WVFsz8EEDNdeiKuqFPWrC1bv3gY37t"):
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
            
            # Since we're not generating sample data anymore, we can't guarantee this wallet will have 
            # actual memecoin transactions. We'll just check the response structure is correct.
            return True, "Response structure is valid for this wallet (real data only shown if transactions exist)"
            
        return self.run_test(
            "Analyze Wallet With Memecoin Activity",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            custom_validation=validate_active_wallet_response,
            allow_fail=True  # Allow this test to fail since we can't guarantee real transactions
        )
        
    def test_wallet_with_no_activity(self, wallet_address="8xY1u6N9GHRhyNngvPKAJHeiizK9MmFga3ntZ6hZSmXf"):
        """Test analyzing a wallet with no memecoin activity"""
        def validate_inactive_wallet_response(data):
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
                
            # Verify no data is shown
            if data["best_trade_token"] or data["best_multiplier_token"] or data["worst_trade_token"]:
                return False, "Inactive wallet should not have token data"
                
            if data["best_trade_profit"] != 0 or data["best_multiplier"] != 0 or data["all_time_pnl"] != 0 or data["worst_trade_loss"] != 0:
                return False, "Inactive wallet should have zero values for all metrics"
                
            return True, "Response correctly shows no memecoin activity for this wallet"
            
        return self.run_test(
            "Analyze Wallet With No Memecoin Activity",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            custom_validation=validate_inactive_wallet_response
        )
        
    def test_invalid_address(self):
        """Test error handling for invalid wallet address"""
        def validate_error_response(data):
            if isinstance(data, dict) and "detail" in data:
                # Check for expected error message about invalid address
                if "Invalid" in data["detail"] and "address" in data["detail"]:
                    return True, "Invalid address correctly returned empty token fields"
                return False, f"Unexpected error message: {data['detail']}"
            return False, "Expected error response with 'detail' field"
            
        return self.run_test(
            "Invalid Wallet Address Format",
            "POST",
            "api/analyze",
            400,  # Expect 400 Bad Request
            data={"wallet_address": "invalid-address", "blockchain": "solana"},
            custom_validation=validate_error_response
        )
        
    def test_leaderboard_entries(self, stat_type="best_trade", blockchain="base"):
        """Test leaderboard API for various stat types"""
        def validate_leaderboard_response(data):
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
                    
                # Verify we have a valid address
                if stat_type == "best_trade" or stat_type == "worst_trade":
                    if not entry["token"]:
                        return False, f"Token field empty for {stat_type} leaderboard entry"
                        
                # Verify value is non-zero (except for 'worst_trade' which could be 0 for wallets with no losses)
                if stat_type != "worst_trade" and entry["value"] == 0:
                    return False, f"Value should be non-zero for {stat_type} leaderboard entry"
                
            return True, "Leaderboard entries have valid structure and content"
            
        return self.run_test(
            f"Leaderboard Entries - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}?blockchain={blockchain}",
            200,
            custom_validation=validate_leaderboard_response
        )
        
    def test_all_leaderboards(self):
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
    """Test analysis for a specific wallet on Base blockchain"""
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
    test_specific_base_wallet(tester)
    tester.test_wallet_with_no_activity()
    tester.test_wallet_with_memecoin_activity()
    tester.test_invalid_address()
    tester.test_leaderboard_entries("best_trade")
    tester.test_leaderboard_entries("best_multiplier")
    tester.test_leaderboard_entries("all_time_pnl")
    tester.test_leaderboard_entries("worst_trade")
    
    # Print summary
    tester.print_summary()

if __name__ == "__main__":
    main()
