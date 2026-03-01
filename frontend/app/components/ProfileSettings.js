"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useRouter } from "next/navigation";

export default function ProfileSettings({ onClose, activeIndustries }) {
    const { user, updatePreferences, logout } = useAuth();
    const router = useRouter();

    const [industryPrefs, setIndustryPrefs] = useState("");
    const [marketPrefs, setMarketPrefs] = useState("");
    const [themePrefs, setThemePrefs] = useState("dark");
    const [saving, setSaving] = useState(false);
    const [portalLoading, setPortalLoading] = useState(false);

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

    useEffect(() => {
        if (user?.preferences) {
            setIndustryPrefs(user.preferences.default_industry || "");
            setMarketPrefs(user.preferences.default_market || "");
            setThemePrefs(user.preferences.theme || "dark");
        }
    }, [user]);

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        await updatePreferences({
            default_industry: industryPrefs,
            default_market: marketPrefs || null,
            theme: themePrefs
        });
        setSaving(false);
        onClose(); // Close modal
    };

    const handleManageSubscription = async () => {
        setPortalLoading(true);
        try {
            const token = localStorage.getItem("remembench_token");
            const res = await fetch(`${API_BASE}/billing/create-portal-session?return_url=${window.location.href}`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                window.location.href = data.url; // Redirect to Stripe Portal
            } else {
                router.push("/pricing"); // Fallback if no portal valid
            }
        } catch (error) {
            console.error(error);
        } finally {
            setPortalLoading(false);
        }
    };

    const handleLogout = () => {
        logout();
    };

    if (!user) return null;

    const availableMarkets = industryPrefs && activeIndustries?.[industryPrefs]
        ? activeIndustries[industryPrefs].markets
        : [];

    return (
        <div className="modal-overlay" style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)", zIndex: 100,
            display: "flex", justifyContent: "flex-end"
        }}>
            <div className="slide-out" style={{
                background: "var(--background-paper)", width: "100%", maxWidth: "400px",
                height: "100%", padding: "2rem", display: "flex", flexDirection: "column",
                borderLeft: "1px solid var(--border-color)",
                animation: "slideIn 0.3s ease-out forwards"
            }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
                    <h2>Profile Settings</h2>
                    <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--color-text-muted)", cursor: "pointer", fontSize: "1.5rem" }}>
                        &times;
                    </button>
                </div>

                <div style={{ marginBottom: "2rem", padding: "1rem", background: "var(--background-default)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                    <p style={{ margin: "0 0 0.5rem 0", fontWeight: "600" }}>Account Details</p>
                    <p style={{ margin: "0 0 0.25rem 0", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>{user.first_name} {user.last_name}</p>
                    <p style={{ margin: "0 0 0.5rem 0", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>{user.email}</p>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem" }}>
                        <div style={{ display: "inline-block", padding: "0.25rem 0.5rem", borderRadius: "12px", background: "var(--color-primary)", color: "white", fontSize: "0.75rem", fontWeight: "600" }}>
                            {user.tier.toUpperCase()} PLAN
                        </div>

                        {user.stripe_customer_id ? (
                            <button onClick={handleManageSubscription} disabled={portalLoading} style={{ background: "none", border: "none", color: "var(--color-text-primary)", fontSize: "0.875rem", textDecoration: "underline", cursor: "pointer" }}>
                                {portalLoading ? "Loading..." : "Manage Billing"}
                            </button>
                        ) : (
                            <button onClick={() => { onClose(); router.push("/pricing"); }} style={{ background: "none", border: "none", color: "var(--color-text-primary)", fontSize: "0.875rem", textDecoration: "underline", cursor: "pointer" }}>
                                Upgrade to Pro
                            </button>
                        )}
                    </div>
                </div>

                <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "1.5rem", flexGrow: 1 }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <label style={{ fontSize: "0.875rem" }}>Default Industry</label>
                        <select
                            value={industryPrefs}
                            onChange={(e) => {
                                setIndustryPrefs(e.target.value);
                                setMarketPrefs(""); // Reset market when industry changes
                            }}
                            className="form-select"
                        >
                            {Object.entries(
                                Object.entries(activeIndustries || {}).reduce((acc, [key, data]) => {
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

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <label style={{ fontSize: "0.875rem" }}>Default Market</label>
                        <select
                            value={marketPrefs}
                            onChange={(e) => setMarketPrefs(e.target.value)}
                            disabled={!industryPrefs}
                            className="form-select"
                        >
                            <option value="">None (All Markets)</option>
                            {availableMarkets.map((m) => (
                                <option key={m} value={m}>{m}</option>
                            ))}
                        </select>
                    </div>

                    <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
                        <button type="submit" disabled={saving} className="btn-primary">
                            {saving ? "Saving..." : "Save Preferences"}
                        </button>

                        <button type="button" onClick={handleLogout} className="btn-secondary" style={{ color: "var(--color-danger)", borderColor: "var(--color-danger)" }}>
                            Sign Out
                        </button>
                    </div>
                </form>
            </div>
            <style jsx>{`
                @keyframes slideIn {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
                .form-select {
                    padding: 0.75rem; border-radius: 8px; background: var(--background-default);
                    border: 1px solid var(--border-color); color: var(--color-text-primary);
                }
                .btn-primary {
                    padding: 0.875rem; border-radius: 8px; background: var(--color-text-primary);
                    color: var(--background-default); border: none; font-weight: 600; cursor: pointer;
                }
                .btn-secondary {
                    padding: 0.875rem; border-radius: 8px; background: transparent;
                    color: inherit; border: 1px solid var(--border-color); font-weight: 600; cursor: pointer;
                }
            `}</style>
        </div>
    );
}
