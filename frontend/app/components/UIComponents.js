import React from 'react';
import { CATEGORY_ICONS } from "../lib/constants";

export function StatCard({ icon, value, label, color }) {
    // Map legacy emoji icons to clean Phosphor/Feather solid-path SVGs
    const renderIcon = (emoji) => {
        const props = { width: 20, height: 20, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", color: "var(--color-brand-primary)" };
        if (emoji === "📊") return <svg {...props}><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>;
        if (emoji === "🔴") return <svg {...props}><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>;
        if (emoji === "📈") return <svg {...props}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>;
        if (emoji === "📂") return <svg {...props}><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>;
        return <span style={{ fontSize: "1.25rem" }}>{emoji}</span>;
    };

    return (
        <div style={{
            background: "var(--color-bg-secondary)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-sm)",
            padding: "var(--space-4)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
            border: "1px solid var(--color-border-subtle)"
        }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
                    {label}
                </div>
                <div style={{ background: "var(--color-brand-primary-subtle)", padding: "0.35rem", borderRadius: "var(--radius-sm)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {renderIcon(icon)}
                </div>
            </div>
            <div style={{ fontSize: "var(--font-size-xl)", fontWeight: 700, color: "var(--color-brand-primary)" }}>
                {value}
            </div>
        </div>
    );
}

export function CategoryBadge({ category }) {
    // Map category string to a discrete Semantic System validation token
    let semantic = "info";
    const catStr = (category || "").toLowerCase();
    if (catStr.includes("outage") || catStr.includes("disruption") || catStr.includes("strike") || catStr.includes("scandal")) semantic = "danger";
    else if (catStr.includes("promo") || catStr.includes("marketing") || catStr.includes("earnings") || catStr.includes("price")) semantic = "info";
    else if (catStr.includes("weather") || catStr.includes("hurricane") || catStr.includes("storm")) semantic = "warning";
    else if (catStr.includes("holiday") || catStr.includes("sports") || catStr.includes("entertainment") || catStr.includes("product")) semantic = "success";

    return (
        <span style={{
            background: `var(--color-semantic-${semantic}-subtle)`,
            color: `var(--color-semantic-${semantic})`,
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            padding: "var(--space-1) var(--space-2)",
            borderRadius: "var(--radius-sm)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.25rem"
        }}>
            {CATEGORY_ICONS[category] || "📌"} {(category || "UNKNOWN").replace(/_/g, " ")}
        </span>
    );
}

export function EventItem({ event, onClick }) {
    const date = new Date(event.start_date);
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    // Derive Confidence semantic color
    const pct = Math.round(event.confidence * 100);
    let confColor = "var(--color-semantic-danger)";
    if (pct >= 90) confColor = "var(--color-semantic-success)";
    else if (pct >= 80) confColor = "var(--color-semantic-warning)";

    return (
        <div style={{ display: "flex", gap: "var(--space-4)", position: "relative", marginBottom: "var(--space-4)" }}>
            {/* Timeline Connector & Date Pill */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "48px", flexShrink: 0 }}>
                <div style={{
                    background: "var(--color-bg-tertiary)",
                    color: "var(--color-text-secondary)",
                    fontSize: "var(--font-size-xs)",
                    fontWeight: 600,
                    padding: "var(--space-1)",
                    width: "100%",
                    borderRadius: "var(--radius-sm)",
                    textAlign: "center",
                    lineHeight: "1.2",
                    border: "1px solid var(--color-border-default)",
                    zIndex: 2
                }}>
                    <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-primary)" }}>{date.getDate()}</div>
                    <div>{monthNames[date.getMonth()]}</div>
                </div>
                {/* Vertical Line via absolute stretching */}
                <div style={{ position: "absolute", top: "50px", bottom: "-20px", left: "23px", width: "2px", background: "var(--color-border-default)", zIndex: 1 }} />
            </div>

            {/* Event Card */}
            <div
                onClick={onClick}
                style={{
                    background: "var(--color-bg-secondary)",
                    border: "1px solid var(--color-border-subtle)",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-4)",
                    boxShadow: "var(--shadow-sm)",
                    cursor: "pointer",
                    flex: 1,
                    transition: "var(--transition-fast)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-2)"
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                    e.currentTarget.style.borderColor = 'var(--color-border-active)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'none';
                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                    e.currentTarget.style.borderColor = 'var(--color-border-subtle)';
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-4)" }}>
                    <div style={{ fontSize: "var(--font-size-md)", fontWeight: 600, color: "var(--color-text-primary)", lineHeight: "1.4" }}>
                        {event.title}
                    </div>
                    {/* Confidence Bar */}
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexShrink: 0 }}>
                        <div style={{ width: "60px", height: "6px", background: "var(--color-bg-tertiary)", borderRadius: "var(--radius-full)", overflow: "hidden", border: "1px solid var(--color-border-subtle)" }}>
                            <div style={{ width: `${pct}%`, height: "100%", background: confColor, borderRadius: "var(--radius-full)" }} />
                        </div>
                        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontWeight: 600 }}>{pct}%</span>
                    </div>
                </div>

                <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)", lineHeight: "1.5" }}>
                    {event.description}
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center", marginTop: "var(--space-2)" }}>
                    <CategoryBadge category={event.category} />
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", fontStyle: "italic" }}>
                        Source: {event.source}
                    </span>
                    {event.geo_label && (
                        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                            • 📍 {event.geo_label}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
