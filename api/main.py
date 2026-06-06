"""
Acme Ltd — Financial Markets Data Warehouse API
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.client import init_indexes
from api.routers import assets, sources, timeseries, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_indexes()
    yield


app = FastAPI(
    title="Acme Financial DWH API",
    description=(
        "Data warehouse platform for AI & Digital Economy financial instruments. "
        "Covers stocks (NVDA, MSFT, GOOGL…), crypto (BTC, ETH, SOL, FET, RNDR…), "
        "commodities (Gold, Silver) and market indices. "
        "Built on a temporal, append-only NoSQL (MongoDB) store."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router)
app.include_router(sources.router)
app.include_router(timeseries.router)
app.include_router(analytics.router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Acme Financial DWH",
        "status":  "ok",
        "theme":   "AI & Digital Economy",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
