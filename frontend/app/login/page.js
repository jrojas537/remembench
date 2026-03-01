"use client";

import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        try {
            await login(email, password);
            router.push("/");
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div style={{
            minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
            background: "var(--background-default)", padding: "1rem"
        }}>
            <div style={{
                background: "var(--background-paper)", padding: "3rem", borderRadius: "16px",
                width: "100%", maxWidth: "400px", border: "1px solid var(--border-color)",
                boxShadow: "0 10px 30px rgba(0,0,0,0.5)"
            }}>
                <div style={{ textAlign: "center", marginBottom: "2rem" }}>
                    <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>⚡</div>
                    <h1 style={{ fontSize: "1.5rem", margin: "0 0 0.5rem 0" }}>Welcome Back</h1>
                    <p style={{ color: "var(--color-text-muted)", margin: 0 }}>Sign in to to access Remembench</p>
                </div>

                {error && (
                    <div style={{
                        background: "rgba(239, 68, 68, 0.1)", border: "1px solid #ef4444",
                        color: "#ef4444", padding: "0.75rem", borderRadius: "8px",
                        marginBottom: "1.5rem", fontSize: "0.875rem"
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <label style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            style={{
                                width: "100%", padding: "0.75rem", borderRadius: "8px",
                                background: "var(--background-default)", border: "1px solid var(--border-color)",
                                color: "var(--color-text-primary)"
                            }}
                        />
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        <label style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            style={{
                                width: "100%", padding: "0.75rem", borderRadius: "8px",
                                background: "var(--background-default)", border: "1px solid var(--border-color)",
                                color: "var(--color-text-primary)"
                            }}
                        />
                    </div>

                    <button
                        type="submit"
                        style={{
                            width: "100%", padding: "0.875rem", borderRadius: "8px",
                            background: "var(--color-text-primary)", color: "var(--background-default)",
                            border: "none", fontWeight: "600", cursor: "pointer", marginTop: "0.5rem",
                            transition: "opacity 0.2s"
                        }}
                    >
                        Sign In
                    </button>
                </form>

                <p style={{ textAlign: "center", marginTop: "2rem", color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
                    Don't have an account? <Link href="/register" style={{ color: "var(--color-text-primary)", textDecoration: "none" }}>Sign up</Link>
                </p>
            </div>
        </div>
    );
}
