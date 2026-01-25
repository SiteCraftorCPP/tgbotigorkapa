import ccxt
import asyncio

async def test_xt_linear():
    ex = ccxt.xt()
    print("Testing fetch_tickers for linear markets...")
    try:
        # XT linear markets use different symbols, e.g. btc_usdt
        # Let's try to fetch all tickers from the linear URL
        ex.urls['api']['public'] = ex.urls['api']['linear']
        tickers = await asyncio.to_thread(ex.fetch_tickers)
        print(f"Found {len(tickers)} tickers")
        if tickers:
            print(f"First 5: {list(tickers.keys())[:5]}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_xt_linear())
