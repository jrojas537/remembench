import asyncio
from datetime import datetime, timezone
import json
import logging

# basic logging setup
logging.basicConfig(level=logging.WARNING)

from app.adapters.gdelt import GdeltAdapter
from app.adapters.open_meteo import OpenMeteoAdapter
from app.adapters.carrier_rss import IndustryRssAdapter
from app.industries import PIZZA_MARKETS

async def main():
    market = next((m for m in PIZZA_MARKETS if m.geo_label == "Detroit Metro"), None)
    if not market:
        # fallback to Detroit for testing if Detroit Metro isn't reloaded locally
        market = next((m for m in PIZZA_MARKETS if m.geo_label == "Detroit"), None)

    industry = "pizza_delivery"
    start_date = datetime(2025, 3, 16)
    end_date = datetime(2025, 3, 18)

    gdelt = GdeltAdapter()
    meteo = OpenMeteoAdapter()
    rss = IndustryRssAdapter() 

    print(f"==========================================")
    print(f"🔥 RAW ADAPTER FETCH 🔥")
    print(f"Market: {market.geo_label} ({market.latitude}, {market.longitude})")
    print(f"Dates:  {start_date.date()} to {end_date.date()}")
    print(f"==========================================\n")

    print("[ 1 ] FETCHING OPEN_METEO WEATHER DATA...")
    weather_events = await meteo.fetch_events(
        start_date, end_date, industry, 
        latitude=market.latitude, longitude=market.longitude, geo_label=market.geo_label
    )
    for i, w in enumerate(weather_events):
        print(f"  {i+1}. {w['start_date']} | {w['title']}")
        print(f"     Severity Data: {w.get('raw_payload', {}).get('weather_data', {})}")
        print(f"     Desc: {w['description']}\n")
    if not weather_events:
        print("  ❌ No remarkable weather events found.\n")

    print("[ 2 ] FETCHING GDELT NEWS DATA...")
    gdelt_events = await gdelt.fetch_events(
        start_date, end_date, industry, 
        latitude=market.latitude, longitude=market.longitude, geo_label=market.geo_label
    )
    for i, g in enumerate(gdelt_events):
        print(f"  {i+1}. {g['start_date']} | {g['title']}")
        print(f"     URL: {g['url']}\n")
    if not gdelt_events:
        print("  ❌ No GDELT news events found.\n")
        
    print("[ 3 ] FETCHING RSS FEED DATA...")
    rss_events = await rss.fetch_events(
        start_date, end_date, industry, 
        latitude=market.latitude, longitude=market.longitude, geo_label=market.geo_label
    )
    for i, r in enumerate(rss_events):
        print(f"  {i+1}. {r['start_date']} | {r['title']}")
        print(f"     URL: {r.get('url', '')}\n")
    if not rss_events:
        print("  ❌ No RSS feed events found.\n")

if __name__ == "__main__":
    asyncio.run(main())
