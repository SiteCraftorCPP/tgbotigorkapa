import asyncio
from datetime import datetime

from exchange.xt_client import XTClient
from utils.deepseek_client import get_deepseek_client
from utils.chart import render_signal_chart
from telegram_bot.bot import TelegramBot


async def main():
    pair = "BTC/USDT"
    timeframe = "15m"
    direction = "LONG"

    xt = XTClient()
    df = await xt.get_ohlcv(pair, timeframe, limit=400)
    if df is None or df.empty:
        print("No data for chart")
        return

    last_close = float(df["close"].iloc[-1])
    atr_guess = float(df["close"].tail(14).std() or 0.001)

    # Делает уровни более реалистичными относительно волатильности
    entry = last_close
    stop = entry - max(atr_guess * 0.6, entry * 0.002)  # ~0.6 ATR или 0.2%
    tp1 = entry + max(atr_guess * 0.8, entry * 0.003)
    tp2 = entry + max(atr_guess * 1.2, entry * 0.005)
    tp3 = entry + max(atr_guess * 1.8, entry * 0.008)

    signal = {
        "signal_id": f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "ticker": pair,
        "direction": direction,
        "timeframe": timeframe,
        "timeframe_higher": "1h",
        "entry_price": entry,
        "stop_loss": stop,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "take_profit_3": tp3,
        "take_profit_4": tp3,
        "risk_percent": 1.0,
        "leverage": 10,
        "created_at": datetime.utcnow(),
        "volume_24h": None,
        "spread_percent": None,
        "atr_value": atr_guess,
        "liquidity_usdt": 500_000,
        "analysis": {
            "trend": {"higher": "UP", "lower": "UP", "score": 35},
            "structure": "HH+HL confirmed on 15m; higher TF aligned",
            "volatility": {"atr": atr_guess, "regime": "normal"},
            "volume": {"24h": "ok", "comment": "steady"},
            "context": "BTC calm, no major news; structure intact; pullback within ATR band",
        },
    }

    # Для тестового поста — форсируем plan и approved без запроса к DeepSeek,
    # чтобы гарантированно отправить в канал.
    ds_result = {
        "approved": True,
        "plan": {
            "entry_zone": {"from": entry * 0.999, "to": entry * 1.001},
            "sl": stop,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "confidence": 0.5,
            "risk": "Test override",
            "reason": "Forced approve for test post",
        },
    }
    signal["deepseek"] = ds_result

    chart_path = render_signal_chart(df, signal, ds_result.get("plan"))
    if chart_path:
        signal["chart_path"] = chart_path

    bot = TelegramBot()
    await bot.send_signal(signal)


if __name__ == "__main__":
    asyncio.run(main())

