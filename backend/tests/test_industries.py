"""
Unit Tests — Industry Registry

Tests the centralized industry configuration that drives the
entire multi-industry platform. Exercises the registry, helpers,
and market/category definitions.
"""

import pytest

from app.industries import (
    INDUSTRIES,
    Market,
    IndustryConfig,
    RSSFeed,
    get_industry,
    get_industry_groups,
    get_all_markets,
    get_gdelt_queries,
    get_rss_feeds,
    WIRELESS_MARKETS,
    PIZZA_MARKETS,
    WIRELESS_CATEGORIES,
    PIZZA_CATEGORIES,
    UNIVERSAL_CATEGORIES,
)


# ------------------------------------------------------------------ #
#  Registry Existence & Structure                                     #
# ------------------------------------------------------------------ #

class TestIndustryRegistry:
    """Verify the industry registry is complete and well-formed."""

    def test_registry_has_five_industries(self):
        assert len(INDUSTRIES) == 5

    def test_all_expected_keys_present(self):
        expected = {
            "wireless_retail", "pizza_full_service", "pizza_delivery",
            "pizza_bar", "pizza_carryout",
        }
        assert set(INDUSTRIES.keys()) == expected

    def test_each_industry_is_industry_config(self):
        for key, config in INDUSTRIES.items():
            assert isinstance(config, IndustryConfig), f"{key} is not IndustryConfig"

    def test_key_matches_config_key_field(self):
        """Registry dict key must match the config's own .key field."""
        for key, config in INDUSTRIES.items():
            assert config.key == key, f"Mismatch: dict key={key}, config.key={config.key}"

    def test_every_industry_has_markets(self):
        for key, config in INDUSTRIES.items():
            assert len(config.markets) > 0, f"{key} has no markets"

    def test_every_industry_has_gdelt_queries(self):
        for key, config in INDUSTRIES.items():
            assert len(config.gdelt_queries) > 0, f"{key} has no GDELT queries"

    def test_every_industry_has_rss_feeds(self):
        for key, config in INDUSTRIES.items():
            assert len(config.rss_feeds) > 0, f"{key} has no RSS feeds"

    def test_every_industry_has_categories(self):
        for key, config in INDUSTRIES.items():
            assert len(config.categories) >= 3, f"{key} has too few categories"

    def test_universal_categories_in_all_industries(self):
        """Weather, holiday, and news should be in every industry."""
        for key, config in INDUSTRIES.items():
            for cat in UNIVERSAL_CATEGORIES:
                assert cat in config.categories, f"{cat} missing from {key}"

    def test_wireless_has_outage_category(self):
        assert "outage" in INDUSTRIES["wireless_retail"].categories

    def test_pizza_has_food_safety_category(self):
        for key in ("pizza_full_service", "pizza_delivery", "pizza_bar", "pizza_carryout"):
            assert "food_safety" in INDUSTRIES[key].categories

    def test_pizza_has_delivery_disruption_category(self):
        for key in ("pizza_full_service", "pizza_delivery", "pizza_bar", "pizza_carryout"):
            assert "delivery_disruption" in INDUSTRIES[key].categories


# ------------------------------------------------------------------ #
#  Market Definitions                                                 #
# ------------------------------------------------------------------ #

class TestMarkets:
    """Verify market definitions."""

    def test_wireless_has_ten_markets(self):
        assert len(WIRELESS_MARKETS) == 10

    def test_pizza_has_ten_markets(self):
        assert len(PIZZA_MARKETS) == 10

    def test_all_markets_are_market_objects(self):
        for m in WIRELESS_MARKETS + PIZZA_MARKETS:
            assert isinstance(m, Market)

    def test_markets_have_valid_coordinates(self):
        for m in WIRELESS_MARKETS + PIZZA_MARKETS:
            assert -90 <= m.latitude <= 90, f"{m.geo_label} bad lat"
            assert -180 <= m.longitude <= 180, f"{m.geo_label} bad lon"

    def test_detroit_in_pizza_markets(self):
        labels = [m.geo_label for m in PIZZA_MARKETS]
        assert "Detroit" in labels

    def test_nyc_in_wireless_markets(self):
        labels = [m.geo_label for m in WIRELESS_MARKETS]
        assert "New York City" in labels

    def test_no_duplicate_market_labels(self):
        for markets in (WIRELESS_MARKETS, PIZZA_MARKETS):
            labels = [m.geo_label for m in markets]
            assert len(labels) == len(set(labels)), "Duplicate market labels"


# ------------------------------------------------------------------ #
#  RSS Feeds                                                          #
# ------------------------------------------------------------------ #

class TestRSSFeeds:
    """Verify RSS feed definitions."""

    def test_wireless_feeds_have_urls(self):
        config = INDUSTRIES["wireless_retail"]
        for feed in config.rss_feeds:
            assert isinstance(feed, RSSFeed)
            assert feed.url.startswith("http")

    def test_pizza_feeds_have_urls(self):
        config = INDUSTRIES["pizza_full_service"]
        for feed in config.rss_feeds:
            assert isinstance(feed, RSSFeed)
            assert feed.url.startswith("http")


# ------------------------------------------------------------------ #
#  Helper Functions                                                   #
# ------------------------------------------------------------------ #

class TestHelpers:
    """Test the industry registry helper functions."""

    def test_get_industry_valid(self):
        config = get_industry("wireless_retail")
        assert config.label == "Wireless Retail"

    def test_get_industry_invalid_raises_keyerror(self):
        with pytest.raises(KeyError, match="Unknown industry"):
            get_industry("nonexistent_industry")

    def test_get_industry_groups(self):
        groups = get_industry_groups()
        assert "wireless" in groups
        assert "pizza" in groups
        assert len(groups["wireless"]) == 1
        assert len(groups["pizza"]) == 4

    def test_get_all_markets(self):
        markets = get_all_markets("pizza_full_service")
        assert len(markets) == 10
        assert all(isinstance(m, Market) for m in markets)

    def test_get_gdelt_queries(self):
        queries = get_gdelt_queries("wireless_retail")
        assert len(queries) > 0
        assert all(isinstance(q, str) for q in queries)

    def test_get_rss_feeds(self):
        feeds = get_rss_feeds("pizza_delivery")
        assert len(feeds) > 0
        assert all(isinstance(f, RSSFeed) for f in feeds)


# ------------------------------------------------------------------ #
#  Group / Label Consistency                                          #
# ------------------------------------------------------------------ #

class TestGroupConsistency:
    """Verify industry grouping and labeling."""

    def test_wireless_group_is_wireless(self):
        assert INDUSTRIES["wireless_retail"].group == "wireless"

    def test_all_pizza_industries_share_group(self):
        for key in ("pizza_full_service", "pizza_delivery", "pizza_bar", "pizza_carryout"):
            assert INDUSTRIES[key].group == "pizza"

    def test_every_industry_has_icon(self):
        for key, config in INDUSTRIES.items():
            assert len(config.icon) > 0, f"{key} has no icon"

    def test_every_industry_has_description(self):
        for key, config in INDUSTRIES.items():
            assert len(config.description) > 5, f"{key} has short description"

    def test_category_labels_match_categories(self):
        """Every category in the list should have a friendly label."""
        for key, config in INDUSTRIES.items():
            for cat in config.categories:
                assert cat in config.category_labels, (
                    f"{key}: category '{cat}' missing from category_labels"
                )
