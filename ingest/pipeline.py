"""
Ingestion pipeline orchestrator.

Run:  python -m ingest.pipeline
"""

from __future__ import annotations
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient

from db.client import get_db, init_indexes
from db.models import DataSourceCreate
from db.repository import AssetRepository, DataSourceRepository, TimeSeriesRepository
from ingest.sources import yahoo_finance, coingecko


# ─────────────────────────────────────────────────────────────────────────────
# Data source definitions
# ─────────────────────────────────────────────────────────────────────────────

YAHOO_SOURCE = DataSourceCreate(
    name="Yahoo Finance",
    provider="yfinance",
    apiEndpoint="https://finance.yahoo.com",
    description="Real-time and historical OHLCV for stocks, ETFs, indices, and commodities. No API key required.",
    attributes={"library": "yfinance", "dataTypes": ["stock", "etf", "index", "commodity"]},
)

COINGECKO_SOURCE = DataSourceCreate(
    name="CoinGecko",
    provider="coingecko",
    apiEndpoint="https://api.coingecko.com/api/v3",
    description="Free cryptocurrency OHLCV and market data. Rate-limited on free tier (≈30 req/min).",
    attributes={"tier": "free", "dataTypes": ["crypto"]},
)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

async def run(period: str = "1y", crypto_days: int = 365):
    db = get_db()
    await init_indexes()

    asset_repo  = AssetRepository(db)
    source_repo = DataSourceRepository(db)
    ts_repo     = TimeSeriesRepository(db)

    # ── Register data sources ────────────────────────────────────────────────
    yahoo_ds      = await source_repo.get_or_create(YAHOO_SOURCE)
    coingecko_ds  = await source_repo.get_or_create(COINGECKO_SOURCE)
    print(f"📡 Data sources ready: {yahoo_ds.name} | {coingecko_ds.name}")

    # ── Ingest Yahoo Finance assets ──────────────────────────────────────────
    print("\n📥 Ingesting Yahoo Finance assets…")
    yahoo_assets = yahoo_finance.get_asset_definitions()
    for asset_def in yahoo_assets:
        asset_doc = await asset_repo.upsert(asset_def)
        print(f"  • {asset_doc.symbol:8s} ({asset_doc.assetClass}) — fetching {period} history…", end=" ")
        points = yahoo_finance.fetch_time_series(
            symbol=asset_doc.symbol,
            asset_id=asset_doc.assetId,
            data_source_id=yahoo_ds.dataSourceId,
            period=period,
        )
        inserted = await ts_repo.bulk_insert(points)
        print(f"{inserted} new points ({len(points)} total)")

    # ── Ingest CoinGecko crypto assets ───────────────────────────────────────
    print("\n📥 Ingesting CoinGecko crypto assets…")
    crypto_assets = coingecko.get_asset_definitions()
    for asset_def in crypto_assets:
        asset_doc = await asset_repo.upsert(asset_def)
        print(f"  • {asset_doc.symbol:8s} ({asset_doc.assetClass}) — fetching {crypto_days}d history…", end=" ")
        points = coingecko.fetch_time_series(
            symbol=asset_doc.symbol,
            asset_id=asset_doc.assetId,
            data_source_id=coingecko_ds.dataSourceId,
            days=crypto_days,
        )
        inserted = await ts_repo.bulk_insert(points)
        print(f"{inserted} new points ({len(points)} total)")
        time.sleep(1.5)   # CoinGecko free-tier rate limit

    print("\n✅ Ingestion complete.")


if __name__ == "__main__":
    asyncio.run(run())
