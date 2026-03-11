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

from datetime import datetime
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
    classification_prompt_addition: str = ""  # Extra instructions for the LLM during classification


# ---------------------------------------------------------------------------
#  Market Definitions
# ---------------------------------------------------------------------------

CAR_WASH_MARKETS = [
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

CAR_WASH_GDELT_QUERIES = [
    '"car wash" (promotion OR deal OR opening OR discount)',
    '("Mister Car Wash" OR "Tommy\'s" OR "El Car Wash" OR "Jax Kar Wash" OR "Clean Express" OR "Zax Autowash") (acquisition OR opening OR promotion OR deal OR discount OR membership)',
    'weather (pollen OR dust OR mud OR snow OR "saharan dust")',
    '"water restrictions" OR "drought" OR "climate"',
]

PIZZA_GDELT_QUERIES = [
    '"pizza restaurant" OR "pizzeria" OR "pizza shop" (promotion OR deal OR coupon)',
    '"food delivery" OR "DoorDash" OR "Uber Eats" OR "Grubhub" (fees OR disruption OR strike)',
    '"food safety" OR "health inspection" OR "food recall" OR "restaurant inspection"',
    '"restaurant closure" OR "dining shutdown" OR "restaurant shutdown"',
    "protest OR demonstration OR road closure OR parade OR concert OR festival",
    "sports OR game OR tournament OR marathon OR stadium",
    '"minimum wage" OR "labor shortage" OR "restaurant workers"',
    '"cheese prices" OR "flour prices" OR "food costs" OR "ingredient prices"',
    '("Jet\'s Pizza" OR "Pizza Hut" OR "Papa Johns" OR "Dominos" OR "Buddy\'s") (promotion OR discount OR launch)',
]


# ---------------------------------------------------------------------------
#  RSS Feed Sets
# ---------------------------------------------------------------------------

CAR_WASH_RSS_FEEDS = [
    RSSFeed(
        url="https://www.carwash.com/feed/",
        label="Professional Carwashing & Detailing",
        source_key="carwash_com",
    ),
    RSSFeed(
        url="https://carwash.org/feed",
        label="International Carwash Association",
        source_key="ica",
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
    "weather", "holiday", "news", "sports", "local_event",
]

CAR_WASH_CATEGORIES = UNIVERSAL_CATEGORIES + [
    "competitor_promo", "outage", "supply_chain", "regulatory",
]

PIZZA_CATEGORIES = UNIVERSAL_CATEGORIES + [
    "pizza_promotions", "delivery_disruption", "food_safety",
    "supply_chain", "labor",
]


# ---------------------------------------------------------------------------
#  Industry Registry
# ---------------------------------------------------------------------------

INDUSTRIES: dict[str, IndustryConfig] = {
    # === CAR WASH ===
    "car_wash": IndustryConfig(
        key="car_wash",
        label="Car Wash",
        icon="🚗",
        description="Automated and full-service car wash operations",
        group="car_wash",
        markets=CAR_WASH_MARKETS,
        gdelt_queries=CAR_WASH_GDELT_QUERIES,
        rss_feeds=CAR_WASH_RSS_FEEDS,
        categories=CAR_WASH_CATEGORIES,
        category_labels={
            "weather": "Weather Impact (Rain/Snow/Pollen)",
            "holiday": "Holiday Weekend",
            "news": "Local News / Traffic",
            "competitor_promo": "Competitor Promo",
            "outage": "Equipment Failure / Disruption",
            "supply_chain": "Supply Chain (Chemicals)",
            "regulatory": "Water Restrictions",
            "local_event": "Local Event",
            "sports": "Sports",
        },
        classification_prompt_addition="Be extraordinarily vigilant checking for the following competitor brands: Mister Car Wash, Tommy's Express, El Car Wash, Jax Kar Wash, Clean Express, and Zax Autowash. If they are expanding, offering promotions, or undergoing acquisitions, mark it with HIGH severity.",
    ),

    # === PIZZA (ALL) ===
    "pizza_all": IndustryConfig(
        key="pizza_all",
        label="Pizza (ALL)",
        icon="🍕",
        description="All pizza operations combined",
        group="pizza",
        markets=PIZZA_MARKETS,
        gdelt_queries=PIZZA_GDELT_QUERIES,
        rss_feeds=PIZZA_RSS_FEEDS,
        categories=PIZZA_CATEGORIES,
        category_labels={
            "weather": "Weather Impact",
            "holiday": "Holiday",
            "news": "News / Local Event",
            "pizza_promotions": "Competitor Activity",
            "delivery_disruption": "Delivery Disruption",
            "food_safety": "Food Safety / Health",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Labor / Staffing",
            "local_event": "Local Event / Festival",
            "sports": "Sports / Game",
        },
        classification_prompt_addition="Be extraordinarily vigilant checking for the following competitor brands: Domino's, Jet's Pizza, Pizza Hut, Papa Johns, and Buddy's Pizza. If they are aggressively promoting discounts, deals, or BOGO offers, or announcing major events, mark it with HIGH severity and ensure it is classified as pizza_promotions.",
    ),

    # === PIZZA — FULL SERVICE ===
    "pizza_full_service": IndustryConfig(
        key="pizza_full_service",
        label="Pizza — Full Service",
        icon="🍽️",
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
            "pizza_promotions": "Competitor Activity",
            "delivery_disruption": "Delivery Disruption",
            "food_safety": "Food Safety / Health",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Labor / Staffing",
            "local_event": "Local Event / Festival",
            "sports": "Sports / Game",
        },
        classification_prompt_addition="Be extraordinarily vigilant checking for the following competitor brands: Domino's, Jet's Pizza, Pizza Hut, Papa Johns, and Buddy's Pizza. If they are aggressively promoting discounts, deals, or BOGO offers, or announcing major events, mark it with HIGH severity and ensure it is classified as pizza_promotions.",
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
            "pizza_promotions": "Competitor Activity",
            "delivery_disruption": "Delivery Platform Disruption",
            "food_safety": "Food Safety / Health",
            "supply_chain": "Supply Chain / Costs",
            "labor": "Driver / Labor Shortage",
            "local_event": "Local Event / Festival",
            "sports": "Sports / Game",
        },
        classification_prompt_addition="Be extraordinarily vigilant checking for the following competitor brands: Domino's, Jet's Pizza, Pizza Hut, Papa Johns, and Buddy's Pizza. If they are aggressively promoting discounts, deals, or BOGO offers, or announcing major events, mark it with HIGH severity and ensure it is classified as pizza_promotions.",
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


def get_related_industry_keys(industry_key: str) -> list[str]:
    """Return a list of industry keys for the given industry.
    If it's an '_all' key, return all keys in its group.
    If it's a specific child key, also include the parent '_all' key."""
    try:
        config = get_industry(industry_key)
        if industry_key.endswith("_all"):
            return [k for k, v in INDUSTRIES.items() if v.group == config.group]
            
        parent_all = f"{config.group}_all"
        if parent_all in INDUSTRIES and parent_all != industry_key:
            return [industry_key, parent_all]
            
        return [industry_key]
    except KeyError:
        return [industry_key]


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


def get_web_search_query(industry_key: str, start_date: datetime, end_date: datetime) -> str:
    """
    Constructs targeted Boolean search strings for external web crawlers (Tavily/Exa).
    
    Contains explicit algorithmic overrides for the 'pizza' vertical. If the search window
    intersects with historically massive pizza consumption peaks (Halloween, Super Bowl, etc.),
    it automatically injects exact-match string literals into the query forcing the web 
    scrapers to hunt for localized holiday promotions natively!
    """
    if industry_key.startswith("pizza"):
        base_pizza_query = '("Dominos" OR "Jet\'s Pizza" OR "Pizza Hut" OR "Papa Johns" OR "Buddy\'s Pizza" OR "pizza") (promotion OR discount OR deal OR coupon OR BOGO OR offer OR "sporting event" OR sports OR game OR playoffs OR tournament)'
        
        event_prompts = []
        if start_date.month == 1 or end_date.month == 1:
            event_prompts.append('"New Year\'s Day"')
        if start_date.month == 2 or end_date.month == 2:
            event_prompts.append('"Super Bowl"')
        if start_date.month == 3 or end_date.month == 3:
            event_prompts.append('("Pi Day" OR "3.14" OR "March Madness")')
        if start_date.month == 10 or end_date.month == 10:
            event_prompts.append('"Halloween"')
        if start_date.month == 11 or end_date.month == 11:
            event_prompts.append('"Thanksgiving Eve"')
        if start_date.month == 12 or end_date.month == 12:
            event_prompts.append('"New Year\'s Eve"')
            
        if event_prompts:
            events_str = " OR ".join(event_prompts)
            return f'{base_pizza_query} OR {events_str}'
            
        return base_pizza_query
        
    if industry_key.startswith("car_wash"):
        return '("car wash" OR "Mister Car Wash" OR "Tommy\'s" OR "El Car Wash" OR "Jax Kar Wash" OR "Clean Express" OR "Zax Autowash") (promotion OR discount OR opening OR "free wash" OR membership OR expansion OR deal OR acquisition)'
    
    # Generic fallback
    label = get_industry(industry_key).label
    return f'{label.replace(" ", " ")} AND (news OR event OR promotion OR disruption)'

