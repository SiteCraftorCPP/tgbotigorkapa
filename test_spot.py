import asyncio
import httpx

async def test_spot():
    url = "https://sapi.xt.com/v4/public/ticker/24h"
    print(f"Testing {url}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=10.0)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            if data.get('rc') == 0:
                tickers = data.get('result', [])
                print(f"Found {len(tickers)} spot tickers")
                usdt_tickers = [t for t in tickers if t.get('s', '').endswith('usdt')]
                print(f"USDT spot tickers: {len(usdt_tickers)}")
                if usdt_tickers:
                    print(f"First 5: {[t['s'] for t in usdt_tickers[:5]]}")
            else:
                print(f"Error: {data}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_spot())
