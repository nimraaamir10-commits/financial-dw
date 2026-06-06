"""
Pydantic models for the temporal data warehouse.

Design principles
─────────────────
• Records are NEVER updated or deleted in-place (temporal DWH).
• Every change creates a new document version.
• Logical deletion = inserting a doc with isDeleted=True.
• validTo=None means "currently active".
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Asset (Financial Instrument)
# ─────────────────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    symbol: str
    name: str
    assetClass: str          # stock | crypto | commodity | index | bond | etf
    region: str              # US | Europe | Asia | Global …
    exchange: Optional[str] = None
    currency: str = "USD"
    description: Optional[str] = None
    attributes: dict[str, Any] = {}   # heterogeneous / class-specific fields


class AssetDocument(AssetCreate):
    """Document stored in MongoDB assets collection."""
    assetId: str = Field(default_factory=_uuid)
    version: int = 1
    validFrom: datetime = Field(default_factory=_now)
    validTo: Optional[datetime] = None
    isDeleted: bool = False
    recordCreatedAt: datetime = Field(default_factory=_now)

    class Config:
        populate_by_name = True


class AssetSummary(BaseModel):
    """Lightweight projection for Q1."""
    assetId: str
    symbol: str
    name: str
    assetClass: str
    region: str
    currency: str


class AssetDetail(AssetDocument):
    """Full projection for Q2."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Data Source (Financial Data Vendor)
# ─────────────────────────────────────────────────────────────────────────────

class DataSourceCreate(BaseModel):
    name: str               # e.g. "Yahoo Finance", "CoinGecko"
    provider: str           # e.g. "yfinance", "coingecko"
    apiEndpoint: str
    description: Optional[str] = None
    attributes: dict[str, Any] = {}


class DataSourceDocument(DataSourceCreate):
    dataSourceId: str = Field(default_factory=_uuid)
    validFrom: datetime = Field(default_factory=_now)
    validTo: Optional[datetime] = None
    recordCreatedAt: datetime = Field(default_factory=_now)

    class Config:
        populate_by_name = True


class DataSourceSummary(BaseModel):
    """Lightweight projection for Q3."""
    dataSourceId: str
    name: str
    provider: str


class DataSourceDetail(DataSourceDocument):
    """Full projection for Q4."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Time-Series Data Point
# ─────────────────────────────────────────────────────────────────────────────

class TimeSeriesPoint(BaseModel):
    """
    A single OHLCV-style data point.
    `attributes` carries any extra fields that are asset-class-specific
    (e.g. marketCap for crypto, dividends for stocks, contractSize for futures).
    """
    assetId: str
    dataSourceId: str
    symbol: str
    date: datetime

    # Core OHLCV (None if not applicable for this asset class)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    adjustedClose: Optional[float] = None

    # Extra, heterogeneous fields
    attributes: dict[str, Any] = {}

    # Provenance
    recordCreatedAt: datetime = Field(default_factory=_now)
    dataVersion: int = 1

    class Config:
        populate_by_name = True
