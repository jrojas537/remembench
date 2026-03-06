"use client";

import React, { useMemo, useState, useEffect } from 'react';
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
import { useTheme } from 'next-themes';
import { StatCard } from "./UIComponents";

export default function MetricCharts({ stats, events }) {
    const { resolvedTheme } = useTheme();
    const [themeColors, setThemeColors] = useState({
        textMuted: "#64748b",
        textPrimary: "#0f172a",
        border: "#e2e8f0",
        bgSecondary: "#ffffff",
        brandPrimary: "#4f46e5",
        semanticSuccess: "#10b981",
        semanticWarning: "#f59e0b",
        semanticDanger: "#ef4444",
        semanticInfo: "#3b82f6"
    });

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const style = getComputedStyle(document.documentElement);
        setThemeColors({
            textMuted: style.getPropertyValue('--color-text-muted').trim() || "#64748b",
            textPrimary: style.getPropertyValue('--color-text-primary').trim() || "#0f172a",
            border: style.getPropertyValue('--color-border-subtle').trim() || "#e2e8f0",
            bgSecondary: style.getPropertyValue('--color-bg-secondary').trim() || "#ffffff",
            brandPrimary: style.getPropertyValue('--color-brand-primary').trim() || "#4f46e5",
            semanticSuccess: style.getPropertyValue('--color-semantic-success').trim() || "#10b981",
            semanticWarning: style.getPropertyValue('--color-semantic-warning').trim() || "#f59e0b",
            semanticDanger: style.getPropertyValue('--color-semantic-danger').trim() || "#ef4444",
            semanticInfo: style.getPropertyValue('--color-semantic-info').trim() || "#3b82f6"
        });
    }, [resolvedTheme]);

    const getSemanticColor = (category) => {
        const catStr = (category || "").toLowerCase();
        if (catStr.includes("outage") || catStr.includes("disruption") || catStr.includes("strike") || catStr.includes("scandal")) return themeColors.semanticDanger;
        else if (catStr.includes("promo") || catStr.includes("marketing") || catStr.includes("earnings") || catStr.includes("price")) return themeColors.semanticInfo;
        else if (catStr.includes("weather") || catStr.includes("hurricane") || catStr.includes("storm")) return themeColors.semanticWarning;
        else if (catStr.includes("holiday") || catStr.includes("sports") || catStr.includes("entertainment") || catStr.includes("product")) return themeColors.semanticSuccess;
        return themeColors.textMuted;
    };

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

    const pieData = stats?.categories
        ? Object.entries(stats.categories).map(([cat, data]) => ({
            name: cat.replace(/_/g, " "),
            value: data.count || 0,
            color: getSemanticColor(cat),
        }))
        : [];

    const barData = stats?.categories
        ? Object.entries(stats.categories).map(([cat, data]) => ({
            category: cat.replace(/_/g, " "),
            severity: parseFloat(((data.avg_severity || 0) * 100).toFixed(0)),
            count: data.count || 0,
            fill: getSemanticColor(cat),
        }))
        : [];

    const trendData = useMemo(() => {
        if (!events || !Array.isArray(events) || events.length === 0) return [];
        const groups = {};
        events.forEach(e => {
            if (!e || !e.start_date) return;
            const d = e.start_date.split('T')[0];
            groups[d] = (groups[d] || 0) + 1;
        });
        return Object.keys(groups).sort().map(d => {
            const dateObj = new Date(d + 'T12:00:00Z');
            return {
                date: dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
                count: groups[d]
            };
        });
    }, [events]);

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", width: "320px", flexShrink: 0 }}>
            {/* Stat Cards - strict 2x2 Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "var(--space-4)" }}>
                <StatCard icon="📊" value={totalEvents} label="Total Events" />
                <StatCard icon="🔴" value={highSeverityCount} label="High Impact" />
                <StatCard icon="📈" value={avgSeverity} label="Avg Impact" />
                <StatCard icon="📂" value={categoryCount} label="Categories" />
            </div>

            {/* Event Velocity Trend */}
            <div style={{
                background: "var(--color-bg-secondary)", borderRadius: "var(--radius-md)",
                boxShadow: "var(--shadow-sm)", padding: "var(--space-5)", border: "1px solid var(--color-border-subtle)",
                display: "flex", flexDirection: "column", gap: "var(--space-4)"
            }}>
                <div>
                    <h3 style={{ margin: "0 0 var(--space-1) 0", fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--color-text-primary)" }}>Event Velocity</h3>
                    <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>Volume of events over the selected period</p>
                </div>
                <div style={{ height: "200px" }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke={themeColors.border} vertical={false} />
                            <XAxis dataKey="date" tick={{ fill: themeColors.textMuted, fontSize: 12 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: themeColors.textMuted, fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                            <Tooltip contentStyle={{ background: themeColors.bgSecondary, border: `1px solid ${themeColors.border}`, borderRadius: 8, color: themeColors.textPrimary }} />
                            <Line type="monotone" dataKey="count" stroke={themeColors.brandPrimary} strokeWidth={3} dot={{ r: 4, fill: themeColors.bgSecondary, strokeWidth: 2, stroke: themeColors.brandPrimary }} activeDot={{ r: 6 }} name="Event Count" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Category Distribution Chart */}
            <div style={{
                background: "var(--color-bg-secondary)", borderRadius: "var(--radius-md)",
                boxShadow: "var(--shadow-sm)", padding: "var(--space-5)", border: "1px solid var(--color-border-subtle)",
                display: "flex", flexDirection: "column", gap: "var(--space-4)"
            }}>
                <div>
                    <h3 style={{ margin: "0 0 var(--space-1) 0", fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--color-text-primary)" }}>Impact by Category</h3>
                    <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>Average impact score per event type</p>
                </div>
                <div style={{ height: "220px" }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={barData} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke={themeColors.border} horizontal={false} />
                            <XAxis type="number" domain={[0, 100]} tick={{ fill: themeColors.textMuted, fontSize: 12 }} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
                            <YAxis type="category" dataKey="category" width={110} tick={{ fill: themeColors.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
                            <Tooltip contentStyle={{ background: themeColors.bgSecondary, border: `1px solid ${themeColors.border}`, borderRadius: 8, color: themeColors.textPrimary }} formatter={(value) => [`${value}%`, "Avg Impact"]} />
                            <Bar dataKey="severity" radius={[0, 4, 4, 0]} maxBarSize={20}>
                                {barData.map((entry, idx) => (
                                    <Cell key={idx} fill={entry.fill} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Category Pie Chart */}
            <div style={{
                background: "var(--color-bg-secondary)", borderRadius: "var(--radius-md)",
                boxShadow: "var(--shadow-sm)", padding: "var(--space-5)", border: "1px solid var(--color-border-subtle)",
                display: "flex", flexDirection: "column", gap: "var(--space-4)"
            }}>
                <div>
                    <h3 style={{ margin: "0 0 var(--space-1) 0", fontSize: "var(--font-size-sm)", fontWeight: 600, color: "var(--color-text-primary)" }}>Event Distribution</h3>
                    <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>By relative occurrence count</p>
                </div>
                <div style={{ height: "220px" }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value" stroke="none">
                                {pieData.map((entry, idx) => (
                                    <Cell key={idx} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip contentStyle={{ background: themeColors.bgSecondary, border: `1px solid ${themeColors.border}`, borderRadius: 8, color: themeColors.textPrimary }} />
                            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: themeColors.textMuted }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
