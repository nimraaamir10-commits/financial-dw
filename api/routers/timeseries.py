"""
UC2 — Time-series endpoint
  Q5: GET /timeseries?asset_id=…&source_id=…[&from=…&to=…&limit=…]
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from typing import Optional

from db.client import get_db
from db.repository import TimeSeriesRepository, AssetRepository

router = APIRouter(prefix="/timeseries", tags=["Time Series"])


def get_ts_repo(db=Depends(get_db)):
    return TimeSeriesRepository(db)

def get_asset_repo(db=Depends(get_db)):
    return AssetRepository(db)


@router.get("/", summary="[Q5] Retrieve time-series data")
async def get_timeseries(
    asset_id:  str            = Query(..., description="Asset UUID"),
    source_id: str            = Query(..., description="Data source UUID"),
    date_from: Optional[datetime] = Query(None, description="Start date (ISO-8601)"),
    date_to:   Optional[datetime] = Query(None, description="End date (ISO-8601)"),
    limit:     int            = Query(500, ge=1, le=5000),
    ts_repo:   TimeSeriesRepository = Depends(get_ts_repo),
):
    """
    Returns OHLCV time-series for the given asset + source combination.
    Supports date-range filtering and pagination via `limit`.
    """
    series = await ts_repo.get_series(
        asset_id=asset_id,
        source_id=source_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    if not series:
        raise HTTPException(
            status_code=404,
            detail="No time-series data found for the given asset/source combination.",
        )
    return {"count": len(series), "series": series}


@router.get("/latest/{asset_id}", summary="Latest price for an asset")
async def latest_price(
    asset_id: str,
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    """Returns the most recent data point available for the asset."""
    point = await ts_repo.latest_price(asset_id)
    if not point:
        raise HTTPException(status_code=404, detail="No data found.")
    return point
