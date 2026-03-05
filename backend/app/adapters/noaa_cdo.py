"""
Remembench — NOAA Climate Data Online (CDO) Adapter

Free US government weather data. Provides station-level ground truth
used to cross-validate Open-Meteo reanalysis data. Higher accuracy
but requires an API token.

Weather events are industry-universal — extreme conditions impact
foot traffic and operations across all verticals.

Docs: https://www.ncei.noaa.gov/cdo-web/
API:  https://www.ncei.noaa.gov/access/services/data/v1
"""

from datetime import datetime
from typing import Any

from app.adapters.base import BaseAdapter
from app.config import settings
from app.schemas import ImpactEventCreate


class NoaaCdoAdapter(BaseAdapter):
    """Adapter for NOAA Climate Data Online API (ground truth validation)."""

    def __init__(self) -> None:
        super().__init__("noaa-cdo")
        self.base_url = "https://www.ncei.noaa.gov/access/services/data/v1"
        self.token = settings.noaa_cdo_token

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
        Fetch daily summaries from NOAA's GHCND dataset
        and flag extreme weather days.

        Requires a NOAA CDO API token (free registration).
        """
        if not self.token:
            self.logger.warning("skipping_fetch", reason="No NOAA CDO token configured")
            return []

        if latitude is None or longitude is None:
            self.logger.warning("skipping_fetch", reason="No coordinates provided")
            return []

        # NOAA supports max 1 year per request — use bounding box for proximity
        params = {
            "dataset": "daily-summaries",
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "dataTypes": "TMAX,TMIN,PRCP,SNOW,AWND",
            "boundingBox": f"{latitude-0.1},{longitude-0.1},{latitude+0.1},{longitude+0.1}",
            "units": "metric",
            "format": "json",
            "limit": 1000,
        }

        headers = {"token": self.token}

        try:
            data = await self._http_get(self.base_url, params=params, headers=headers)
        except Exception as exc:
            self.logger.error("noaa_fetch_failed", error=str(exc))
            return []

        if not isinstance(data, list):
            self.logger.warning("unexpected_response_format", data_type=type(data).__name__)
            return []

        return self._normalize(data, latitude, longitude, geo_label, industry)

    def _normalize(
        self,
        records: list[dict[str, Any]],
        latitude: float,
        longitude: float,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """
        Convert raw NOAA structured JSON summary records into formatted ImpactEvents.
        
        Args:
            records: Raw JSON records from NOAA API.
            latitude: Target latitude coordinate.
            longitude: Target longitude coordinate.
            geo_label: Human readable label.
            industry: The designated industry context.
            
        Returns:
            list[ImpactEventCreate]: Safely typed events formatted for Database upsertion.
        """
        events: list[ImpactEventCreate] = []

        # Group records by date (NOAA returns one record per datatype per station)
        daily_data: dict[str, dict[str, Any]] = {}
        for record in records:
            date_key: str = str(record.get("DATE", ""))[:10]
            if not date_key:
                continue
                
            if date_key not in daily_data:
                daily_data[date_key] = {}
                
            datatype: str = str(record.get("datatype", ""))
            raw_val = record.get("value")
            
            # Strict safety bounds on typing incoming arbitrary float/int representations
            if isinstance(raw_val, (int, float)):
                daily_data[date_key][datatype] = float(raw_val)

        for date_str, values in daily_data.items():
            tmax: float | None = values.get("TMAX")
            tmin: float | None = values.get("TMIN")
            prcp: float | None = values.get("PRCP")  # mm
            snow: float | None = values.get("SNOW")  # mm
            awnd: float | None = values.get("AWND")  # m/s

            significant: list[dict[str, Any]] = []

            # Extreme cold
            if tmin is not None and tmin <= -10.0:
                significant.append({
                    "type": "extreme_cold",
                    "title": f"[NOAA] Extreme Cold: {tmin:.0f}°C low",
                    "severity": self._clamp_severity(0.5 + abs(tmin) / 40.0),
                })

            # Extreme heat
            if tmax is not None and tmax >= 38.0:
                significant.append({
                    "type": "extreme_heat",
                    "title": f"[NOAA] Extreme Heat: {tmax:.0f}°C high",
                    "severity": self._clamp_severity(0.4 + (tmax - 35.0) / 15.0),
                })

            # Heavy snow (100mm = 10cm)
            if snow is not None and snow >= 100.0:
                snow_cm = snow / 10.0
                significant.append({
                    "type": "heavy_snow" if snow_cm < 30.0 else "blizzard",
                    "title": f"[NOAA] {'Blizzard' if snow_cm >= 30.0 else 'Heavy Snow'}: {snow_cm:.0f}cm",
                    "severity": self._clamp_severity(0.55 + snow_cm / 60.0),
                })

            # Heavy rain
            if prcp is not None and prcp >= 40.0:
                significant.append({
                    "type": "heavy_rain",
                    "title": f"[NOAA] Heavy Rain: {prcp:.0f}mm",
                    "severity": self._clamp_severity(0.4 + prcp / 200.0),
                })

            # High wind (m/s → km/h)
            if awnd is not None:
                wind_kmh = awnd * 3.6
                if wind_kmh >= 70.0:
                    significant.append({
                        "type": "high_wind",
                        "title": f"[NOAA] High Wind: {wind_kmh:.0f} km/h",
                        "severity": self._clamp_severity(0.4 + wind_kmh / 200.0),
                    })

            for item in significant:
                try:
                    event_date = datetime.fromisoformat(date_str)
                except ValueError:
                    continue  # Protect against malformed ISO string drops
                    
                events.append(ImpactEventCreate(
                    source="noaa-cdo",
                    source_id=f"noaa-{date_str}-{latitude}-{longitude}-{item.get('type')}",
                    category="weather",
                    subcategory=item.get("type", "generic"),
                    title=item.get("title", "Weather Alert"),
                    description="NOAA station-level ground truth observation.",
                    severity=float(item.get("severity", 0.5)),
                    confidence=0.95,  # Station-level = highest confidence
                    start_date=event_date,
                    end_date=event_date,
                    latitude=latitude,
                    longitude=longitude,
                    geo_radius_km=5.0,  # Station-level is very local
                    geo_label=geo_label,
                    industry=industry,
                    raw_payload=values,
                ))

        self.logger.info(
            "noaa_events_detected",
            total_days=len(daily_data),
            significant_days=len(events),
            industry=industry,
        )
        return events
