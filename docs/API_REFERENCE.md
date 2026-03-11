# Remembench API Reference
**Version**: 0.2.0

Remembench — YoY Performance Context Engine. Surfaces weather, promotions, holidays, events, and disruptions that impact specific industries, markets, and date ranges.

## Endpoints

### GET `/api/v1/agent/anomalies`
**Token-optimized anomaly search for AI Agents**

Highly compressed endpoint specifically built for LLM/Agent consumption.
Strips raw JSON payloads and metadata to save token space in the context window.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `industry` | query | Yes | string | Target industry slug (e.g. 'wireless_retail', 'pizza_full_service') |
| `start_date` | query | Yes | string | Start date YYYY-MM-DD |
| `end_date` | query | Yes | string | End date YYYY-MM-DD |
| `market` | query | No | Unknown | Optional specific market (e.g., 'New York City') |
| `limit` | query | No | integer | Max results (capped at 200) |
| `detail_level` | query | No | string | 'low' returns just a bullet point summary. 'high' returns the full text schema. |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/agent/anomaly/{event_id}`
**Fetch full descriptive payload for a single event**

Agent Drill-Down tool. After an agent identifies an interesting event using `detail_level=low`,
it can fetch the full descriptive payload here.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `event_id` | path | Yes | string | - |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/auth/register`
**Register User**

Register a new user.
Creates a new user account and sets up empty default preferences.

#### Responses

| Code | Description |
|------|-------------|
| `201` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/auth/login`
**Login For Access Token**

Authenticate user and return a JWT token.
Uses JSON body `email` and `password` inside `UserLogin`.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/users/me`
**Read Users Me**

Get the currently authenticated user's profile and preferences.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |


---

### PUT `/api/v1/users/me/preferences`
**Update User Preferences**

Update the authenticated user's preferences (like default industry and market).

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/billing/create-checkout-session`
**Create Checkout**

Generate a linked Stripe checkout URL to upgrade a user's subscription tier.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `lookup_key` | query | Yes | string | - |
| `success_url` | query | Yes | string | - |
| `cancel_url` | query | Yes | string | - |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/billing/create-portal-session`
**Create Portal**

Generate a link for a user to manage their active Stripe subscription.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `return_url` | query | Yes | string | - |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/billing/webhook`
**Stripe Webhook**

Listen to server-to-server webhook events dispatched from Stripe to sync our internal database state.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |


---

### POST `/api/v1/events/`
**Create Event**

Create a new impact event.

Typically called by adapters during ingestion, not by end users.
If latitude/longitude are provided, a PostGIS point is created
for spatial queries.

#### Responses

| Code | Description |
|------|-------------|
| `201` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/events/`
**List Events**

List impact events with optional filters.

Returns events sorted by date (newest first) for the specified
industry. Supports filtering by category, source, market, and date range.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `category` | query | No | Unknown | Filter by impact category |
| `source` | query | No | Unknown | Filter by data source |
| `geo_label` | query | No | Unknown | Filter by market name (partial match) |
| `industry` | query | No | string | Industry vertical |
| `start_date` | query | No | Unknown | Filter events on or after this date |
| `end_date` | query | No | Unknown | Filter events on or before this date |
| `limit` | query | No | integer | Max results to return |
| `offset` | query | No | integer | Pagination offset |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/events/stats/summary`
**Event Stats**

Get summary statistics of impact events per category.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `industry` | query | No | string | Industry vertical |
| `start_date` | query | No | Unknown | Filter events on or after this date |
| `end_date` | query | No | Unknown | Filter events on or before this date |
| `geo_label` | query | No | Unknown | Filter by market name (includes National) |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/events/briefing`
**Get Executive Briefing**

Generate an AI Executive Briefing from a list of events natively structured in JSON.

Security & Performance Architecture:
- Rate Limited: Strictly capped at 5 requests per minute per IP via Redis (`slowapi`) 
  to prevent malicious token extortion attacks against the downstream LLM.
- Semantic Caching: Requests are cryptographically hashed inside `ClassificationService`.
  Identical payloads bypass the LLM entirely, yielding ~0ms latency and $0 billing cost.
  
Args:
    request: FastAPI raw request object (required by slowapi memory tracker).
    payload: Pydantic schema containing isolated array of ImpactEvents + targeting industry.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/events/{event_id}`
**Get Event**

Retrieve a single impact event by its UUID.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `event_id` | path | Yes | string | - |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/yoy/compare`
**Compare Yoy**

Execute a complex geospatial Year-Over-Year (YoY) event aggregation.

Security & Performance Architecture:
- Rate Limited: Capped at 30 requests per minute per IP via Redis (`slowapi`).
  This ceiling explicitly protects PostgreSQL from connection starvation caused 
  by aggressive multi-year bounding queries across massive historical datasets.

Calculates the exact temporal equivalent of the requested date range for previous 
years, aggregates semantic event overlaps, and computes significance deltas 
(e.g., "3 more competitor promos this year compared to last year").

Example: comparing Feb 1-28 2025 against Feb 1-28 2024 for the
Detroit pizza market. If there was a major blizzard in 2024 but
not 2025, that context helps explain why sales are up this year.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `start_date` | query | Yes | string | Start of the target period |
| `end_date` | query | Yes | string | End of the target period |
| `lookback_years` | query | No | integer | Years to look back |
| `geo_label` | query | No | Unknown | Optional market filter |
| `categories` | query | No | Unknown | Categories to include |
| `industry` | query | No | string | Industry vertical |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/ingestion/run`
**Trigger Manual Ingestion**

Manually triggers the overarching intelligence ingestion pipeline for a date range.

Iterates through all registered adapters for the vertical, executes remote fetching,
LLM semantic classification, deduplication dropping, and inserts clean records into PostgreSQL.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `start_date` | query | Yes | string | Start of bounding time-series to ingest |
| `end_date` | query | Yes | string | End of bounding time-series to ingest |
| `industry` | query | No | string | Designated industry vertical code |
| `latitude` | query | No | Unknown | Spatial core bounding reference |
| `longitude` | query | No | Unknown | Spatial core bounding reference |
| `geo_label` | query | No | Unknown | Human readable market name |


#### Responses

| Code | Description |
|------|-------------|
| `200` | A statistical dictionary block confirming database inserts and fetched source volume. |
| `422` | Validation Error |


---

### GET `/api/v1/ingestion/task/{task_id}`
**Check Task Status**

Check the status of an asynchronous ingestion task.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `task_id` | path | Yes | string | - |


#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |
| `422` | Validation Error |


---

### POST `/api/v1/ingestion/backfill`
**Schedule Historical Backfill**

Triggers a massive asynchronous historical backfill ingestion job via Celery.

Returns immediately with a trackable job ID pointing to the detached worker queue.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `start_date` | query | Yes | string | ISO 8601 date string (e.g. 2024-01-01) |
| `end_date` | query | Yes | string | ISO 8601 date string (e.g. 2024-12-31) |
| `industry` | query | No | string | Industry vertical target |
| `geo_label` | query | No | Unknown | Specific local market constraint |


#### Responses

| Code | Description |
|------|-------------|
| `200` | A task dictionary containing the async Celery job ID. |
| `422` | Validation Error |


---

### GET `/api/v1/industries/`
**List Industries**

Return all configured industries grouped by vertical.

Used by the frontend to populate the industry switcher,
market dropdown, and category filters dynamically.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |


---

### GET `/api/v1/webhooks/`
**List Webhooks**

Returns an index of all webhooks owned mechanically by the authenticated user.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |


---

### POST `/api/v1/webhooks/`
**Create Webhook**

Registers a new active Webhook destination securely tied to the current User's tenant ID.
The response payload dictates a generated 'secret_token' so the user can HMAC-verify payloads.

#### Responses

| Code | Description |
|------|-------------|
| `201` | Successful Response |
| `422` | Validation Error |


---

### DELETE `/api/v1/webhooks/{webhook_id}`
**Delete Webhook**

Safely tears down a user's webhook notification flow based on valid IDs.

#### Parameters

| Name | In | Required | Type | Description |
|------|----|----------|------|-------------|
| `webhook_id` | path | Yes | string | - |


#### Responses

| Code | Description |
|------|-------------|
| `204` | Successful Response |
| `422` | Validation Error |


---

### GET `/api/v1/health`
**Health Check**

Check API and database connectivity.

#### Responses

| Code | Description |
|------|-------------|
| `200` | Successful Response |


---
