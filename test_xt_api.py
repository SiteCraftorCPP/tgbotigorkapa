import asyncio
import json
from exchange.xt_client import XTClient
from utils.logger import logger

async def test_xt():
    client = XTClient()
    print("Testing raw request to exchangeInfo...")
    try:
        response = client.exchange.fapiPublicGetExchangeInfo()
        print(f"Raw response keys: {response.keys()}")
        if 'result' in response:
            print(f"Result keys: {response['result'].keys()}")
            if 'symbols' in response['result']:
                print(f"Found {len(response['result']['symbols'])} symbols")
            else:
                # Maybe it's a different endpoint?
                print("No 'symbols' in result")
                print(f"Result content preview: {str(response['result'])[:500]}")
    except Exception as e:
        print(f"Raw request failed: {e}")

    print("\nTesting fetch_tickers...")
    try:
        tickers = await client._run_in_executor(client.exchange.fetch_tickers)
        print(f"Fetched {len(tickers)} tickers")
        usdt_tickers = [s for s in tickers.keys() if 'USDT' in s.upper()]
        print(f"USDT tickers count: {len(usdt_tickers)}")
        if usdt_tickers:
            print(f"Example USDT tickers: {usdt_tickers[:5]}")
    except Exception as e:
        print(f"fetch_tickers failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_xt())
