"use client";

import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import ProfileSettings from "./ProfileSettings";
import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import { FALLBACK_INDUSTRIES } from "../lib/constants";

export default function TopNav() {
    const { user } = useAuth();
    const [showSettings, setShowSettings] = useState(false);

    return (
        <header className="app-header" style={{
            background: "var(--color-bg-secondary)",
            borderBottom: "1px solid var(--color-border-subtle)",
            padding: "var(--space-4) var(--space-8)"
        }}>
            <div className="header-content" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                {/* Left: Logo */}
                <div className="logo-section" style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                    <div className="logo-icon" style={{ fontSize: "1.5rem" }}>⚡</div>
                    <div className="logo-text">
                        <h1 style={{ margin: 0, fontSize: "var(--font-size-xl)", fontWeight: 700, color: "var(--color-text-primary)" }}>Remembench</h1>
                        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
                            YoY Performance Context Engine
                        </span>
                    </div>
                </div>

                {/* Right: Status, Auth, Theme */}
                <div className="header-status" style={{ display: "flex", alignItems: "center", gap: "var(--space-6)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                        <div style={{ width: "8px", height: "8px", borderRadius: "var(--radius-full)", background: "var(--color-semantic-success)", boxShadow: "0 0 10px var(--color-semantic-success-subtle)" }}></div>
                        <span style={{ fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>System Online</span>
                    </div>

                    <div style={{ width: "1px", height: "24px", background: "var(--color-border-default)" }}></div>

                    {user ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                                <div style={{
                                    width: "32px", height: "32px", borderRadius: "var(--radius-full)",
                                    background: "var(--color-brand-primary-subtle)", color: "var(--color-brand-primary)",
                                    display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "var(--font-size-sm)"
                                }}>
                                    {user.first_name ? user.first_name[0].toUpperCase() : user.email[0].toUpperCase()}
                                </div>
                                <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-primary)" }}>
                                    Signed in as <strong>{user.first_name || user.email}</strong>
                                </span>
                            </div>
                            <button
                                onClick={() => setShowSettings(true)}
                                style={{
                                    background: "var(--color-bg-tertiary)", border: "1px solid var(--color-border-default)",
                                    padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)",
                                    color: "var(--color-text-secondary)", cursor: "pointer", fontSize: "var(--font-size-xs)",
                                    fontWeight: 500, transition: "var(--transition-fast)"
                                }}
                                onMouseEnter={(e) => e.target.style.background = "var(--color-bg-secondary)"}
                                onMouseLeave={(e) => e.target.style.background = "var(--color-bg-tertiary)"}
                            >
                                Profile / Preferences
                            </button>
                        </div>
                    ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
                            <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-muted)" }}>Browsing in public mode</span>
                            <Link href="/login" style={{
                                background: "var(--color-brand-primary)", color: "#ffffff",
                                padding: "var(--space-2) var(--space-4)", borderRadius: "var(--radius-sm)", textDecoration: "none",
                                fontWeight: "600", fontSize: "var(--font-size-sm)", transition: "var(--transition-fast)"
                            }}>
                                Log In
                            </Link>
                        </div>
                    )}

                    <ThemeToggle />
                </div>
            </div>

            {showSettings && (
                <ProfileSettings
                    onClose={() => setShowSettings(false)}
                    activeIndustries={FALLBACK_INDUSTRIES}
                />
            )}
        </header>
    );
}
