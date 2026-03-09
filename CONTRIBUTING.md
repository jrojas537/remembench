# Contributing to Remembench

Welcome to the internal developer guide for Remembench! This document is meant to serve as a roadmap for any engineer pulling down the codebase for the first time. It covers project topology, how to add new data streams, and our development philosophy.

---

## 1. Local Development Setup

Remembench is bifurcated into a decoupled FastAPI backend and Next.js frontend. They can be run entirely locally without Docker for rapid iteration.

### Requirements
*   Python 3.11+
*   Node.js 18+ (20+ recommended)
*   A local PostgreSQL database (or you can connect to a staging cloud instance via `.env`)
*   A local Redis instance (used for Celery + Route caching)

### Backend Quickstart

```bash
cd backend

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Duplicate environment variables
cp ../.env.example .env

# Run FastAPI (Hot Reloading)
uvicorn app.main:app --reload --port 8000

# OPTIONAL: Run a local Celery Worker for testing ingestions
celery -A app.tasks.celery_app worker --loglevel=info
```

### Frontend Quickstart

```bash
cd frontend

# Install Node modules
npm install

# Run the Next.js development server
npm run dev

# Open Dashboard in browser at: http://localhost:3000
```

---

## 2. Adding a New Industry

Remembench was architected around the "Registry Pattern". You **never** need to touch database schemas, Next.js UI arrays, or API routing when adding a new industry.

All you need to modify is **`backend/app/industries.py`**.

```python
# Add your new industry key
"coffee_shops": {
    "name": "Coffee Shops",
    "description": "Foot traffic impact for cafes.",
    "markets": ["Seattle Metro", "Portland", "NYC"],
    
    # What web searches should trigger when looking for relevant deals?
    "query_builder": lambda start, end: f"(Starbucks OR Dunkin OR Peet's) (deal OR bogo OR promotion)",
    
    # What keywords should GDELT look for in global news databases?
    "gdelt_queries": ["coffee bean price", "cafe strike", "starbucks closing"],
    
    # Do we have specific industry RSS feeds to ingest?
    "rss_feeds": [
        "https://www.restaurantbusinessonline.com/rss/coffee",
    ],
    
    # Define LLM parsing rules. How should Claude classify these events?
    "classification_prompt_addition": "Focus heavily on union news, bean shortages, and seasonal drink launches (e.g. Pumpkin Spice)."
}
```

Once added, the frontend dynamically reads from the API and populates the UI drop-downs. Nightly ingestions automatically begin scraping data for your new vertical.

---

## 3. Adding a New Data Adapter

If you want to ingest a completely new platform (e.g., Reddit, Twitter, Google Trends, a specialized API), you create a new Adapter.

1. Navigate to `backend/app/adapters/`.
2. Create a new file `my_new_source.py`.
3. Inherit from `BaseAdapter`.

```python
from datetime import datetime
from app.adapters.base import BaseAdapter
from app.schemas import ImpactEventCreate

class MyNewSourceAdapter(BaseAdapter):
    def __init__(self):
        super().__init__("my-new-source")
        
        # If your adapter returns unstructured text (like News), set this to True.
        # It tells the ingestion engine to route the outputs through the Semantic Deduplicator
        # and Anthropic LLM classifier automatically.
        self.requires_llm_classification = True 

    async def fetch_events(self, start_date, end_date, industry, latitude=None, longitude=None, geo_label=None):
        # 1. Perform HTTP requests here (Use self._http_get() for built-in backoff)
        data = await self._http_get("https://api.mysource.com/trends")
        
        events = []
        for item in data:
            events.append(ImpactEventCreate(
                source="my-new-source",
                source_id=item["unique_id"],
                title="Pending Classification",
                description=item["full_text"],
                start_date=start_date,
                end_date=end_date,
                geo_label=geo_label,
                industry=industry,
                # Store the raw chaotic dictionary here. The UI can display it in a JSON modal.
                raw_payload=item 
            ))
            
        return events
```
4. Register your new class inside `__init__.py` or inject it into the `IngestionService` adapter array.

---

## 4. Development Principles

1.  **AI is Expensive, Databases are Cheap**: Never send an LLM a string that you haven't validated first. Check PostgreSQL for the `source_id`. Run `sentence-transformers` locally to deduplicate identical semantic text. Use the LLM as the *last* step in the funnel.
2.  **Graceful Degradation**: External APIs fail constantly. If NOAA is down, or GDELT is returning a 500, the `BaseAdapter` handles retries, and `IngestionService` safely moves on without crashing the execution context.
3.  **Strict Database Typings**: The `ImpactEvent` SQLAlchemy model heavily relies on precise DateTime bindings and Geography types (`ST_Point`). Pydantic ensures nothing enters the DB that is malformed.

---

## 5. Code Review Standards

When submitting a PR:
- Run the 100+ native `pytest` hooks suite via `python -m pytest tests/`.
- Ensure new endpoints feature explicit return models.
- Supply inline documentation (`"""docstrings"""`) explaining the *Why* of a complex algorithm, not just the *What*.
