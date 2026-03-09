"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "./contexts/AuthContext";
import ProfileSettings from "./components/ProfileSettings";
import EventDetailsModal from "./components/EventDetailsModal";
import Link from "next/link";
import EventFeed from "./components/EventFeed";
import MetricCharts from "./components/MetricCharts";
import {
    FALLBACK_INDUSTRIES,
    API_BASE,
    CATEGORY_ICONS,
    CATEGORY_COLORS
} from "./lib/constants";

/* ------------------------------------------------------------------ *
 *  Main Dashboard Page                                                *
 * ------------------------------------------------------------------ */

import { useDashboardData } from "./hooks/useDashboardData";

/**
 * Main Dashboard Component
 * 
 * Serves as the primary interface for the Remembench platform. It brings together the
 * data fetching logic (via the `useDashboardData` hook), user preferences, date constraints,
 * and renders the active events alongside interactive metrics and AI-generated briefings.
 * 
 * Flow:
 * 1. Derives initial date bounds based on a 7-day or 3-day history looking backward from Fridays.
 * 2. Fetches the industry JSON registry to populate the dropdown filters.
 * 3. Pipes the selected filters into the `useDashboardData` React hook.
 * 4. Renders the `<MetricCharts />` and `<EventFeed />` using the returned data.
 *
 * @returns {JSX.Element} The rendered dashboard layout.
 */
export default function Dashboard() {
    const { user, token } = useAuth();
    const [hideDemo, setHideDemo] = useState(false);

    const [industries, setIndustries] = useState(null);
    const [industry, setIndustry] = useState("pizza_all");

    // We defer hook variables until default dates are computed
    const [geoFilter, setGeoFilter] = useState("Detroit Metro");
    const [categoryFilter, setCategoryFilter] = useState("");
    const [selectedEventId, setSelectedEventId] = useState(null);

    const { defaultStart, defaultEnd } = useMemo(() => {
        const today = new Date();

        // Exact same day, one year ago
        const lastYear = new Date(today);
        lastYear.setFullYear(today.getFullYear() - 1);

        // Default end date anchor (will be re-evaluated by derivedEndDate based on free/premium tier bounds)
        const endAnchor = new Date(lastYear);
        endAnchor.setDate(lastYear.getDate() + 6);

        return {
            defaultStart: lastYear.toISOString().split('T')[0],
            defaultEnd: endAnchor.toISOString().split('T')[0],
        }
    }, []);

    const [startDate, setStartDate] = useState(defaultStart);

    // Phase 5: Auto-Calculate End Date based on User Tier (+7 days vs +3 days)
    const derivedEndDate = useMemo(() => {
        const start = new Date(startDate || defaultStart);
        const isPremium = user?.tier === "premium";
        const daysToAdd = isPremium ? 6 : 2; // 7 days total (start + 6) or 3 days total (start + 2)
        start.setDate(start.getDate() + daysToAdd);
        return start.toISOString().split('T')[0];
    }, [startDate, defaultStart, user]);

    // Call the decoupled hook
    const {
        events,
        stats,
        loading,
        hasRun,
        isDemo,
        isSearchingWeb,
        searchResultMsg,
        aiBriefing,
        isGeneratingBriefing,
        loadData
    } = useDashboardData({
        industry,
        geoFilter,
        categoryFilter,
        startDate,
        endDate: derivedEndDate,
        defaultStart,
        defaultEnd,
        user,
        token
    });

    // Removed legacy `formattedBriefing` Markdown regex parsed string handling natively 
    // since the API now yields an explicitly typed ExecutiveBriefing object.

    // Ensure dashboard starts scrolled to the top
    useEffect(() => {
        window.scrollTo(0, 0);
    }, []);

    // Fetch industry registry on mount
    useEffect(() => {
        fetch(`${API_BASE}/industries/`)
            .then((res) => {
                if (!res.ok) throw new Error("API fail");
                return res.json();
            })
            .then((data) => {
                const flat = {};
                Object.entries(data.groups).forEach(([group, items]) => {
                    items.forEach((item) => {
                        flat[item.key] = { ...item, group };
                    });
                });
                setIndustries(flat);
            })
            .catch(() => {
                console.warn("Failed to fetch industries, using fallback");
                setIndustries(FALLBACK_INDUSTRIES);
            });
    }, []);

    // Dynamic config based on selected industry
    const activeIndustries = industries || FALLBACK_INDUSTRIES;
    const industryConfig = useMemo(() => activeIndustries[industry], [activeIndustries, industry]);

    /**
     * Handles industry selection changes.
     * Automatically locks the geoFilter to 'Detroit Metro' to prevent cross-contamination
     * of markets when switching between different industry taxonomies.
     * 
     * @param {string} newIndustry - The key of the newly selected industry (e.g., 'pizza_all')
     */
    const handleIndustryChange = (newIndustry) => {
        setIndustry(newIndustry);
        setGeoFilter("Detroit Metro"); // Keep Detroit Metro as the default market when changing industries
        setCategoryFilter("");
    };

    /**
     * Generates and downloads a CSV export of the current active dataset.
     * Maps the event properties (dates, severity, confidence) into strict strings.
     * Replaces inner quotes dynamically to prevent CSV column breaking.
     */
    const handleExportCSV = useCallback(() => {
        if (!events || events.length === 0) return;

        const headers = ["Date", "Category", "Title", "Source", "Geography", "Severity", "Confidence", "Strategic Intel"];

        const rows = events.map(e => {
            const date = new Date(e.start_date).toLocaleDateString();
            const category = e.category || "";
            const title = e.title ? e.title.replace(/"/g, '""') : "";
            const source = e.source || "";
            const geo = e.geo_label || "";
            const severity = Math.round(e.severity * 100) + "%";
            const confidence = Math.round(e.confidence * 100) + "%";

            let intel = "";
            if (e.raw_payload?.details?.detailed_impact) {
                intel = e.raw_payload.details.detailed_impact.replace(/"/g, '""');
            }

            return `"${date}","${category}","${title}","${source}","${geo}","${severity}","${confidence}","${intel}"`;
        });

        const csvContent = [headers.join(","), ...rows].join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `remembench_${industry}_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }, [events, industry]);

    /**
     * Triggers the native browser print dialogue configured via `@media print` CSS
     * rules to cleanly export the visualizations onto a static PDF representation.
     */
    const handlePrintPDF = useCallback(() => {
        window.print();
    }, []);

    // Compute display stats
    const totalEvents = stats
        ? Object.values(stats.categories).reduce((s, c) => s + c.count, 0)
        : 0;
    const avgSeverity = stats
        ? (
            Object.values(stats.categories).reduce(
                (s, c) => s + c.avg_severity * c.count,
                0
            ) / Math.max(totalEvents, 1)
        ).toFixed(2)
        : "—";
    const categoryCount = stats ? Object.keys(stats.categories).length : 0;
    const highSeverityCount = events.filter((e) => e.severity >= 0.7).length;

    // Chart data — filtered to current industry's categories
    const pieData = stats
        ? Object.entries(stats.categories).map(([cat, data]) => ({
            name: cat.replace(/_/g, " "),
            value: data.count,
            color: CATEGORY_COLORS[cat] || "#64748b",
        }))
        : [];

    const barData = stats
        ? Object.entries(stats.categories).map(([cat, data]) => ({
            category: cat.replace(/_/g, " "),
            severity: parseFloat((data.avg_severity * 100).toFixed(0)),
            count: data.count,
            fill: CATEGORY_COLORS[cat] || "#64748b",
        }))
        : [];

    const trendData = useMemo(() => {
        if (!events || events.length === 0) return [];
        // Group by YYYY-MM-DD
        const groups = {};
        events.forEach(e => {
            const d = e.start_date.split('T')[0];
            groups[d] = (groups[d] || 0) + 1;
        });
        // Sort chronologically and format
        return Object.keys(groups).sort().map(d => {
            const dateObj = new Date(d + 'T12:00:00Z');
            return {
                date: dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
                count: groups[d]
            };
        });
    }, [events]);

    const handleSaveView = useCallback(() => {
        // In a real app, this would hit a backend endpoint to save to user's profile.
        // For now, we simulate a success state via alert.
        alert(`Saved View:\nIndustry: ${activeIndustries[industry]?.label}\nMarket: ${geoFilter || "All Markets"}\nDates: ${startDate} to ${derivedEndDate}`);
    }, [industry, geoFilter, startDate, derivedEndDate, activeIndustries]);

    return (
        <div style={{ padding: "var(--space-6) var(--space-8)" }}>
            {/* Demo Mode Banner */}
            {isDemo && !hideDemo && (
                <div style={{
                    background: "var(--color-semantic-info-subtle)",
                    borderLeft: "4px solid var(--color-semantic-info)",
                    color: "var(--color-text-primary)",
                    padding: "var(--space-3) var(--space-4)",
                    borderRadius: "var(--radius-sm)",
                    marginBottom: "var(--space-6)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "var(--font-size-sm)"
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-semantic-info)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                        <span>
                            <strong>Demo Mode</strong> — Showing sample {industryConfig.label.toLowerCase()} data. Start the backend to see live data.
                        </span>
                    </div>
                    <button onClick={() => setHideDemo(true)} style={{ background: "none", border: "none", color: "var(--color-text-muted)", cursor: "pointer" }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            )}

            {/* Controls Bar */}
            <div style={{
                background: "var(--color-bg-secondary)", borderRadius: "var(--radius-md)",
                boxShadow: "var(--shadow-sm)", padding: "var(--space-4)", marginBottom: "var(--space-6)"
            }}>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)", alignItems: "flex-end" }}>
                    {/* Industry Switcher */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)", flex: "1 1 180px" }}>
                        <label htmlFor="industry-filter" style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Industry</label>
                        <select
                            id="industry-filter"
                            value={industry}
                            onChange={(e) => handleIndustryChange(e.target.value)}
                            style={{ padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border-default)", background: "var(--color-bg-primary)", color: "var(--color-text-primary)", fontSize: "var(--font-size-sm)", width: "100%", outline: "none" }}
                        >
                            {Object.entries(
                                Object.entries(activeIndustries).reduce((acc, [key, data]) => {
                                    const group = data.group || "other";
                                    if (!acc[group]) acc[group] = [];
                                    acc[group].push({ key, ...data });
                                    return acc;
                                }, {})
                            ).map(([group, items]) => (
                                <optgroup key={group} label={group.toUpperCase()}>
                                    {items.map((item) => (
                                        <option key={item.key} value={item.key}>
                                            {item.icon} {item.label}
                                        </option>
                                    ))}
                                </optgroup>
                            ))}
                        </select>
                    </div>

                    {/* Market Filter */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)", flex: "1 1 180px" }}>
                        <label htmlFor="geo-filter" style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Market</label>
                        <select
                            id="geo-filter"
                            value={geoFilter}
                            onChange={(e) => setGeoFilter(e.target.value)}
                            style={{ padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border-default)", background: "var(--color-bg-primary)", color: "var(--color-text-primary)", fontSize: "var(--font-size-sm)", width: "100%", outline: "none" }}
                        >
                            {industryConfig.markets.map((m) => {
                                const marketName = typeof m === 'string' ? m : m.geo_label;
                                return <option key={marketName} value={marketName}>{marketName}</option>;
                            })}
                        </select>
                    </div>

                    {/* Category Filter */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)", flex: "1 1 180px" }}>
                        <label htmlFor="category-filter" style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Category</label>
                        <select
                            id="category-filter"
                            value={categoryFilter}
                            onChange={(e) => setCategoryFilter(e.target.value)}
                            style={{ padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border-default)", background: "var(--color-bg-primary)", color: "var(--color-text-primary)", fontSize: "var(--font-size-sm)", width: "100%", outline: "none" }}
                        >
                            <option value="">All Categories</option>
                            {industryConfig.categories.map((cat) => (
                                <option key={cat} value={cat}>
                                    {CATEGORY_ICONS[cat] || "📌"} {cat.replace(/_/g, " ")}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Start Date */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)", flex: "0 1 180px" }}>
                        <label htmlFor="start-date" style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
                            Search Window (Start)
                        </label>
                        <input
                            type="date"
                            id="start-date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            style={{ padding: "var(--space-2)", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border-default)", background: "var(--color-bg-primary)", color: "var(--color-text-primary)", fontSize: "var(--font-size-sm)", width: "100%", outline: "none" }}
                        />
                        <div style={{ fontSize: "10px", color: "var(--color-text-muted)", marginTop: "4px" }}>
                            Ends: <strong>{derivedEndDate}</strong> {(!user || user.tier === "free") ? "(+3 Days)" : "(+7 Days)"}
                        </div>
                    </div>
                </div>

                {/* Sub-row for buttons & warnings */}
                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px solid var(--color-border-subtle)" }}>
                    {(!user || user.tier === "free") ? (
                        <div style={{ background: "var(--color-semantic-warning-subtle)", color: "var(--color-semantic-warning)", padding: "var(--space-2) var(--space-4)", borderRadius: "var(--radius-full)", fontSize: "var(--font-size-xs)", display: "flex", alignItems: "center", gap: "var(--space-2)", fontWeight: 500 }}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                            <span>Searching <b>{startDate}</b> through <b>{derivedEndDate}</b> (3 days). <Link href="/pricing" style={{ color: "var(--color-semantic-warning)", textDecoration: "underline", fontWeight: "700" }}>Upgrade</Link> for 7-day searches.</span>
                        </div>
                    ) : (
                        <div style={{ background: "var(--color-semantic-success-subtle)", color: "var(--color-semantic-success)", padding: "var(--space-2) var(--space-4)", borderRadius: "var(--radius-full)", fontSize: "var(--font-size-xs)", display: "flex", alignItems: "center", gap: "var(--space-2)", fontWeight: 500 }}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            <span>Premium Enabled. Searching <b>{startDate}</b> through <b>{derivedEndDate}</b> (7 days).</span>
                        </div>
                    )}

                    <div style={{ display: "flex", gap: "var(--space-2)" }}>
                        <button
                            onClick={handleSaveView}
                            title="Save this view"
                            style={{ background: "transparent", border: "1px solid var(--color-border-default)", padding: "var(--space-2) var(--space-4)", borderRadius: "var(--radius-sm)", color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)", fontWeight: 500, cursor: "pointer", transition: "var(--transition-fast)" }}
                            onMouseEnter={(e) => e.target.style.background = "var(--color-bg-tertiary)"}
                            onMouseLeave={(e) => e.target.style.background = "transparent"}
                        >
                            🔖 Save View
                        </button>
                        <button
                            onClick={handleExportCSV}
                            disabled={loading || isSearchingWeb || events.length === 0}
                            title="Download CSV"
                            style={{ background: "transparent", border: "1px solid var(--color-border-default)", padding: "var(--space-2) var(--space-4)", borderRadius: "var(--radius-sm)", color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)", fontWeight: 500, cursor: (loading || isSearchingWeb || events.length === 0) ? "not-allowed" : "pointer", opacity: (loading || isSearchingWeb || events.length === 0) ? 0.5 : 1, transition: "var(--transition-fast)" }}
                            onMouseEnter={(e) => { if (!(loading || isSearchingWeb || events.length === 0)) e.target.style.background = "var(--color-bg-tertiary)"; }}
                            onMouseLeave={(e) => e.target.style.background = "transparent"}
                        >
                            ⬇️ CSV
                        </button>
                        <button
                            onClick={handlePrintPDF}
                            disabled={loading || isSearchingWeb || events.length === 0}
                            title="Print Dashboard to PDF"
                            style={{ background: "transparent", border: "1px solid var(--color-border-default)", padding: "var(--space-2) var(--space-4)", borderRadius: "var(--radius-sm)", color: "var(--color-text-secondary)", fontSize: "var(--font-size-sm)", fontWeight: 500, cursor: (loading || isSearchingWeb || events.length === 0) ? "not-allowed" : "pointer", opacity: (loading || isSearchingWeb || events.length === 0) ? 0.5 : 1, transition: "var(--transition-fast)" }}
                            onMouseEnter={(e) => { if (!(loading || isSearchingWeb || events.length === 0)) e.target.style.background = "var(--color-bg-tertiary)"; }}
                            onMouseLeave={(e) => e.target.style.background = "transparent"}
                        >
                            📄 PDF
                        </button>
                        <button
                            onClick={loadData}
                            disabled={loading || isSearchingWeb}
                            style={{ background: "var(--color-brand-primary)", border: "none", padding: "var(--space-2) var(--space-5)", borderRadius: "var(--radius-sm)", color: "#ffffff", fontSize: "var(--font-size-sm)", fontWeight: 600, cursor: (loading || isSearchingWeb) ? "not-allowed" : "pointer", opacity: (loading || isSearchingWeb) ? 0.8 : 1, transition: "var(--transition-fast)", boxShadow: "var(--shadow-sm)" }}
                            onMouseEnter={(e) => { if (!(loading || isSearchingWeb)) e.target.style.background = "var(--color-brand-primary-hover)"; }}
                            onMouseLeave={(e) => { if (!(loading || isSearchingWeb)) e.target.style.background = "var(--color-brand-primary)"; }}
                        >
                            {(loading || isSearchingWeb) ? "⏳ Running..." : "▶ Run Report"}
                        </button>
                    </div>
                </div>
            </div>

            <div className="report-layout">
                {/* AI Executive Briefing Banner */}
                {hasRun && (events.length > 0 || isGeneratingBriefing) && !isDemo && (
                    <div style={{
                        gridColumn: "1 / -1",
                        background: "var(--color-bg-card)",
                        border: "1px solid var(--color-border)",
                        boxShadow: "var(--shadow-md)",
                        borderRadius: "12px",
                        padding: "1.5rem",
                        display: "flex",
                        gap: "1rem",
                        alignItems: "flex-start",
                        animation: "fadeInUp 500ms ease-out"
                    }}>
                        <div style={{ fontSize: "1.5rem", animation: isGeneratingBriefing ? "spin 2s linear infinite" : "none" }}>
                            {isGeneratingBriefing ? "🤖" : "⚙️"}
                        </div>
                        <div>
                            <h3 style={{ margin: "0 0 0.5rem 0", color: "var(--color-accent-cyan)", fontSize: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                AI Executive Briefing
                                {isGeneratingBriefing && <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", fontWeight: "normal" }}>Synthesizing {events.length} events...</span>}
                            </h3>
                            {isGeneratingBriefing ? (
                                <p style={{ margin: 0, color: "var(--color-text-muted)", lineHeight: "1.6", fontSize: "0.95rem" }}>
                                    Analyzing market trends, competitive actions, and environmental disruptions...
                                </p>
                            ) : aiBriefing && typeof aiBriefing === 'object' ? (
                                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                    <p style={{ margin: 0, color: "var(--color-text-primary)", lineHeight: "1.6", fontSize: "0.95rem" }}>
                                        {aiBriefing.executive_summary}
                                    </p>

                                    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", fontSize: "0.85rem" }}>
                                        <div style={{ background: "var(--color-bg-glass)", padding: "0.5rem 0.75rem", borderRadius: "0.5rem", border: "1px solid var(--color-border)" }}>
                                            <span style={{ color: "var(--color-text-muted)", marginRight: "0.5rem" }}>Threat Level:</span>
                                            <strong style={{ color: aiBriefing.overall_threat_score > 0.6 ? "#ef4444" : "var(--color-accent-cyan)" }}>
                                                {(aiBriefing.overall_threat_score * 10).toFixed(1)} / 10
                                            </strong>
                                        </div>
                                        <div style={{ background: "var(--color-bg-glass)", padding: "0.5rem 0.75rem", borderRadius: "0.5rem", border: "1px solid var(--color-border)" }}>
                                            <span style={{ color: "var(--color-text-muted)", marginRight: "0.5rem" }}>Sentiment:</span>
                                            <strong style={{ color: aiBriefing.market_sentiment === "Bearish" ? "#ef4444" : "var(--color-accent-cyan)" }}>
                                                {aiBriefing.market_sentiment}
                                            </strong>
                                        </div>
                                    </div>

                                    {aiBriefing.immediate_actions_recommended?.length > 0 && (
                                        <div style={{ background: "rgba(34, 211, 238, 0.05)", padding: "1rem", borderRadius: "0.5rem", borderLeft: "3px solid var(--color-accent-cyan)" }}>
                                            <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "var(--color-text-primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Recommended Actions</h4>
                                            <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--color-text-secondary)", fontSize: "0.9rem", lineHeight: "1.5" }}>
                                                {aiBriefing.immediate_actions_recommended.map((action, idx) => (
                                                    <li key={idx} style={{ marginBottom: "0.25rem" }}>{action}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            ) : aiBriefing && typeof aiBriefing === 'string' ? (
                                // Fallback for error messages generated by the backend catch block
                                <p style={{ margin: 0, color: "var(--color-text-muted)", lineHeight: "1.6", fontSize: "0.95rem" }}>{aiBriefing}</p>
                            ) : (
                                <p style={{ margin: 0, color: "var(--color-text-muted)", lineHeight: "1.6", fontSize: "0.95rem" }}>No briefing available for this context.</p>
                            )}
                        </div>
                    </div>
                )}

                <EventFeed
                    events={events}
                    loading={loading}
                    hasRun={hasRun}
                    isSearchingWeb={isSearchingWeb}
                    searchResultMsg={searchResultMsg}
                    onEventClick={setSelectedEventId}
                />

                <MetricCharts stats={stats} events={events} />
            </div>

            {selectedEventId && (
                <EventDetailsModal
                    eventId={selectedEventId}
                    onClose={() => setSelectedEventId(null)}
                    token={token}
                    API_BASE={API_BASE}
                />
            )}
        </div>
    );
}
