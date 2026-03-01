"""
Unit Tests — Weather Adapter Detection Logic

Tests the _detect_significant_weather() method of OpenMeteoAdapter
in isolation. No HTTP calls — pure unit testing of the weather
detection algorithm and severity calculations.
"""

import pytest

from app.adapters.open_meteo import OpenMeteoAdapter


@pytest.fixture
def adapter():
    """Create an OpenMeteoAdapter instance for testing."""
    return OpenMeteoAdapter()


# ------------------------------------------------------------------ #
#  Extreme Cold Detection                                             #
# ------------------------------------------------------------------ #

class TestExtremeCold:
    """Test extreme cold weather detection."""

    def test_no_event_at_minus_5(self, adapter):
        """Temperatures above -10°C should NOT trigger an event."""
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-5, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        assert len(events) == 0

    def test_event_at_minus_10(self, adapter):
        """Exactly -10°C should trigger extreme cold."""
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-10, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        assert len(events) == 1
        assert events[0]["type"] == "extreme_cold"

    def test_event_at_minus_30(self, adapter):
        """Very cold temps should produce higher severity."""
        events = adapter._detect_significant_weather(
            temp_max=-15, temp_min=-30, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        cold_event = events[0]
        assert cold_event["severity"] > 0.8

    def test_severity_increases_with_colder_temps(self, adapter):
        mild = adapter._detect_significant_weather(
            temp_max=0, temp_min=-12, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        extreme = adapter._detect_significant_weather(
            temp_max=-10, temp_min=-35, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        assert extreme[0]["severity"] > mild[0]["severity"]


# ------------------------------------------------------------------ #
#  Extreme Heat Detection                                             #
# ------------------------------------------------------------------ #

class TestExtremeHeat:

    def test_no_event_at_35c(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=35, temp_min=20, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        assert len(events) == 0

    def test_event_at_38c(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=38, temp_min=25, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        assert any(e["type"] == "extreme_heat" for e in events)

    def test_event_at_45c(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=45, temp_min=30, precipitation=0,
            snowfall=0, windspeed=10, weather_code=0,
        )
        heat = [e for e in events if e["type"] == "extreme_heat"][0]
        assert heat["severity"] > 0.6


# ------------------------------------------------------------------ #
#  Snowfall Detection                                                 #
# ------------------------------------------------------------------ #

class TestSnowfall:

    def test_no_event_at_5cm(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-5, precipitation=5,
            snowfall=5, windspeed=10, weather_code=0,
        )
        assert len(events) == 0

    def test_heavy_snow_at_15cm(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-5, precipitation=15,
            snowfall=15, windspeed=10, weather_code=0,
        )
        snow_events = [e for e in events if "snow" in e["type"]]
        assert len(snow_events) == 1
        assert snow_events[0]["type"] == "heavy_snow"

    def test_blizzard_at_35cm(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-10, precipitation=35,
            snowfall=35, windspeed=50, weather_code=0,
        )
        blizzard = [e for e in events if e["type"] == "blizzard"]
        assert len(blizzard) == 1
        assert blizzard[0]["severity"] >= 0.9

    def test_boundary_at_10cm(self, adapter):
        """Exactly 10cm should trigger heavy_snow."""
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-5, precipitation=10,
            snowfall=10, windspeed=10, weather_code=0,
        )
        assert any(e["type"] == "heavy_snow" for e in events)


# ------------------------------------------------------------------ #
#  Heavy Rain Detection                                               #
# ------------------------------------------------------------------ #

class TestHeavyRain:

    def test_no_event_at_30mm(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=15, precipitation=30,
            snowfall=0, windspeed=10, weather_code=0,
        )
        assert len(events) == 0

    def test_heavy_rain_at_50mm(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=15, precipitation=50,
            snowfall=0, windspeed=10, weather_code=0,
        )
        rain = [e for e in events if "rain" in e["type"]]
        assert len(rain) == 1
        assert rain[0]["type"] == "heavy_rain"

    def test_extreme_rain_at_90mm(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=15, precipitation=90,
            snowfall=0, windspeed=10, weather_code=0,
        )
        rain = [e for e in events if "rain" in e["type"]]
        assert len(rain) == 1
        assert rain[0]["type"] == "extreme_rain"

    def test_rain_minus_snow_calculation(self, adapter):
        """Rain that is actually snow should not count as rain."""
        events = adapter._detect_significant_weather(
            temp_max=0, temp_min=-5, precipitation=50,
            snowfall=50, windspeed=10, weather_code=0,
        )
        rain_events = [e for e in events if "rain" in e["type"]]
        assert len(rain_events) == 0  # All precip was snow


# ------------------------------------------------------------------ #
#  High Wind Detection                                                #
# ------------------------------------------------------------------ #

class TestHighWind:

    def test_no_event_at_60kmh(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=10, precipitation=0,
            snowfall=0, windspeed=60, weather_code=0,
        )
        assert len(events) == 0

    def test_event_at_70kmh(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=10, precipitation=0,
            snowfall=0, windspeed=70, weather_code=0,
        )
        assert any(e["type"] == "high_wind" for e in events)

    def test_event_at_120kmh(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=10, precipitation=0,
            snowfall=0, windspeed=120, weather_code=0,
        )
        wind = [e for e in events if e["type"] == "high_wind"][0]
        assert wind["severity"] > 0.7


# ------------------------------------------------------------------ #
#  Multi-Event Detection                                              #
# ------------------------------------------------------------------ #

class TestMultiEvent:
    """Test that multiple weather anomalies in one day are detected."""

    def test_blizzard_plus_cold(self, adapter):
        """A blizzard day should produce both blizzard AND extreme cold events."""
        events = adapter._detect_significant_weather(
            temp_max=-10, temp_min=-25, precipitation=35,
            snowfall=35, windspeed=50, weather_code=0,
        )
        types = {e["type"] for e in events}
        assert "blizzard" in types
        assert "extreme_cold" in types

    def test_rain_plus_wind(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=25, temp_min=18, precipitation=60,
            snowfall=0, windspeed=90, weather_code=0,
        )
        types = {e["type"] for e in events}
        assert "heavy_rain" in types
        assert "high_wind" in types


# ------------------------------------------------------------------ #
#  Null/None Handling                                                 #
# ------------------------------------------------------------------ #

class TestNullHandling:
    """Test graceful handling of missing weather data."""

    def test_all_none_returns_empty(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=None, temp_min=None, precipitation=None,
            snowfall=None, windspeed=None, weather_code=None,
        )
        assert events == []

    def test_partial_none_does_not_crash(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=None, temp_min=-15, precipitation=None,
            snowfall=None, windspeed=None, weather_code=None,
        )
        assert len(events) == 1
        assert events[0]["type"] == "extreme_cold"

    def test_rain_none_snowfall_none_no_rain_event(self, adapter):
        """If both precipitation and snowfall are None, no rain check."""
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=10, precipitation=None,
            snowfall=None, windspeed=10, weather_code=0,
        )
        rain_events = [e for e in events if "rain" in e.get("type", "")]
        assert len(rain_events) == 0


# ------------------------------------------------------------------ #
#  Severity Clamping                                                  #
# ------------------------------------------------------------------ #

class TestSeverityClamping:
    """Verify severity values are always clamped to [0, 1]."""

    def test_extreme_cold_clamped_to_one(self, adapter):
        """Even with -100°C, severity should not exceed 1.0."""
        events = adapter._detect_significant_weather(
            temp_max=-50, temp_min=-100, precipitation=0,
            snowfall=0, windspeed=0, weather_code=0,
        )
        assert events[0]["severity"] <= 1.0

    def test_extreme_wind_clamped_to_one(self, adapter):
        events = adapter._detect_significant_weather(
            temp_max=20, temp_min=10, precipitation=0,
            snowfall=0, windspeed=500, weather_code=0,
        )
        assert events[0]["severity"] <= 1.0
