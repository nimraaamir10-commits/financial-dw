"""
UC3 — Analytics engine.

Pure Python / pandas computations that run on data retrieved from MongoDB.
Designed so the same functions can be fed by Apache Spark or any DataFrame source.
"""

from __future__ import annotations
from typing import Any
import pandas as pd
import numpy as np


def to_df(series: list[dict]) -> pd.DataFrame:
    """Convert list of time-series dicts to a clean DataFrame."""
    df = pd.DataFrame(series)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.set_index("date").sort_index()
    for col in ["open", "high", "low", "close", "volume", "adjustedClose"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Descriptive stats
# ─────────────────────────────────────────────────────────────────────────────

def descriptive_stats(series: list[dict], field: str = "close") -> dict:
    df = to_df(series)
    if df.empty or field not in df:
        return {}
    s = df[field].dropna()
    return {
        "field":  field,
        "count":  int(s.count()),
        "min":    round(float(s.min()), 4),
        "max":    round(float(s.max()), 4),
        "mean":   round(float(s.mean()), 4),
        "median": round(float(s.median()), 4),
        "std":    round(float(s.std()), 4),
        "first":  round(float(s.iloc[0]), 4),
        "last":   round(float(s.iloc[-1]), 4),
        "change_pct": round((float(s.iloc[-1]) - float(s.iloc[0])) / float(s.iloc[0]) * 100, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Moving averages & trend
# ─────────────────────────────────────────────────────────────────────────────

def moving_averages(series: list[dict], field: str = "close", windows: list[int] = [7, 30, 90]) -> list[dict]:
    df = to_df(series)
    if df.empty or field not in df:
        return []
    result = df[[field]].copy()
    for w in windows:
        result[f"ma_{w}d"] = result[field].rolling(w).mean().round(4)
    result = result.reset_index()
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result.dropna().to_dict(orient="records")


def trend_signal(series: list[dict], field: str = "close") -> dict:
    """
    Simple Golden Cross / Death Cross signal.
    Golden Cross = MA50 > MA200 → bullish.
    Death Cross  = MA50 < MA200 → bearish.
    """
    df = to_df(series)
    if df.empty or field not in df or len(df) < 200:
        return {"signal": "insufficient_data"}
    s = df[field].dropna()
    ma50  = s.rolling(50).mean().iloc[-1]
    ma200 = s.rolling(200).mean().iloc[-1]
    signal = "golden_cross_bullish" if ma50 > ma200 else "death_cross_bearish"
    return {
        "signal": signal,
        "ma_50":  round(float(ma50),  4),
        "ma_200": round(float(ma200), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Volatility / Risk
# ─────────────────────────────────────────────────────────────────────────────

def volatility(series: list[dict], field: str = "close", window: int = 30) -> dict:
    """Annualised rolling volatility (standard deviation of log returns)."""
    df = to_df(series)
    if df.empty or field not in df:
        return {}
    log_ret = np.log(df[field] / df[field].shift(1)).dropna()
    ann_vol = round(float(log_ret.rolling(window).std().iloc[-1]) * np.sqrt(252) * 100, 2)
    return {
        "annualised_volatility_pct": ann_vol,
        "window_days": window,
        "interpretation": (
            "low (<15%)" if ann_vol < 15 else
            "moderate (15-30%)" if ann_vol < 30 else
            "high (30-60%)" if ann_vol < 60 else
            "extreme (>60%)"
        ),
    }


def max_drawdown(series: list[dict], field: str = "close") -> dict:
    df = to_df(series)
    if df.empty or field not in df:
        return {}
    s = df[field].dropna()
    peak = s.cummax()
    drawdown = (s - peak) / peak
    mdd = round(float(drawdown.min()) * 100, 2)
    return {"max_drawdown_pct": mdd, "interpretation": f"{abs(mdd):.1f}% peak-to-trough decline"}


# ─────────────────────────────────────────────────────────────────────────────
# Comparison
# ─────────────────────────────────────────────────────────────────────────────

def compare_assets(series_map: dict[str, list[dict]], field: str = "close") -> list[dict]:
    """
    Normalise multiple assets to 100 at start date for visual comparison.
    series_map: {"NVDA": [...], "AMD": [...], ...}
    Returns list of {date, symbol, normalised_value}.
    """
    rows = []
    for symbol, series in series_map.items():
        df = to_df(series)
        if df.empty or field not in df:
            continue
        s = df[field].dropna()
        base = s.iloc[0]
        for date, val in s.items():
            rows.append({
                "date":   date.strftime("%Y-%m-%d"),
                "symbol": symbol,
                "normalised": round(float(val) / float(base) * 100, 4),
                "price": round(float(val), 4),
            })
    return sorted(rows, key=lambda x: (x["date"], x["symbol"]))


# ─────────────────────────────────────────────────────────────────────────────
# Simple forecast (linear regression next-day price)
# ─────────────────────────────────────────────────────────────────────────────

def forecast_next_day(series: list[dict], field: str = "close", lookback: int = 30) -> dict:
    """
    Linear regression on last `lookback` days → next-day price estimate.
    Clearly labelled as a naive statistical model (NOT financial advice).
    """
    from sklearn.linear_model import LinearRegression
    df = to_df(series)
    if df.empty or field not in df or len(df) < lookback:
        return {"error": "Insufficient data"}
    s = df[field].dropna().tail(lookback)
    X = np.arange(len(s)).reshape(-1, 1)
    y = s.values
    model = LinearRegression().fit(X, y)
    next_val = float(model.predict([[len(s)]])[0])
    last_val = float(s.iloc[-1])
    return {
        "model": "LinearRegression",
        "lookback_days": lookback,
        "last_close": round(last_val, 4),
        "predicted_next_close": round(next_val, 4),
        "predicted_change_pct": round((next_val - last_val) / last_val * 100, 2),
        "disclaimer": "Naive statistical model. Not financial advice.",
    }
