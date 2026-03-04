"""
Remembench — Industry RSS Feed Adapter

Monitors RSS feeds relevant to each industry vertical:
- Wireless: Verizon, T-Mobile, AT&T newsrooms
- Pizza: PMQ Pizza Magazine, Restaurant Business, NRN

Feeds are loaded from the industry registry, so adding a new
industry's news sources is just a config change.

All feeds are legal, public, and machine-readable (no scraping risk).
"""

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from app.adapters.base import BaseAdapter
from app.industries import get_rss_feeds
from app.schemas import ImpactEventCreate


# ---------------------------------------------------------------------------
#  Keyword Sets for Classification
# ---------------------------------------------------------------------------

# Wireless-specific promotion keywords
_WIRELESS_PROMO_KEYWORDS = [
    "deal", "offer", "promotion", "discount", "bogo", "buy one get one",
    "trade-in", "free", "savings", "price", "unlimited", "plan",
    "switch", "credit", "rebate", "limited time", "exclusive",
]

_WIRELESS_OUTAGE_KEYWORDS = [
    "outage", "disruption", "restoration", "service issue",
    "network issue", "down", "incident",
]

# Pizza/restaurant-specific keywords
_RESTAURANT_PROMO_KEYWORDS = [
    "deal", "offer", "promotion", "discount", "special",
    "limited time", "free", "buy one get one", "coupon",
    "new menu", "grand opening", "expansion",
]

_FOOD_SAFETY_KEYWORDS = [
    "recall", "inspection", "health department", "contamination",
    "food safety", "foodborne", "listeria", "salmonella",
]

_SUPPLY_CHAIN_KEYWORDS = [
    "cheese", "flour", "dough", "ingredient", "supply chain",
    "food cost", "price increase", "shortage",
]


class IndustryRssAdapter(BaseAdapter):
    """
    Industry-aware RSS feed adapter.

    Handles RSS feeds for ALL industries — wireless carrier newsrooms,
    pizza/restaurant trade publications, and more. The adapter name
    is kept as 'rss' for backward compatibility with stored events.
    """

    def __init__(self) -> None:
        super().__init__("rss")
        self.requires_llm_classification = True

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
        Fetch RSS feeds for the specified industry and extract
        relevant announcements within the date range.
        """
        # Strip tzinfo so we can compare against naive parsed RSS dates safely
        start_date = start_date.replace(tzinfo=None)
        end_date = end_date.replace(tzinfo=None)

        all_events: list[ImpactEventCreate] = []

        # Get industry-specific RSS feeds from the registry
        feeds = get_rss_feeds(industry)

        for feed_config in feeds:
            events = await self._process_feed(
                feed_config.source_key,
                feed_config.url,
                feed_config.label,
                start_date, end_date,
                geo_label, industry,
            )
            all_events.extend(events)

        self.logger.info(
            "rss_events_fetched",
            industry=industry,
            total_events=len(all_events),
            feed_count=len(feeds),
        )
        return all_events

    async def _process_feed(
        self,
        source_key: str,
        url: str,
        feed_label: str,
        start_date: datetime,
        end_date: datetime,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """Parse a single RSS feed and extract relevant entries safely."""
        events: list[ImpactEventCreate] = []

        try:
            raw_content = await self._http_get(url, timeout=15.0)
            if not isinstance(raw_content, str):
                raw_content = str(raw_content)
        except Exception as exc:
            self.logger.warning(
                "rss_fetch_failed",
                source=source_key, url=url, error=str(exc),
            )
            return []

        # Attempt to parse the feed, capturing malformed XML breaks
        try:
            feed = feedparser.parse(raw_content)
        except Exception as e:
            self.logger.error("rss_parse_error", source=source_key, error=str(e))
            return []
            
        if not hasattr(feed, "entries") or not isinstance(feed.entries, list):
            self.logger.warning("rss_invalid_entries", source=source_key)
            return []

        for entry in feed.entries:
            # Parse publication date
            pub_date = self._parse_entry_date(entry)
            if pub_date is None:
                continue

            # Strict bounds checking
            if pub_date < start_date or pub_date > end_date:
                continue

            # Safely coerce Feedparser types into explicit strings
            title: str = str(entry.get("title", ""))
            summary: str = str(entry.get("summary", entry.get("description", "")))
            link: str = str(entry.get("link", ""))

            if not title:
                continue  # Impossible to rank without a title

            # Classify based on industry definitions
            category, subcategory = self._classify_entry(title, summary, industry)
            if category is None:
                continue  # Skip irrelevant entries based on the _classify_entry filters

            severity = self._estimate_severity(title, summary, industry, source_key)

            try:
                events.append(ImpactEventCreate(
                    source="rss",
                    source_id=f"rss-{source_key}-{link[:200]}",
                    category=category,
                    subcategory=subcategory,
                    title=f"[{source_key.upper()}] {title[:450]}",
                    description=summary[:1000] if summary else None,
                    severity=severity,
                    confidence=0.85,  # Published news sources = high confidence correlation
                    start_date=pub_date,
                    end_date=pub_date, # Explicitly matching start_date for single-day granularity
                    geo_label=geo_label or "National",
                    industry=industry,
                    raw_payload={
                        "source_key": source_key,
                        "link": link,
                        "feed_label": feed_label,
                    },
                ))
            except Exception as schema_err:
                self.logger.warning("rss_schema_build_failed", title=title, err=str(schema_err))
                continue

        return events

    def _parse_entry_date(self, entry: dict) -> datetime | None:
        """Extract and parse the publication date from an RSS entry."""
        for date_field in ("published", "updated", "created"):
            # Prioritize parsed date tuples from feedparser, convert to naive UTC
            parsed_date_tuple = entry.get(f"{date_field}_parsed")
            if parsed_date_tuple:
                try:
                    # Convert time.struct_time to naive datetime
                    return datetime(*parsed_date_tuple[:6])
                except (ValueError, TypeError):
                    pass # Fallback to string parsing

            # Fallback to string parsing if parsed_date_tuple is not available or fails
            date_str = entry.get(date_field)
            if date_str:
                try:
                    # parsedate_to_datetime returns timezone-aware datetime
                    dt = parsedate_to_datetime(date_str)
                    return dt.replace(tzinfo=None) if dt else None # Convert to naive
                except (ValueError, TypeError):
                    try:
                        # fromisoformat can handle some ISO 8601 strings
                        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        return dt.replace(tzinfo=None)
                    except (ValueError, TypeError):
                        continue
        return None

    def _classify_entry(
        self, title: str, summary: str, industry: str,
    ) -> tuple[str | None, str | None]:
        """Classify an RSS entry based on industry context."""
        combined = f"{title} {summary}".lower()

        if industry.startswith("pizza"):
            # Pizza / restaurant classification
            if any(kw in combined for kw in _FOOD_SAFETY_KEYWORDS):
                return "food_safety", "recall_or_inspection"
            if any(kw in combined for kw in _SUPPLY_CHAIN_KEYWORDS):
                return "supply_chain", "cost_or_shortage"
            if any(kw in combined for kw in _RESTAURANT_PROMO_KEYWORDS):
                return "competitor_promo", "restaurant_promotion"
            # General restaurant news is still useful
            return "news", "industry_news"

        if industry == "wireless_retail":
            # Wireless classification
            if any(kw in combined for kw in _WIRELESS_PROMO_KEYWORDS):
                return "competitor_promo", "carrier_announcement"
            if any(kw in combined for kw in _WIRELESS_OUTAGE_KEYWORDS):
                return "outage", "carrier_outage_report"
            # Skip entries that aren't promo/outage relevant for wireless
            return None, None

        # Default: treat everything as general news
        return "news", "general"

    def _estimate_severity(
        self, title: str, summary: str, industry: str, source_key: str,
    ) -> float:
        """Estimate the competitive impact of a news item."""
        combined = f"{title} {summary}".lower()
        severity = 0.4  # Base severity

        # Universal severity boosters
        if any(kw in combined for kw in ["major", "massive", "unprecedented", "recall"]):
            severity += 0.2
        if any(kw in combined for kw in ["nationwide", "all locations", "all customers"]):
            severity += 0.1

        # Industry-specific boosters
        if industry.startswith("pizza"):
            if any(kw in combined for kw in ["health department", "contamination", "shutdown"]):
                severity += 0.25
        elif industry == "wireless_retail":
            if any(kw in combined for kw in ["free", "bogo", "buy one get one"]):
                severity += 0.25
            if any(kw in combined for kw in ["switch", "trade-in", "credit"]):
                severity += 0.1

        return self._clamp_severity(severity)
