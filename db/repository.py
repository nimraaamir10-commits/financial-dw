"""
Temporal data warehouse repository.

All writes are APPEND-ONLY — no in-place update or delete.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from db.models import (
    AssetCreate, AssetDocument, AssetSummary,
    DataSourceCreate, DataSourceDocument, DataSourceSummary,
    TimeSeriesPoint,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Assets
# ─────────────────────────────────────────────────────────────────────────────

class AssetRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db.assets

    async def upsert(self, payload: AssetCreate) -> AssetDocument:
        """
        Insert a new asset. If the symbol already exists, create a new version
        and logically close the previous one (temporal update pattern).
        """
        now = _now()
        existing = await self.col.find_one(
            {"symbol": payload.symbol, "isDeleted": False, "validTo": None},
            sort=[("version", -1)],
        )
        if existing:
            # Close previous version
            await self.col.update_one(
                {"_id": existing["_id"]},
                {"$set": {"validTo": now}},
            )
            new_version = existing["version"] + 1
        else:
            new_version = 1

        doc = AssetDocument(
            **payload.model_dump(),
            version=new_version,
            validFrom=now,
        )
        await self.col.insert_one(doc.model_dump())
        return doc

    async def soft_delete(self, symbol: str) -> bool:
        """Mark asset as deleted (temporal deletion = marker record)."""
        now = _now()
        existing = await self.col.find_one(
            {"symbol": symbol, "isDeleted": False, "validTo": None}
        )
        if not existing:
            return False
        # Close current version
        await self.col.update_one({"_id": existing["_id"]}, {"$set": {"validTo": now}})
        # Insert deletion marker
        marker = AssetDocument(
            **{k: existing[k] for k in AssetCreate.model_fields},
            assetId=existing["assetId"],
            version=existing["version"] + 1,
            validFrom=now,
            isDeleted=True,
        )
        await self.col.insert_one(marker.model_dump())
        return True

    async def list_active(self) -> list[AssetSummary]:
        cursor = self.col.find(
            {"isDeleted": False, "validTo": None},
            {"assetId": 1, "symbol": 1, "name": 1, "assetClass": 1, "region": 1, "currency": 1, "_id": 0},
        )
        return [AssetSummary(**doc) async for doc in cursor]

    async def get_by_id(self, asset_id: str) -> Optional[dict]:
        return await self.col.find_one(
            {"assetId": asset_id, "isDeleted": False, "validTo": None},
            {"_id": 0},
        )

    async def history_at(self, symbol: str, point_in_time: datetime) -> Optional[dict]:
        """Return the asset record that was valid at the given timestamp."""
        return await self.col.find_one(
            {
                "symbol": symbol,
                "isDeleted": False,
                "validFrom": {"$lte": point_in_time},
                "$or": [
                    {"validTo": None},
                    {"validTo": {"$gt": point_in_time}},
                ],
            },
            {"_id": 0},
            sort=[("version", -1)],
        )


# ─────────────────────────────────────────────────────────────────────────────
# Data Sources
# ─────────────────────────────────────────────────────────────────────────────

class DataSourceRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db.data_sources

    async def get_or_create(self, payload: DataSourceCreate) -> DataSourceDocument:
        existing = await self.col.find_one({"provider": payload.provider, "validTo": None})
        if existing:
            return DataSourceDocument(**{k: existing[k] for k in existing if k != "_id"})
        doc = DataSourceDocument(**payload.model_dump())
        await self.col.insert_one(doc.model_dump())
        return doc

    async def list_all(self) -> list[DataSourceSummary]:
        cursor = self.col.find(
            {"validTo": None},
            {"dataSourceId": 1, "name": 1, "provider": 1, "_id": 0},
        )
        return [DataSourceSummary(**doc) async for doc in cursor]

    async def get_by_id(self, source_id: str) -> Optional[dict]:
        return await self.col.find_one({"dataSourceId": source_id}, {"_id": 0})


# ─────────────────────────────────────────────────────────────────────────────
# Time Series
# ─────────────────────────────────────────────────────────────────────────────

class TimeSeriesRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db.time_series

    async def bulk_insert(self, points: list[TimeSeriesPoint]) -> int:
        """
        Append-only bulk insert. Duplicate (assetId, dataSourceId, date)
        are skipped (upsert on the unique index).
        """
        if not points:
            return 0
        from pymongo import UpdateOne
        ops = [
            UpdateOne(
                {
                    "assetId":      p.assetId,
                    "dataSourceId": p.dataSourceId,
                    "date":         p.date,
                },
                {"$setOnInsert": p.model_dump()},
                upsert=True,
            )
            for p in points
        ]
        result = await self.col.bulk_write(ops, ordered=False)
        return result.upserted_count

    async def get_series(
        self,
        asset_id: str,
        source_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[dict]:
        query: dict[str, Any] = {"assetId": asset_id, "dataSourceId": source_id}
        if date_from or date_to:
            query["date"] = {}
            if date_from:
                query["date"]["$gte"] = date_from
            if date_to:
                query["date"]["$lte"] = date_to
        cursor = self.col.find(query, {"_id": 0}).sort("date", 1).limit(limit)
        return [doc async for doc in cursor]

    async def latest_price(self, asset_id: str) -> Optional[dict]:
        return await self.col.find_one(
            {"assetId": asset_id},
            {"_id": 0},
            sort=[("date", -1)],
        )

    async def aggregate_stats(
        self,
        asset_id: str,
        source_id: str,
        field: str = "close",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        match: dict[str, Any] = {"assetId": asset_id, "dataSourceId": source_id}
        if date_from or date_to:
            match["date"] = {}
            if date_from:
                match["date"]["$gte"] = date_from
            if date_to:
                match["date"]["$lte"] = date_to

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": None,
                "count":   {"$sum": 1},
                "min":     {"$min": f"${field}"},
                "max":     {"$max": f"${field}"},
                "avg":     {"$avg": f"${field}"},
                "first":   {"$first": f"${field}"},
                "last":    {"$last": f"${field}"},
            }},
        ]
        async for doc in self.col.aggregate(pipeline):
            doc.pop("_id", None)
            return doc
        return {}
