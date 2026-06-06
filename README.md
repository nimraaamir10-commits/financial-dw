# Acme Financial Data Warehouse
### Theme: AI & Digital Economy

A temporal, append-only financial data warehouse built on **MongoDB + FastAPI + Apache Spark + MCP**.  
Covers stocks (NVDA, MSFT, GOOGL, AMD, META, TSLA, AMZN, SNOW, IONQ), ETFs (BOTZ),  
crypto (BTC, ETH, SOL, FET, RNDR, NEAR), commodities (Gold, Silver) and market indices (S&P 500, NASDAQ).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | MongoDB Atlas (NoSQL) |
| Backend API | FastAPI + Uvicorn |
| Data Ingestion | Yahoo Finance (yfinance) + CoinGecko API |
| Analytics | Apache Spark (PySpark) + Pandas |
| ML Forecast | Spark MLlib LinearRegression |
| LLM Integration | MCP (Model Context Protocol) |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio (17 tests) |
| Container | Docker + Docker Compose |

---

## Architecture

```
External APIs                 Platform                          Consumers
─────────────    ──────────────────────────────────────────    ──────────────
Yahoo Finance ──► Ingest Pipeline ──► MongoDB (NoSQL)    ──►  REST API :8000
CoinGecko     ──►  (append-only        (temporal DWH)    ──►  Spark Analytics
                    temporal)                            ──►  MCP Server :8001
                                                         ──►  LLM (Claude)
```

---

## Quick Start (Local)

### Prerequisites
- Python 3.10+
- MongoDB Atlas account (free M0 tier) or local MongoDB
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/nimraaamir10-commits/financial-dw
cd financial-dw

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your MongoDB Atlas connection string

# 4. Run data ingestion (~3-5 minutes)
python -m ingest.pipeline

# 5. Start the API
uvicorn api.main:app --reload

# 6. Open Swagger UI
# http://localhost:8000/docs

# 7. Start MCP server (separate terminal)
python -m mcp_server.server
```

### Run Spark Analytics

```bash
pip install pyspark
python spark/spark_analytics.py --asset_id <uuid> --source_id <uuid>
```

### Run Unit Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
# Expected: 17 passed
```

---

## API Reference (`http://localhost:8000/docs` for full Swagger UI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/assets/` | [Q1] List all assets (summary) |
| GET | `/assets/{asset_id}` | [Q2] Full asset detail |
| GET | `/assets/{symbol}/history?at=<datetime>` | Point-in-time historical snapshot |
| GET | `/sources/` | [Q3] List all data providers |
| GET | `/sources/{source_id}` | [Q4] Full source detail |
| GET | `/timeseries/?asset_id=&source_id=` | [Q5] OHLCV time-series |
| GET | `/analytics/stats` | Min/max/mean/std/% change |
| GET | `/analytics/moving-avg` | 7d, 30d, 90d moving averages |
| GET | `/analytics/trend` | Golden / Death Cross signal |
| GET | `/analytics/volatility` | Annualised volatility + risk label |
| GET | `/analytics/drawdown` | Max peak-to-trough drawdown |
| GET | `/analytics/forecast` | Next-day price (linear regression) |
| GET | `/analytics/compare` | Normalised multi-asset comparison |

---

## Apache Spark Pipeline (UC3)

The `spark/spark_analytics.py` script implements two Spark workflows:

**1. Aggregation Workflow (Spark SQL)**
- Reads time-series from MongoDB
- Computes count, min, max, avg, std, % change
- Monthly OHLCV aggregations grouped by year-month
- Results saved to `spark_results` collection (append-only)

**2. ML Forecast Workflow (Spark MLlib)**
- Features: day index, open, high, low, volume
- Model: LinearRegression (80/20 train/test split)
- Metrics: RMSE and R2 reported
- Next-day closing price predicted

---

## LLM Integration via MCP (UC4)

Add this to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "acme-financial-dwh": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/financial-dw",
      "env": {
        "API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Available MCP Tools (11 total):**
`list_assets` · `get_asset` · `list_sources` · `fetch_time_series` · `get_stats` · `get_volatility` · `get_drawdown` · `get_trend_signal` · `forecast_price` · `compare_assets` · `summarize_asset`

**Example prompts:**
- "Summarize NVIDIA's performance over the last year"
- "Compare BTC, ETH, and SOL since January"
- "Is TSLA showing a bullish or bearish trend?"
- "Forecast NVDA's price tomorrow"

---

## Dataset: AI & Digital Economy

| Asset | Class | Source | Theme |
|-------|-------|--------|-------|
| NVDA | Stock | Yahoo Finance | AI Infrastructure |
| AMD | Stock | Yahoo Finance | AI Infrastructure |
| MSFT | Stock | Yahoo Finance | AI Cloud & Software |
| GOOGL | Stock | Yahoo Finance | AI Cloud & Software |
| META | Stock | Yahoo Finance | AI Cloud & Software |
| TSLA | Stock | Yahoo Finance | AI Robotics & Autonomy |
| AMZN | Stock | Yahoo Finance | AI Cloud |
| SNOW | Stock | Yahoo Finance | AI Data Platforms |
| IONQ | Stock | Yahoo Finance | Quantum Computing |
| BOTZ | ETF | Yahoo Finance | AI Basket |
| ^GSPC | Index | Yahoo Finance | US Market Benchmark |
| ^IXIC | Index | Yahoo Finance | Tech/AI Benchmark |
| GC=F | Commodity | Yahoo Finance | AI-era inflation hedge |
| SI=F | Commodity | Yahoo Finance | Chip manufacturing input |
| BTC | Crypto | CoinGecko | Digital Store of Value |
| ETH | Crypto | CoinGecko | Smart Contract Platform |
| SOL | Crypto | CoinGecko | AI-Friendly L1 |
| FET | Crypto | CoinGecko | Decentralised AI |
| RNDR | Crypto | CoinGecko | Decentralised GPU Compute |
| NEAR | Crypto | CoinGecko | AI-Friendly L1 |

**Total: ~3,500 OHLCV data points | Period: 1 year | Sources: 2**

---

## Temporal DWH Design

- **No updates, no deletes** — all writes are INSERT-only (append-only)
- **Version chain** — every change creates a new document with version++, validFrom=now; previous record gets validTo=now
- **Soft delete** — inserts a marker doc with isDeleted=True
- **Point-in-time query** — `GET /assets/{symbol}/history?at=2024-06-01T00:00:00Z`

---

## Unit Tests

```
tests/
└── test_repository.py   # 17 tests covering:
    ├── AssetRepository  — upsert, versioning, soft delete
    ├── TimeSeriesRepository — bulk insert, idempotency
    ├── Yahoo Finance Ingestor — NaN handling, asset catalogue
    ├── CoinGecko Ingestor — symbol lookup, definitions
    └── Analytics Engine — stats, forecast, volatility
```

Run: `pytest tests/ -v` → **17 passed**

---

## Project Structure

```
financial-dw/
├── api/
│   ├── main.py              # FastAPI app
│   └── routers/
│       ├── assets.py        # UC2 Q1, Q2
│       ├── sources.py       # UC2 Q3, Q4
│       ├── timeseries.py    # UC2 Q5
│       └── analytics.py     # UC3
├── analytics/
│   └── engine.py            # Stats, MA, volatility, forecast, compare
├── db/
│   ├── client.py            # MongoDB connection + indexes
│   ├── models.py            # Pydantic temporal models
│   └── repository.py        # Append-only data access layer
├── ingest/
│   ├── pipeline.py          # Orchestrator
│   └── sources/
│       ├── yahoo_finance.py # Stocks, ETFs, indices, commodities
│       └── coingecko.py     # Crypto (AI-linked)
├── mcp_server/
│   └── server.py            # UC4 — MCP tools for LLM
├── spark/
│   └── spark_analytics.py   # Apache Spark aggregations + MLlib forecast
├── tests/
│   └── test_repository.py   # 17 unit tests (pytest)
├── demo_video.mp4            # End-to-end demo video
├── REPORT.md                 # Short project report
├── Project_Report.docx       # Project report (Word)
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

*Nimra Aamir · nimra.aamir10@e-uvt.ro · June 2026*
