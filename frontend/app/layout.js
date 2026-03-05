import "./globals.css";
import { ThemeProvider } from "next-themes";
import { Inter } from "next/font/google";
import { AuthProvider } from "./contexts/AuthContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
    title: "Remembench | YoY Performance Context Engine",
    description:
        "Surfaces weather, promotions, holidays, events, and disruptions that impact specific industries, markets, and date ranges. Better forecasting through contextual intelligence.",
};
export default function RootLayout({ children }) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body className={`${inter.variable} font-sans antialiased bg-bg-primary text-text-primary`}>
                <AuthProvider>
                    <ThemeProvider attribute="class" defaultTheme="system" enableSystem={true}>
                        <div className="app-container">
                            <header className="app-header">
                                <div className="header-content">
                                    <div className="logo-section">
                                        <div className="logo-icon">⚡</div>
                                        <div className="logo-text">
                                            <h1>Remembench</h1>
                                            <span style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", fontWeight: 500 }}>
                                                YoY Performance Context Engine
                                            </span>
                                        </div>
                                    </div>
                                    <div className="header-status">
                                        <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--color-success)", boxShadow: "0 0 10px var(--color-success)" }}></div>
                                        <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--color-text-secondary)" }}>System Online</span>
                                    </div>
                                </div>
                            </header>
                            <main className="main-content">
                                {children}
                            </main>
                        </div>
                    </ThemeProvider>
                </AuthProvider>
            </body>
        </html>
    );
}
