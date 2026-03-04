"""
Remembench — Ingestion Service

Orchestrates the data pipeline for all source adapters (in parallel):
1. Looks up industry config to determine which adapters/queries to use
2. Runs each adapter for the given date range and geography
3. Deduplicates events by (source, source_id)
4. Bulk-inserts into PostgreSQL using ON CONFLICT DO NOTHING

Performance note: the batch upsert replaces the original N+1 pattern
(one SELECT per event to check for duplicates) with a single INSERT
per batch of 100 rows.
"""

import asyncio
from datetime import datetime
from difflib import SequenceMatcher

from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import BaseAdapter
from app.adapters.open_meteo import OpenMeteoAdapter
from app.adapters.noaa_cdo import NoaaCdoAdapter
from app.adapters.gdelt import GdeltAdapter
from app.adapters.carrier_rss import IndustryRssAdapter
from app.adapters.holidays import HolidayAdapter
from app.adapters.web_search import WebSearchAdapter
from app.logging import get_logger
from app.models import ImpactEvent
from app.schemas import ImpactEventCreate
from app.services.classification import ClassificationService

logger = get_logger("services.ingestion")


class IngestionService:
    """
    Coordinates data ingestion across all source adapters,
    handles deduplication, and persists to the database.

    Usage:
        service = IngestionService()
        summary = await service.ingest(db, start, end, industry="pizza_full_service")
    """

    def __init__(self) -> None:
        self.adapters: list[BaseAdapter] = [
            OpenMeteoAdapter(),
            NoaaCdoAdapter(),
            GdeltAdapter(),
            IndustryRssAdapter(),
            HolidayAdapter(),
            WebSearchAdapter(),
        ]
        self.classification_service = ClassificationService()

    async def ingest(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        industry: str = "wireless_retail",
        latitude: float | None = None,
        longitude: float | None = None,
        geo_label: str | None = None,
    ) -> dict:
        """
        Run all adapters for the given parameters and persist new events.

        Args:
            db: Async database session
            start_date: Start of the date range to ingest
            end_date: End of the date range to ingest
            industry: Industry vertical key (determines queries/feeds)
            latitude: Optional latitude for geo-specific queries
            longitude: Optional longitude for geo-specific queries
            geo_label: Optional human-readable market name

        Returns:
            Summary dict with counts of fetched, deduped, and inserted events.
        """
        all_events: list[ImpactEventCreate] = []
        adapter_stats: dict[str, dict] = {}

        # 1. Fetch Phase
        async def _fetch_from_adapter(adapter: BaseAdapter) -> tuple[BaseAdapter, list[ImpactEventCreate]]:
            try:
                # Give adapters plenty of time for AI parsing and rich external fetching
                # especially for heavy WebSearch extraction
                async with asyncio.timeout(60.0):
                    events = await adapter.fetch_events(
                        start_date=start_date,
                        end_date=end_date,
                        industry=industry,
                        latitude=latitude,
                        longitude=longitude,
                        geo_label=geo_label,
                    )
                adapter_stats[adapter.name] = {
                    "fetched": len(events),
                    "status": "success",
                }
                return adapter, events
            except Exception as exc:
                logger.error(
                    "adapter_failed",
                    adapter=adapter.name,
                    industry=industry,
                    error=str(exc),
                    exc_info=True,
                )
                adapter_stats[adapter.name] = {
                    "fetched": 0,
                    "status": "error",
                    "error": str(exc),
                }
                return adapter, []

        fetch_results = await asyncio.gather(
            *[_fetch_from_adapter(a) for a in self.adapters]
        )

        # 2. Separation Phase
        structured_events: list[ImpactEventCreate] = []
        unstructured_events: list[ImpactEventCreate] = []

        for adapter, events in fetch_results:
            if getattr(adapter, 'requires_llm_classification', False):
                unstructured_events.extend(events)
            else:
                structured_events.extend(events)

        # 3. Global Semantic Deduplication (across all unstructured sources)
        unique_unstructured = []
        seen_texts = []
        
        for ev in unstructured_events:
            text_to_analyze = ev.raw_payload.get("content", ev.description) if ev.raw_payload else ev.description
            if not text_to_analyze:
                unique_unstructured.append(ev)
                continue
                
            # Check similarity against already seen texts (cross-adapter checks!)
            is_duplicate = False
            for seen in seen_texts:
                similarity = SequenceMatcher(None, text_to_analyze, seen).ratio()
                if similarity > 0.85:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                seen_texts.append(text_to_analyze)
                unique_unstructured.append(ev)

        # 4. Batch Classification on unique events (Cut system prompt tax by 10x)
        batch_size = 10
        batches = [unique_unstructured[i:i + batch_size] for i in range(0, len(unique_unstructured), batch_size)]
        
        sem = asyncio.Semaphore(3) # Max 3 concurrent batched LLM calls (30 items total inflight)
        
        async def _process_batch(batch):
            async with sem:
                texts = [ev.raw_payload.get("content", ev.description) if ev.raw_payload else ev.description for ev in batch]
                classifications = await self.classification_service.classify_events_batch(texts, industry)
                
                for i, ev in enumerate(batch):
                    if i < len(classifications):
                        classification = classifications[i]
                        ev.severity = classification.get("severity", ev.severity)
                        ev.confidence = classification.get("confidence", ev.confidence)
                        ev.category = classification.get("category", ev.category)
                        ev.subcategory = classification.get("subcategory", ev.subcategory)
                        
                        summary = classification.get("summary", ev.title)
                        details = classification.get("details", {})
                        
                        # Explicitly elevate promotion details to the title to be highly visible
                        if isinstance(details, dict):
                            promo_details = details.get("promotion_details")
                            competitor = details.get("competitor_name")
                            
                            prefix_parts = []
                            if competitor and competitor.lower() not in summary.lower():
                                prefix_parts.append(competitor)
                            if promo_details:
                                prefix_parts.append(promo_details)
                                
                            if prefix_parts:
                                ev.title = f"{' - '.join(prefix_parts)} | {summary}"
                            else:
                                ev.title = summary
                        else:
                            ev.title = summary
                        
                        # Use detailed impact for description to provide more value, fallback to summary
                        detailed_impact = details.get("detailed_impact") if isinstance(details, dict) else None
                        ev.description = detailed_impact or summary
                        
                        # Store rich details in the payload for the frontend modal
                        if "details" in classification:
                            if not ev.raw_payload:
                                ev.raw_payload = {}
                            ev.raw_payload["details"] = classification["details"]
        
        if batches:
            await asyncio.gather(*[_process_batch(b) for b in batches])

        # 5. Combine and Persist
        all_events = structured_events + unique_unstructured

        # Deduplicate by (source, source_id) before persistence
        deduped = self._deduplicate(all_events)

        # Batch upsert to database
        inserted = await self._persist(db, deduped)

        summary = {
            "industry": industry,
            "date_range": f"{start_date.date()} to {end_date.date()}",
            "geo_label": geo_label,
            "total_fetched": len(all_events),
            "after_dedup": len(deduped),
            "inserted": inserted,
            "adapters": adapter_stats,
        }

        logger.info("ingestion_complete", **summary)
        return summary

    def _deduplicate(
        self, events: list[ImpactEventCreate]
    ) -> list[ImpactEventCreate]:
        """Remove duplicate events based on (source, source_id) key."""
        seen: set[str] = set()
        unique: list[ImpactEventCreate] = []

        for event in events:
            if event.source_id:
                key = f"{event.source}:{event.source_id}"
                if key in seen:
                    continue
                seen.add(key)
            unique.append(event)

        return unique

    async def _persist(
        self,
        db: AsyncSession,
        events: list[ImpactEventCreate],
    ) -> int:
        """
        Bulk insert events using PostgreSQL ON CONFLICT DO NOTHING.

        Leverages the partial unique index on (source, source_id) to
        skip duplicates without needing a pre-check SELECT.

        Processes in batches of 100 to avoid overly large SQL statements.
        """
        if not events:
            return 0

        inserted_count = 0
        batch_size = 100

        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            values = []

            for event in batch:
                row = {
                    "source": event.source,
                    "source_id": event.source_id,
                    "category": event.category,
                    "subcategory": event.subcategory,
                    "title": event.title,
                    "description": event.description,
                    "severity": event.severity,
                    "confidence": event.confidence,
                    "start_date": event.start_date,
                    "end_date": event.end_date,
                    "geo_radius_km": event.geo_radius_km,
                    "geo_label": event.geo_label,
                    "industry": event.industry,
                    "raw_payload": event.raw_payload,
                }

                # PostGIS geography — standard EWKT string for executemany binding
                if event.latitude is not None and event.longitude is not None:
                    row["geography"] = f"SRID=4326;POINT({event.longitude} {event.latitude})"

                values.append(row)

            # Do not use .values(values) as it embeds into AST and breaks Geometry types.
            # Instead, pass parameters natively into execute.
            stmt = (
                pg_insert(ImpactEvent)
                .on_conflict_do_nothing(
                    index_elements=["source", "source_id"],
                    index_where=text("source_id IS NOT NULL"),
                )
            )
            result = await db.execute(stmt, values)
            inserted_count += len(values)

        await db.commit()
        return inserted_count

    async def close_adapters(self) -> None:
        """Close all adapter HTTP clients — call during app shutdown."""
        for adapter in self.adapters:
            await adapter.close()
