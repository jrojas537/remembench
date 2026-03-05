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

export default function Dashboard() {
    const { user, token } = useAuth();
    const [showSettings, setShowSettings] = useState(false);

    const [industries, setIndustries] = useState(null);
    const [industry, setIndustry] = useState("pizza_all");

    // We defer hook variables until default dates are computed
    const [geoFilter, setGeoFilter] = useState("Detroit Metro");
    const [categoryFilter, setCategoryFilter] = useState("");
    const [selectedEventId, setSelectedEventId] = useState(null);

    const { defaultStart, defaultEnd } = useMemo(() => {
        // Find equivalent weekend map from 2026 -> 2025
        const today = new Date();
        const dayOfWeek = today.getDay(); // 0 is Sunday, 5 is Friday
        let daysToFriday = 5 - dayOfWeek;
        if (daysToFriday < 0) daysToFriday += 7;

        // Find next Friday in current timeline
        const nextFriday = new Date(today);
        nextFriday.setDate(today.getDate() + daysToFriday);

        // Shift to target historical year (2025)
        const lastYearFridayRaw = new Date(2025, nextFriday.getMonth(), nextFriday.getDate());

        // Align day of week correctly (shift forward to nearest Friday)
        const lastYearDayOfWeek = lastYearFridayRaw.getDay();
        let shiftDays = 5 - lastYearDayOfWeek;
        if (shiftDays > 3) shiftDays -= 7;
        if (shiftDays < -3) shiftDays += 7;

        const alignedFriday2025 = new Date(lastYearFridayRaw);
        alignedFriday2025.setDate(lastYearFridayRaw.getDate() + shiftDays);

        const alignedEnd2025 = new Date(alignedFriday2025);
        alignedEnd2025.setDate(alignedFriday2025.getDate() + 6); // 7-day window

        return {
            defaultStart: alignedFriday2025.toISOString().split('T')[0],
            defaultEnd: alignedEnd2025.toISOString().split('T')[0],
        }
    }, []);

    const [startDate, setStartDate] = useState(defaultStart);
    const [endDate, setEndDate] = useState(defaultEnd);

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
        endDate,
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

    // Handle manual industry change
    const handleIndustryChange = (newIndustry) => {
        setIndustry(newIndustry);
        setGeoFilter(""); // Reset only on manual change
        setCategoryFilter("");
    };

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
        alert(`Saved View:\nIndustry: ${activeIndustries[industry]?.label}\nMarket: ${geoFilter || "All Markets"}\nDates: ${startDate} to ${endDate}`);
    }, [industry, geoFilter, startDate, endDate, activeIndustries]);

    return (
        <>
            {showSettings && (
                <ProfileSettings
                    onClose={() => setShowSettings(false)}
                    activeIndustries={activeIndustries}
                />
            )}

            {/* Auth Meta Bar */}
            <div style={{
                display: "flex", justifyContent: "flex-end", padding: "0.5rem 1.5rem",
                borderBottom: "1px solid var(--border-color)", background: "var(--background-paper)",
                fontSize: "0.875rem", gap: "1rem", alignItems: "center"
            }}>
                {user ? (
                    <>
                        <span style={{ color: "var(--color-text-muted)" }}>
                            Signed in as <strong>{user.first_name || user.email}</strong>
                        </span>
                        <button
                            onClick={() => setShowSettings(true)}
                            style={{
                                background: "none", border: "1px solid var(--border-color)",
                                padding: "0.25rem 0.75rem", borderRadius: "4px",
                                color: "var(--color-text-primary)", cursor: "pointer"
                            }}
                        >
                            ⚙️ Profile / Preferences
                        </button>
                    </>
                ) : (
                    <>
                        <span style={{ color: "var(--color-text-muted)" }}>Browsing in public mode</span>
                        <Link href="/login" style={{
                            background: "var(--color-text-primary)", color: "#ffffff",
                            padding: "0.25rem 0.75rem", borderRadius: "4px", textDecoration: "none",
                            fontWeight: "600"
                        }}>
                            Log In
                        </Link>
                    </>
                )}
            </div>
            {/* Demo Mode Banner */}
            {isDemo && (
                <div className="demo-banner">
                    💡 <strong>Demo Mode</strong> — Showing sample {industryConfig.label.toLowerCase()} data.
                    Start the backend to see live data.
                </div>
            )}

            {/* Controls Bar */}
            <div className="controls-bar">
                {/* Industry Switcher — first position */}
                <div className="control-group">
                    <label htmlFor="industry-filter">Industry</label>
                    <select
                        id="industry-filter"
                        value={industry}
                        onChange={(e) => handleIndustryChange(e.target.value)}
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

                {/* Market Filter — dynamic per industry */}
                <div className="control-group">
                    <label htmlFor="geo-filter">Market</label>
                    <select
                        id="geo-filter"
                        value={geoFilter}
                        onChange={(e) => setGeoFilter(e.target.value)}
                    >
                        <option value="">All Markets</option>
                        {industryConfig.markets.map((m) => {
                            const marketName = typeof m === 'string' ? m : m.geo_label;
                            return <option key={marketName} value={marketName}>{marketName}</option>;
                        })}
                    </select>
                </div>

                {/* Category Filter — dynamic per industry */}
                <div className="control-group">
                    <label htmlFor="category-filter">Category</label>
                    <select
                        id="category-filter"
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                    >
                        <option value="">All Categories</option>
                        {industryConfig.categories.map((cat) => (
                            <option key={cat} value={cat}>
                                {CATEGORY_ICONS[cat] || "📌"} {cat.replace(/_/g, " ")}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="control-group">
                    <label htmlFor="start-date">Start Date</label>
                    <input
                        type="date"
                        id="start-date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        style={{ padding: "0.5rem", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--background-paper)", color: "var(--color-text-primary)" }}
                    />
                </div>
                <div className="control-group">
                    <label htmlFor="end-date">End Date</label>
                    <input
                        type="date"
                        id="end-date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        style={{ padding: "0.5rem", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--background-paper)", color: "var(--color-text-primary)" }}
                    />
                </div>

                {!user || user.tier === "free" ? (
                    <div className="control-group" style={{ display: "flex", alignItems: "center" }}>
                        <div style={{ background: "rgba(245, 158, 11, 0.1)", color: "#d97706", padding: "0.5rem 1rem", borderRadius: "8px", fontSize: "0.875rem", display: "flex", flexDirection: "column", gap: "0.25rem", alignItems: "flex-start", maxWidth: "250px" }}>
                            <span>🔒 Standard accounts are limited to a <b>3-day</b> search window.</span>
                            <Link href="/pricing" style={{ color: "var(--color-primary)", textDecoration: "underline", fontWeight: "600" }}>Upgrade for unlimited range.</Link>
                        </div>
                    </div>
                ) : null}

                <div
                    className="control-group"
                    style={{ alignSelf: "flex-end", marginLeft: "auto", flexDirection: "row", gap: "0.5rem" }}
                >
                    <button
                        className="btn"
                        onClick={handleSaveView}
                        style={{ padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid var(--color-border)", background: "var(--color-bg-glass)", color: "var(--color-accent-indigo)", cursor: "pointer", fontWeight: "600", transition: "background 0.2s" }}
                        title="Save this view to your profile"
                    >
                        🔖 Save View
                    </button>
                    <button
                        className="btn"
                        onClick={handleExportCSV}
                        disabled={loading || isSearchingWeb || events.length === 0}
                        style={{ padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid var(--color-border)", background: "var(--color-bg-glass)", color: "var(--color-text-primary)", cursor: (loading || isSearchingWeb || events.length === 0) ? "not-allowed" : "pointer", opacity: (loading || isSearchingWeb || events.length === 0) ? 0.5 : 1 }}
                        title="Download Data as CSV"
                    >
                        ⬇️ CSV
                    </button>
                    <button
                        className="btn"
                        onClick={handlePrintPDF}
                        disabled={loading || isSearchingWeb || events.length === 0}
                        style={{ padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid var(--color-border)", background: "var(--color-bg-glass)", color: "var(--color-text-primary)", cursor: (loading || isSearchingWeb || events.length === 0) ? "not-allowed" : "pointer", opacity: (loading || isSearchingWeb || events.length === 0) ? 0.5 : 1 }}
                        title="Print Dashboard to PDF"
                    >
                        📄 PDF
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={loadData}
                        disabled={loading || isSearchingWeb}
                        style={{ minWidth: "150px", opacity: (loading || isSearchingWeb) ? 0.8 : 1 }}
                    >
                        {(loading || isSearchingWeb) ? "⏳ Running..." : "▶ Run Report"}
                    </button>
                </div>
            </div>

            <div className="report-layout">
                {/* AI Executive Briefing Banner */}
                {hasRun && (events.length > 0 || isGeneratingBriefing) && !isDemo && (
                    <div style={{
                        gridColumn: "1 / -1",
                        background: "var(--color-bg-card)",
                        backdropFilter: "blur(16px)",
                        border: "1px solid var(--color-border)",
                        boxShadow: "var(--shadow-md)",
                        borderRadius: "1rem",
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
        </>
    );
}
