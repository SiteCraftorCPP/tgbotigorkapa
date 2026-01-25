import asyncio
import httpx
import json

async def test_v4():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    # Try symbols list
    url_symbols = "https://fapi.xt.com/future/market/v1/public/symbol/list"
    print(f"Testing {url_symbols}...")
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url_symbols, timeout=60.0)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            if data.get('returnCode') == 0:
                symbols = data.get('result', [])
                print(f"Found {len(symbols)} symbols")
                if symbols:
                    print(f"First symbol: {symbols[0]}")
            else:
                print(f"Error in response: {data}")
        except Exception as e:
            print(f"Symbols list failed: {repr(e)}")

    # Try tickers
    url_tickers = "https://fapi.xt.com/future/market/v1/public/q/tickers"
    print(f"\nTesting {url_tickers}...")
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url_tickers, timeout=60.0)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            if data.get('returnCode') == 0:
                tickers = data.get('result', [])
                print(f"Found {len(tickers)} tickers")
                if tickers:
                    print(f"First ticker: {tickers[0]}")
            else:
                print(f"Error in response: {data}")
        except Exception as e:
            print(f"Tickers failed: {repr(e)}")

if __name__ == "__main__":
    asyncio.run(test_v4())
