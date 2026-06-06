"""
Unit tests for DAL, Ingestion, and Analytics Engine.
Run: pytest tests/ -v
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


def make_mock_db():
    db = MagicMock()
    db.assets = MagicMock()
    db.data_sources = MagicMock()
    db.time_series = MagicMock()
    return db

NOW = datetime.now(timezone.utc)
SAMPLE_ASSET = {"symbol":"TSLA","name":"Tesla Inc.","assetClass":"stock",
                "region":"US","exchange":"NASDAQ","currency":"USD",
                "description":"EV leader","attributes":{"sector":"Automotive"}}


class TestAssetRepository:

    @pytest.mark.asyncio
    async def test_upsert_new_asset_version_1(self):
        from db.models import AssetCreate
        from db.repository import AssetRepository
        db = make_mock_db()
        db.assets.find_one = AsyncMock(return_value=None)
        db.assets.insert_one = AsyncMock()
        repo = AssetRepository(db)
        asset = await repo.upsert(AssetCreate(**SAMPLE_ASSET))
        assert asset.version == 1
        assert asset.validTo is None
        assert asset.isDeleted is False

    @pytest.mark.asyncio
    async def test_upsert_existing_increments_version(self):
        from db.models import AssetCreate
        from db.repository import AssetRepository
        existing = {"_id":"id","symbol":"TSLA","name":"Tesla","assetClass":"stock",
                    "region":"US","exchange":"NASDAQ","currency":"USD","description":"old",
                    "attributes":{},"assetId":"uuid-1","version":1,
                    "validFrom":NOW,"validTo":None,"isDeleted":False,"recordCreatedAt":NOW}
        db = make_mock_db()
        db.assets.find_one = AsyncMock(return_value=existing)
        db.assets.update_one = AsyncMock()
        db.assets.insert_one = AsyncMock()
        repo = AssetRepository(db)
        asset = await repo.upsert(AssetCreate(**SAMPLE_ASSET))
        assert asset.version == 2
        db.assets.update_one.assert_called_once()
        db.assets.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_inserts_marker(self):
        from db.repository import AssetRepository
        existing = {"_id":"id","symbol":"TSLA","name":"Tesla","assetClass":"stock",
                    "region":"US","exchange":"NASDAQ","currency":"USD","description":"d",
                    "attributes":{},"assetId":"uuid-1","version":1,
                    "validFrom":NOW,"validTo":None,"isDeleted":False,"recordCreatedAt":NOW}
        db = make_mock_db()
        db.assets.find_one = AsyncMock(return_value=existing)
        db.assets.update_one = AsyncMock()
        db.assets.insert_one = AsyncMock()
        repo = AssetRepository(db)
        result = await repo.soft_delete("TSLA")
        assert result is True
        call_args = db.assets.insert_one.call_args[0][0]
        assert call_args["isDeleted"] is True
        assert call_args["version"] == 2

    @pytest.mark.asyncio
    async def test_soft_delete_missing_returns_false(self):
        from db.repository import AssetRepository
        db = make_mock_db()
        db.assets.find_one = AsyncMock(return_value=None)
        repo = AssetRepository(db)
        assert await repo.soft_delete("NONE") is False


class TestTimeSeriesRepository:

    @pytest.mark.asyncio
    async def test_bulk_insert_returns_count(self):
        from db.models import TimeSeriesPoint
        from db.repository import TimeSeriesRepository
        mock_result = MagicMock()
        mock_result.upserted_count = 3
        db = make_mock_db()
        db.time_series.bulk_write = AsyncMock(return_value=mock_result)
        points = [TimeSeriesPoint(assetId="a1",dataSourceId="s1",symbol="TSLA",
                  date=datetime(2024,1,i+1,tzinfo=timezone.utc),close=200.0+i)
                  for i in range(3)]
        repo = TimeSeriesRepository(db)
        assert await repo.bulk_insert(points) == 3

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_returns_zero(self):
        from db.repository import TimeSeriesRepository
        db = make_mock_db()
        repo = TimeSeriesRepository(db)
        assert await repo.bulk_insert([]) == 0
        db.time_series.bulk_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotency_returns_zero_on_duplicate(self):
        from db.models import TimeSeriesPoint
        from db.repository import TimeSeriesRepository
        mock_result = MagicMock()
        mock_result.upserted_count = 0
        db = make_mock_db()
        db.time_series.bulk_write = AsyncMock(return_value=mock_result)
        point = TimeSeriesPoint(assetId="a1",dataSourceId="s1",symbol="TSLA",
                date=datetime(2024,1,1,tzinfo=timezone.utc),close=200.0)
        repo = TimeSeriesRepository(db)
        assert await repo.bulk_insert([point]) == 0


class TestYahooFinanceIngestor:

    def test_safe_handles_nan(self):
        from ingest.sources.yahoo_finance import _safe
        assert _safe(float("nan")) is None
        assert _safe(None) is None
        assert _safe(123.45) == 123.45

    def test_tsla_in_definitions(self):
        from ingest.sources.yahoo_finance import get_asset_definitions
        assert "TSLA" in [a.symbol for a in get_asset_definitions()]

    def test_nvda_in_definitions(self):
        from ingest.sources.yahoo_finance import get_asset_definitions
        assert "NVDA" in [a.symbol for a in get_asset_definitions()]


class TestCoinGeckoIngestor:

    def test_btc_eth_in_definitions(self):
        from ingest.sources.coingecko import get_asset_definitions
        symbols = [a.symbol for a in get_asset_definitions()]
        assert "BTC" in symbols
        assert "ETH" in symbols

    def test_coingecko_id_lookup(self):
        from ingest.sources.coingecko import _coingecko_id
        assert _coingecko_id("BTC") == "bitcoin"
        assert _coingecko_id("ETH") == "ethereum"
        assert _coingecko_id("UNKNOWN") is None


class TestAnalyticsEngine:

    SERIES = [{"date": datetime(2024,1,i+1,tzinfo=timezone.utc),
               "close":100.0+i,"open":99.0+i,"high":101.0+i,
               "low":98.0+i,"volume":1000000.0} for i in range(60)]

    def test_stats_keys(self):
        from analytics.engine import descriptive_stats
        r = descriptive_stats(self.SERIES)
        for k in ["count","min","max","mean","median","std","change_pct"]:
            assert k in r

    def test_stats_count(self):
        from analytics.engine import descriptive_stats
        assert descriptive_stats(self.SERIES)["count"] == 60

    def test_forecast_returns_prediction(self):
        from analytics.engine import forecast_next_day
        r = forecast_next_day(self.SERIES)
        assert "predicted_next_close" in r

    def test_empty_returns_empty(self):
        from analytics.engine import descriptive_stats
        assert descriptive_stats([]) == {}