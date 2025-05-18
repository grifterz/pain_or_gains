import requests
import sys
import json
from datetime import datetime

class MemeAnalyzerTester:
    def __init__(self, base_url="https://994f8226-f44b-42aa-9a0f-715c84fc22e4.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, custom_validation=None):
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
                
                # Try to parse response as JSON
                try:
                    response_data = response.json()
                    print(f"📊 Response data: {json.dumps(response_data, indent=2)}")
                    
                    # Run custom validation if provided
                    if custom_validation:
                        validation_success, validation_message = custom_validation(response_data)
                        if validation_success:
                            print(f"✅ Validation passed: {validation_message}")
                            self.tests_passed += 1
                            return True, response_data
                        else:
                            print(f"❌ Validation failed: {validation_message}")
                            return False, response_data
                    else:
                        # If no custom validation, consider it a pass
                        self.tests_passed += 1
                        return True, response_data
                        
                except ValueError:
                    print("⚠️ Response is not valid JSON")
                    if custom_validation:
                        return False, None
                    else:
                        self.tests_passed += 1
                        return True, None
            else:
                print(f"❌ Status check failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Error response: {response.json()}")
                except:
                    print(f"Error response: {response.text}")
                return False, None

        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            return False, None

    def test_api_root(self):
        """Test the API root endpoint"""
        return self.run_test(
            "API Root",
            "GET",
            "api",
            200
        )

    def test_analyze_solana_wallet(self, wallet_address="GPT8wwUbnYgxckmFmV2Pj1MYucodd9R4P8xNqv9WEwrr"):
        """Test analysis for a Solana wallet"""
        def validate_response(data):
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
                
            # Verify all values are zero or empty strings (no sample data)
            if data["best_trade_profit"] != 0.0 or data["best_trade_token"] != "":
                return False, f"Expected zero values, but got: best_trade_profit={data['best_trade_profit']}, best_trade_token={data['best_trade_token']}"
                
            if data["best_multiplier"] != 0.0 or data["best_multiplier_token"] != "":
                return False, f"Expected zero values, but got: best_multiplier={data['best_multiplier']}, best_multiplier_token={data['best_multiplier_token']}"
                
            if data["all_time_pnl"] != 0.0:
                return False, f"Expected zero values, but got: all_time_pnl={data['all_time_pnl']}"
                
            if data["worst_trade_loss"] != 0.0 or data["worst_trade_token"] != "":
                return False, f"Expected zero values, but got: worst_trade_loss={data['worst_trade_loss']}, worst_trade_token={data['worst_trade_token']}"
                
            return True, "Response correctly shows zero values for all metrics (no sample data)"
            
        return self.run_test(
            "Analyze Solana Wallet",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            custom_validation=validate_response
        )

    def test_analyze_base_wallet(self, wallet_address="0x671b746d2c5a34609cce723cbf8f475639bc0fa2"):
        """Test analysis for a Base wallet"""
        def validate_response(data):
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
                
            # Verify all values are zero or empty strings (no sample data)
            if data["best_trade_profit"] != 0.0 or data["best_trade_token"] != "":
                return False, f"Expected zero values, but got: best_trade_profit={data['best_trade_profit']}, best_trade_token={data['best_trade_token']}"
                
            if data["best_multiplier"] != 0.0 or data["best_multiplier_token"] != "":
                return False, f"Expected zero values, but got: best_multiplier={data['best_multiplier']}, best_multiplier_token={data['best_multiplier_token']}"
                
            if data["all_time_pnl"] != 0.0:
                return False, f"Expected zero values, but got: all_time_pnl={data['all_time_pnl']}"
                
            if data["worst_trade_loss"] != 0.0 or data["worst_trade_token"] != "":
                return False, f"Expected zero values, but got: worst_trade_loss={data['worst_trade_loss']}, worst_trade_token={data['worst_trade_token']}"
                
            return True, "Response correctly shows zero values for all metrics (no sample data)"
            
        return self.run_test(
            "Analyze Base Wallet",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"},
            custom_validation=validate_response
        )

    def test_analyze_random_wallet(self, wallet_address="0x8c87af79c0b9bb8856a5ca09cb5a2a0a38b8f43e"):
        """Test analysis for a random wallet"""
        def validate_response(data):
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
                
            # Verify all values are zero or empty strings (no sample data)
            if data["best_trade_profit"] != 0.0 or data["best_trade_token"] != "":
                return False, f"Expected zero values, but got: best_trade_profit={data['best_trade_profit']}, best_trade_token={data['best_trade_token']}"
                
            if data["best_multiplier"] != 0.0 or data["best_multiplier_token"] != "":
                return False, f"Expected zero values, but got: best_multiplier={data['best_multiplier']}, best_multiplier_token={data['best_multiplier_token']}"
                
            if data["all_time_pnl"] != 0.0:
                return False, f"Expected zero values, but got: all_time_pnl={data['all_time_pnl']}"
                
            if data["worst_trade_loss"] != 0.0 or data["worst_trade_token"] != "":
                return False, f"Expected zero values, but got: worst_trade_loss={data['worst_trade_loss']}, worst_trade_token={data['worst_trade_token']}"
                
            return True, "Response correctly shows zero values for all metrics (no sample data)"
            
        return self.run_test(
            "Analyze Random Wallet",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"},
            custom_validation=validate_response
        )

    def test_solana_leaderboard(self, stat_type="best_trade"):
        """Test Solana leaderboard endpoint"""
        def validate_response(data):
            if not isinstance(data, list):
                return False, f"Expected a list response, got {type(data)}"
                
            # Verify the leaderboard is empty (no sample data)
            if len(data) > 0:
                return False, f"Expected empty leaderboard, but got {len(data)} entries"
                
            return True, "Leaderboard is correctly empty (no sample data)"
            
        return self.run_test(
            f"Solana Leaderboard - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}?blockchain=solana",
            200,
            custom_validation=validate_response
        )

    def test_base_leaderboard(self, stat_type="best_trade"):
        """Test Base leaderboard endpoint"""
        def validate_response(data):
            if not isinstance(data, list):
                return False, f"Expected a list response, got {type(data)}"
                
            # Verify the leaderboard is empty (no sample data)
            if len(data) > 0:
                return False, f"Expected empty leaderboard, but got {len(data)} entries"
                
            return True, "Leaderboard is correctly empty (no sample data)"
            
        return self.run_test(
            f"Base Leaderboard - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}?blockchain=base",
            200,
            custom_validation=validate_response
        )