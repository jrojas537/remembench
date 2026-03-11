import json
import hashlib
import asyncio
from datetime import datetime, timezone
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
        Implements a tiered fallback chain to ensure maximum reliability:
        1. Tavily (Primary): Returns highly structured content optimized for LLM consumption.
        2. Exa (Secondary): Returns semantic neural-search web hits if Tavily fails.
        3. DuckDuckGo (Tertiary): Free synchronous fallback executed in an async thread pool.
        
        All results are heavily cached via Redis to prevent redundant API billing.
        
        Args:
            start_date: The beginning of the search constraint window.
            end_date: The termination date of the search window.
            industry: The active vertical key (e.g., 'pizza_all').
            latitude: (Optional) Geolocation Y coordinate.
            longitude: (Optional) Geolocation X coordinate.
            geo_label: (Optional) Semantic market name (e.g., 'Detroit Metro').
            
        Returns:
            List[ImpactEventCreate]: Unstructured payload items ready for LLM NLP mapping.
        """
        limit = 15
        market = geo_label if geo_label else "Unknown"
        from datetime import timedelta
        start_str = start_date.strftime("%Y-%m-%d")
        # Look back 90 days to catch articles announcing ongoing promos
        oxa_start_str = (start_date - timedelta(days=90)).strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        year = start_date.year

        # Build a tight, industry-specific query targeting EVENT DRIVERS and PROMOTIONS
        industry_terms = get_web_search_query(industry, start_date, end_date)

        query = (
            f"{industry_terms} {market} {year}"
        )
        
        raw_results = []
        now = datetime.now(end_date.tzinfo) if end_date.tzinfo else datetime.now()
        is_historical = (now - end_date).days > 30

        logger.info(f"Routing WebSearch: query='{query}' is_historical={is_historical}")

        # ---------------------------------------------------------------------
        # Tier 1 & 2 Router (Historical vs Recent)
        # Exa Neural Search is uniquely capable of strict historical chronological bounding 
        # for events that bypass traditional index recency (e.g. > 30 days old). 
        # Tavily is profoundly superior for recent/live data structuring and NLP comprehension.
        # The logic dynamically prioritizes the appropriate SDK based on the search_date trajectory.
        # ---------------------------------------------------------------------

        async def _run_exa():
            try:
                import json
                from app.cache import get_redis
                redis_pool = get_redis()
                rd = await anext(redis_pool)
                exa_cache_key = f"exa:search:{hashlib.md5(query.encode()).hexdigest()}"
                
                cached = await rd.get(exa_cache_key)
                all_res = []
                
                if cached:
                    logger.info(f"Exa Cache HIT for: {query}")
                    cached_data = json.loads(cached)
                    class FauxResult:
                        def __init__(self, t, tx, u): self.title = t; self.text = tx; self.url = u
                    all_res = [FauxResult(r['title'], r['text'], r['url']) for r in cached_data]
                else:
                    logger.info(f"Attempting Exa search for: {query}")
                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: self.exa_client.search_and_contents(
                            query,
                            num_results=limit,
                            start_published_date=oxa_start_str,
                            end_published_date=end_str
                        )
                    )
                    all_res = response.results
                    cacheable = [{"title": r.title, "text": r.text, "url": r.url} for r in all_res]
                    await rd.setex(exa_cache_key, 1209600, json.dumps(cacheable))
                
                for res in all_res:
                    raw_results.append({
                        "network": "exa",
                        "original_text": f"Title: {res.title}\nContent: {res.text[:1000] if res.text else ''}", 
                        "url": res.url,
                        "market": market,
                        "industry": industry
                    })
            except Exception as e:
                logger.warning(f"Exa search failed: {str(e)}")

        async def _run_tavily():
            try:
                import json
                from app.cache import get_redis
                redis_pool = get_redis()
                rd = await anext(redis_pool)
                tavily_cache_key = f"tavily:search:{hashlib.md5(query.encode()).hexdigest()}"
                
                cached = await rd.get(tavily_cache_key)
                if cached:
                    logger.info(f"Tavily Cache HIT for: {query}")
                    response = json.loads(cached)
                else:
                    logger.info(f"Attempting Tavily search for: {query}")
                    response = await self.tavily_client.search(
                        query=query, 
                        search_depth="advanced",
                        max_results=limit,
                        include_answer=False
                    )
                    await rd.setex(tavily_cache_key, 1209600, json.dumps(response))
                
                for res in response.get("results", []):
                    raw_results.append({
                        "network": "tavily",
                        "original_text": f"Title: {res.get('title')}\nContent: {res.get('content')}",
                        "url": res.get("url"),
                        "market": market,
                        "industry": industry
                    })
            except Exception as e:
                logger.warning(f"Tavily search failed: {str(e)}")

        # Dispatch Route priority
        if is_historical and self.exa_client:
            await _run_exa()
            if not raw_results and self.tavily_client:
                await _run_tavily()
        else:
            if self.tavily_client:
                await _run_tavily()
            if not raw_results and self.exa_client:
                await _run_exa()
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
