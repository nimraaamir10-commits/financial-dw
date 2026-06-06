"""
Yahoo Finance ingestor via yfinance.

Covers: Stocks, ETFs, Commodities, Market Indices.
No API key required.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import yfinance as yf
import pandas as pd

from db.models import AssetCreate, TimeSeriesPoint


# ─────────────────────────────────────────────────────────────────────────────
# Asset catalogue  — "AI & Digital Economy" theme
# ─────────────────────────────────────────────────────────────────────────────

AI_ECONOMY_ASSETS: list[dict[str, Any]] = [
    # ── AI / Semiconductor Stocks ───────────────────────────────────────────
    {
        "symbol": "NVDA",  "name": "NVIDIA Corporation",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "World's leading AI-chip maker powering data centers and autonomous systems.",
        "attributes": {"sector": "Technology", "industry": "Semiconductors", "theme": "AI Infrastructure"},
    },
    {
        "symbol": "AMD",  "name": "Advanced Micro Devices",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "CPU/GPU competitor challenging NVIDIA in the AI accelerator market.",
        "attributes": {"sector": "Technology", "industry": "Semiconductors", "theme": "AI Infrastructure"},
    },
    {
        "symbol": "MSFT", "name": "Microsoft Corporation",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "Azure cloud + OpenAI partnership — enterprise AI backbone.",
        "attributes": {"sector": "Technology", "industry": "Software", "theme": "AI Cloud & Software"},
    },
    {
        "symbol": "GOOGL", "name": "Alphabet Inc.",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "Google DeepMind & TPU chips driving AI search and cloud services.",
        "attributes": {"sector": "Technology", "industry": "Internet", "theme": "AI Cloud & Software"},
    },
    {
        "symbol": "META",  "name": "Meta Platforms Inc.",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "Open-source LLaMA models + AI-driven ad targeting platform.",
        "attributes": {"sector": "Technology", "industry": "Social Media", "theme": "AI Cloud & Software"},
    },
    {
        "symbol": "TSLA",  "name": "Tesla Inc.",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "EV leader with Dojo supercomputer and Full Self-Driving AI ambitions.",
        "attributes": {"sector": "Consumer Discretionary", "industry": "Automotive", "theme": "AI Robotics & Autonomy"},
    },
    # ── Cloud / Data Infrastructure ─────────────────────────────────────────
    {
        "symbol": "AMZN", "name": "Amazon.com Inc.",
        "assetClass": "stock",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "AWS cloud + Bedrock AI services, largest cloud revenue globally.",
        "attributes": {"sector": "Technology", "industry": "Cloud Computing", "theme": "AI Cloud & Software"},
    },
    {
        "symbol": "SNOW",  "name": "Snowflake Inc.",
        "assetClass": "stock",   "region": "US", "exchange": "NYSE", "currency": "USD",
        "description": "Cloud data platform enabling AI/ML workloads at massive scale.",
        "attributes": {"sector": "Technology", "industry": "Data Infrastructure", "theme": "AI Data Platforms"},
    },
    # ── Quantum Computing ────────────────────────────────────────────────────
    {
        "symbol": "IONQ",  "name": "IonQ Inc.",
        "assetClass": "stock",   "region": "US", "exchange": "NYSE", "currency": "USD",
        "description": "Pure-play quantum computing company targeting post-AI computational power.",
        "attributes": {"sector": "Technology", "industry": "Quantum Computing", "theme": "AI Next Frontier"},
    },
    # ── AI-focused ETFs ─────────────────────────────────────────────────────
    {
        "symbol": "BOTZ",  "name": "Global X Robotics & AI ETF",
        "assetClass": "etf",     "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "ETF tracking companies in robotics, AI, and automation industries.",
        "attributes": {"theme": "AI Basket", "expenseRatio": 0.68},
    },
    # ── Market Indices ──────────────────────────────────────────────────────
    {
        "symbol": "^GSPC", "name": "S&P 500 Index",
        "assetClass": "index",   "region": "US", "exchange": "NYSE", "currency": "USD",
        "description": "Broad US equity benchmark — baseline for AI sector comparison.",
        "attributes": {"components": 500},
    },
    {
        "symbol": "^IXIC", "name": "NASDAQ Composite Index",
        "assetClass": "index",   "region": "US", "exchange": "NASDAQ", "currency": "USD",
        "description": "Tech-heavy US index; strong correlation with AI stock performance.",
        "attributes": {"components": 3000},
    },
    # ── Commodities (AI supply chain) ───────────────────────────────────────
    {
        "symbol": "GC=F",  "name": "Gold Futures (COMEX)",
        "assetClass": "commodity", "region": "Global", "exchange": "COMEX", "currency": "USD",
        "description": "Gold — safe-haven asset and benchmark for AI-era monetary inflation.",
        "attributes": {"unit": "troy oz", "contractSize": 100},
    },
    {
        "symbol": "SI=F",  "name": "Silver Futures (COMEX)",
        "assetClass": "commodity", "region": "Global", "exchange": "COMEX", "currency": "USD",
        "description": "Silver — industrial metal critical in chip manufacturing and EVs.",
        "attributes": {"unit": "troy oz", "contractSize": 5000},
    },
]


def get_asset_definitions() -> list[AssetCreate]:
    return [AssetCreate(**a) for a in AI_ECONOMY_ASSETS]


def fetch_time_series(
    symbol: str,
    asset_id: str,
    data_source_id: str,
    period: str = "1y",
) -> list[TimeSeriesPoint]:
    """
    Download OHLCV data from Yahoo Finance and convert to TimeSeriesPoint list.
    """
    ticker = yf.Ticker(symbol)
    df: pd.DataFrame = ticker.history(period=period, auto_adjust=True)

    if df.empty:
        return []

    points: list[TimeSeriesPoint] = []
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        pass

    extra_attrs: dict = {}
    if info.get("sector"):
        extra_attrs["sector"] = info["sector"]
    if info.get("marketCap"):
        extra_attrs["marketCap"] = info["marketCap"]
    if info.get("trailingPE"):
        extra_attrs["trailingPE"] = info["trailingPE"]
    if info.get("dividendYield"):
        extra_attrs["dividendYield"] = info["dividendYield"]

    for ts, row in df.iterrows():
        date = pd.Timestamp(ts).to_pydatetime()
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        points.append(TimeSeriesPoint(
            assetId=asset_id,
            dataSourceId=data_source_id,
            symbol=symbol,
            date=date,
            open=_safe(row.get("Open")),
            high=_safe(row.get("High")),
            low=_safe(row.get("Low")),
            close=_safe(row.get("Close")),
            volume=_safe(row.get("Volume")),
            adjustedClose=_safe(row.get("Close")),   # already adjusted by yfinance
            attributes={
                **extra_attrs,
                "dividends": _safe(row.get("Dividends")),
                "stockSplits": _safe(row.get("Stock Splits")),
            },
        ))

    return points


def _safe(val) -> float | None:
    try:
        f = float(val)
        return None if (f != f) else f   # NaN check
    except (TypeError, ValueError):
        return None
