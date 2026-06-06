"""
CoinGecko ingestor — free public API, no key required.

Covers the top AI-linked cryptocurrencies:
  BTC, ETH, SOL, BNB, NEAR, FET (Fetch.ai), RNDR (Render)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import requests
import time

from db.models import AssetCreate, TimeSeriesPoint


# ─────────────────────────────────────────────────────────────────────────────
# Asset catalogue — AI-linked crypto assets
# ─────────────────────────────────────────────────────────────────────────────

CRYPTO_ASSETS: list[dict[str, Any]] = [
    {
        "coingecko_id": "bitcoin",
        "symbol": "BTC", "name": "Bitcoin",
        "assetClass": "crypto", "region": "Global", "currency": "USD",
        "description": "Digital gold — the foundational store-of-value asset in the crypto economy.",
        "attributes": {
            "blockchain": "Bitcoin",
            "consensusMechanism": "Proof-of-Work",
            "maxSupply": 21_000_000,
            "theme": "Digital Store of Value",
        },
    },
    {
        "coingecko_id": "ethereum",
        "symbol": "ETH", "name": "Ethereum",
        "assetClass": "crypto", "region": "Global", "currency": "USD",
        "description": "Smart-contract platform powering DeFi, NFTs, and AI agent token economies.",
        "attributes": {
            "blockchain": "Ethereum",
            "consensusMechanism": "Proof-of-Stake",
            "theme": "Smart Contract Platform",
        },
    },
    {
        "coingecko_id": "solana",
        "symbol": "SOL", "name": "Solana",
        "assetClass": "crypto", "region": "Global", "currency": "USD",
        "description": "High-throughput L1 blockchain attracting AI agent and DePIN projects.",
        "attributes": {
            "blockchain": "Solana",
            "consensusMechanism": "Proof-of-History + PoS",
            "tps": 65_000,
            "theme": "AI-Friendly L1",
        },
    },
    {
        "coingecko_id": "fetch-ai",
        "symbol": "FET", "name": "Fetch.ai",
        "assetClass": "crypto", "region": "Global", "currency": "USD",
        "description": "Decentralised AI network — autonomous economic agents on-chain.",
        "attributes": {
            "blockchain": "Cosmos / Ethereum",
            "theme": "Decentralised AI",
        },
    },
    {
        "coingecko_id": "render-token",
        "symbol": "RNDR", "name": "Render Network",
        "assetClass": "crypto", "region": "Global", "currency": "USD",
        "description": "Decentralised GPU rendering — critical infrastructure for AI training.",
        "attributes": {
            "blockchain": "Solana",
            "theme": "Decentralised AI Compute",
        },
    },
    {
        "coingecko_id": "near",
        "symbol": "NEAR", "name": "NEAR Protocol",
        "assetClass": "crypto", "region": "Global", "currency": "USD",
        "description": "User-friendly L1 with AI-assistant integrations baked into its roadmap.",
        "attributes": {
            "blockchain": "NEAR",
            "consensusMechanism": "Nightshade Sharding",
            "theme": "AI-Friendly L1",
        },
    },
]

BASE_URL = "https://api.coingecko.com/api/v3"
HEADERS = {"accept": "application/json"}


def get_asset_definitions() -> list[AssetCreate]:
    return [
        AssetCreate(**{k: v for k, v in a.items() if k != "coingecko_id"})
        for a in CRYPTO_ASSETS
    ]


def _coingecko_id(symbol: str) -> str | None:
    for a in CRYPTO_ASSETS:
        if a["symbol"] == symbol:
            return a["coingecko_id"]
    return None


def fetch_time_series(
    symbol: str,
    asset_id: str,
    data_source_id: str,
    days: int = 365,
) -> list[TimeSeriesPoint]:
    """
    Fetch daily OHLCV from CoinGecko /coins/{id}/ohlc endpoint.
    Falls back to /market_chart for close price if OHLC unavailable.
    """
    cg_id = _coingecko_id(symbol)
    if not cg_id:
        return []

    # OHLC endpoint (max 365 days on free tier)
    ohlc_days = min(days, 365)
    url = f"{BASE_URL}/coins/{cg_id}/ohlc"
    params = {"vs_currency": "usd", "days": ohlc_days}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        raw = resp.json()   # [[timestamp_ms, open, high, low, close], ...]
    except Exception as e:
        print(f"  ⚠  CoinGecko OHLC failed for {symbol}: {e}")
        return []

    # Companion market data for volume + market cap
    market_data: dict[int, dict] = {}
    try:
        time.sleep(1.2)   # free-tier rate limit
        mc_url = f"{BASE_URL}/coins/{cg_id}/market_chart"
        mc_resp = requests.get(
            mc_url,
            params={"vs_currency": "usd", "days": ohlc_days, "interval": "daily"},
            headers=HEADERS, timeout=15,
        )
        mc_resp.raise_for_status()
        mc = mc_resp.json()
        for ts_ms, vol in mc.get("total_volumes", []):
            market_data[ts_ms] = market_data.get(ts_ms, {})
            market_data[ts_ms]["volume"] = vol
        for ts_ms, cap in mc.get("market_caps", []):
            market_data.setdefault(ts_ms, {})["marketCap"] = cap
    except Exception:
        pass   # volume/cap is nice-to-have

    points: list[TimeSeriesPoint] = []
    for row in raw:
        ts_ms, open_, high, low, close = row
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        extra = market_data.get(ts_ms, {})
        points.append(TimeSeriesPoint(
            assetId=asset_id,
            dataSourceId=data_source_id,
            symbol=symbol,
            date=dt,
            open=open_,
            high=high,
            low=low,
            close=close,
            adjustedClose=close,
            volume=extra.get("volume"),
            attributes={
                "marketCap": extra.get("marketCap"),
                "source": "coingecko",
            },
        ))

    return points
