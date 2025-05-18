import requests
import unittest
import json
import sys
from datetime import datetime

class MemecoinsAPITester:
    def __init__(self, base_url="https://43b589cc-db04-440d-85a8-d0c5492c5451.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
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

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.text}")
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "api",
            200
        )

    def test_analyze_solana_wallet(self, wallet_address="8kzcTCwWTmsYTkNPbsMiQGE9sBJqXY5X38UHgtQ8cEwN"):
        """Test analyzing a Solana wallet"""
        return self.run_test(
            "Analyze Solana Wallet",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "solana"}
        )
    
    def test_analyze_base_wallet(self, wallet_address="0x5A927Ac639636E534b678Ec56a1a9fE5F3993c54"):
        """Test analyzing a Base wallet"""
        return self.run_test(
            "Analyze Base Wallet",
            "POST",
            "api/analyze",
            200,
            data={"wallet_address": wallet_address, "blockchain": "base"}
        )
    
    def test_invalid_wallet_address(self):
        """Test with invalid wallet address"""
        return self.run_test(
            "Invalid Wallet Address",
            "POST",
            "api/analyze",
            400,
            data={"wallet_address": "invalid-address", "blockchain": "solana"}
        )
    
    def test_leaderboard_solana(self, stat_type="best_trade"):
        """Test getting Solana leaderboard"""
        return self.run_test(
            f"Solana Leaderboard - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}",
            200,
            params={"blockchain": "solana", "limit": 10}
        )
    
    def test_leaderboard_base(self, stat_type="best_trade"):
        """Test getting Base leaderboard"""
        return self.run_test(
            f"Base Leaderboard - {stat_type}",
            "GET",
            f"api/leaderboard/{stat_type}",
            200,
            params={"blockchain": "base", "limit": 10}
        )
    
    def test_invalid_leaderboard_stat(self):
        """Test with invalid leaderboard stat type"""
        return self.run_test(
            "Invalid Leaderboard Stat Type",
            "GET",
            "api/leaderboard/invalid_stat",
            400,
            params={"blockchain": "solana", "limit": 10}
        )

def main():
    # Setup
    tester = MemecoinsAPITester()
    
    # Run tests
    tester.test_root_endpoint()
    
    # Test wallet analysis
    solana_success, solana_data = tester.test_analyze_solana_wallet()
    base_success, base_data = tester.test_analyze_base_wallet()
    tester.test_invalid_blockchain()
    
    # Test leaderboard endpoints
    for stat_type in ["best_trade", "best_multiplier", "all_time_pnl", "worst_trade"]:
        tester.test_leaderboard_solana(stat_type)
        tester.test_leaderboard_base(stat_type)
    
    tester.test_invalid_leaderboard_stat()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())