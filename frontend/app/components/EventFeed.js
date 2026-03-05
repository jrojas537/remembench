import React from 'react';
import { EventItem } from "./UIComponents";

export default function EventFeed({ events, loading, hasRun, isSearchingWeb, searchResultMsg, onEventClick }) {
    return (
        <div className="report-content-left">
            <div className="card">
                <div className="card-header">
                    <div>
                        <div className="card-title">Impact Timeline</div>
                        <div className="card-subtitle">
                            Events that could influence YoY performance — sorted by most recent
                        </div>
                    </div>
                    <span
                        style={{
                            fontSize: "var(--font-size-sm)",
                            color: "var(--color-text-muted)",
                        }}
                    >
                        {events.length} events
                    </span>
                </div>

                {loading ? (
                    <div className="event-list">
                        {[1, 2, 3, 4].map((i) => (
                            <div
                                key={i}
                                className="skeleton"
                                style={{ height: 80, width: "100%" }}
                            />
                        ))}
                    </div>
                ) : !hasRun ? (
                    <div className="empty-state" style={{ padding: "4rem", textAlign: "center" }}>
                        <div className="empty-icon" style={{ fontSize: "3rem", marginBottom: "1rem" }}>👋</div>
                        <h3>Ready to analyze</h3>
                        <p style={{ color: "var(--color-text-muted)" }}>
                            Select your parameters and click &quot;Run Report&quot; to gather insights.
                        </p>
                    </div>
                ) : isSearchingWeb && events.length === 0 ? (
                    <div className="empty-state" style={{ padding: "4rem", textAlign: "center" }}>
                        <div className="spinner" style={{ fontSize: "2rem", animation: "spin 2s linear infinite" }}>🤖</div>
                        <h3>Scanning Live Web...</h3>
                        <p style={{ color: "var(--color-accent-amber)" }}>
                            Firing AI agents to analyze current web events. This may take 10-20 seconds.
                        </p>
                    </div>
                ) : events.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">🔍</div>
                        <h3>No events found</h3>
                        <p>No local or live web data found for this date range and market.</p>
                    </div>
                ) : (
                    <div className="event-list" style={{ position: "relative" }}>
                        {isSearchingWeb && (
                            <div style={{
                                padding: "1rem",
                                borderRadius: "var(--radius-lg)",
                                background: "rgba(56, 189, 248, 0.08)",
                                border: "1px solid rgba(56, 189, 248, 0.2)",
                                color: "var(--color-accent-cyan)",
                                display: "flex",
                                alignItems: "center",
                                gap: "0.75rem",
                                fontSize: "0.875rem",
                                marginBottom: "1rem"
                            }}>
                                <span className="spinner" style={{ animation: "spin 2s linear infinite" }}>🤖</span>
                                <strong>Combining live web events with local weather...</strong>
                                <span style={{ marginLeft: "auto", opacity: 0.7 }}>Checking news & promos</span>
                            </div>
                        )}
                        {searchResultMsg && (
                            <div style={{
                                padding: "1rem",
                                borderRadius: "var(--radius-lg)",
                                background: "rgba(167, 139, 250, 0.08)",
                                border: "1px solid rgba(167, 139, 250, 0.2)",
                                color: "var(--color-accent-purple)",
                                display: "flex",
                                alignItems: "center",
                                gap: "0.75rem",
                                fontSize: "0.875rem",
                                marginBottom: "1rem",
                                animation: "fadeIn 0.3s ease-out"
                            }}>
                                <span style={{ fontSize: "1.2rem" }}>ℹ️</span>
                                <strong>{searchResultMsg}</strong>
                            </div>
                        )}
                        {events.map((event) => (
                            <EventItem
                                key={event.id}
                                event={event}
                                onClick={() => onEventClick(event.id)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
