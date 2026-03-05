"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

// The Auth context holds the current user state and functions to manipulating it
const AuthContext = createContext({
    user: null,
    token: null,
    loading: true,
    login: async () => { },
    register: async () => { },
    logout: () => { },
    updatePreferences: async () => { },
});

const API_BASE =
    typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
        : "/api/v1";

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    // Check for existing token and fetch user on initial load
    useEffect(() => {
        const storedToken = localStorage.getItem("remembench_token");
        if (storedToken) {
            setToken(storedToken);
            fetchCurrentUser(storedToken);
        } else {
            setLoading(false);
            // Option: Redirect to login if on protected route?
            // Currently, dashboard works in 'preview' mode without auth
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const fetchCurrentUser = async (authToken) => {
        try {
            const res = await fetch(`${API_BASE}/users/me`, {
                headers: {
                    "Authorization": `Bearer ${authToken}`
                }
            });
            if (res.ok) {
                const userData = await res.json();
                setUser(userData);

                if (userData.preferences?.theme === "dark") {
                    document.documentElement.classList.add("dark-theme");
                } else {
                    document.documentElement.classList.remove("dark-theme");
                }
            } else {
                // Token is invalid/expired
                logout();
            }
        } catch (error) {
            console.error("Failed to fetch user:", error);
        } finally {
            setLoading(false);
        }
    };

    const login = async (email, password) => {
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Login failed");
            }

            const data = await response.json();
            const token = data.access_token;

            localStorage.setItem("remembench_token", token);
            setToken(token);
            await fetchCurrentUser(token);
            router.push("/");
        } catch (error) {
            throw error;
        }
    };

    const register = async (email, password, firstName, lastName) => {
        try {
            const response = await fetch(`${API_BASE}/auth/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email,
                    password,
                    first_name: firstName,
                    last_name: lastName
                }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Registration failed");
            }

            // Auto login after successful registration
            await login(email, password);
        } catch (error) {
            throw error;
        }
    };

    const logout = () => {
        localStorage.removeItem("remembench_token");
        setToken(null);
        setUser(null);
        router.push("/login"); // Force redirect out of protected areas
    };

    const updatePreferences = async (newPrefs) => {
        if (!token) return;

        try {
            const response = await fetch(`${API_BASE}/users/me/preferences`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(newPrefs),
            });

            if (response.ok) {
                const updatedPrefs = await response.json();
                setUser(prev => ({ ...prev, preferences: updatedPrefs }));
            }
        } catch (error) {
            console.error("Failed to update preferences", error);
        }
    };

    return (
        <AuthContext.Provider value={{ user, token, loading, login, register, logout, updatePreferences }}>
            {children}
        </AuthContext.Provider>
    );
}

// Hook to use auth within components
export const useAuth = () => useContext(AuthContext);
