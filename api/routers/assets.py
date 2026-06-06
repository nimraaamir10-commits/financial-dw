"""
UC2 — Asset endpoints
  Q1: GET /assets          → list (summary)
  Q2: GET /assets/{id}     → full detail
      GET /assets/{id}/history?at=<datetime>  → temporal point-in-time
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime

from db.client import get_db
from db.repository import AssetRepository

router = APIRouter(prefix="/assets", tags=["Assets"])


def get_repo(db=Depends(get_db)):
    return AssetRepository(db)


@router.get("/", summary="[Q1] List all active assets")
async def list_assets(repo: AssetRepository = Depends(get_repo)):
    """Returns lightweight identification data for every active financial asset."""
    assets = await repo.list_active()
    return {"count": len(assets), "assets": [a.model_dump() for a in assets]}


@router.get("/{asset_id}", summary="[Q2] Get full asset detail")
async def get_asset(asset_id: str, repo: AssetRepository = Depends(get_repo)):
    """Returns all attributes of the currently active version of an asset."""
    doc = await repo.get_by_id(asset_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    return doc


@router.get("/{symbol}/history", summary="Point-in-time asset snapshot")
async def asset_at(
    symbol: str,
    at: datetime = Query(..., description="ISO-8601 timestamp, e.g. 2024-01-15T00:00:00Z"),
    repo: AssetRepository = Depends(get_repo),
):
    """
    Returns the asset record that was valid at the given point in time.
    Demonstrates the temporal DWH capability.
    """
    doc = await repo.history_at(symbol, at)
    if not doc:
        raise HTTPException(status_code=404, detail=f"No record for '{symbol}' at {at}.")
    return doc
