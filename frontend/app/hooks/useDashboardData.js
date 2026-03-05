"use client";

import { useState, useCallback } from "react";
import { API_BASE, generateDemoData, generateDemoStats } from "../lib/constants";

export function useDashboardData({
    industry,
    geoFilter,
    categoryFilter,
    startDate,
    endDate,
    defaultStart,
    defaultEnd,
    user,
    token
}) {
    const [events, setEvents] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [hasRun, setHasRun] = useState(false);
    const [isDemo, setIsDemo] = useState(false);
    const [isSearchingWeb, setIsSearchingWeb] = useState(false);
    const [searchResultMsg, setSearchResultMsg] = useState(null);
    const [aiBriefing, setAiBriefing] = useState(null);
    const [isGeneratingBriefing, setIsGeneratingBriefing] = useState(false);

    const loadData = useCallback(async () => {
        setLoading(true);
        setHasRun(true);
        setSearchResultMsg(null);

        try {
            // Setup parameters
            const isPremium = user?.tier === "pro";

            const params = new URLSearchParams({
                limit: "50",
                industry,
            });

            // Handle date ranges and constraints
            if (!isPremium) {
                const start = new Date(startDate || defaultStart);
                const end = new Date(endDate || defaultEnd);
                const diffTime = end.getTime() - start.getTime();
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays > 7 || diffDays < 0) {
                    // Limit the query parameters without mutating the user's UI state mid-selection
                    const newStart = new Date(end);
                    newStart.setDate(newStart.getDate() - 7);
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

            // Show immediate results from DB if any exist (e.g. weather)
            setEvents(eventsRes || []);
            setStats(statsRes || { categories: {} });
            setLoading(false);

            if (!isDemo) {
                setIsSearchingWeb(true);
                try {
                    const runParams = new URLSearchParams();
                    runParams.set("start_date", params.get("start_date"));
                    runParams.set("end_date", params.get("end_date"));
                    runParams.set("industry", industry);
                    if (geoFilter) runParams.set("geo_label", geoFilter);

                    const submitRes = await fetch(`${API_BASE}/ingestion/run?${runParams}`, {
                        method: "POST",
                        headers
                    });

                    if (submitRes.ok) {
                        const submitData = await submitRes.json();

                        // Check if it was queued (and not immediately cached)
                        if (submitData.status === "queued" && submitData.task_id) {
                            let isDone = false;
                            let attempts = 0;
                            // Poll every 3 seconds for up to 3 minutes (60 attempts)
                            while (!isDone && attempts < 60) {
                                await new Promise(resolve => setTimeout(resolve, 3000));
                                const pollRes = await fetch(`${API_BASE}/ingestion/task/${submitData.task_id}`, { headers });

                                if (pollRes.ok) {
                                    const pollData = await pollRes.json();
                                    if (pollData.status === "SUCCESS" || pollData.status === "FAILURE") {
                                        isDone = true;
                                        if (pollData.status === "FAILURE") {
                                            console.error("Background ingestion failed.");
                                        }
                                    }
                                }
                                attempts++;
                            }
                        }
                    }

                    // Re-fetch data after ingestion finishes (now with new web events)
                    const [newEventsRes, newStatsRes] = await Promise.all([
                        fetch(`${API_BASE}/events/?${params}`, { headers }).then((r) => r.json()),
                        fetch(`${API_BASE}/events/stats/summary?${statsParams}`, { headers }).then((r) => r.json()),
                    ]);

                    const newEventsCount = newEventsRes?.length || 0;
                    const oldEventsCount = eventsRes?.length || 0;
                    if (newEventsCount <= oldEventsCount) {
                        setSearchResultMsg("Live web search complete. No new events found.");
                        setTimeout(() => setSearchResultMsg(null), 5000);
                    } else {
                        setSearchResultMsg(`Found ${newEventsCount - oldEventsCount} new events from the web!`);
                        setTimeout(() => setSearchResultMsg(null), 4000);
                    }

                    setEvents(newEventsRes || []);
                    setStats(newStatsRes || { categories: {} });

                    // Generate AI Briefing
                    setIsGeneratingBriefing(true);
                    try {
                        const briefRes = await fetch(`${API_BASE}/events/briefing`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                ...headers
                            },
                            body: JSON.stringify({
                                industry: industry,
                                events: newEventsRes || []
                            })
                        });
                        const briefData = await briefRes.json();
                        setAiBriefing(briefData.briefing);
                    } catch (e) {
                        console.error("AI Briefing failed:", e);
                        setAiBriefing("Could not generate briefing at this time.");
                    } finally {
                        setIsGeneratingBriefing(false);
                    }
                } catch (e) {
                    console.error("Live web search failed:", e);
                    setSearchResultMsg("Web search timed out or encountered an error.");
                    setTimeout(() => setSearchResultMsg(null), 5000);
                } finally {
                    setIsSearchingWeb(false);
                }
            }
            setIsDemo(false);
        } catch {
            // Backend not running — use industry-specific demo data
            const demoEvents = generateDemoData(industry);
            const filtered = demoEvents.filter((e) => {
                if (geoFilter && e.geo_label !== geoFilter && e.geo_label !== "National") return false;
                // Note: The original page.js un-pinned the category filter before load, so we don't strictly need to filter here on initial load, but for completeness or demo mode updates:
                if (categoryFilter && e.category !== categoryFilter) return false;
                return true;
            });
            setEvents(filtered);
            setStats(generateDemoStats(industry));
            setIsDemo(true);
        } finally {
            setLoading(false);
        }
    }, [industry, geoFilter, categoryFilter, token, user, startDate, endDate, defaultStart, defaultEnd, isDemo]);

    return {
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
    };
}
