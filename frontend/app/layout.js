import "./globals.css";
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
        <html lang="en">
            <body className={inter.className}>
                <AuthProvider>
                    <div className="app-container">
                        <header className="app-header">
                            <div>
                                <h1>⚡ Remembench</h1>
                                <span className="header-subtitle">
                                    YoY Performance Context Engine
                                </span>
                            </div>
                            <div className="header-status">
                                <span className="status-dot"></span>
                                <span>System Online</span>
                            </div>
                        </header>
                        <main className="main-content">{children}</main>
                    </div>
                </AuthProvider>
            </body>
        </html>
    );
}
