"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "./contexts/AuthContext";
import ProfileSettings from "./components/ProfileSettings";
import EventDetailsModal from "./components/EventDetailsModal";
import Link from "next/link";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend,
} from "recharts";

/* ------------------------------------------------------------------ *
 *  Industry Registry — matches backend's industries.py                *
 *  In production, this would be fetched from GET /api/v1/industries   *
 * ------------------------------------------------------------------ */

const FALLBACK_INDUSTRIES = {
    wireless_retail: {
        label: "Wireless Retail",
        icon: "📱",
        group: "wireless",
        markets: [
            "New York City", "Los Angeles", "Chicago", "Houston",
            "Dallas", "Philadelphia", "Miami", "Atlanta", "Phoenix", "Seattle",
        ],
        categories: [
            "weather", "competitor_promo", "outage", "holiday", "news",
            "internal_promo", "system_issue",
        ],
    },
    pizza_full_service: {
        label: "Pizza — Full Service",
        icon: "🍕",
        group: "pizza",
        markets: [
            "Detroit", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event",
        ],
    },
    pizza_delivery: {
        label: "Pizza — Delivery",
        icon: "🛵",
        group: "pizza",
        markets: [
            "Detroit", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event",
        ],
    },
    pizza_bar: {
        label: "Pizza — Bar & Restaurant",
        icon: "🍺",
        group: "pizza",
        markets: [
            "Detroit", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event",
        ],
    },
    pizza_carryout: {
        label: "Pizza — Carry-Out",
        icon: "📦",
        group: "pizza",
        markets: [
            "Detroit", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event",
        ],
    },
};

/* ------------------------------------------------------------------ *
 *  Constants                                                          *
 * ------------------------------------------------------------------ */

const API_BASE =
    typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
        : "/api/v1";

// Extended color map covering all industries' categories
const CATEGORY_COLORS = {
    weather: "#38bdf8",
    competitor_promo: "#f97316",
    outage: "#ef4444",
    holiday: "#a78bfa",
    news: "#2dd4bf",
    internal_promo: "#6366f1",
    system_issue: "#fb923c",
    delivery_disruption: "#f472b6",
    food_safety: "#dc2626",
    supply_chain: "#fbbf24",
    labor: "#8b5cf6",
    local_event: "#34d399",
};

const CATEGORY_ICONS = {
    weather: "🌦️",
    competitor_promo: "📢",
    outage: "⚠️",
    holiday: "🎉",
    news: "📰",
    internal_promo: "🏷️",
    system_issue: "🔧",
    delivery_disruption: "🚗",
    food_safety: "🏥",
    supply_chain: "📦",
    labor: "👷",
    local_event: "🎪",
};

/* ------------------------------------------------------------------ *
 *  Demo Data — industry-specific samples                              *
 * ------------------------------------------------------------------ */

const WIRELESS_DEMO_EVENTS = [
    {
        category: "weather", subcategory: "blizzard",
        title: "Blizzard: 35cm snowfall in NYC metro area",
        description: "Major winter storm dropped 35cm of snow across the Northeast, severely limiting foot traffic to retail stores for 3 consecutive days.",
        severity: 0.92, confidence: 0.88, geo_label: "New York City", daysAgo: 365 + 45,
    },
    {
        category: "competitor_promo", subcategory: "carrier_announcement",
        title: "[VERIZON] Buy One Get One Free — iPhone 15 Pro",
        description: "Verizon announced aggressive BOGO promotion on iPhone 15 Pro with new line activation, running for 2 weeks nationwide.",
        severity: 0.85, confidence: 0.92, geo_label: "National", daysAgo: 365 + 30,
    },
    {
        category: "holiday", subcategory: "public_holiday",
        title: "Presidents' Day Weekend",
        description: "Federal holiday weekend. Historically one of the top 10 wireless retail weekends due to carrier promotions.",
        severity: 0.55, confidence: 0.95, geo_label: "National", daysAgo: 365 + 20,
    },
    {
        category: "outage", subcategory: "network_outage",
        title: "AT&T Nationwide Network Outage — 12 hours",
        description: "Major AT&T service disruption affected millions of customers. Resulted in surge of walk-in traffic to competitor stores.",
        severity: 0.95, confidence: 0.87, geo_label: "National", daysAgo: 365 + 15,
    },
    {
        category: "news", subcategory: "local_disruption",
        title: "Super Bowl LVIII — Las Vegas",
        description: "Major sporting event drew attention away from retail. Historically reduces non-essential shopping on game day by 15-25%.",
        severity: 0.45, confidence: 0.78, geo_label: "National", daysAgo: 365 + 25,
    },
    {
        category: "weather", subcategory: "extreme_cold",
        title: "Extreme Cold: -18°C low in Chicago",
        description: "Polar vortex conditions brought dangerously cold temperatures to the Midwest, reducing foot traffic by an estimated 40%.",
        severity: 0.78, confidence: 0.85, geo_label: "Chicago", daysAgo: 365 + 40,
    },
];

const PIZZA_DEMO_EVENTS = [
    {
        category: "weather", subcategory: "heavy_snow",
        title: "Heavy Snow: 25cm in Detroit metro",
        description: "Lake-effect snow event dropped 25cm across metro Detroit, shutting down roads and boosting delivery demand while reducing dine-in traffic.",
        severity: 0.82, confidence: 0.9, geo_label: "Detroit", daysAgo: 365 + 35,
    },
    {
        category: "competitor_promo", subcategory: "restaurant_promotion",
        title: "[DOMINOS] 50% Off All Menu-Price Pizzas",
        description: "Domino's launched nationwide 50% off promotion for online orders, running for 2 weeks. Significant competitive pressure on local pizzerias.",
        severity: 0.78, confidence: 0.88, geo_label: "National", daysAgo: 365 + 28,
    },
    {
        category: "holiday", subcategory: "public_holiday",
        title: "Super Bowl Sunday",
        description: "Historically the #1 pizza delivery day of the year. Delivery volume spikes 40-60% over normal Sunday. Critical staffing day.",
        severity: 0.95, confidence: 0.97, geo_label: "National", daysAgo: 365 + 22,
    },
    {
        category: "delivery_disruption", subcategory: "platform_issue",
        title: "DoorDash Platform Outage — Detroit Metro",
        description: "DoorDash experienced a 4-hour outage affecting the Detroit metro area. Third-party delivery orders dropped to zero during window.",
        severity: 0.7, confidence: 0.85, geo_label: "Detroit", daysAgo: 365 + 18,
    },
    {
        category: "food_safety", subcategory: "inspection_or_recall",
        title: "FDA: Mozzarella Cheese Recall — Midwest Region",
        description: "FDA issued recall on mozzarella from a major Midwest distributor due to potential contamination. Affected supply for multiple restaurants.",
        severity: 0.88, confidence: 0.92, geo_label: "Detroit", daysAgo: 365 + 12,
    },
    {
        category: "supply_chain", subcategory: "ingredient_costs",
        title: "Cheese Prices Hit 18-Month High",
        description: "Block cheese prices rose 22% over 6 weeks due to supply constraints. Impacts menu pricing and profit margins for all pizza operators.",
        severity: 0.65, confidence: 0.8, geo_label: "National", daysAgo: 365 + 8,
    },
    {
        category: "labor", subcategory: "staffing",
        title: "Michigan Minimum Wage Increase Takes Effect",
        description: "Michigan minimum wage increased to $12.50/hr. Impacts labor costs for restaurant and delivery operations statewide.",
        severity: 0.6, confidence: 0.95, geo_label: "Detroit", daysAgo: 365 + 3,
    },
    {
        category: "local_event", subcategory: "festival",
        title: "Detroit Auto Show — Downtown Events",
        description: "North American International Auto Show brings 800,000+ visitors to downtown Detroit over 2 weeks. Boosts downtown restaurant traffic significantly.",
        severity: 0.72, confidence: 0.82, geo_label: "Detroit", daysAgo: 365 + 42,
    },
];

function generateDemoData(industry) {
    const isPizza = industry.startsWith("pizza");
    const entries = isPizza ? PIZZA_DEMO_EVENTS : WIRELESS_DEMO_EVENTS;
    const now = new Date();

    return entries.map((entry) => {
        const eventDate = new Date(now);
        eventDate.setDate(eventDate.getDate() - entry.daysAgo);
        return {
            id: crypto.randomUUID(),
            ...entry,
            source: entry.category === "weather" ? "open-meteo" : "gdelt",
            start_date: eventDate.toISOString(),
            end_date: eventDate.toISOString(),
            created_at: now.toISOString(),
            updated_at: now.toISOString(),
            industry,
        };
    });
}

function generateDemoStats(industry) {
    const isPizza = industry.startsWith("pizza");
    if (isPizza) {
        return {
            industry,
            categories: {
                weather: { count: 38, avg_severity: 0.65 },
                competitor_promo: { count: 15, avg_severity: 0.68 },
                holiday: { count: 28, avg_severity: 0.55 },
                delivery_disruption: { count: 12, avg_severity: 0.62 },
                food_safety: { count: 6, avg_severity: 0.78 },
                supply_chain: { count: 9, avg_severity: 0.58 },
                labor: { count: 7, avg_severity: 0.52 },
                local_event: { count: 16, avg_severity: 0.48 },
            },
        };
    }
    return {
        industry,
        categories: {
            weather: { count: 47, avg_severity: 0.68 },
            competitor_promo: { count: 23, avg_severity: 0.72 },
            outage: { count: 8, avg_severity: 0.81 },
            holiday: { count: 34, avg_severity: 0.52 },
            news: { count: 19, avg_severity: 0.41 },
        },
    };
}

/* ------------------------------------------------------------------ *
 *  Sub-Components                                                     *
 * ------------------------------------------------------------------ */

function StatCard({ icon, value, label, color }) {
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

function SeverityBar({ severity }) {
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

function CategoryBadge({ category }) {
    return (
        <span className={`badge badge-${category}`}>
            {CATEGORY_ICONS[category] || "📌"} {(category || "").replace(/_/g, " ")}
        </span>
    );
}

function EventItem({ event, onClick }) {
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
                <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <CategoryBadge category={event.category} />
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

/* ------------------------------------------------------------------ *
 *  Main Dashboard Page                                                *
 * ------------------------------------------------------------------ */

export default function Dashboard() {
    const { user, token } = useAuth();
    const [showSettings, setShowSettings] = useState(false);

    const [industries, setIndustries] = useState(null);
    const [industry, setIndustry] = useState("wireless_retail");
    const [events, setEvents] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [geoFilter, setGeoFilter] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("");
    const [isDemo, setIsDemo] = useState(false);
    const [isSearchingWeb, setIsSearchingWeb] = useState(false);
    const [selectedEventId, setSelectedEventId] = useState(null);

    const defaultStartDate = useMemo(() => {
        const d = new Date();
        d.setDate(d.getDate() - 3);
        return d.toISOString().split('T')[0];
    }, []);
    const defaultEndDate = useMemo(() => {
        const d = new Date();
        return d.toISOString().split('T')[0];
    }, []);

    const [startDate, setStartDate] = useState(defaultStartDate);
    const [endDate, setEndDate] = useState(defaultEndDate);

    // Apply user preferences on load
    useEffect(() => {
        if (user?.preferences) {
            if (user.preferences.default_industry) {
                setIndustry(user.preferences.default_industry);
            }
            if (user.preferences.default_market) {
                setGeoFilter(user.preferences.default_market);
            }
        }
    }, [user]);

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

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            // Setup parameters
            const isPremium = user?.tier === "pro";

            const params = new URLSearchParams({
                limit: "50",
                industry,
            });

            // Handle date ranges and constraints
            if (!isPremium) {
                const start = new Date(startDate || defaultStartDate);
                const end = new Date(endDate || defaultEndDate);
                const diffTime = end.getTime() - start.getTime();
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays > 3 || diffDays < 0) {
                    // Limit the query parameters without mutating the user's UI state mid-selection
                    const newStart = new Date(end);
                    newStart.setDate(newStart.getDate() - 3);
                    const formattedStart = newStart.toISOString().split('T')[0];
                    params.set("start_date", formattedStart);
                } else {
                    params.set("start_date", start.toISOString().split('T')[0]);
                }
                params.set("end_date", end.toISOString().split('T')[0]);
            } else {
                if (startDate) params.set("start_date", startDate);
                if (endDate) params.set("end_date", endDate);
            }

            if (geoFilter) params.set("geo_label", geoFilter);
            if (categoryFilter) params.set("category", categoryFilter);

            const headers = token ? { "Authorization": `Bearer ${token}` } : {};

            // Synchronize parameters for the summary endpoint so UI matches the exact range requested
            const statsParams = new URLSearchParams(params);
            statsParams.delete("limit");

            const [eventsRes, statsRes] = await Promise.all([
                fetch(`${API_BASE}/events/?${params}`, { headers }).then((r) => {
                    // 401 unauth will fall through to demo data gracefully if required
                    if (!r.ok) throw new Error("API unavailable");
                    return r.json();
                }),
                fetch(
                    `${API_BASE}/events/stats/summary?${statsParams}`,
                    { headers }
                ).then((r) => {
                    if (!r.ok) throw new Error("API unavailable");
                    return r.json();
                }),
            ]);

            if (eventsRes.length === 0 && !isDemo) {
                setIsSearchingWeb(true);
                try {
                    const runParams = new URLSearchParams();
                    runParams.set("start_date", params.get("start_date"));
                    runParams.set("end_date", params.get("end_date"));
                    runParams.set("industry", industry);
                    if (geoFilter) runParams.set("geo_label", geoFilter);

                    await fetch(`${API_BASE}/ingestion/run?${runParams}`, {
                        method: "POST",
                        headers
                    });

                    // Re-fetch data after ingestion finishes
                    const [newEventsRes, newStatsRes] = await Promise.all([
                        fetch(`${API_BASE}/events/?${params}`, { headers }).then((r) => r.json()),
                        fetch(`${API_BASE}/events/stats/summary?${statsParams}`, { headers }).then((r) => r.json()),
                    ]);
                    setEvents(newEventsRes);
                    setStats(newStatsRes);
                } catch (e) {
                    console.error("Live web search failed:", e);
                    setEvents([]);
                    setStats({ categories: {} });
                } finally {
                    setIsSearchingWeb(false);
                }
            } else {
                setEvents(eventsRes);
                setStats(statsRes);
            }
            setIsDemo(false);
        } catch {
            // Backend not running — use industry-specific demo data
            const demoEvents = generateDemoData(industry);
            const filtered = demoEvents.filter((e) => {
                if (geoFilter && e.geo_label !== geoFilter && e.geo_label !== "National") return false;
                if (categoryFilter && e.category !== categoryFilter) return false;
                return true;
            });
            setEvents(filtered);
            setStats(generateDemoStats(industry));
            setIsDemo(true);
        } finally {
            setLoading(false);
        }
    }, [industry, geoFilter, categoryFilter, token, user, startDate, endDate, defaultStartDate, defaultEndDate]);

    useEffect(() => {
        loadData();
    }, [loadData]);

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
                            background: "var(--color-text-primary)", color: "var(--background-default)",
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
                    style={{ alignSelf: "flex-end", marginLeft: "auto" }}
                >
                    <button className="btn btn-primary" onClick={loadData}>
                        🔄 Refresh
                    </button>
                </div>
            </div>

            {/* Stat Cards */}
            <div className="stats-grid">
                <StatCard
                    icon="📊"
                    value={totalEvents}
                    label="Total Events"
                    color="var(--color-accent-cyan)"
                />
                <StatCard
                    icon="🔴"
                    value={highSeverityCount}
                    label="High Impact"
                    color="var(--color-accent-rose)"
                />
                <StatCard
                    icon="📈"
                    value={avgSeverity}
                    label="Avg Impact"
                    color="var(--color-accent-amber)"
                />
                <StatCard
                    icon="📂"
                    value={categoryCount}
                    label="Categories"
                    color="var(--color-accent-emerald)"
                />
            </div>

            {/* Dashboard Grid */}
            <div className="dashboard-grid">
                {/* Category Distribution Chart */}
                <div className="card">
                    <div className="card-header">
                        <div>
                            <div className="card-title">Impact by Category</div>
                            <div className="card-subtitle">
                                Average impact score per event type
                            </div>
                        </div>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={barData} layout="vertical">
                                <CartesianGrid
                                    strokeDasharray="3 3"
                                    stroke="rgba(255,255,255,0.06)"
                                />
                                <XAxis
                                    type="number"
                                    domain={[0, 100]}
                                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                                    tickFormatter={(v) => `${v}%`}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="category"
                                    width={130}
                                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: "#1e293b",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        borderRadius: 8,
                                        color: "#f1f5f9",
                                    }}
                                    formatter={(value) => [`${value}%`, "Avg Impact"]}
                                />
                                <Bar
                                    dataKey="severity"
                                    radius={[0, 6, 6, 0]}
                                    maxBarSize={28}
                                >
                                    {barData.map((entry, idx) => (
                                        <Cell key={idx} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Category Pie Chart */}
                <div className="card">
                    <div className="card-header">
                        <div>
                            <div className="card-title">Event Distribution</div>
                            <div className="card-subtitle">By impact category</div>
                        </div>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={55}
                                    outerRadius={90}
                                    paddingAngle={3}
                                    dataKey="value"
                                    stroke="none"
                                >
                                    {pieData.map((entry, idx) => (
                                        <Cell key={idx} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{
                                        background: "#1e293b",
                                        border: "1px solid rgba(255,255,255,0.1)",
                                        borderRadius: 8,
                                        color: "#f1f5f9",
                                    }}
                                />
                                <Legend
                                    iconType="circle"
                                    iconSize={8}
                                    wrapperStyle={{ fontSize: 12, color: "#94a3b8" }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Impact Timeline */}
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
                ) : isSearchingWeb ? (
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
                    <div className="event-list">
                        {events.map((event) => (
                            <EventItem
                                key={event.id}
                                event={event}
                                onClick={() => setSelectedEventId(event.id)}
                            />
                        ))}
                    </div>
                )}
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
