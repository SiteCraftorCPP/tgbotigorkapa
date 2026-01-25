import httpx
import asyncio

async def get_xt_futures_symbols():
    url = "https://fapi.xt.com/future/market/v1/public/symbol/list"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url, timeout=20.0)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            if data.get('returnCode') == 0:
                symbols = data.get('result', [])
                usdt_symbols = [s['symbol'] for s in symbols if s.get('quoteCurrency') == 'usdt']
                print(f"Found {len(usdt_symbols)} USDT symbols")
                return usdt_symbols
            else:
                print(f"API Error: {data}")
        except Exception as e:
            print(f"Request failed: {e}")
    return []

if __name__ == "__main__":
    asyncio.run(get_xt_futures_symbols())
