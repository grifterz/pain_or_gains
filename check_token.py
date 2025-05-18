import requests
import re
import json

token_address = "5HyZiyaSsQt8VZBAJcULZhtykiVmkAkWLiQJCER9pump"

# Try direct API call
print(f"Checking token {token_address} via Solscan API...")
api_url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
headers = {"accept": "application/json"}

try:
    api_response = requests.get(api_url, headers=headers)
    print(f"API response status: {api_response.status_code}")
    
    if api_response.status_code == 200:
        data = api_response.json()
        print(f"API response data: {json.dumps(data, indent=2)}")
        
        name = data.get("name", "")
        symbol = data.get("symbol", "")
        if name or symbol:
            print(f"Found token name: {name}, symbol: {symbol}")
        else:
            print("API returned no name/symbol")
    else:
        print(f"API error: {api_response.text}")
except Exception as e:
    print(f"API request failed: {str(e)}")

# Try web scraping
print("\nFalling back to web scraping...")
web_url = f"https://solscan.io/token/{token_address}"

try:
    web_response = requests.get(web_url)
    print(f"Web response status: {web_response.status_code}")
    
    if web_response.status_code == 200:
        html = web_response.text
        print(f"Got {len(html)} bytes of HTML")
        
        # Look for title
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            title = title_match.group(1)
            print(f"Page title: {title}")
            
            # Parse token info from title
            token_match = re.search(r'(.*?) \((\w+)\)', title)
            if token_match:
                name = token_match.group(1)
                symbol = token_match.group(2)
                print(f"Found token name: {name}, symbol: {symbol}")
        
        # Look for other token indicators in HTML
        html_snippet = html[:5000]  # Just look at the first part
        print(f"\nHTML snippet:\n{html_snippet}")
    else:
        print(f"Web scraping error: {web_response.text}")
except Exception as e:
    print(f"Web scraping failed: {str(e)}")
