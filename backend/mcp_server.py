import sys
import json
import asyncio
from datetime import datetime
from sqlalchemy import select, and_

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

from app.database import AsyncSessionLocal
from app.models import ImpactEvent

# Create an MCP server
mcp = FastMCP("Remembench Context Engine")

@mcp.tool()
async def get_market_anomalies(industry: str, start_date: str, end_date: str, market: str = None) -> str:
    """
    Search the Remembench database for anomalies, disruptions, and events that impacted a market.
    Returns a highly compressed, token-efficient timeline of events.
    Use this to get a broad overview of what happened during a specific date range.
    
    Args:
        industry: The slug of the target industry (e.g. 'wireless_retail', 'pizza_full_service').
        start_date: The start of the date range (YYYY-MM-DD).
        end_date: The end of the date range (YYYY-MM-DD).
        market: Optional specific geographical market (e.g. 'New York City', 'Detroit').
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return "Error: Invalid date format. Must use YYYY-MM-DD."

    async with AsyncSessionLocal() as db:
        query = select(ImpactEvent).where(
            and_(
                ImpactEvent.industry == industry,
                ImpactEvent.start_date >= start_dt,
                ImpactEvent.start_date <= end_dt
            )
        )
        if market:
            query = query.where(ImpactEvent.geo_label == market)
        
        query = query.order_by(ImpactEvent.start_date.desc()).limit(50)
        
        result_set = await db.execute(query)
        events = result_set.scalars().all()

        if not events:
            return f"No recorded anomalies found for {industry} between {start_date} and {end_date}."

        result = [f"Found {len(events)} events (returning token-compressed summaries). To get full details, use get_anomaly_details(event_id)."]
        for e in events:
            date_str = e.start_date.strftime("%Y-%m-%d")
            # Compress to single line, expose the ID for drill-down tool
            result.append(f"* [{date_str}] id={e.id} | score={e.severity:.2f} | cat={e.category} | {e.title}")

        return "\n".join(result)

@mcp.tool()
async def get_anomaly_details(event_id: str) -> str:
    """
    Agent Drill-Down Tool.
    If you found an interesting event using `get_market_anomalies`, pass the ID here to 
    get the full, long-form description and confidence scores.
    
    Args:
        event_id: The UUID string of the event retrieved from get_market_anomalies.
    """
    async with AsyncSessionLocal() as db:
        event = await db.get(ImpactEvent, event_id)
        if not event:
            return f"Error: No event found matching ID {event_id}"
        
        details = {
            "date": event.start_date.strftime("%Y-%m-%d"),
            "category": event.category,
            "subcategory": event.subcategory,
            "title": event.title,
            "detailed_description": event.description,
            "severity_score": round(event.severity, 2),
            "confidence_score": round(event.confidence, 2),
            "market": event.geo_label
        }
        # Return as pretty-printed JSON (easier for LLMs to read than flat code dicts)
        return json.dumps(details, indent=2)

if __name__ == "__main__":
    # Initialize and run the FastMCP server on standard I/O (required for Claude Desktop, Cursor, etc)
    mcp.run()
