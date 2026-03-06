"use client";

import { useAuth } from "../contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useState } from "react";

const API_BASE =
    typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
        : "/api/v1";

export default function PricingPage() {
    const { user, token } = useAuth();
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleUpgrade = async (lookupKey) => {
        if (!user) {
            router.push("/login?redirect=/pricing");
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/billing/create-checkout-session?lookup_key=${lookupKey}&success_url=${window.location.origin}/pricing&cancel_url=${window.location.origin}/pricing`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Failed to initiate checkout");
            }

            // Redirect directly to Stripe Checkout
            window.location.href = data.url;
        } catch (err) {
            setError(err.message);
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: "4rem 2rem", maxWidth: "1000px", margin: "0 auto" }}>
            <div style={{ textAlign: "center", marginBottom: "4rem" }}>
                <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>Simple, transparent pricing</h1>
                <p style={{ color: "var(--color-text-muted)", fontSize: "1.125rem", maxWidth: "600px", margin: "0 auto" }}>
                    Unlock complete contextual intelligence and unlimited historical forecasting data for your market.
                </p>
            </div>

            {error && (
                <div style={{ background: "rgba(239, 68, 68, 0.1)", border: "1px solid #ef4444", color: "#ef4444", padding: "1rem", borderRadius: "8px", marginBottom: "2rem", textAlign: "center" }}>
                    {error}
                </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "2rem" }}>

                {/* Free Tier */}
                <div style={{
                    background: "var(--background-paper)", border: "1px solid var(--border-color)",
                    borderRadius: "16px", padding: "2rem", display: "flex", flexDirection: "column"
                }}>
                    <h3 style={{ fontSize: "1.5rem", marginTop: 0 }}>Free</h3>
                    <div style={{ fontSize: "2.5rem", fontWeight: "bold", margin: "1rem 0" }}>$0 <span style={{ fontSize: "1rem", color: "var(--color-text-muted)", fontWeight: "normal" }}>/mo</span></div>

                    <ul style={{ listStyle: "none", padding: 0, margin: "0 0 2rem 0", color: "var(--color-text-muted)", flexGrow: 1 }}>
                        <li style={{ marginBottom: "0.75rem" }}>✓ View recent anomalies (7 days)</li>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Basic National Level Metrics</li>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Limited to 1 Industry Preference</li>
                    </ul>

                    {user?.tier === "free" ? (
                        <button disabled style={{ padding: "1rem", borderRadius: "8px", background: "var(--background-default)", border: "1px solid var(--border-color)", color: "var(--color-text-muted)", fontWeight: "bold", cursor: "not-allowed", width: "100%" }}>
                            Current Plan
                        </button>
                    ) : (
                        <button disabled={user?.tier === "premium"} style={{ padding: "1rem", borderRadius: "8px", background: "transparent", border: "1px solid var(--color-border-default)", color: "var(--color-text-primary)", fontWeight: "bold", cursor: "pointer", width: "100%" }}>
                            {user?.tier === "premium" ? "Included" : "Get Started"}
                        </button>
                    )}
                </div>

                {/* Premium Tier */}
                <div style={{
                    background: "var(--background-paper)", border: "2px solid var(--color-primary)",
                    borderRadius: "16px", padding: "2rem", display: "flex", flexDirection: "column",
                    position: "relative"
                }}>
                    <div style={{ position: "absolute", top: "-14px", right: "2rem", background: "var(--color-primary)", color: "white", padding: "4px 12px", borderRadius: "12px", fontSize: "0.75rem", fontWeight: "bold" }}>
                        POPULAR
                    </div>

                    <h3 style={{ fontSize: "1.5rem", marginTop: 0 }}>Premium Access</h3>
                    <div style={{ fontSize: "2.5rem", fontWeight: "bold", margin: "1rem 0" }}>$49 <span style={{ fontSize: "1rem", color: "var(--color-text-muted)", fontWeight: "normal" }}>/mo</span></div>

                    <ul style={{ listStyle: "none", padding: 0, margin: "0 0 2rem 0", color: "var(--color-text-primary)", flexGrow: 1 }}>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Unlimited historical context lookup</li>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Deep local market segmentation</li>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Multiple targeted intelligence profiles</li>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Export detailed YoY reports (CSV)</li>
                        <li style={{ marginBottom: "0.75rem" }}>✓ Daily email alerts for anomalies</li>
                    </ul>

                    {user?.tier === "premium" ? (
                        <button disabled style={{ padding: "1rem", borderRadius: "8px", background: "var(--background-default)", border: "1px solid var(--color-primary)", color: "var(--color-primary)", fontWeight: "bold", cursor: "not-allowed", width: "100%" }}>
                            Active Subscription
                        </button>
                    ) : (
                        <button
                            disabled={loading}
                            onClick={() => handleUpgrade("remembench_pro_monthly")}
                            style={{ padding: "1rem", borderRadius: "8px", background: "var(--color-primary)", color: "white", border: "none", fontWeight: "bold", cursor: loading ? "wait" : "pointer", width: "100%", transition: "opacity 0.2s", opacity: loading ? 0.7 : 1 }}
                        >
                            {loading ? "Redirecting..." : "Upgrade to Premium"}
                        </button>
                    )}
                </div>

            </div>
        </div>
    )
}
