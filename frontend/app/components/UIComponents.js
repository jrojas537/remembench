import React from 'react';
import { CATEGORY_ICONS } from "../lib/constants";

export function StatCard({ icon, value, label, color }) {
    return (
        <div className="stat-card">
            <div className="stat-icon">{icon}</div>
            <div className="stat-value" style={{ color }}>
                {value}
            </div>
            <div className="stat-label">{label}</div>
        </div>
    );
}

export function SeverityBar({ severity }) {
    const pct = Math.round(severity * 100);
    const cls =
        severity >= 0.7
            ? "severity-high"
            : severity >= 0.4
                ? "severity-medium"
                : "severity-low";
    return (
        <div className="severity-bar" title={`Impact: ${pct}%`}>
            <div
                className={`severity-bar-fill ${cls}`}
                style={{ width: `${pct}%` }}
            />
        </div>
    );
}

export function CategoryBadge({ category }) {
    return (
        <span className={`badge badge-${category}`}>
            {CATEGORY_ICONS[category] || "📌"} {(category || "").replace(/_/g, " ")}
        </span>
    );
}

export function EventItem({ event, onClick }) {
    const date = new Date(event.start_date);
    const monthNames = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];

    return (
        <div className="event-item" data-category={event.category} onClick={onClick} style={{ cursor: "pointer" }}>
            <div className="event-date">
                <span className="day">{date.getDate()}</span>
                {monthNames[date.getMonth()]} {date.getFullYear()}
            </div>
            <div>
                <div className="event-title">{event.title}</div>
                <div className="event-desc">{event.description}</div>
                <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                    <CategoryBadge category={event.category} />
                    <span className="badge badge-source">🌐 Source: {event.source}</span>
                    {event.geo_label && (
                        <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                            📍 {event.geo_label}
                        </span>
                    )}
                </div>
            </div>
            <div className="event-meta">
                <div style={{ width: 80 }}>
                    <SeverityBar severity={event.severity} />
                </div>
                <span
                    style={{
                        fontSize: "0.7rem",
                        color: "var(--color-text-muted)",
                    }}
                >
                    {Math.round(event.confidence * 100)}% conf
                </span>
            </div>
        </div>
    );
}
