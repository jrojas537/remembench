"""
Industry Registry — Centralized configuration for all supported verticals.

Remembench supports multiple industries out of the box. Each industry defines
its own markets (geographic locations with coordinates), GDELT search queries,
competitor/industry RSS feeds, and event categories.

Adding a new industry is as simple as adding an entry to the INDUSTRIES dict.
The frontend dynamically reads this registry via the /api/v1/industries endpoint.

Currently supported:
- Wireless Retail (cellphone stores, carrier retail)
- Pizza Restaurants (full-service, delivery, bar, carry-out)
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
#  Data Classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Market:
    """A geographic market with coordinates for weather/geo-specific queries."""
    geo_label: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RSSFeed:
    """An RSS feed to monitor for industry-relevant news."""
    url: str
    label: str
    source_key: str  # e.g. "verizon", "pmq_pizza"


@dataclass(frozen=True)
class IndustryConfig:
    """Full configuration for a single industry vertical."""
    key: str                          # Machine-readable ID
    label: str                        # Display name
    icon: str                         # Emoji icon
    description: str                  # Short description
    group: str                        # Grouping key (e.g. "pizza", "wireless")
    markets: list[Market]             # Default markets to ingest
    gdelt_queries: list[str]          # GDELT search terms
    rss_feeds: list[RSSFeed]          # RSS feeds to monitor
    categories: list[str]             # Event categories relevant to this industry
    category_labels: dict[str, str] = field(default_factory=dict)  # Friendly names


# ---------------------------------------------------------------------------
#  Market Definitions
# ---------------------------------------------------------------------------

# Major US metro areas for wireless retail analysis
WIRELESS_MARKETS = [
    Market("New York City", 40.7128, -74.0060),
    Market("Los Angeles", 34.0522, -118.2437),
    Market("Chicago", 41.8781, -87.6298),
    Market("Houston", 29.7604, -95.3698),
    Market("Dallas", 32.7767, -96.7970),
    Market("Philadelphia", 39.9526, -75.1652),
    Market("Miami", 25.7617, -80.1918),
    Market("Atlanta", 33.7490, -84.3880),
    Market("Phoenix", 33.4484, -112.0740),
    Market("Seattle", 47.6062, -122.3321),
]

# Detroit metro area + key Michigan cities for pizza analysis
PIZZA_MARKETS = [
    Market("Detroit Metro", 42.3314, -83.0458),
    Market("Dearborn", 42.3223, -83.1763),
    Market("Warren", 42.4775, -83.0277),
    Market("Ann Arbor", 42.2808, -83.7430),
    Market("Royal Oak", 42.4895, -83.1446),
    Market("Ferndale", 42.4606, -83.1346),
    Market("Livonia", 42.3684, -83.3527),
    Market("Sterling Heights", 42.5803, -83.0302),
    Market("Farmington Hills", 42.4853, -83.3771),
    Market("Troy", 42.6064, -83.1498),
]


# ---------------------------------------------------------------------------
#  GDELT Query Sets
# ---------------------------------------------------------------------------

WIRELESS_GDELT_QUERIES = [
    "wireless store OR cell phone store OR mobile retail",
    "(T-Mobile OR Verizon OR AT&T) (promotion OR deal OR offer OR \"limited time\")",
    "network outage OR service disruption OR cellular outage",
    "store closure OR retail closure OR power outage",
    "protest OR demonstration OR road closure OR parade",
    "(iPhone OR Galaxy OR Pixel) launch OR availability OR pre-order",
]

PIZZA_GDELT_QUERIES = [
    '"pizza restaurant" OR "pizzeria" OR "pizza shop" (promotion OR deal OR coupon)',
    '"food delivery" OR "DoorDash" OR "Uber Eats" OR "Grubhub" (fees OR disruption OR strike)',
    '"food safety" OR "health inspection" OR "food recall" OR "restaurant inspection"',
    '"restaurant closure" OR "dining shutdown" OR "restaurant shutdown"',
    "protest OR demonstration OR road closure OR parade",
    '"minimum wage" OR "labor shortage" OR "restaurant workers"',
    '"cheese prices" OR "flour prices" OR "food costs" OR "ingredient prices"',
    '("Little Caesars" OR "Pizza Hut" OR "Papa Johns" OR "Dominos") (promotion OR discount OR launch)',
]


# ---------------------------------------------------------------------------
#  RSS Feed Sets
# ---------------------------------------------------------------------------

WIRELESS_RSS_FEEDS = [
    RSSFeed(
        url="https://www.verizon.com/about/rss-feeds/news-releases",
        label="Verizon News Releases",
        source_key="verizon",
    ),
    RSSFeed(
        url="https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVJaEk&_gl=1",
        label="T-Mobile via BusinessWire",
        source_key="tmobile",
    ),
    RSSFeed(
        url="https://about.att.com/rss/press_releases.xml",
        label="AT&T Newsroom",
        source_key="att",
    ),
]

PIZZA_RSS_FEEDS = [
    RSSFeed(
        url="https://www.pmq.com/feed/",
        label="PMQ Pizza Magazine",
        source_key="pmq_pizza",
    ),
    RSSFeed(
        url="https://www.restaurantbusinessonline.com/rss/xml",
        label="Restaurant Business Online",
        source_key="restaurant_business",
    ),
    RSSFeed(
        url="https://www.nrn.com/rss.xml",
        label="Nation's Restaurant News",
        source_key="nrn",
    ),
]


# ---------------------------------------------------------------------------
#  Category Definitions
# ---------------------------------------------------------------------------

# Categories shared across all industries
UNIVERSAL_CATEGORIES = [
    "weather", "holiday", "news",
]

WIRELESS_CATEGORIES = UNIVERSAL_CATEGORIES + [
    "competitor_promo", "outage", "internal_promo", "system_issue",
]

PIZZA_CATEGORIES = UNIVERSAL_CATEGORIES + [
    "competitor_promo", "delivery_disruption", "food_safety",
    "supply_chain", "labor", "local_event",
]


# ---------------------------------------------------------------------------
#  Industry Registry
# ---------------------------------------------------------------------------

INDUSTRIES: dict[str, IndustryConfig] = {
    # === WIRELESS RETAIL ===
    "wireless_retail": IndustryConfig(
        key="wireless_retail",
        label="Wireless Retail",
        icon="📱",
        description="Cellphone stores, carrier retail, and mobile device sales",
        group="wireless",
        markets=WIRELESS_MARKETS,
        gdelt_queries=WIRELESS_GDELT_QUERIES,
        rss_feeds=WIRELESS_RSS_FEEDS,
        categories=WIRELESS_CATEGORIES,
        category_labels={
            "weather": "Weather Impact",
            "holiday": "Holiday",
            "news": "News / Local Event",
            "competitor_promo": "Competitor Promotion",
            "outage": "Network / Service Outage",
            "internal_promo": "Internal Promotion",
            "system_issue": "System Issue",
        },
    ),

    # === PIZZA — FULL SERVICE ===
    "pizza_full_service": IndustryConfig(
        key="pizza_full_service",
        label="Pizza — Full Service",
        icon="🍕",
        description="Full-service dine-in pizza restaurants",
        group="pizza",
        markets=PIZZA_MARKETS,
        gdelt_queries=PIZZA_GDELT_QUERIES,
        rss_feeds=PIZZA_RSS_FEEDS,
        categories=PIZZA_CATEGORIES,
        category_labels={
            "weather": "Weather Impact",
            "holiday": "Holiday",
            "news": "News / Local Event",
            "competitor_promo": "Competitor Activity",
            "delivery_disruption": "Delivery Disruption",
            "food_safety": "Food Safety / Health",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Labor / Staffing",
            "local_event": "Local Event / Festival",
        },
    ),

    # === PIZZA — DELIVERY ===
    "pizza_delivery": IndustryConfig(
        key="pizza_delivery",
        label="Pizza — Delivery",
        icon="🛵",
        description="Pizza delivery and takeout-focused operations",
        group="pizza",
        markets=PIZZA_MARKETS,
        gdelt_queries=PIZZA_GDELT_QUERIES,
        rss_feeds=PIZZA_RSS_FEEDS,
        categories=PIZZA_CATEGORIES,
        category_labels={
            "weather": "Weather Impact",
            "holiday": "Holiday",
            "news": "News / Local Event",
            "competitor_promo": "Competitor Activity",
            "delivery_disruption": "Delivery Platform Disruption",
            "food_safety": "Food Safety / Health",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Driver / Labor Shortage",
            "local_event": "Local Event / Festival",
        },
    ),

    # === PIZZA — BAR ===
    "pizza_bar": IndustryConfig(
        key="pizza_bar",
        label="Pizza — Bar & Restaurant",
        icon="🍺",
        description="Pizza restaurants with bar/taproom",
        group="pizza",
        markets=PIZZA_MARKETS,
        gdelt_queries=PIZZA_GDELT_QUERIES,
        rss_feeds=PIZZA_RSS_FEEDS,
        categories=PIZZA_CATEGORIES,
        category_labels={
            "weather": "Weather Impact",
            "holiday": "Holiday",
            "news": "News / Local Event",
            "competitor_promo": "Competitor Activity",
            "delivery_disruption": "Delivery Disruption",
            "food_safety": "Food Safety / Liquor License",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Labor / Staffing",
            "local_event": "Local Event / Sports",
        },
    ),

    # === PIZZA — CARRY-OUT ===
    "pizza_carryout": IndustryConfig(
        key="pizza_carryout",
        label="Pizza — Carry-Out",
        icon="📦",
        description="Carry-out and takeout pizza operations",
        group="pizza",
        markets=PIZZA_MARKETS,
        gdelt_queries=PIZZA_GDELT_QUERIES,
        rss_feeds=PIZZA_RSS_FEEDS,
        categories=PIZZA_CATEGORIES,
        category_labels={
            "weather": "Weather Impact",
            "holiday": "Holiday",
            "news": "News / Local Event",
            "competitor_promo": "Competitor Activity",
            "delivery_disruption": "Delivery Disruption",
            "food_safety": "Food Safety / Health",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Labor / Staffing",
            "local_event": "Local Event / Festival",
        },
    ),
}


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def get_industry(key: str) -> IndustryConfig:
    """Look up an industry by key. Raises KeyError if not found."""
    try:
        return INDUSTRIES[key]
    except KeyError:
        valid = ", ".join(INDUSTRIES.keys())
        raise KeyError(
            f"Unknown industry '{key}'. Valid options: {valid}"
        ) from None


def get_industry_groups() -> dict[str, list[IndustryConfig]]:
    """Group industries by their group key for UI display."""
    groups: dict[str, list[IndustryConfig]] = {}
    for config in INDUSTRIES.values():
        groups.setdefault(config.group, []).append(config)
    return groups


def get_all_markets(industry_key: str) -> list[Market]:
    """Return the list of markets for a given industry."""
    return get_industry(industry_key).markets


def get_gdelt_queries(industry_key: str) -> list[str]:
    """Return GDELT search queries for a given industry."""
    return get_industry(industry_key).gdelt_queries


def get_rss_feeds(industry_key: str) -> list[RSSFeed]:
    """Return RSS feeds for a given industry."""
    return get_industry(industry_key).rss_feeds
