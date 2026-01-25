import ccxt
import json

def check_xt():
    xt = ccxt.xt()
    print(f"XT has fetch_markets: {xt.has['fetchMarkets']}")
    print(f"XT has fetch_ohlcv: {xt.has['fetchOHLCV']}")
    print(f"XT URLs: {json.dumps(xt.urls, indent=2)}")
    
    # Try to load markets
    try:
        # XT might have separate URLs for swap/future
        # Let's check if it supports 'defaultType': 'future'
        xt_future = ccxt.xt({'options': {'defaultType': 'future'}})
        print(f"XT Future URLs: {json.dumps(xt_future.urls, indent=2)}")
        
        # xt_future.load_markets() is slow, let's just check the URLs first
    except Exception as e:
        print(f"Error checking XT Future: {e}")

if __name__ == "__main__":
    check_xt()
