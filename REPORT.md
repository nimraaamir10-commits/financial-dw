# Project Report — Acme Financial Data Warehouse

**Student:** Nimra Aamir
**Email:** nimra.aamir10@e-uvt.ro
**GitHub:** https://github.com/nimraaamir10-commits/financial-dw
**Date:** June 2026

---

## 1. What Was Built

A temporal financial data warehouse for Acme Ltd that ingests real-world market data, stores it in MongoDB (NoSQL), and exposes it via REST API and LLM assistant (MCP). All 4 use cases implemented: UC1 ingestion, UC2 REST API, UC3 analytics, UC4 LLM via MCP.

---

## 2. Data Used

**Theme: AI & Digital Economy** — 20 assets, 5 asset classes, 2 sources, ~3500 data points (1 year).

| Symbol | Name | Class | Source |
|--------|------|-------|--------|
| NVDA | NVIDIA Corporation | Stock | Yahoo Finance |
| AMD | Advanced Micro Devices | Stock | Yahoo Finance |
| MSFT | Microsoft Corporation | Stock | Yahoo Finance |
| TSLA | Tesla Inc. | Stock | Yahoo Finance |
| BTC | Bitcoin | Crypto | CoinGecko |
| ETH | Ethereum | Crypto | CoinGecko |
| SOL | Solana | Crypto | CoinGecko |
| GC=F | Gold Futures | Commodity | Yahoo Finance |

---

## 3. How to Reproduce

1. Clone: git clone https://github.com/nimraaamir10-commits/financial-dw
2. Install: pip install -r requirements.txt
3. Configure: copy .env.example .env (add MongoDB Atlas URI)
4. Ingest: python -m ingest.pipeline
5. Run API: uvicorn api.main:app --reload
6. Open: http://localhost:8000/docs
