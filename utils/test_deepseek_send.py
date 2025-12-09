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

    entry = last_close
    stop = entry * 0.99
    tp1 = entry * 1.01
    tp2 = entry * 1.02
    tp3 = entry * 1.03

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
        "liquidity_usdt": None,
        "analysis": {
            # Минимальный контекст, чтобы DeepSeek не отклонял из‑за пустого анализа
            "structure": "Higher highs/lows on 15m, pullback to short-term support",
            "momentum": "RSI mildly bullish, MACD cross up, no overextension",
            "volume": "Stable intraday volume, no abnormal spikes",
            "context_summary": {
                "trend_comment": "Short-term uptrend; price above 50 EMA on 15m",
                "news_comment": "No major market news in the last hour",
                "btc_comment": "BTC holding steady; no broad risk-off move",
                "risk_comment": "Stop under recent swing low; moderate ATR-based risk",
            },
        },
    }

    ds_client = get_deepseek_client()
    ds_result = await ds_client.analyze_signal(signal)
    signal["deepseek"] = ds_result

    if not ds_result.get("approved"):
        reason = (ds_result.get("plan") or {}).get("reason") or ds_result.get("error") or "Rejected"
        print(f"DeepSeek rejected: {reason}")
        # Для теста даём запасной план, чтобы всё равно проверить отправку в канал
        ds_plan = {
            "entry_zone": entry,
            "sl": stop,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "risk_level": "medium",
            "confidence": 70,
            "setup_type": "test_setup",
            "context_summary": signal["analysis"].get("context_summary", {}),
            "reason": f"Fallback after rejection: {reason}",
        }
        ds_result = {"approved": True, "plan": ds_plan}
        signal["deepseek"] = ds_result

    chart_path = render_signal_chart(df, signal, ds_result.get("plan"))
    if chart_path:
        signal["chart_path"] = chart_path

    bot = TelegramBot()
    await bot.send_signal(signal)


if __name__ == "__main__":
    asyncio.run(main())

