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

# WMO Weather Code descriptions for human-readable weather summaries
_WMO_CODE_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
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
        """Convert raw Open-Meteo daily data into ImpactEvents.

        Produces TWO categories of events:
        1. daily_conditions → context event for EVERY day (enables LLM to
           reason about moderate weather that still impacts delivery/foot traffic)
        2. severe_weather → events that breach extreme thresholds
        """
        daily = data["daily"]
        events: list[ImpactEventCreate] = []

        dates = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        snow = daily.get("snowfall_sum", [])
        wind = daily.get("windspeed_10m_max", [])
        weather_codes = daily.get("weathercode", [])

        def _c_to_f(c: float | None) -> str:
            """Format a Celsius value as 'X°C / Y°F' string."""
            if c is None:
                return "N/A"
            return f"{c:.1f}°C / {(c * 9/5 + 32):.1f}°F"

        for i, date_str in enumerate(dates):
            t_max = temps_max[i] if i < len(temps_max) else None
            t_min = temps_min[i] if i < len(temps_min) else None
            precipitation = precip[i] if i < len(precip) else None
            snowfall = snow[i] if i < len(snow) else None
            windspeed = wind[i] if i < len(wind) else None
            wcode = weather_codes[i] if i < len(weather_codes) else None

            event_date = datetime.fromisoformat(date_str)
            weather_desc = _WMO_CODE_DESCRIPTIONS.get(wcode, "Unknown conditions") if wcode is not None else "Unknown conditions"

            # --------------- 1. DAILY CONDITIONS CONTEXT EVENT ---------------
            # Always emit — gives the LLM full weather context for every day.
            # Severity is softly graded: 0.1 (clear) to 0.6 (heavy precip/wind).
            base_severity = 0.1
            if snowfall is not None and snowfall >= 1:
                base_severity = min(0.6, 0.15 + snowfall / 30)
            elif precipitation is not None and precipitation >= 10:
                base_severity = min(0.5, 0.15 + precipitation / 150)
            elif windspeed is not None and windspeed >= 40:
                base_severity = min(0.4, 0.15 + windspeed / 200)
            elif t_min is not None and t_min < 0:
                base_severity = min(0.45, 0.15 + abs(t_min) / 30)

            context_desc = (
                f"Weather: {weather_desc}. "
                f"High: {_c_to_f(t_max)}, Low: {_c_to_f(t_min)}. "
                f"Precipitation: {precipitation:.1f}mm, Snow: {snowfall:.1f}cm, "
                f"Max Wind: {windspeed:.1f} km/h."
                if all(v is not None for v in [t_max, t_min, precipitation, snowfall, windspeed])
                else f"Weather: {weather_desc}."
            )

            events.append(ImpactEventCreate(
                source="open-meteo",
                source_id=f"open-meteo-daily-{date_str}-{latitude}-{longitude}",
                category="weather",
                subcategory="daily_conditions",
                title=f"Daily Weather: {weather_desc} — {date_str} ({geo_label})",
                description=context_desc,
                severity=self._clamp_severity(base_severity),
                confidence=0.9,
                start_date=event_date,
                end_date=event_date,
                latitude=latitude,
                longitude=longitude,
                geo_radius_km=15.0,
                geo_label=geo_label,
                industry=industry,
                raw_payload={
                    "temp_max_c": t_max,
                    "temp_max_f": round(t_max * 9/5 + 32, 1) if t_max is not None else None,
                    "temp_min_c": t_min,
                    "temp_min_f": round(t_min * 9/5 + 32, 1) if t_min is not None else None,
                    "precipitation_mm": precipitation,
                    "snowfall_cm": snowfall,
                    "windspeed_kmh": windspeed,
                    "weather_code": wcode,
                    "weather_description": weather_desc,
                },
            ))

            # --------------- 2. SEVERE WEATHER ALERT EVENTS -----------------
            # Only emit when conditions breach extreme business-impact thresholds.
            severe_events = self._detect_significant_weather(
                temp_max=t_max, temp_min=t_min, precipitation=precipitation,
                snowfall=snowfall, windspeed=windspeed, weather_code=wcode,
            )
            for weather_event in severe_events:
                events.append(ImpactEventCreate(
                    source="open-meteo",
                    source_id=f"open-meteo-{date_str}-{latitude}-{longitude}-{weather_event['type']}",
                    category="weather",
                    subcategory=weather_event["type"],
                    title=weather_event["title"],
                    description=weather_event["description"],
                    severity=weather_event["severity"],
                    confidence=0.85,
                    start_date=event_date,
                    end_date=event_date,
                    latitude=latitude,
                    longitude=longitude,
                    geo_radius_km=15.0,
                    geo_label=geo_label,
                    industry="all",
                    raw_payload={
                        "temp_max_c": t_max,
                        "temp_min_c": t_min,
                        "precipitation_mm": precipitation,
                        "snowfall_cm": snowfall,
                        "windspeed_kmh": windspeed,
                        "weather_code": wcode,
                    },
                ))

        significant_count = len([e for e in events if e.subcategory != "daily_conditions"])
        self.logger.info(
            "weather_events_detected",
            total_days=len(dates),
            daily_context_events=len(dates),
            significant_events=significant_count,
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
