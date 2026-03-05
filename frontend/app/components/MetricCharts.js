import React, { useMemo } from 'react';
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
    LineChart,
    Line,
} from "recharts";
import { CATEGORY_COLORS } from "../lib/constants";
import { StatCard } from "./UIComponents";

export default function MetricCharts({ stats, events }) {
    // Compute display stats securely mapping optional chains protecting against arbitrary API responses
    const totalEvents = stats?.categories
        ? Object.values(stats.categories).reduce((s, c) => s + (c.count || 0), 0)
        : 0;

    const avgSeverity = stats?.categories
        ? (
            Object.values(stats.categories).reduce(
                (s, c) => s + (c.avg_severity || 0) * (c.count || 0),
                0
            ) / Math.max(totalEvents, 1)
        ).toFixed(2)
        : "—";

    const categoryCount = stats?.categories ? Object.keys(stats.categories).length : 0;
    const highSeverityCount = events?.filter ? events.filter((e) => (e.severity || 0) >= 0.7).length : 0;

    // Chart data — filtered to current industry's categories
    const pieData = stats?.categories
        ? Object.entries(stats.categories).map(([cat, data]) => ({
            name: cat.replace(/_/g, " "),
            value: data.count || 0,
            color: CATEGORY_COLORS[cat] || "#64748b",
        }))
        : [];

    const barData = stats?.categories
        ? Object.entries(stats.categories).map(([cat, data]) => ({
            category: cat.replace(/_/g, " "),
            severity: parseFloat(((data.avg_severity || 0) * 100).toFixed(0)),
            count: data.count || 0,
            fill: CATEGORY_COLORS[cat] || "#64748b",
        }))
        : [];

    const trendData = useMemo(() => {
        if (!events || !Array.isArray(events) || events.length === 0) return [];
        // Group by YYYY-MM-DD
        const groups = {};
        events.forEach(e => {
            if (!e || !e.start_date) return;
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

    return (
        <div className="report-content-right">
            {/* Stat Cards */}
            <div className="stats-grid">
                <StatCard icon="📊" value={totalEvents} label="Total Events" color="var(--color-accent-cyan)" />
                <StatCard icon="🔴" value={highSeverityCount} label="High Impact" color="var(--color-accent-rose)" />
                <StatCard icon="📈" value={avgSeverity} label="Avg Impact" color="var(--color-accent-amber)" />
                <StatCard icon="📂" value={categoryCount} label="Categories" color="var(--color-accent-emerald)" />
            </div>

            {/* Event Velocity Trend */}
            <div className="card">
                <div className="card-header">
                    <div>
                        <div className="card-title">Event Velocity</div>
                        <div className="card-subtitle">
                            Volume of events over the selected period
                        </div>
                    </div>
                </div>
                <div className="chart-container" style={{ height: "200px" }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#f1f5f9" }} />
                            <Line type="monotone" dataKey="count" stroke="var(--color-accent-indigo)" strokeWidth={3} dot={{ r: 4, fill: "var(--color-bg-card)", strokeWidth: 2, stroke: "var(--color-accent-indigo)" }} activeDot={{ r: 6 }} name="Event Count" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

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
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                            <XAxis type="number" domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                            <YAxis type="category" dataKey="category" width={130} tick={{ fill: "#94a3b8", fontSize: 12 }} />
                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#f1f5f9" }} formatter={(value) => [`${value}%`, "Avg Impact"]} />
                            <Bar dataKey="severity" radius={[0, 6, 6, 0]} maxBarSize={28}>
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
                            <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value" stroke="none">
                                {pieData.map((entry, idx) => (
                                    <Cell key={idx} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#f1f5f9" }} />
                            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
