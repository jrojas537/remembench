/**
 * API client for the YoY Anomaly Engine backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
}

export async function fetchEvents({ category, source, geoLabel, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({ limit, offset, industry: 'wireless_retail' });
    if (category) params.set('category', category);
    if (source) params.set('source', source);
    if (geoLabel) params.set('geo_label', geoLabel);
    return apiFetch(`/events/?${params}`);
}

export async function fetchEventStats() {
    return apiFetch('/events/stats/summary?industry=wireless_retail');
}

export async function fetchYoYComparison({
    startDate,
    endDate,
    lookbackYears = 1,
    geoLabel,
    categories,
}) {
    const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        lookback_years: lookbackYears,
        industry: 'wireless_retail',
    });
    if (geoLabel) params.set('geo_label', geoLabel);
    if (categories?.length) {
        categories.forEach(c => params.append('categories', c));
    }
    return apiFetch(`/yoy/compare?${params}`);
}

export async function runIngestion({ startDate, endDate, latitude, longitude, geoLabel }) {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (latitude) params.set('latitude', latitude);
    if (longitude) params.set('longitude', longitude);
    if (geoLabel) params.set('geo_label', geoLabel);
    return apiFetch(`/ingest/run?${params}`, { method: 'POST' });
}

export async function triggerBackfill({ startDate, endDate, geoLabel }) {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (geoLabel) params.set('geo_label', geoLabel);
    return apiFetch(`/ingest/backfill?${params}`, { method: 'POST' });
}

export async function fetchHealth() {
    return apiFetch('/health', { method: 'GET' });
}
