# Remembench User Guide

Welcome to Remembench! This guide provides step-by-step instructions on how to use the Remembench Dashboard to analyze YoY (Year-over-Year) performance context, manage impact events, and set up webhook integrations.

## Analyzing YoY Performance Context

The core feature of the Remembench Dashboard is its ability to compare business context across multiple years for a given market.

1. **Select an Industry**: Use the dropdown at the top of the dashboard to select your specific industry (e.g., Wireless Retail, Pizza Full-Service).
2. **Select a Target Date Range**: Choose the start and end dates representing the period of business performance you are investigating.
3. **Select a Market location (Optional)**: Filter the contextual data down to a specific geospatial area (e.g., NYC, Detroit Metro).
4. **Compare Settings**: Choose how many `lookback_years` (1 to 5) you wish to evaluate.

The system calculates parallel date ranges in previous years automatically and displays:
- A timeline of overlapping Impact Events.
- An AI-generated "Executive Briefing" summarizing the context differences.

## 2. Managing Impact Events

Remembench automatically scrapes weather, news, events, and competitor promos. 
If an event was incorrectly classified, or you want to add manual data, you can use the API or interface (if available in your deployment).

### Manually triggering data ingestion

Sometimes you may want to immediately fetch the latest RSS or news data rather than waiting for the nightly Celery cycle:

```bash
curl -X POST "http://localhost/api/v1/ingestion/run" \
     -H "Content-Type: application/json" \
     -d '{"industry": "wireless_retail"}'
```

Because ingestion operations are asynchronous, the API returns immediately. You can check the dashboard to see newly generated events over the following 2-5 minutes.

## 3. Webhook Subscriptions

Remembench can push real-time alerts to downstream services (like Slack, Zapier, or a database) whenever a high-severity event is ingested and detected.

### Creating a Webhook

To subscribe to events:

1. Send a POST request to the Webhook registration endpoint:
```bash
curl -X POST "http://localhost/api/v1/webhooks/" \
     -H "Content-Type: application/json" \
     -d '{
           "url": "https://hooks.zapier.com/hooks/catch/123/abc/",
           "description": "Critical alerts for NYC Wireless",
           "events": ["*"],
           "is_active": true,
           "headers": {"Authorization": "Bearer some-token"}
         }'
```

Every time Remembench categorizes a new Impact Event that matches the subscription's severity checks, an HTTP POST request is triggered from Remembench to the destination `url` containing the JSON payload of the event.

## 4. Troubleshooting

| Issue | Resolution |
|-------|------------|
| **No dashboard data appearing** | Ensure the Celery workers are running and you have explicitly triggered a `backfill` or waited for the nightly run. Also, verify `REDIS_URL` works so the cache acts correctly. |
| **LLM Classification Timeout** | Check your Anthropic `ANTHROPIC_API_KEY`. If rate limits are hit, Celery will automatically use exponential backoff and retry later. |
| **YOY Compare Loading Forever** | A large date range cross-referenced over 5 years against a massive event dataset might trigger an Nginx timeout. Use a smaller date range or add more restrictive GEO filters. |
