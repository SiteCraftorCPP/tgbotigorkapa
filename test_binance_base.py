import asyncio
import ccxt
import json

class TestXT(ccxt.binance):
    def __init__(self):
        super().__init__({
            'urls': {
                'api': {
                    'fapiPublic': 'https://fapi.xt.com',
                    'fapiPrivate': 'https://fapi.xt.com',
                }
            }
        })

async def test_binance_base():
    ex = TestXT()
    print("Testing fapiPublicGetExchangeInfo with base https://fapi.xt.com ...")
    try:
        res = await asyncio.to_thread(ex.fapiPublicGetExchangeInfo)
        print(f"Success! Found {len(res.get('symbols', []))} symbols")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_binance_base())
