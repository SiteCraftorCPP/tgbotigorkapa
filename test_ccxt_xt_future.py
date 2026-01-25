import ccxt
import asyncio

async def test_ccxt_xt_future():
    exchange = ccxt.xt({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    print("Loading markets...")
    try:
        markets = await asyncio.to_thread(exchange.load_markets)
        print(f"Loaded {len(markets)} markets")
        
        usdt_futures = [s for s, m in markets.items() if m.get('future') and m.get('quote') == 'USDT']
        print(f"USDT Futures count: {len(usdt_futures)}")
        if usdt_futures:
            print(f"Example pairs: {usdt_futures[:5]}")
            
        print("\nFetching tickers...")
        tickers = await asyncio.to_thread(exchange.fetch_tickers)
        print(f"Fetched {len(tickers)} tickers")
        
    except Exception as e:
        print(f"Failed: {e}")
    finally:
        await asyncio.to_thread(exchange.close)

if __name__ == "__main__":
    asyncio.run(test_ccxt_xt_future())
