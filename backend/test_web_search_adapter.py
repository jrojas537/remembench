"""
test_web_search_adapter.py — Verify the WebSearchAdapter chain-of-responsibility
produces historical event data for Detroit Metro pizza delivery.

Usage:
    cd backend && venv/bin/python test_web_search_adapter.py

The adapter tries in order:
  1. Tavily (structured, paid — needs TAVILY_API_KEY)
  2. Exa  (semantic, paid — needs EXA_API_KEY)
  3. DuckDuckGo (free, always works)

This script tests all three and shows you exactly what raw data they return
BEFORE the LLM classification layer sees it.
"""

import asyncio
import os
import sys
from datetime import datetime

# Allow running from the backend/ dir without installing the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.adapters.web_search import WebSearchAdapter
from app.adapters.open_meteo import OpenMeteoAdapter
from app.config import settings

# ─── Test Parameters ──────────────────────────────────────────────────────────
MARKET     = "Detroit Metro"
LATITUDE   = 42.3314
LONGITUDE  = -83.0458
INDUSTRY   = "pizza_delivery"
START_DATE = datetime(2025, 3, 16)
END_DATE   = datetime(2025, 3, 18)

def banner(text: str) -> None:
    line = "─" * 60
    print(f"\n{line}\n  {text}\n{line}")


async def test_weather():
    banner("[ OPEN-METEO ] Daily Weather Conditions")
    adapter = OpenMeteoAdapter()
    events = await adapter.fetch_events(
        start_date=START_DATE, end_date=END_DATE, industry=INDUSTRY,
        latitude=LATITUDE, longitude=LONGITUDE, geo_label=MARKET,
    )
    if not events:
        print("  ❌ No data returned")
        return

    for e in events:
        if e.subcategory == "daily_conditions":
            print(f"  📅 {e.start_date.date()} | {e.title}")
            print(f"     {e.description}")
            print(f"     Severity: {e.severity:.2f}")
        else:
            print(f"  ⚠️  SEVERE: {e.title} (severity={e.severity:.2f})")
    await adapter.close()


async def test_web_search():
    banner("[ WEB SEARCH ] Tavily → Exa → DuckDuckGo Cascade")

    # Show which keys are configured
    has_tavily = bool(getattr(settings, "tavily_api_key", ""))
    has_exa    = bool(getattr(settings, "exa_api_key", ""))
    print(f"  Tavily Key: {'✅ SET' if has_tavily else '❌ NOT SET'}")
    print(f"  Exa Key:    {'✅ SET' if has_exa else '❌ NOT SET'}")
    print(f"  DuckDuckGo: ✅ Always available (no key)\n")

    adapter = WebSearchAdapter()
    events = await adapter.fetch_events(
        start_date=START_DATE, end_date=END_DATE, industry=INDUSTRY,
        latitude=LATITUDE, longitude=LONGITUDE, geo_label=MARKET,
    )

    if not events:
        print("  ❌ No results returned from any provider")
        return

    print(f"  ✅ Got {len(events)} raw result(s)\n")
    for i, e in enumerate(events, 1):
        provider = e.source.replace("web_search_", "").upper()
        print(f"  [{i}] Provider: {provider}")
        print(f"       Title:   {e.title}")
        url = e.raw_payload.get("url", "N/A") if e.raw_payload else "N/A"
        print(f"       URL:     {url}")
        snippet = e.description[:300].replace("\n", " ") if e.description else "—"
        print(f"       Snippet: {snippet}...")
        print()


async def main():
    print("\n" + "=" * 60)
    print("  🔥 REMEMBENCH — RAW ADAPTER DIAGNOSTIC SCRIPT")
    print(f"  Market:   {MARKET}")
    print(f"  Industry: {INDUSTRY}")
    print(f"  Dates:    {START_DATE.date()} → {END_DATE.date()}")
    print("=" * 60)

    await test_weather()
    await test_web_search()

    print("\n✅ Done.\n")


if __name__ == "__main__":
    asyncio.run(main())
