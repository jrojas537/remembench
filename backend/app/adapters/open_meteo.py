"""
Remembench — Open-Meteo Historical Weather Adapter

Free, open-source weather API with 80+ years of hourly data at
1-10km resolution using ERA5 reanalysis models. No API key needed.

Weather events are industry-universal — extreme cold, heavy snow/rain,
and high winds impact foot traffic and delivery operations across
all verticals (retail, restaurants, etc.)

Docs: https://open-meteo.com/en/docs/historical-weather-api
"""

from datetime import datetime

from app.adapters.base import BaseAdapter
from app.config import settings
from app.schemas import ImpactEventCreate

# Weather severity thresholds.
# These represent conditions significant enough to impact business
# operations — both retail foot traffic and delivery services.
_WEATHER_SEVERITY_THRESHOLDS = {
    "extreme_cold": {"temp_max_c": -10, "severity": 0.8},
    "extreme_heat": {"temp_max_c": 40, "severity": 0.7},
    "heavy_snow": {"snowfall_cm": 15, "severity": 0.9},
    "blizzard": {"snowfall_cm": 30, "severity": 1.0},
    "heavy_rain": {"precipitation_mm": 50, "severity": 0.6},
    "extreme_rain": {"precipitation_mm": 100, "severity": 0.85},
    "high_wind": {"windspeed_kmh": 80, "severity": 0.7},
}


class OpenMeteoAdapter(BaseAdapter):
    """Adapter for Open-Meteo Historical Weather API."""

    def __init__(self) -> None:
        super().__init__("open-meteo")
        self.base_url = settings.open_meteo_base_url

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
        Fetch daily weather data and detect significant weather events
        that could impact business operations.

        Weather is industry-universal: a blizzard impacts both wireless
        stores and pizza delivery equally.
        """
        if latitude is None or longitude is None:
            self.logger.warning("skipping_fetch", reason="No coordinates provided")
            return []

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "snowfall_sum",
                "windspeed_10m_max",
                "weathercode",
            ]),
            "temperature_unit": "celsius",
            "windspeed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
        }

        data = await self._http_get(self.base_url, params=params)

        if not isinstance(data, dict) or "daily" not in data:
            self.logger.error("unexpected_response", data_type=type(data).__name__)
            return []

        return self._normalize(data, latitude, longitude, geo_label, industry)

    def _normalize(
        self,
        data: dict,
        latitude: float,
        longitude: float,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """Convert raw Open-Meteo daily data into ImpactEvents for significant weather days."""
        daily = data["daily"]
        events: list[ImpactEventCreate] = []

        dates = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        snow = daily.get("snowfall_sum", [])
        wind = daily.get("windspeed_10m_max", [])
        weather_codes = daily.get("weathercode", [])

        for i, date_str in enumerate(dates):
            weather_events = self._detect_significant_weather(
                temp_max=temps_max[i] if i < len(temps_max) else None,
                temp_min=temps_min[i] if i < len(temps_min) else None,
                precipitation=precip[i] if i < len(precip) else None,
                snowfall=snow[i] if i < len(snow) else None,
                windspeed=wind[i] if i < len(wind) else None,
                weather_code=weather_codes[i] if i < len(weather_codes) else None,
            )

            for weather_event in weather_events:
                event_date = datetime.fromisoformat(date_str)
                events.append(ImpactEventCreate(
                    source="open-meteo",
                    source_id=f"open-meteo-{date_str}-{latitude}-{longitude}-{weather_event['type']}",
                    category="weather",
                    subcategory=weather_event["type"],
                    title=weather_event["title"],
                    description=weather_event["description"],
                    severity=weather_event["severity"],
                    confidence=0.85,  # Reanalysis data: reliable but not station-level
                    start_date=event_date,
                    end_date=event_date,
                    latitude=latitude,
                    longitude=longitude,
                    geo_radius_km=15.0,  # ~10km grid resolution
                    geo_label=geo_label,
                    industry=industry,
                    raw_payload={
                        "temp_max": temps_max[i] if i < len(temps_max) else None,
                        "temp_min": temps_min[i] if i < len(temps_min) else None,
                        "precipitation_mm": precip[i] if i < len(precip) else None,
                        "snowfall_cm": snow[i] if i < len(snow) else None,
                        "windspeed_kmh": wind[i] if i < len(wind) else None,
                        "weather_code": weather_codes[i] if i < len(weather_codes) else None,
                    },
                ))

        self.logger.info(
            "weather_events_detected",
            total_days=len(dates),
            significant_days=len(events),
            geo_label=geo_label,
            industry=industry,
        )
        return events

    def _detect_significant_weather(
        self,
        temp_max: float | None,
        temp_min: float | None,
        precipitation: float | None,
        snowfall: float | None,
        windspeed: float | None,
        weather_code: int | None,
    ) -> list[dict]:
        """
        Detect weather conditions significant enough to impact business.

        Returns a list of event dicts, each with type, title,
        description, and severity score.
        """
        events: list[dict] = []

        # --- Extreme Cold ---
        if temp_min is not None and temp_min <= -10:
            events.append({
                "type": "extreme_cold",
                "title": f"Extreme Cold: {temp_min:.0f}°C low",
                "description": (
                    f"Minimum temperature dropped to {temp_min:.1f}°C. "
                    f"Significantly reduces foot traffic and may impact delivery operations."
                ),
                "severity": self._clamp_severity(0.5 + abs(temp_min) / 40),
            })

        # --- Extreme Heat ---
        if temp_max is not None and temp_max >= 38:
            events.append({
                "type": "extreme_heat",
                "title": f"Extreme Heat: {temp_max:.0f}°C high",
                "description": (
                    f"Maximum temperature reached {temp_max:.1f}°C. "
                    f"Potentially reduces foot traffic and outdoor activity."
                ),
                "severity": self._clamp_severity(0.4 + (temp_max - 35) / 15),
            })

        # --- Heavy Snowfall ---
        if snowfall is not None and snowfall >= 10:
            severity = 0.9 if snowfall >= 30 else 0.7 if snowfall >= 20 else 0.55
            label = "Blizzard" if snowfall >= 30 else "Heavy Snow"
            events.append({
                "type": "blizzard" if snowfall >= 30 else "heavy_snow",
                "title": f"{label}: {snowfall:.1f}cm",
                "description": (
                    f"{snowfall:.1f}cm of snowfall recorded. "
                    f"{'Major travel disruption — roads, delivery, and foot traffic severely impacted.' if snowfall >= 30 else 'Significant reduction in foot traffic and delivery times likely.'}"
                ),
                "severity": self._clamp_severity(severity),
            })

        # --- Heavy Rain ---
        if precipitation is not None and snowfall is not None:
            rain_only = max(0, precipitation - snowfall)
            if rain_only >= 40:
                events.append({
                    "type": "heavy_rain" if rain_only < 80 else "extreme_rain",
                    "title": f"Heavy Rainfall: {rain_only:.1f}mm",
                    "description": (
                        f"{rain_only:.1f}mm of rainfall. "
                        f"Potential flooding, reduced foot traffic, and delivery delays."
                    ),
                    "severity": self._clamp_severity(0.4 + rain_only / 200),
                })

        # --- High Wind ---
        if windspeed is not None and windspeed >= 70:
            events.append({
                "type": "high_wind",
                "title": f"High Wind: {windspeed:.0f} km/h",
                "description": (
                    f"Wind speeds reached {windspeed:.1f} km/h. "
                    f"Safety concerns, potential property damage, and reduced foot traffic."
                ),
                "severity": self._clamp_severity(0.4 + windspeed / 200),
            })

        return events
