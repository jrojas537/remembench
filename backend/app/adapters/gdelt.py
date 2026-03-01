"""
Remembench — GDELT News & Events Adapter

Searches the GDELT DOC 2.0 API for news articles relevant to the
specified industry. Queries are loaded from the industry registry,
so adding pizza-specific terms vs. wireless-specific terms is just
a config change.

GDELT is a free, open global database of events from news media,
updated every 15 minutes, covering 100+ languages since 1979.

Used for: competitor news, local disruptions, protests, natural
disasters, food safety incidents, and any newsworthy events that
could impact retail performance.

Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""

from datetime import datetime

from app.adapters.base import BaseAdapter
from app.industries import get_gdelt_queries
from app.schemas import ImpactEventCreate


# GDELT tone threshold — strong negative tone correlates with
# events that disrupt normal business operations
_NEGATIVE_TONE_THRESHOLD = -5.0


class GdeltAdapter(BaseAdapter):
    """Adapter for GDELT DOC 2.0 API for news-based event detection."""

    def __init__(self) -> None:
        super().__init__("gdelt")
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    async def fetch_events(
        self,
        start_date: datetime,
        end_date: datetime,
        industry: str = "wireless_retail",
        latitude: float | None = None,
        longitude: float | None = None,
        geo_label: str | None = None,
    ) -> list[ImpactEventCreate]:
        """
        Search GDELT for articles matching industry-specific terms.

        Queries are loaded dynamically from the industry registry,
        so each vertical gets its own relevant search terms.
        """
        all_events: list[ImpactEventCreate] = []

        # Get industry-specific search queries from the registry
        queries = get_gdelt_queries(industry)

        for query_term in queries:
            events = await self._search_gdelt(
                query_term, start_date, end_date,
                latitude, longitude, geo_label, industry,
            )
            all_events.extend(events)

        # Deduplicate by source_id within this adapter
        seen_ids: set[str] = set()
        deduped: list[ImpactEventCreate] = []
        for event in all_events:
            if event.source_id and event.source_id not in seen_ids:
                seen_ids.add(event.source_id)
                deduped.append(event)

        self.logger.info(
            "gdelt_events_fetched",
            industry=industry,
            raw_count=len(all_events),
            deduped_count=len(deduped),
            geo_label=geo_label,
        )
        return deduped

    async def _search_gdelt(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        latitude: float | None,
        longitude: float | None,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """Execute a single GDELT DOC API search and normalize results."""
        # Build geographic proximity filter if coordinates are provided
        geo_filter = ""
        if latitude is not None and longitude is not None:
            geo_filter = f" near:{latitude},{longitude}"

        params = {
            "query": f"{query}{geo_filter}",
            "mode": "ArtList",
            "maxrecords": 50,
            "format": "json",
            "startdatetime": start_date.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end_date.strftime("%Y%m%d%H%M%S"),
            "sort": "ToneDesc",
        }

        try:
            data = await self._http_get(self.base_url, params=params)
        except Exception as exc:
            self.logger.warning("gdelt_search_failed", query=query, error=str(exc))
            return []

        if not isinstance(data, dict):
            return []

        articles = data.get("articles", [])
        return self._normalize_articles(articles, geo_label, industry)

    def _normalize_articles(
        self,
        articles: list[dict],
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """Convert GDELT articles into normalized ImpactEvents."""
        events: list[ImpactEventCreate] = []

        for article in articles:
            url = article.get("url", "")
            title = article.get("title", "")
            seendate = article.get("seendate", "")
            tone = article.get("tone", 0)
            source_country = article.get("sourcecountry", "")
            domain = article.get("domain", "")

            if not title or not seendate:
                continue

            # Parse GDELT date format (YYYYMMDDTHHMMSS)
            try:
                event_date = datetime.strptime(seendate[:8], "%Y%m%d")
            except (ValueError, IndexError):
                continue

            category, subcategory = self._classify_article(title, industry)
            severity = self._estimate_severity(tone, title)

            events.append(ImpactEventCreate(
                source="gdelt",
                source_id=f"gdelt-{url[:200]}",
                category=category,
                subcategory=subcategory,
                title=title[:512],
                description=f"Source: {domain}. Tone: {tone:.1f}.",
                severity=severity,
                confidence=0.5,  # GDELT has ~55% field accuracy
                start_date=event_date,
                end_date=event_date,
                geo_label=geo_label,
                industry=industry,
                raw_payload={
                    "url": url,
                    "tone": tone,
                    "source_country": source_country,
                    "domain": domain,
                },
            ))

        return events

    def _classify_article(self, title: str, industry: str) -> tuple[str, str | None]:
        """
        Classify a GDELT article into our category taxonomy.

        Classification is industry-aware: pizza-related keywords map to
        food-specific categories, while wireless keywords map to
        telecom-specific categories.
        """
        title_lower = title.lower()

        # Universal categories (apply to all industries)
        if any(kw in title_lower for kw in ["storm", "hurricane", "tornado", "flood", "blizzard", "wildfire"]):
            return "weather", "severe_weather_news"
        if any(kw in title_lower for kw in ["protest", "demonstration", "parade", "road closure"]):
            return "news", "local_disruption"

        # Pizza-specific categories
        if industry.startswith("pizza"):
            if any(kw in title_lower for kw in ["food safety", "health inspection", "food recall", "contamination"]):
                return "food_safety", "inspection_or_recall"
            if any(kw in title_lower for kw in ["doordash", "uber eats", "grubhub", "delivery disruption"]):
                return "delivery_disruption", "platform_issue"
            if any(kw in title_lower for kw in ["cheese price", "flour price", "food cost", "ingredient"]):
                return "supply_chain", "ingredient_costs"
            if any(kw in title_lower for kw in ["minimum wage", "labor shortage", "restaurant workers"]):
                return "labor", "staffing"
            if any(kw in title_lower for kw in ["promotion", "deal", "offer", "discount", "special"]):
                return "competitor_promo", "restaurant_promotion"

        # Wireless-specific categories
        if industry == "wireless_retail":
            if any(kw in title_lower for kw in ["promotion", "deal", "offer", "discount", "bogo", "trade-in"]):
                return "competitor_promo", "carrier_promotion"
            if any(kw in title_lower for kw in ["outage", "disruption", "down", "failure"]):
                return "outage", "network_outage"

        # General fallback
        if any(kw in title_lower for kw in ["closure", "shut down", "closed"]):
            return "news", "business_closure"

        return "news", "general"

    def _estimate_severity(self, tone: float, title: str) -> float:
        """
        Estimate impact severity from GDELT tone score and keywords.

        Tone ranges from -100 to +100. Strong negative tone usually
        correlates with events that disrupt normal operations.
        """
        base_severity = 0.3
        if tone < _NEGATIVE_TONE_THRESHOLD:
            base_severity += abs(tone) / 50

        title_lower = title.lower()
        if any(kw in title_lower for kw in ["major", "massive", "unprecedented", "emergency"]):
            base_severity += 0.2
        if any(kw in title_lower for kw in ["nationwide", "widespread", "citywide"]):
            base_severity += 0.15

        return self._clamp_severity(base_severity)
