import os
from datetime import datetime
from typing import Dict, Optional

import mplfinance as mpf
import matplotlib.pyplot as plt
import pandas as pd


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def render_signal_chart(
    df: pd.DataFrame, signal: Dict, plan: Optional[Dict] = None, limit: int = 120
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
    entry_zone_dict = None
    if isinstance(entry_zone, dict):
        entry_from = _as_float(entry_zone.get("from"))
        entry_to = _as_float(entry_zone.get("to"))
        if entry_from and entry_to:
            entry_level = (entry_from + entry_to) / 2
            entry_zone_dict = {"from": entry_from, "to": entry_to}
    else:
        entry_level = _as_float(entry_level)

    # Файл
    charts_dir = os.path.join("logs", "charts")
    _ensure_dir(charts_dir)
    fname = f"{signal.get('ticker','signal').replace('/','_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    out_path = os.path.join(charts_dir, fname)

    # Настройка стиля
    try:
        market_colors = mpf.make_marketcolors(
            up="#2fb98f",
            down="#e06464",
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

        fig, axes = mpf.plot(
            tail,
            type="candle",
            style=style,
            volume=False,
            returnfig=True,
        )
        ax = axes[0]

        # Рисуем зону входа
        if entry_zone_dict:
            y1 = float(entry_zone_dict["from"])
            y2 = float(entry_zone_dict["to"])
            ax.axhspan(y1, y2, color="#1f77b4", alpha=0.12, linewidth=0)
            entry_label_y = (y1 + y2) / 2
        else:
            entry_label_y = entry_level

        # Функция для подписей справа
        def add_line(y, color, text, ls="--"):
            if y is None:
                return
            ax.axhline(y, color=color, linestyle=ls, linewidth=1.2, alpha=0.9)
            x_min, x_max = ax.get_xlim()
            dx = (x_max - x_min) * 0.005
            ax.text(
                x_max + dx,
                y,
                text,
                color=color,
                fontsize=8,
                va="center",
                ha="left",
            )

        add_line(stop, "#e76f51", "Stop-Loss", ls="--")
        add_line(entry_label_y, "#4d7cff", "Entry", ls="--")
        add_line(tp1, "#1db989", "Target 1", ls="--")
        add_line(tp2, "#1db989", "Target 2", ls="--")
        add_line(tp3, "#1db989", "Target 3", ls="--")

        # Опциональный TP4 если есть
        tp4 = (plan or {}).get("tp4")
        if tp4:
            tp4 = _as_float(tp4)
            add_line(tp4, "#1db989", "Target 4", ls="--")

        ax.set_title(f"{signal.get('ticker')} {signal.get('timeframe')}", color="#d0d4dc")

        fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="#0b0d11")
        plt.close(fig)
        return out_path
    except Exception:
        return None

