"""
Acme Financial DWH — MCP Server (UC4)

Exposes platform capabilities as tools for an LLM (e.g. Claude) to call.
Run:  python -m mcp_server.server

Tools exposed:
  • list_assets          — discover all financial instruments
  • get_asset            — details of one asset
  • list_sources         — available data providers
  • fetch_time_series    — OHLCV data for an asset
  • get_stats            — descriptive statistics
  • get_volatility       — risk / volatility metric
  • get_drawdown         — max drawdown
  • get_trend_signal     — golden/death cross
  • forecast_price       — next-day price forecast
  • compare_assets       — normalised multi-asset comparison
  • summarize_asset      — plain-language summary of an asset
"""

from __future__ import annotations
import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

server = Server("acme-financial-dwh")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helper
# ─────────────────────────────────────────────────────────────────────────────

async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_assets",
            description="List all financial assets in the data warehouse. Returns symbol, name, class, region, currency.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_asset",
            description="Get full details of a financial asset by its assetId UUID.",
            inputSchema={
                "type": "object",
                "properties": {"asset_id": {"type": "string", "description": "UUID of the asset"}},
                "required": ["asset_id"],
            },
        ),
        types.Tool(
            name="list_sources",
            description="List all financial data providers (sources) registered in the warehouse.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="fetch_time_series",
            description="Fetch OHLCV time-series data for an asset from a specific data source.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                    "date_from": {"type": "string", "description": "ISO-8601 start date, e.g. 2024-01-01"},
                    "date_to":   {"type": "string", "description": "ISO-8601 end date"},
                    "limit":     {"type": "integer", "default": 90},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
        types.Tool(
            name="get_stats",
            description="Get descriptive statistics (min, max, mean, median, std, % change) for an asset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                    "field":     {"type": "string", "default": "close"},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
        types.Tool(
            name="get_volatility",
            description="Get annualised rolling volatility for an asset. Returns risk interpretation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                    "window":    {"type": "integer", "default": 30},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
        types.Tool(
            name="get_drawdown",
            description="Get the maximum peak-to-trough drawdown for an asset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
        types.Tool(
            name="get_trend_signal",
            description="Get the Golden Cross / Death Cross trend signal for an asset (bullish or bearish).",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
        types.Tool(
            name="forecast_price",
            description="Forecast next-day closing price using linear regression. Includes disclaimer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                    "lookback":  {"type": "integer", "default": 30},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
        types.Tool(
            name="compare_assets",
            description="Normalise multiple assets to 100 at start and compare their relative performance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of asset UUIDs to compare",
                    },
                    "source_id": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to":   {"type": "string"},
                },
                "required": ["asset_ids", "source_id"],
            },
        ),
        types.Tool(
            name="summarize_asset",
            description=(
                "Generate a plain-language summary of an asset including its latest price, "
                "stats, volatility, trend signal, and next-day forecast. "
                "Use this to explain a financial instrument to a non-expert."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_id":  {"type": "string"},
                    "source_id": {"type": "string"},
                },
                "required": ["asset_id", "source_id"],
            },
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tool execution
# ─────────────────────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    result: Any = None

    if name == "list_assets":
        result = await _get("/assets/")

    elif name == "get_asset":
        result = await _get(f"/assets/{arguments['asset_id']}")

    elif name == "list_sources":
        result = await _get("/sources/")

    elif name == "fetch_time_series":
        params = {
            "asset_id":  arguments["asset_id"],
            "source_id": arguments["source_id"],
            "limit":     arguments.get("limit", 90),
        }
        if arguments.get("date_from"):
            params["date_from"] = arguments["date_from"]
        if arguments.get("date_to"):
            params["date_to"] = arguments["date_to"]
        result = await _get("/timeseries/", params)

    elif name == "get_stats":
        result = await _get("/analytics/stats", {
            "asset_id":  arguments["asset_id"],
            "source_id": arguments["source_id"],
            "field":     arguments.get("field", "close"),
        })

    elif name == "get_volatility":
        result = await _get("/analytics/volatility", {
            "asset_id":  arguments["asset_id"],
            "source_id": arguments["source_id"],
            "window":    arguments.get("window", 30),
        })

    elif name == "get_drawdown":
        result = await _get("/analytics/drawdown", {
            "asset_id":  arguments["asset_id"],
            "source_id": arguments["source_id"],
        })

    elif name == "get_trend_signal":
        result = await _get("/analytics/trend", {
            "asset_id":  arguments["asset_id"],
            "source_id": arguments["source_id"],
        })

    elif name == "forecast_price":
        result = await _get("/analytics/forecast", {
            "asset_id":  arguments["asset_id"],
            "source_id": arguments["source_id"],
            "lookback":  arguments.get("lookback", 30),
        })

    elif name == "compare_assets":
        params: dict = {
            "asset_ids": arguments["asset_ids"],
            "source_id": arguments["source_id"],
        }
        if arguments.get("date_from"):
            params["date_from"] = arguments["date_from"]
        if arguments.get("date_to"):
            params["date_to"] = arguments["date_to"]
        result = await _get("/analytics/compare", params)

    elif name == "summarize_asset":
        # Aggregate multiple calls into one rich summary
        aid = arguments["asset_id"]
        sid = arguments["source_id"]
        asset   = await _get(f"/assets/{aid}")
        stats   = await _get("/analytics/stats",      {"asset_id": aid, "source_id": sid})
        vol     = await _get("/analytics/volatility", {"asset_id": aid, "source_id": sid})
        dd      = await _get("/analytics/drawdown",   {"asset_id": aid, "source_id": sid})
        trend   = await _get("/analytics/trend",      {"asset_id": aid, "source_id": sid})
        fcast   = await _get("/analytics/forecast",   {"asset_id": aid, "source_id": sid})
        result  = {
            "asset":    asset,
            "stats":    stats,
            "volatility": vol,
            "drawdown": dd,
            "trend":    trend,
            "forecast": fcast,
        }

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [types.TextContent(type="text", text=json.dumps(result, default=str, indent=2))]


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print(f"🤖 Acme Financial DWH MCP Server starting (API: {API_BASE})")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
