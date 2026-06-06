"""MongoDB async client with index setup."""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://acme:acme_secret@localhost:27017/financial_dw?authSource=admin")
MONGO_DB  = os.getenv("MONGO_DB",  "financial_dw")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def get_db():
    return get_client()[MONGO_DB]


async def init_indexes():
    """Create indexes for efficient temporal + time-series queries."""
    db = get_db()

    # ── assets ────────────────────────────────────────────────────────────────
    await db.assets.create_indexes([
        IndexModel([("assetId", ASCENDING)]),
        IndexModel([("symbol", ASCENDING), ("validFrom", DESCENDING)]),
        IndexModel([("assetClass", ASCENDING), ("validTo", ASCENDING)]),
        IndexModel([("isDeleted", ASCENDING), ("validTo", ASCENDING)]),
    ])

    # ── data_sources ──────────────────────────────────────────────────────────
    await db.data_sources.create_indexes([
        IndexModel([("dataSourceId", ASCENDING)], unique=True),
        IndexModel([("provider", ASCENDING)]),
    ])

    # ── time_series ───────────────────────────────────────────────────────────
    await db.time_series.create_indexes([
        IndexModel([
            ("assetId",      ASCENDING),
            ("dataSourceId", ASCENDING),
            ("date",         DESCENDING),
        ], unique=True),
        IndexModel([("symbol", ASCENDING), ("date", DESCENDING)]),
        IndexModel([("recordCreatedAt", DESCENDING)]),
    ])

    print("✅ MongoDB indexes ready.")
