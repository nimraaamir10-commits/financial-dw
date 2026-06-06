"""
UC3 — Analytics endpoints
  /analytics/stats        → descriptive statistics
  /analytics/moving-avg   → moving averages
  /analytics/trend        → golden/death cross signal
  /analytics/volatility   → annualised volatility
  /analytics/drawdown     → max drawdown
  /analytics/forecast     → next-day price (linear regression)
  /analytics/compare      → normalised multi-asset comparison
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from typing import Optional, List

from db.client import get_db
from db.repository import TimeSeriesRepository, AssetRepository
from analytics import engine

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_ts_repo(db=Depends(get_db)):
    return TimeSeriesRepository(db)

def get_asset_repo(db=Depends(get_db)):
    return AssetRepository(db)


async def _fetch(ts_repo, asset_id, source_id, date_from, date_to, limit=1000):
    series = await ts_repo.get_series(asset_id, source_id, date_from, date_to, limit)
    if not series:
        raise HTTPException(404, "No time-series data found.")
    return series


@router.get("/stats", summary="Descriptive statistics for an asset")
async def stats(
    asset_id:  str = Query(...),
    source_id: str = Query(...),
    field:     str = Query("close"),
    date_from: Optional[datetime] = None,
    date_to:   Optional[datetime] = None,
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    series = await _fetch(ts_repo, asset_id, source_id, date_from, date_to)
    return engine.descriptive_stats(series, field)


@router.get("/moving-avg", summary="Moving averages (7d, 30d, 90d)")
async def moving_avg(
    asset_id:  str = Query(...),
    source_id: str = Query(...),
    field:     str = Query("close"),
    date_from: Optional[datetime] = None,
    date_to:   Optional[datetime] = None,
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    series = await _fetch(ts_repo, asset_id, source_id, date_from, date_to)
    return engine.moving_averages(series, field)


@router.get("/trend", summary="Golden Cross / Death Cross signal")
async def trend(
    asset_id:  str = Query(...),
    source_id: str = Query(...),
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    series = await _fetch(ts_repo, asset_id, source_id, None, None, 1000)
    return engine.trend_signal(series)


@router.get("/volatility", summary="Annualised rolling volatility")
async def vol(
    asset_id:  str = Query(...),
    source_id: str = Query(...),
    window:    int = Query(30),
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    series = await _fetch(ts_repo, asset_id, source_id, None, None, 1000)
    return engine.volatility(series, window=window)


@router.get("/drawdown", summary="Maximum drawdown")
async def drawdown(
    asset_id:  str = Query(...),
    source_id: str = Query(...),
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    series = await _fetch(ts_repo, asset_id, source_id, None, None, 1000)
    return engine.max_drawdown(series)


@router.get("/forecast", summary="Next-day price forecast (linear regression)")
async def forecast(
    asset_id:  str = Query(...),
    source_id: str = Query(...),
    lookback:  int = Query(30),
    ts_repo: TimeSeriesRepository = Depends(get_ts_repo),
):
    series = await _fetch(ts_repo, asset_id, source_id, None, None, 1000)
    return engine.forecast_next_day(series, lookback=lookback)


@router.get("/compare", summary="Normalised multi-asset comparison")
async def compare(
    asset_ids:  List[str] = Query(..., description="List of asset UUIDs to compare"),
    source_id:  str = Query(...),
    date_from:  Optional[datetime] = None,
    date_to:    Optional[datetime] = None,
    asset_repo: AssetRepository = Depends(get_asset_repo),
    ts_repo:    TimeSeriesRepository = Depends(get_ts_repo),
):
    series_map = {}
    for aid in asset_ids:
        asset = await asset_repo.get_by_id(aid)
        if not asset:
            continue
        series = await ts_repo.get_series(aid, source_id, date_from, date_to, 1000)
        if series:
            series_map[asset["symbol"]] = series
    if not series_map:
        raise HTTPException(404, "No data found for the given assets.")
    return engine.compare_assets(series_map)
