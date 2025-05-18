import requests
import sys
import json
from datetime import datetime

class MemecoinsAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, expected_content=None):
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
            
            # Check status code
            status_success = response.status_code == expected_status
            if not status_success:
                print(f"❌ Failed - Expected status {expected_status}, got {response.status_code}")
                self.failed_tests.append({
                    "name": name,
                    "reason": f"Expected status {expected_status}, got {response.status_code}",
                    "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                })
                return False, response
            
            # Check content if expected_content is provided
            content_success = True
            response_json = {}
            
            try:
                if response.text:
                    response_json = response.json()
            except json.JSONDecodeError:
                if expected_content:
                    print(f"❌ Failed - Expected JSON response, got non-JSON: {response.text[:100]}")
                    content_success = False
            
            if expected_content and content_success:
                for key, value in expected_content.items():
                    if key not in response_json:
                        print(f"❌ Failed - Expected key '{key}' not found in response")
                        content_success = False
                        break
                    elif callable(value):
                        if not value(response_json[key]):
                            print(f"❌ Failed - Validation failed for key '{key}': {response_json[key]}")
                            content_success = False
                            break
                    elif response_json[key] != value:
                        print(f"❌ Failed - Expected '{key}' to be '{value}', got '{response_json[key]}'")
                        content_success = False
                        break
            
            success = status_success and content_success
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if expected_content:
                    print(f"   Response contains expected content")
            else:
                self.failed_tests.append({
                    "name": name,
                    "reason": "Content validation failed",
                    "response": str(response_json)[:200] + "..." if len(str(response_json)) > 200 else str(response_json)
                })
            
            return success, response
        
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "name": name,
                "reason": f"Exception: {str(e)}",
                "response": "N/A"
            })
            return False, None

    def test_no_memecoin_activity(self):
        """Test analyzing a wallet with no memecoin activity"""
        wallet_address = "7EqvJ1KaFzV9FrcvZezSKob3VfsBuN6mEMcCkSTJw48G"
        
        success, response = self.run_test(
            "Analyze Wallet With No Memecoin Activity",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"},
            expected_content={
                "wallet_address": wallet_address,
                "blockchain": "solana",
                "best_trade_profit": 0.0,
                "best_trade_token": "",
                "best_multiplier": 0.0,
                "best_multiplier_token": "",
                "all_time_pnl": 0.0,
                "worst_trade_loss": 0.0,
                "worst_trade_token": ""
            }
        )
        
        if success:
            print("   Response correctly shows no memecoin activity for this wallet")
        
        return success

    def test_memecoin_activity(self):
        """Test analyzing a wallet with memecoin activity"""
        wallet_address = "8kzcTCwWTmsYTkNPbsMiQGE9sBJqXY5X38UHgtQ8cEwN"
        
        success, response = self.run_test(
            "Analyze Wallet With Memecoin Activity",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"}
        )
        
        if success:
            # Check if the response contains actual data (not empty stats)
            response_json = response.json()
            has_data = (
                response_json.get("best_trade_token") != "" or
                response_json.get("best_multiplier_token") != "" or
                response_json.get("worst_trade_token") != "" or
                abs(response_json.get("all_time_pnl", 0)) > 0.000001
            )
            
            if has_data:
                print("   Response contains real memecoin activity data")
                return True
            else:
                print("❌ Expected real data for active wallet, but found empty stats")
                self.failed_tests.append({
                    "name": "Analyze Wallet With Memecoin Activity",
                    "reason": "Expected real data for active wallet, but found empty stats",
                    "response": str(response_json)
                })
                return False
        
        return False

    def test_invalid_wallet_address(self):
        """Test analyzing an invalid wallet address"""
        wallet_address = "invalid-address"
        
        success, response = self.run_test(
            "Invalid Wallet Address Format",
            "POST",
            "api/analyze",
            400,  # Should return 400 Bad Request
            data={"wallet_address": wallet_address, "blockchain": "solana"}
        )
        
        if not success and response and response.status_code == 200:
            print(f"Response: {response.text}")
        
        return success

    def test_leaderboard(self, stat_type):
        """Test leaderboard endpoint for a specific stat type"""
        success, response = self.run_test(
            f"Leaderboard Entries - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}?blockchain=solana",
            200
        )
        
        if success:
            response_json = response.json()
            
            # Check if the leaderboard has entries
            if len(response_json) > 0:
                # Check if entries have real data (non-empty token names)
                valid_entries = [entry for entry in response_json if entry.get("token", "")]
                
                if len(valid_entries) > 0:
                    print(f"   Leaderboard contains {len(valid_entries)} valid entries with real memecoin activity")
                    return True
                else:
                    print("❌ Leaderboard entries don't have valid token names")
                    self.failed_tests.append({
                        "name": f"Leaderboard Entries - {stat_type}",
                        "reason": "Leaderboard entries don't have valid token names",
                        "response": str(response_json)[:200]
                    })
                    return False
            else:
                print("❌ Leaderboard is empty")
                self.failed_tests.append({
                    "name": f"Leaderboard Entries - {stat_type}",
                    "reason": "Leaderboard is empty",
                    "response": str(response_json)
                })
                return False
        
        return False

    def print_summary(self):
        """Print a summary of the test results"""
        print("\n" + "=" * 50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 50)
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}")
                print(f"    Reason: {test['reason']}")
            
            print("\n" + "=" * 50)

def main():
    # Use the public endpoint from the frontend .env file
    base_url = "https://994f8226-f44b-42aa-9a0f-715c84fc22e4.preview.emergentagent.com"
    
    tester = MemecoinsAPITester(base_url)
    
    # Run tests
    tester.test_no_memecoin_activity()
    tester.test_memecoin_activity()
    tester.test_invalid_wallet_address()
    
    # Test all leaderboard stat types
    tester.test_leaderboard("best_trade")
    tester.test_leaderboard("best_multiplier")
    tester.test_leaderboard("all_time_pnl")
    tester.test_leaderboard("worst_trade")
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())