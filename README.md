# Acme Financial Data Warehouse
### Theme: AI & Digital Economy

A temporal, append-only financial data warehouse built on **MongoDB + FastAPI + MCP**.  
Covers stocks (NVDA, MSFT, GOOGL, AMD, META, TSLA, AMZN, SNOW, IONQ), ETFs (BOTZ),  
crypto (BTC, ETH, SOL, FET, RNDR, NEAR), commodities (Gold, Silver) and market indices (S&P 500, NASDAQ).

---

## Architecture

```
External APIs                 Platform                        Consumers
─────────────    ────────────────────────────────────────    ──────────────
Yahoo Finance ──► Ingest Pipeline ──► MongoDB (NoSQL)  ──►  REST API :8000
CoinGecko     ──►  (append-only        (temporal DWH)  ──►  MCP Server :8001
                    temporal)                          ──►  Analytics Engine
                                                       ──►  LLM (Claude)
```

## Quick Start (Docker — recommended)

```bash
git clone <repo>
cd financial-dw
cp .env.example .env

# 1. Start MongoDB + API + MCP server
docker compose up -d

# 2. Run the data ingestion (downloads ~1 year of data)
docker compose exec api python -m ingest.pipeline

# 3. Open the interactive API docs
open http://localhost:8000/docs
```

## Quick Start (Local)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Set env vars (edit .env first)
cp .env.example .env

# Ensure MongoDB is running locally on port 27017, then:
python -m ingest.pipeline          # ingest data
uvicorn api.main:app --reload      # start API
python -m mcp_server.server        # start MCP server (separate terminal)
```

---

## API Reference  (`http://localhost:8000/docs` for full Swagger UI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/assets/` | [Q1] List all assets (summary) |
| GET | `/assets/{asset_id}` | [Q2] Full asset detail |
| GET | `/assets/{symbol}/history?at=<datetime>` | Point-in-time historical snapshot |
| GET | `/sources/` | [Q3] List all data providers |
| GET | `/sources/{source_id}` | [Q4] Full source detail |
| GET | `/timeseries/?asset_id=…&source_id=…` | [Q5] OHLCV time-series |
| GET | `/analytics/stats` | Min/max/mean/std/% change |
| GET | `/analytics/moving-avg` | 7d, 30d, 90d moving averages |
| GET | `/analytics/trend` | Golden / Death Cross signal |
| GET | `/analytics/volatility` | Annualised volatility + risk label |
| GET | `/analytics/drawdown` | Max peak-to-trough drawdown |
| GET | `/analytics/forecast` | Next-day price (linear regression) |
| GET | `/analytics/compare` | Normalised multi-asset comparison |

### Example Calls

```bash
# List all assets
curl http://localhost:8000/assets/

# Get time-series for NVDA (replace UUIDs from list call)
curl "http://localhost:8000/timeseries/?asset_id=<nvda_id>&source_id=<yahoo_id>&limit=30"

# Compare NVDA vs AMD vs BTC
curl "http://localhost:8000/analytics/compare?asset_ids=<id1>&asset_ids=<id2>&asset_ids=<id3>&source_id=<sid>"

# Volatility risk for Ethereum
curl "http://localhost:8000/analytics/volatility?asset_id=<eth_id>&source_id=<cg_id>"
```

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

Then ask Claude things like:
- *"List all assets in the warehouse"*
- *"Summarize NVIDIA's performance over the last year"*
- *"Compare BTC, ETH, and SOL performance since January"*
- *"What's the volatility risk of RNDR vs traditional gold?"*
- *"Is MSFT showing a bullish or bearish trend signal?"*
- *"Forecast NVDA's price tomorrow"*

---

## Dataset: AI & Digital Economy

| Asset | Class | Theme |
|-------|-------|-------|
| NVDA  | Stock | AI Infrastructure |
| AMD   | Stock | AI Infrastructure |
| MSFT  | Stock | AI Cloud & Software |
| GOOGL | Stock | AI Cloud & Software |
| META  | Stock | AI Cloud & Software |
| TSLA  | Stock | AI Robotics & Autonomy |
| AMZN  | Stock | AI Cloud |
| SNOW  | Stock | AI Data Platforms |
| IONQ  | Stock | Quantum Computing |
| BOTZ  | ETF   | AI Basket |
| ^GSPC | Index | US Market Benchmark |
| ^IXIC | Index | Tech/AI Benchmark |
| GC=F  | Commodity | AI-era inflation hedge |
| SI=F  | Commodity | Chip manufacturing input |
| BTC   | Crypto | Digital Store of Value |
| ETH   | Crypto | Smart Contract Platform |
| SOL   | Crypto | AI-Friendly L1 |
| FET   | Crypto | Decentralised AI |
| RNDR  | Crypto | Decentralised GPU Compute |
| NEAR  | Crypto | AI-Friendly L1 |

---

## Temporal DWH Design

- **No updates, no deletes** — all writes are `INSERT`-only
- **Version chain**: each logical change creates a new document with `version++`, `validFrom=now`; the previous record gets `validTo=now`
- **Soft delete**: inserts a marker doc with `isDeleted=True`
- **Point-in-time query**: `GET /assets/{symbol}/history?at=2024-06-01T00:00:00Z`

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
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```


