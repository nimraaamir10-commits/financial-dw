# Project Report — Acme Financial Data Warehouse

**Student:** Nimra Aamir  
**Email:** nimra.aamir10@e-uvt.ro  
**GitHub:** https://github.com/nimraaamir10-commits/financial-dw  
**Date:** June 2026  

---

## 1. What Was Built

A temporal financial data warehouse for Acme Ltd that ingests real-world market data, stores it in MongoDB (NoSQL), exposes it via REST API, runs analytics using Apache Spark, and integrates with an LLM via MCP. All 4 use cases implemented: UC1 ingestion, UC2 REST API, UC3 Spark analytics, UC4 LLM via MCP.

---

## 2. Data Used

**Theme: AI & Digital Economy** — 20 assets, 5 asset classes, 2 sources, ~3,500 OHLCV data points (1 year).

| Symbol | Name | Class | Source |
|--------|------|-------|--------|
| NVDA | NVIDIA Corporation | Stock | Yahoo Finance |
| AMD | Advanced Micro Devices | Stock | Yahoo Finance |
| MSFT | Microsoft Corporation | Stock | Yahoo Finance |
| GOOGL | Alphabet Inc. | Stock | Yahoo Finance |
| META | Meta Platforms | Stock | Yahoo Finance |
| TSLA | Tesla Inc. | Stock | Yahoo Finance |
| AMZN | Amazon.com Inc. | Stock | Yahoo Finance |
| SNOW | Snowflake Inc. | Stock | Yahoo Finance |
| IONQ | IonQ Inc. | Stock | Yahoo Finance |
| BOTZ | Global X Robotics & AI ETF | ETF | Yahoo Finance |
| ^GSPC | S&P 500 Index | Index | Yahoo Finance |
| ^IXIC | NASDAQ Composite | Index | Yahoo Finance |
| GC=F | Gold Futures | Commodity | Yahoo Finance |
| SI=F | Silver Futures | Commodity | Yahoo Finance |
| BTC | Bitcoin | Crypto | CoinGecko |
| ETH | Ethereum | Crypto | CoinGecko |
| SOL | Solana | Crypto | CoinGecko |
| FET | Fetch.ai | Crypto | CoinGecko |
| RNDR | Render Network | Crypto | CoinGecko |
| NEAR | NEAR Protocol | Crypto | CoinGecko |

---

## 3. Apache Spark Pipeline

`spark/spark_analytics.py` implements two Spark workflows:

- **Aggregation (Spark SQL):** Reads from MongoDB, computes monthly OHLCV stats, saves to `spark_results` collection (append-only)
- **ML Forecast (Spark MLlib):** LinearRegression with 80/20 train/test split, reports RMSE and R², predicts next-day closing price

---

## 4. Unit Tests

17 unit tests using pytest covering DAL, ingestion pipeline, and analytics engine. All passing.

---

## 5. How to Reproduce

1. Clone: `git clone https://github.com/nimraaamir10-commits/financial-dw`
2. Install: `pip install -r requirements.txt`
3. Configure: copy `.env.example` to `.env` (add MongoDB Atlas URI)
4. Ingest: `python -m ingest.pipeline`
5. Run API: `uvicorn api.main:app --reload`
6. Open: `http://localhost:8000/docs`
7. Spark: `python spark/spark_analytics.py --asset_id <uuid> --source_id <uuid>`
8. Tests: `pytest tests/ -v`