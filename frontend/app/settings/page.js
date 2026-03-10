"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../contexts/AuthContext";
import { API_BASE_URL } from "../lib/api";

export default function SettingsPage() {
    const { user, token, logout } = useAuth();
    const router = useRouter();

    const [webhooks, setWebhooks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Form State
    const [url, setUrl] = useState("");
    const [name, setName] = useState("");
    const [minSeverity, setMinSeverity] = useState("0.7");
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (!token) {
            router.push("/login");
            return;
        }
        fetchWebhooks();
    }, [token, router]);

    const fetchWebhooks = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE_URL}/webhooks/`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) {
                if (res.status === 401) {
                    logout();
                    router.push("/login");
                    return;
                }
                throw new Error("Failed to fetch webhooks");
            }
            const data = await res.json();
            setWebhooks(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateWebhook = async (e) => {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            const res = await fetch(`${API_BASE_URL}/webhooks/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    url,
                    name,
                    min_severity: parseFloat(minSeverity),
                    is_active: true,
                }),
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || "Failed to create webhook");
            }

            // Reset form on success
            setUrl("");
            setName("");
            setMinSeverity("0.7");

            // Refresh list to show the new hook with its secret token
            await fetchWebhooks();
        } catch (err) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDeleteWebhook = async (id) => {
        if (!confirm("Are you sure you want to delete this real-time alert hook?")) return;

        try {
            const res = await fetch(`${API_BASE_URL}/webhooks/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (!res.ok) throw new Error("Failed to delete webhook");

            // Update local state instantly rather than re-fetching
            setWebhooks(webhooks.filter((w) => w.id !== id));
        } catch (err) {
            setError(err.message);
        }
    };

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-900">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-600 border-t-blue-500"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-900 text-gray-100 p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-2">Account Settings</h1>
                <p className="text-gray-400 mb-10">Configure real-time integrations and active system alerts.</p>

                {error && (
                    <div className="mb-6 rounded-md bg-red-900/30 p-4 border border-red-500/50 text-red-200">
                        {error}
                    </div>
                )}

                <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden mb-8">
                    <div className="p-6 border-b border-gray-700">
                        <h2 className="text-xl font-semibold text-white">Create Webhook Alert</h2>
                        <p className="text-sm text-gray-400 mt-1">
                            Push real-time NLP classified Events to Zapier, Make, Slack, or custom MCP servers.
                        </p>
                    </div>

                    <div className="p-6">
                        <form onSubmit={handleCreateWebhook} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">Display Name</label>
                                    <input
                                        type="text"
                                        required
                                        maxLength={255}
                                        placeholder="e.g. Marketing Slack Channel"
                                        className="w-full rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">Target URL</label>
                                    <input
                                        type="url"
                                        required
                                        placeholder="https://hooks.zapier.com/..."
                                        className="w-full rounded-md border border-gray-600 bg-gray-900 px-3 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        value={url}
                                        onChange={(e) => setUrl(e.target.value)}
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">
                                    Trigger Threshold (Minimum Severity)
                                </label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="range"
                                        min="0.0"
                                        max="1.0"
                                        step="0.1"
                                        className="w-48 accent-blue-500"
                                        value={minSeverity}
                                        onChange={(e) => setMinSeverity(e.target.value)}
                                    />
                                    <span className="text-sm font-mono bg-gray-900 px-2 py-1 rounded border border-gray-600">
                                        {minSeverity}
                                    </span>
                                    <span className="text-xs text-gray-400">
                                        (0.0 = All Events, 0.7 = High Impact, 0.9 = Disaster)
                                    </span>
                                </div>
                            </div>

                            <div className="flex justify-end pt-4">
                                <button
                                    type="submit"
                                    disabled={isSubmitting}
                                    className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 transition-colors"
                                >
                                    {isSubmitting ? "Creating..." : "Deploy Webhook"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                {/* Existing Webhooks List */}
                <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                    <div className="p-6 border-b border-gray-700 flex justify-between items-center">
                        <h2 className="text-xl font-semibold text-white">Active Integrations</h2>
                        <span className="text-sm bg-gray-900 border border-gray-600 px-2 py-1 rounded-full text-gray-300">
                            {webhooks.length} / 5
                        </span>
                    </div>

                    {webhooks.length === 0 ? (
                        <div className="p-8 text-center text-gray-400">
                            No active webhooks configured. Create one above to start receiving live pipeline events.
                        </div>
                    ) : (
                        <ul className="divide-y divide-gray-700">
                            {webhooks.map((hook) => (
                                <li key={hook.id} className="p-6 flex flex-col md:flex-row md:items-start justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-3 mb-1">
                                            <div className={`w-2 h-2 rounded-full ${hook.is_active ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                            <h3 className="text-lg font-medium text-white truncate">{hook.name}</h3>
                                            <span className="text-xs font-mono bg-blue-900/30 text-blue-300 border border-blue-800 rounded px-2 py-0.5">
                                                Severity &gt;= {hook.min_severity}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-400 truncate mb-3">📍 {hook.url}</p>

                                        <div className="bg-gray-900 border border-gray-700 rounded p-3 relative">
                                            <p className="text-xs text-gray-500 mb-1">HMAC Payload Verification Secret:</p>
                                            <code className="text-sm text-emerald-400 break-all select-all font-mono">
                                                {hook.secret_token}
                                            </code>
                                        </div>
                                    </div>

                                    <div className="flex shrink-0">
                                        <button
                                            onClick={() => handleDeleteWebhook(hook.id)}
                                            className="text-red-400 hover:text-red-300 hover:bg-red-900/20 px-3 py-1.5 rounded transition-colors text-sm font-medium"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
}
