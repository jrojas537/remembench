"""
Remembench — Holiday API Adapter

Fetches public and school holidays from free APIs. Holidays significantly
impact business traffic patterns across all industries:
- Wireless retail: Black Friday, back-to-school drives purchases
- Pizza: Super Bowl Sunday, holidays drive delivery volume
- Both: Thanksgiving/Christmas closures reduce foot traffic

Sources:
- Abstract API (public holidays, free tier — requires key)
- OpenHolidays API (school holidays, open-source — no key needed)
- Built-in US calendar fallback (no API needed)
"""

from datetime import datetime, timezone

from app.adapters.base import BaseAdapter
from app.config import settings
from app.schemas import ImpactEventCreate

# Holiday severity mapping — represents "deviation from normal traffic."
# Higher values = more significant impact (positive or negative).
_HOLIDAY_SEVERITY: dict[str, float] = {
    "super bowl": 0.85,       # Huge for pizza delivery
    "black friday": 1.0,
    "christmas": 0.9,
    "cyber monday": 0.85,
    "independence day": 0.7,
    "memorial day": 0.65,
    "labor day": 0.65,
    "thanksgiving": 0.8,
    "new year": 0.6,
    "valentine's day": 0.5,   # Significant for restaurants
    "mother's day": 0.6,      # Significant for restaurants
    "father's day": 0.5,
    "back to school": 0.75,
    "martin luther king": 0.3,
    "presidents": 0.35,
    "columbus": 0.3,
    "veterans": 0.3,
    "st. patrick": 0.45,      # Relevant for bars/restaurants
    "halloween": 0.5,
}


class HolidayAdapter(BaseAdapter):
    """Adapter for public and school holiday APIs."""

    def __init__(self) -> None:
        super().__init__("holiday-api")
        self.abstract_api_key = settings.abstract_api_key

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
        Fetch holidays for the given date range.

        Holidays are industry-universal — they impact traffic patterns
        across all verticals, just in different ways.
        """
        events: list[ImpactEventCreate] = []

        # Fetch from Abstract API if key is configured
        if self.abstract_api_key:
            abstract_events = await self._fetch_abstract_api(
                start_date, end_date, geo_label, industry,
            )
            events.extend(abstract_events)
        else:
            # Fallback: use built-in major US holiday calendar
            events.extend(self._get_builtin_holidays(
                start_date, end_date, geo_label, industry,
            ))

        # Fetch school holidays (always — no API key needed)
        school_events = await self._fetch_school_holidays(
            start_date, end_date, geo_label, industry,
        )
        events.extend(school_events)

        self.logger.info(
            "holiday_events_fetched",
            total=len(events),
            industry=industry,
            date_range=f"{start_date.date()} to {end_date.date()}",
        )
        return events

    async def _fetch_abstract_api(
        self,
        start_date: datetime,
        end_date: datetime,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """Fetch public holidays from Abstract API (free tier)."""
        events: list[ImpactEventCreate] = []

        for year in range(start_date.year, end_date.year + 1):
            url = "https://holidays.abstractapi.com/v1/"
            params = {
                "api_key": self.abstract_api_key,
                "country": "US",
                "year": year,
            }

            try:
                data = await self._http_get(url, params=params)
            except Exception as exc:
                self.logger.warning("abstract_api_failed", year=year, error=str(exc))
                continue

            if not isinstance(data, list):
                continue

            for holiday in data:
                name = holiday.get("name", "")
                date_str = holiday.get("date", "")
                h_type = holiday.get("type", "")

                if not date_str:
                    continue

                try:
                    h_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                if h_date < start_date or h_date > end_date:
                    continue

                severity = self._get_holiday_severity(name)

                events.append(ImpactEventCreate(
                    source="holiday-api",
                    source_id=f"abstract-{date_str}-{name[:50]}",
                    category="holiday",
                    subcategory=h_type or "public_holiday",
                    title=name,
                    description=f"Type: {h_type}. Affects normal traffic patterns.",
                    severity=severity,
                    confidence=0.95,
                    start_date=h_date,
                    end_date=h_date,
                    geo_label=geo_label or "National",
                    industry=industry,
                    raw_payload=holiday,
                ))

        return events

    async def _fetch_school_holidays(
        self,
        start_date: datetime,
        end_date: datetime,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """Fetch school holidays from OpenHolidays API (free, no key)."""
        url = "https://openholidaysapi.org/SchoolHolidays"
        params = {
            "countryIsoCode": "US",
            "validFrom": start_date.strftime("%Y-%m-%d"),
            "validTo": end_date.strftime("%Y-%m-%d"),
            "languageIsoCode": "EN",
        }

        try:
            data = await self._http_get(url, params=params)
        except Exception as exc:
            self.logger.warning("openholidays_failed", error=str(exc))
            return []

        if not isinstance(data, list):
            return []

        events: list[ImpactEventCreate] = []
        for holiday in data:
            name_entries = holiday.get("name", [])
            name = name_entries[0].get("text", "School Holiday") if name_entries else "School Holiday"
            start = holiday.get("startDate", "")
            end = holiday.get("endDate", "")

            if not start:
                continue

            try:
                h_start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
                h_end = datetime.fromisoformat(end).replace(tzinfo=timezone.utc) if end else h_start
            except ValueError:
                continue

            # Back-to-school and summer break impact multiple industries
            severity = 0.75 if "summer" in name.lower() else 0.5

            events.append(ImpactEventCreate(
                source="holiday-api",
                source_id=f"openholidays-{start}-{name[:50]}",
                category="holiday",
                subcategory="school_holiday",
                title=f"School: {name}",
                description=(
                    f"School holiday period from {start} to {end}. "
                    f"Impacts family traffic patterns and seasonal spending."
                ),
                severity=severity,
                confidence=0.85,
                start_date=h_start,
                end_date=h_end,
                geo_label=geo_label or "National",
                industry=industry,
                raw_payload=holiday,
            ))

        return events

    def _get_builtin_holidays(
        self,
        start_date: datetime,
        end_date: datetime,
        geo_label: str | None,
        industry: str,
    ) -> list[ImpactEventCreate]:
        """
        Fallback: major US holidays from a built-in calendar.

        Used when no Abstract API key is configured. Dates are approximate
        (holidays like Thanksgiving move each year).
        """
        major_holidays = [
            ("New Year's Day", 1, 1),
            ("Martin Luther King Jr. Day", 1, 20),
            ("Super Bowl Sunday", 2, 9),     # Approximate
            ("Valentine's Day", 2, 14),
            ("Presidents' Day", 2, 17),
            ("St. Patrick's Day", 3, 17),
            ("Memorial Day", 5, 26),
            ("Independence Day", 7, 4),
            ("Labor Day", 9, 1),
            ("Halloween", 10, 31),
            ("Veterans Day", 11, 11),
            ("Thanksgiving", 11, 27),
            ("Black Friday", 11, 28),
            ("Christmas Eve", 12, 24),
            ("Christmas Day", 12, 25),
            ("New Year's Eve", 12, 31),
        ]

        events: list[ImpactEventCreate] = []
        for year in range(start_date.year, end_date.year + 1):
            for name, month, day in major_holidays:
                try:
                    h_date = datetime(year, month, day, tzinfo=timezone.utc)
                except ValueError:
                    continue

                if h_date < start_date or h_date > end_date:
                    continue

                events.append(ImpactEventCreate(
                    source="holiday-api",
                    source_id=f"builtin-{year}-{month}-{day}-{name[:30]}",
                    category="holiday",
                    subcategory="public_holiday",
                    title=name,
                    description="Built-in US holiday calendar (no API key configured).",
                    severity=self._get_holiday_severity(name),
                    confidence=0.8,
                    start_date=h_date,
                    end_date=h_date,
                    geo_label=geo_label or "National",
                    industry=industry,
                ))

        return events

    def _get_holiday_severity(self, name: str) -> float:
        """
        Look up severity score for a holiday by name.

        Returns a higher score for holidays with greater business impact
        (e.g., Black Friday = 1.0, minor holidays = 0.3).
        """
        name_lower = name.lower()
        for keyword, severity in _HOLIDAY_SEVERITY.items():
            if keyword in name_lower:
                return severity
        return 0.3  # Default for minor/unknown holidays
