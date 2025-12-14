import os
from datetime import datetime
from typing import Dict, Optional

import mplfinance as mpf
import pandas as pd


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _tf_to_pandas_freq(tf: Optional[str]) -> Optional[str]:
    """Конвертирует TF вида '1m', '5m', '1h', '4h' в pandas offset alias."""
    if not tf or not isinstance(tf, str):
        return None
    tf = tf.lower().strip()
    if tf.endswith("m"):
        try:
            return f"{int(tf[:-1])}min"
        except Exception:
            return None
    if tf.endswith("h"):
        try:
            return f"{int(tf[:-1])}h"
        except Exception:
            return None
    return None


def render_signal_chart(
    df: pd.DataFrame, signal: Dict, plan: Optional[Dict] = None, limit: int = 100
) -> Optional[str]:
    """
    Рендерит свечной график с уровнями entry/SL/TP.
    Возвращает путь к сохранённому PNG или None.
    """
    if df is None or df.empty:
        return None

    tail = df.tail(limit).copy()
    # mplfinance ожидает индекс datetime и колонки open/high/low/close/volume
    if not isinstance(tail.index, pd.DatetimeIndex):
        try:
            tail.index = pd.to_datetime(tail.index)
        except Exception:
            return None

    # Дополнительно нормализуем частоту, чтобы не было "решётки" из множества свечей в одном таймстемпе
    tf_freq = _tf_to_pandas_freq(signal.get("timeframe"))
    if tf_freq:
        try:
            tail = (
                tail.resample(tf_freq)
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum" if "volume" in tail.columns else "first",
                    }
                )
                .dropna(how="any")
            )
        except Exception:
            pass

    levels = []
    colors = []
    labels = []

    # Используем план DeepSeek при наличии, иначе базовые уровни
    entry_zone = None
    if plan:
        entry_zone = plan.get("entry_zone")
    stop = (plan or {}).get("sl", signal.get("stop_loss"))
    tp1 = (plan or {}).get("tp1", signal.get("take_profit_1"))
    tp2 = (plan or {}).get("tp2", signal.get("take_profit_2"))
    tp3 = (plan or {}).get("tp3", signal.get("take_profit_3"))

    def _as_float(val):
        try:
            return float(val)
        except Exception:
            return None

    stop = _as_float(stop)
    tp1 = _as_float(tp1)
    tp2 = _as_float(tp2)
    tp3 = _as_float(tp3)

    # Entry как середина зоны, если зона
    entry_level = signal.get("entry_price")
    if isinstance(entry_zone, dict):
        entry_from = _as_float(entry_zone.get("from"))
        entry_to = _as_float(entry_zone.get("to"))
        if entry_from and entry_to:
            entry_level = (entry_from + entry_to) / 2
            levels.extend([entry_from, entry_to])
            colors.extend(["#2a9d8f", "#2a9d8f"])
            labels.extend(["Entry from", "Entry to"])
    else:
        entry_level = _as_float(entry_level)

    # Основные линии
    for val, color, label in [
        (entry_level, "#1f77b4", "Entry"),
        (stop, "#e76f51", "Stop"),
        (tp1, "#2ca02c", "TP1"),
        (tp2, "#2ca02c", "TP2"),
        (tp3, "#2ca02c", "TP3"),
    ]:
        if val:
            levels.append(val)
            colors.append(color)
            labels.append(label)

    # Файл
    charts_dir = os.path.join("logs", "charts")
    _ensure_dir(charts_dir)
    fname = f"{signal.get('ticker','signal').replace('/','_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    out_path = os.path.join(charts_dir, fname)

    # Настройка стиля
    market_colors = mpf.make_marketcolors(
        up="#4caf50",
        down="#ef5350",
        wick="inherit",
        edge="inherit",
        volume="inherit",
    )
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=market_colors,
        facecolor="#0f1115",
        edgecolor="#0f1115",
        gridcolor="#1c1f26",
        rc={
            "axes.labelcolor": "#d0d4dc",
            "xtick.color": "#9aa0aa",
            "ytick.color": "#9aa0aa",
            "figure.facecolor": "#0b0d11",
        },
    )

    try:
        fill_between = None
        if isinstance(entry_zone, dict) and entry_zone.get("from") and entry_zone.get("to"):
            y1 = [float(entry_zone["from"])] * len(tail)
            y2 = [float(entry_zone["to"])] * len(tail)
            fill_between = dict(y1=y1, y2=y2, color="#1f77b4", alpha=0.10)

        plot_kwargs = dict(
            tail=tail,
        )
        # Обязательные параметры
        plot_args = {
            "type": "candle",
            "style": style,
            "hlines": dict(hlines=levels, colors=colors, linewidths=[1.4] * len(levels)),
            "title": f"{signal.get('ticker')} {signal.get('timeframe')}",
            "figsize": (16, 9),  # Ширина x Высота в дюймах (широкий формат)
            "savefig": dict(
                fname=out_path,
                dpi=200,
                bbox_inches="tight",
                facecolor="#0b0d11",
            ),
            "widths": dict(candle=0.7, wick=0.6),
            "datetime_format": "%H:%M",
        }
        if fill_between:
            plot_args["fill_between"] = fill_between

        mpf.plot(tail, **plot_args)
        return out_path
    except Exception as e:
        # Помогаем отладить, почему график не построился
        try:
            from utils.logger import log_error
            log_error(f"render_signal_chart failed: {e}", "chart")
        except Exception:
            pass
        return None

