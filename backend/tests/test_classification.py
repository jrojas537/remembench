"""
Unit Tests — GDELT & RSS Classification Logic

Tests the article/entry classification methods that categorize
news and events into our taxonomy. Industry-aware classification
is the key differentiator of these adapters.
"""

import pytest

from app.adapters.gdelt import GdeltAdapter
from app.adapters.carrier_rss import IndustryRssAdapter


# ------------------------------------------------------------------ #
#  GDELT Article Classification                                       #
# ------------------------------------------------------------------ #

class TestGdeltClassification:
    """Test GdeltAdapter._classify_article for industry-aware classification."""

    @pytest.fixture
    def adapter(self):
        return GdeltAdapter()

    # --- Wireless Industry ---

    def test_wireless_outage_detected(self, adapter):
        cat, sub = adapter._classify_article(
            "Major network outage hits millions", "wireless_retail"
        )
        assert cat == "outage"

    def test_wireless_promo_detected(self, adapter):
        cat, sub = adapter._classify_article(
            "Verizon launches new unlimited plan promotion", "wireless_retail"
        )
        assert cat == "competitor_promo"

    def test_wireless_generic_news(self, adapter):
        cat, sub = adapter._classify_article(
            "Technology industry sees growth in 2025", "wireless_retail"
        )
        assert cat == "news"

    # --- Pizza Industry ---

    def test_pizza_food_safety_recall(self, adapter):
        cat, sub = adapter._classify_article(
            "FDA issues food recall for cheese contamination", "pizza_full_service"
        )
        assert cat == "food_safety"

    def test_pizza_delivery_disruption(self, adapter):
        cat, sub = adapter._classify_article(
            "DoorDash suffers service outage during peak hours", "pizza_delivery"
        )
        assert cat in ("delivery_disruption", "outage")

    def test_pizza_supply_chain(self, adapter):
        cat, sub = adapter._classify_article(
            "Flour prices surge due to wheat shortage", "pizza_full_service"
        )
        assert cat in ("supply_chain", "news")

    def test_pizza_labor(self, adapter):
        cat, sub = adapter._classify_article(
            "Minimum wage increase takes effect", "pizza_bar"
        )
        assert cat in ("labor", "news")

    def test_pizza_competitor(self, adapter):
        cat, sub = adapter._classify_article(
            "Dominos launches 50% off promotion nationwide", "pizza_carryout"
        )
        assert cat in ["competitor_promo", "pizza_promotions"]


# ------------------------------------------------------------------ #
#  GDELT Severity Estimation                                          #
# ------------------------------------------------------------------ #

class TestGdeltSeverity:
    """Test GdeltAdapter._estimate_severity."""

    @pytest.fixture
    def adapter(self):
        return GdeltAdapter()

    def test_very_negative_tone_high_severity(self, adapter):
        severity = adapter._estimate_severity(-15.0, "major crisis forces closures")
        assert severity > 0.7

    def test_neutral_tone_low_severity(self, adapter):
        severity = adapter._estimate_severity(0.0, "business as usual")
        assert severity < 0.5

    def test_positive_tone_low_severity(self, adapter):
        severity = adapter._estimate_severity(5.0, "market growth continues")
        assert severity < 0.4

    def test_severity_always_clamped(self, adapter):
        severity = adapter._estimate_severity(-100.0, "catastrophe")
        assert 0.0 <= severity <= 1.0


# ------------------------------------------------------------------ #
#  RSS Classification                                                 #
# ------------------------------------------------------------------ #

class TestRSSClassification:
    """Test IndustryRssAdapter._classify_entry for industry-aware classification."""

    @pytest.fixture
    def adapter(self):
        return IndustryRssAdapter()

    # --- Wireless Industry ---

    def test_wireless_promotion(self, adapter):
        cat, sub = adapter._classify_entry(
            "New Buy One Get One deal on iPhones",
            "Limited time offer for new customers",
            "wireless_retail",
        )
        assert cat == "competitor_promo"

    def test_wireless_carrier_news(self, adapter):
        cat, sub = adapter._classify_entry(
            "5G expansion reaches rural areas",
            "Coverage improvements across the midwest",
            "wireless_retail",
        )
        assert cat is None

    # --- Pizza Industry ---

    def test_pizza_food_safety(self, adapter):
        cat, sub = adapter._classify_entry(
            "FDA recalls mozzarella due to listeria contamination",
            "Multiple brands affected by the recall",
            "pizza_full_service",
        )
        assert cat == "food_safety"

    def test_pizza_supply_chain(self, adapter):
        cat, sub = adapter._classify_entry(
            "Cheese prices surge amid supply chain disruption",
            "Dairy costs up 15% month over month",
            "pizza_delivery",
        )
        assert cat == "supply_chain"

    def test_pizza_competitor_promo(self, adapter):
        cat, sub = adapter._classify_entry(
            "Domino's launches new discount promotion",
            "50% off all online orders this weekend",
            "pizza_carryout",
        )
        assert cat in ["competitor_promo", "pizza_promotions"]

    def test_pizza_generic_news(self, adapter):
        cat, sub = adapter._classify_entry(
            "Pizza industry trends in 2025",
            "Growth in delivery and digital ordering",
            "pizza_bar",
        )
        assert cat == "news"


# ------------------------------------------------------------------ #
#  RSS Severity Estimation                                            #
# ------------------------------------------------------------------ #

class TestRSSSeverity:
    """Test IndustryRssAdapter._estimate_severity."""

    @pytest.fixture
    def adapter(self):
        return IndustryRssAdapter()

    def test_promo_keywords_increase_severity(self, adapter):
        severity = adapter._estimate_severity(
            "Massive BOGO deal on all phones",
            "Buy one get one free, limited time only",
            "wireless_retail",
            "verizon-newsroom",
        )
        assert severity > 0.4

    def test_recall_high_severity(self, adapter):
        severity = adapter._estimate_severity(
            "Emergency recall of contaminated ingredients",
            "FDA warning to restaurants nationwide",
            "pizza_full_service",
            "pmq-feed",
        )
        assert severity > 0.5

    def test_mild_news_low_severity(self, adapter):
        severity = adapter._estimate_severity(
            "Industry conference scheduled for Q3",
            "Annual event to be held in Atlanta",
            "wireless_retail",
            "generic-news",
        )
        assert severity < 0.6
