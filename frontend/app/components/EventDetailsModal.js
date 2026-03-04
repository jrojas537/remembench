"use client";

import { useEffect, useState } from "react";

export default function EventDetailsModal({ eventId, onClose, token, API_BASE }) {
    const [event, setEvent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!eventId) return;
        // eslint-disable-next-line react-hooks/exhaustive-deps
        setLoading(true); // Suppressing react-hooks/set-state-in-effect intentionally
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};

        fetch(`${API_BASE}/events/${eventId}`, { headers })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to load event details");
                return res.json();
            })
            .then((data) => {
                setEvent(data);
                setLoading(false);
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    }, [eventId, token, API_BASE]);

    if (!eventId) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "700px", width: "90%", maxHeight: "90vh", overflowY: "auto" }}>
                <div className="modal-header">
                    <h2 className="card-title" style={{ fontSize: "1.5rem" }}>Event Details</h2>
                    <button className="btn-close" onClick={onClose}>&times;</button>
                </div>

                {loading ? (
                    <div style={{ padding: "3rem", textAlign: "center", color: "var(--color-text-muted)" }}>
                        <div className="spinner"></div>
                        <p>Loading rich intel...</p>
                    </div>
                ) : error ? (
                    <div style={{ padding: "2rem", color: "var(--color-accent-rose)" }}>
                        <p>⚠️ {error}</p>
                    </div>
                ) : (
                    <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                        <div>
                            <h3 style={{ fontSize: "1.25rem", color: "var(--color-text-primary)", marginBottom: "0.5rem" }}>{event.title}</h3>
                            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
                                <span className={`badge badge-${event.category}`}>
                                    {event.category.replace(/_/g, " ")}
                                </span>
                                <span style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                                    📅 {new Date(event.start_date).toLocaleDateString()}
                                </span>
                                {event.geo_label && (
                                    <span style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                                        📍 {event.geo_label}
                                    </span>
                                )}
                            </div>
                        </div>

                        <div className="description-section">
                            <h4 style={{ fontSize: "0.875rem", textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>Event Analysis</h4>
                            <p style={{ color: "var(--color-text-secondary)", lineHeight: "1.7", whiteSpace: "pre-wrap" }}>
                                {event.description || "No detailed description available."}
                            </p>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                            <div className="metric-box" style={{ background: "rgba(255,255,255,0.03)", padding: "1rem", borderRadius: "12px", border: "1px solid var(--color-border)" }}>
                                <label style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", display: "block", marginBottom: "0.5rem" }}>Impact Severity</label>
                                <div style={{ fontSize: "1.5rem", fontWeight: "800", color: event.severity > 0.7 ? "var(--color-accent-rose)" : event.severity > 0.4 ? "var(--color-accent-amber)" : "var(--color-accent-emerald)" }}>
                                    {Math.round(event.severity * 100)}%
                                </div>
                            </div>
                            <div className="metric-box" style={{ background: "rgba(255,255,255,0.03)", padding: "1rem", borderRadius: "12px", border: "1px solid var(--color-border)" }}>
                                <label style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", textTransform: "uppercase", display: "block", marginBottom: "0.5rem" }}>AI Confidence</label>
                                <div style={{ fontSize: "1.5rem", fontWeight: "800", color: "var(--color-accent-cyan)" }}>
                                    {Math.round(event.confidence * 100)}%
                                </div>
                            </div>
                        </div>

                        {event.raw_payload?.details && (
                            <div className="intel-section" style={{ background: "rgba(99, 102, 241, 0.05)", padding: "1.25rem", borderRadius: "16px", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                                <h4 style={{ fontSize: "0.875rem", textTransform: "uppercase", color: "var(--color-accent-indigo)", marginBottom: "1rem" }}>Strategic Intel</h4>
                                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                    {event.raw_payload.details.competitor_name && (
                                        <div>
                                            <b style={{ color: "var(--color-text-primary)" }}>Competitor:</b> {event.raw_payload.details.competitor_name}
                                        </div>
                                    )}
                                    {event.raw_payload.details.promotion_details && (
                                        <div>
                                            <b style={{ color: "var(--color-text-primary)" }}>Promotion:</b> {event.raw_payload.details.promotion_details}
                                        </div>
                                    )}
                                    {event.raw_payload.details.detailed_impact && (
                                        <div>
                                            <b style={{ color: "var(--color-text-primary)" }}>Deep Impact Analysis:</b>
                                            <p style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>{event.raw_payload.details.detailed_impact}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        <div style={{ marginTop: "auto", display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "1rem", borderTop: "1px solid var(--color-border)" }}>
                            <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>Source: <b>{event.source}</b></span>
                            {event.raw_payload?.url && (
                                <a href={event.raw_payload.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ fontSize: "0.875rem" }}>
                                    View Original Source ↗
                                </a>
                            )}
                        </div>
                    </div>
                )}
            </div>

            <style jsx>{`
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.7);
                    backdrop-filter: blur(8px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                    animation: fadeIn 0.2s ease-out;
                }
                .btn-close {
                    background: none;
                    border: none;
                    color: var(--color-text-muted);
                    font-size: 2rem;
                    cursor: pointer;
                    line-height: 1;
                    padding: 0;
                }
                .btn-close:hover {
                    color: var(--color-text-primary);
                }
                .spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(255,255,255,0.1);
                    border-radius: 50%;
                    border-top-color: var(--color-accent-indigo);
                    animation: spin 1s ease-in-out infinite;
                    margin: 0 auto 1rem;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}
