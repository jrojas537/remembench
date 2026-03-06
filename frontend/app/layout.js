import "./globals.css";
import { ThemeProvider } from "next-themes";
import { Inter } from "next/font/google";
import { AuthProvider } from "./contexts/AuthContext";
import TopNav from "./components/TopNav";

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
                            <TopNav />
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
