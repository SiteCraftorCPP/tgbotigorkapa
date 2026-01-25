import asyncio
import httpx
from utils.logger import logger

async def test_endpoints():
    endpoints = [
        "https://fapi.xt.com/future/market/v1/public/symbol/list",
        "https://fapi.xt.com/future/market/v1/public/q/tickers",
        "https://fapi.xt.com/fapi/v1/ticker/24hr",
        "https://fapi.xt.com/fapi/v1/exchangeInfo"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers) as client:
        for url in endpoints:
            print(f"\nTesting {url}...")
            try:
                response = await client.get(url, timeout=30.0)
                print(f"Status: {response.status_code}")
                try:
                    data = response.json()
                    print(f"Keys: {data.keys()}")
                    if 'result' in data:
                        res = data['result']
                        if isinstance(res, list):
                            print(f"Result is list of length {len(res)}")
                            if len(res) > 0:
                                print(f"First item: {str(res[0])[:200]}")
                        elif isinstance(res, dict):
                            print(f"Result is dict with keys: {res.keys()}")
                            if 'symbols' in res:
                                print(f"Found {len(res['symbols'])} symbols")
                    elif 'data' in data:
                        d = data['data']
                        if isinstance(d, list):
                            print(f"Data is list of length {len(d)}")
                        elif isinstance(d, dict):
                            print(f"Data is dict with keys: {d.keys()}")
                    else:
                        print(f"Response preview: {str(data)[:200]}...")
                except Exception as je:
                    print(f"JSON decode failed: {je}")
                    print(f"Raw response preview: {response.text[:200]}...")
            except Exception as e:
                print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
