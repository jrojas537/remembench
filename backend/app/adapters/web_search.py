import json
import hashlib
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.adapters.base import BaseAdapter
from app.schemas import ImpactEventCreate
from app.config import settings
from app.logging import get_logger
from app.industries import get_web_search_query

logger = get_logger("web_search_adapter")

try:
    from tavily import AsyncTavilyClient
except ImportError:
    AsyncTavilyClient = None

try:
    from exa_py import Exa
except ImportError:
    Exa = None

try:
    from duckduckgo_search import DDGS as _DDGS
except ImportError:
    _DDGS = None


class WebSearchAdapter(BaseAdapter):
    """
    Adapter that uses search engines (Tavily/Exa/DuckDuckGo) to find
    news articles and promotions when structured sources are empty.
    """
    name = "web_search"
    requires_llm_classification = True

    def __init__(self):
        super().__init__("web_search")
        self.requires_llm_classification = True
        
        # Initialize clients only if their keys exist
        self.tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key) if getattr(settings, "tavily_api_key", None) else None
        
        # Exa is currently synchronous in its standard API, so we wrap it
        self.exa_client = Exa(getattr(settings, "exa_api_key", "")) if getattr(settings, "exa_api_key", None) else None
        
        # DDGS is synchronous — we'll run it in an executor when needed
        self.has_ddgs = _DDGS is not None

    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        industry: str = "wireless_retail",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        geo_label: Optional[str] = None,
    ) -> List[ImpactEventCreate]:
        """
        Attempts to fetch news surrounding a specific market/industry over a date range.
        Implementing BaseAdapter contract.
        """
        limit = 5
        market = geo_label if geo_label else "Unknown"
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        year = start_date.year

        # Build a tight, industry-specific query targeting EVENT DRIVERS and PROMOTIONS
        industry_terms = get_web_search_query(industry, start_date, end_date)

        query = (
            f"{industry_terms} {market} {year}"
        )
        
        raw_results = []
        
        # 1. Try Tavily (Best structured output for LLMs)
        if self.tavily_client:
            try:
                logger.info(f"Attempting Tavily search for: {query}")
                response = await self.tavily_client.search(
                    query=query, 
                    search_depth="advanced",
                    max_results=limit,
                    include_answer=False
                )
                
                for res in response.get("results", []):
                    raw_results.append({
                        "network": "tavily",
                        "original_text": f"Title: {res.get('title')}\nContent: {res.get('content')}",
                        "url": res.get("url"),
                        "market": market,
                        "industry": industry
                    })
            except Exception as e:
                logger.warning(f"Tavily search failed, falling back to Exa: {str(e)}")

        # 2. Try Exa if Tavily failed to find anything or crashed
        if not raw_results and self.exa_client:
            try:
                logger.info(f"Attempting Exa search for: {query}")
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.exa_client.search_and_contents(
                        query,
                        num_results=limit,
                        use_autoprompt=True,
                        start_published_date=start_str,
                        end_published_date=end_str
                    )
                )
                
                for res in response.results:
                    raw_results.append({
                        "network": "exa",
                        "original_text": f"Title: {res.title}\nContent: {res.text[:1000] if res.text else ''}", 
                        "url": res.url,
                        "market": market,
                        "industry": industry
                    })
            except Exception as e:
                logger.warning(f"Exa search failed, falling back to DDG: {str(e)}")

        # 3. DuckDuckGo fallback — synchronous, run in executor
        if not raw_results and self.has_ddgs:
            try:
                logger.info(f"Attempting DuckDuckGo fallback search for: {query}")
                loop = asyncio.get_running_loop()
                ddg_results = await loop.run_in_executor(
                    None,
                    lambda: list(_DDGS().text(query, max_results=limit))
                )
                for res in ddg_results:
                    raw_results.append({
                        "network": "duckduckgo",
                        "original_text": f"Title: {res.get('title')}\nContent: {res.get('body')}",
                        "url": res.get("href"),
                        "market": market,
                        "industry": industry
                    })
            except Exception as e:
                logger.error(f"DDG fallback failed. All search providers exhausted: {str(e)}")
        
        # Package into ImpactEventCreate
        events = []
        for res in raw_results:
            url_val = res.get('url') or ""
            if not url_val:
                url_val = res.get('original_text', '')[:100]
                
            url_hash = hashlib.md5(
                url_val.encode('utf-8', errors='replace'), usedforsecurity=False
            ).hexdigest()[:12]
            
            events.append(
                ImpactEventCreate(
                    source=f"web_search_{res['network']}",
                    source_id=url_hash,
                    category="Local News",
                    subcategory="Unclassified",
                    title="Analyzing News Event",
                    description=res["original_text"][:2000],  # truncated for safely passing to LLM
                    severity=0.0, # LLM will upgrade
                    confidence=0.0, # LLM will upgrade
                    start_date=start_date,
                    end_date=end_date,
                    geo_label=geo_label,
                    latitude=latitude,
                    longitude=longitude,
                    industry=industry,
                    geo_radius_km=25.0,
                    raw_payload=res
                )
            )

        return events

    async def close(self) -> None:
        """Cleanup any active clients."""
        pass
