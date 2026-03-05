/* ------------------------------------------------------------------ *
 *  Industry Registry — matches backend's industries.py                *
 *  In production, this would be fetched from GET /api/v1/industries   *
 * ------------------------------------------------------------------ */

export const FALLBACK_INDUSTRIES = {
    pizza_all: {
        label: "Pizza (ALL)",
        icon: "🍕",
        group: "pizza",
        markets: [
            "Detroit Metro", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event", "sports",
        ],
    },
    pizza_full_service: {
        label: "Pizza — Full Service",
        icon: "🍽️",
        group: "pizza",
        markets: [
            "Detroit Metro", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event", "sports",
        ],
    },
    pizza_delivery: {
        label: "Pizza — Delivery",
        icon: "🛵",
        group: "pizza",
        markets: [
            "Detroit Metro", "Dearborn", "Warren", "Ann Arbor", "Royal Oak",
            "Ferndale", "Livonia", "Sterling Heights", "Farmington Hills", "Troy",
        ],
        categories: [
            "weather", "competitor_promo", "holiday", "news",
            "delivery_disruption", "food_safety", "supply_chain", "labor", "local_event", "sports",
        ],
    },
};

/* ------------------------------------------------------------------ *
 *  Constants                                                          *
 * ------------------------------------------------------------------ */

export const API_BASE =
    typeof window !== "undefined"
        ? (process.env.NEXT_PUBLIC_API_URL || "/api/v1")
        : "/api/v1";

// Extended color map covering all industries' categories
export const CATEGORY_COLORS = {
    weather: "#38bdf8",
    competitor_promo: "#f97316",
    outage: "#ef4444",
    holiday: "#a78bfa",
    news: "#2dd4bf",
    internal_promo: "#6366f1",
    system_issue: "#fb923c",
    delivery_disruption: "#f472b6",
    food_safety: "#dc2626",
    supply_chain: "#fbbf24",
    labor: "#8b5cf6",
    local_event: "#34d399",
    sports: "#10b981",
};

export const CATEGORY_ICONS = {
    weather: "🌦️",
    competitor_promo: "📢",
    outage: "⚠️",
    holiday: "🎉",
    news: "📰",
    internal_promo: "🏷️",
    system_issue: "🔧",
    delivery_disruption: "🚗",
    food_safety: "🏥",
    supply_chain: "📦",
    labor: "👷",
    local_event: "🎪",
    sports: "🏅",
};

/* ------------------------------------------------------------------ *
 *  Demo Data — industry-specific samples                              *
 * ------------------------------------------------------------------ */

export const WIRELESS_DEMO_EVENTS = [
    {
        category: "weather", subcategory: "blizzard",
        title: "Blizzard: 35cm snowfall in NYC metro area",
        description: "Major winter storm dropped 35cm of snow across the Northeast, severely limiting foot traffic to retail stores for 3 consecutive days.",
        severity: 0.92, confidence: 0.88, geo_label: "New York City", daysAgo: 365 + 45,
    },
    {
        category: "competitor_promo", subcategory: "carrier_announcement",
        title: "[VERIZON] Buy One Get One Free — iPhone 15 Pro",
        description: "Verizon announced aggressive BOGO promotion on iPhone 15 Pro with new line activation, running for 2 weeks nationwide.",
        severity: 0.85, confidence: 0.92, geo_label: "National", daysAgo: 365 + 30,
    },
    {
        category: "holiday", subcategory: "public_holiday",
        title: "Presidents' Day Weekend",
        description: "Federal holiday weekend. Historically one of the top 10 wireless retail weekends due to carrier promotions.",
        severity: 0.55, confidence: 0.95, geo_label: "National", daysAgo: 365 + 20,
    },
    {
        category: "outage", subcategory: "network_outage",
        title: "AT&T Nationwide Network Outage — 12 hours",
        description: "Major AT&T service disruption affected millions of customers. Resulted in surge of walk-in traffic to competitor stores.",
        severity: 0.95, confidence: 0.87, geo_label: "National", daysAgo: 365 + 15,
    },
    {
        category: "news", subcategory: "local_disruption",
        title: "Super Bowl LVIII — Las Vegas",
        description: "Major sporting event drew attention away from retail. Historically reduces non-essential shopping on game day by 15-25%.",
        severity: 0.45, confidence: 0.78, geo_label: "National", daysAgo: 365 + 25,
    },
    {
        category: "weather", subcategory: "extreme_cold",
        title: "Extreme Cold: -18°C low in Chicago",
        description: "Polar vortex conditions brought dangerously cold temperatures to the Midwest, reducing foot traffic by an estimated 40%.",
        severity: 0.78, confidence: 0.85, geo_label: "Chicago", daysAgo: 365 + 40,
    },
];

export const PIZZA_DEMO_EVENTS = [
    {
        category: "weather", subcategory: "heavy_snow",
        title: "Heavy Snow: 25cm in Detroit metro",
        description: "Lake-effect snow event dropped 25cm across metro Detroit, shutting down roads and boosting delivery demand while reducing dine-in traffic.",
        severity: 0.82, confidence: 0.9, geo_label: "Detroit", daysAgo: 365 + 35,
    },
    {
        category: "competitor_promo", subcategory: "restaurant_promotion",
        title: "[DOMINOS] 50% Off All Menu-Price Pizzas",
        description: "Domino's launched nationwide 50% off promotion for online orders, running for 2 weeks. Significant competitive pressure on local pizzerias.",
        severity: 0.78, confidence: 0.88, geo_label: "National", daysAgo: 365 + 28,
    },
    {
        category: "holiday", subcategory: "public_holiday",
        title: "Super Bowl Sunday",
        description: "Historically the #1 pizza delivery day of the year. Delivery volume spikes 40-60% over normal Sunday. Critical staffing day.",
        severity: 0.95, confidence: 0.97, geo_label: "National", daysAgo: 365 + 22,
    },
    {
        category: "delivery_disruption", subcategory: "platform_issue",
        title: "DoorDash Platform Outage — Detroit Metro",
        description: "DoorDash experienced a 4-hour outage affecting the Detroit metro area. Third-party delivery orders dropped to zero during window.",
        severity: 0.7, confidence: 0.85, geo_label: "Detroit", daysAgo: 365 + 18,
    },
    {
        category: "food_safety", subcategory: "inspection_or_recall",
        title: "FDA: Mozzarella Cheese Recall — Midwest Region",
        description: "FDA issued recall on mozzarella from a major Midwest distributor due to potential contamination. Affected supply for multiple restaurants.",
        severity: 0.88, confidence: 0.92, geo_label: "Detroit", daysAgo: 365 + 12,
    },
    {
        category: "supply_chain", subcategory: "ingredient_costs",
        title: "Cheese Prices Hit 18-Month High",
        description: "Block cheese prices rose 22% over 6 weeks due to supply constraints. Impacts menu pricing and profit margins for all pizza operators.",
        severity: 0.65, confidence: 0.8, geo_label: "National", daysAgo: 365 + 8,
    },
    {
        category: "labor", subcategory: "staffing",
        title: "Michigan Minimum Wage Increase Takes Effect",
        description: "Michigan minimum wage increased to $12.50/hr. Impacts labor costs for restaurant and delivery operations statewide.",
        severity: 0.6, confidence: 0.95, geo_label: "Detroit", daysAgo: 365 + 3,
    },
    {
        category: "local_event", subcategory: "festival",
        title: "Detroit Auto Show — Downtown Events",
        description: "North American International Auto Show brings 800,000+ visitors to downtown Detroit over 2 weeks. Boosts downtown restaurant traffic significantly.",
        severity: 0.72, confidence: 0.82, geo_label: "Detroit", daysAgo: 365 + 42,
    },
];

/**
 * Generates an array of synthetic event documents mapping directly 
 * to the `ImpactEventResponse` schema for local demo purposes.
 * 
 * @param {string} industry - The target industry group key (e.g. "pizza_all").
 * @returns {Array<Object>} Synthetic array of complete event objects.
 */
export function generateDemoData(industry = "wireless_retail") {
    const isPizza = industry.startsWith("pizza");
    const entries = isPizza ? PIZZA_DEMO_EVENTS : WIRELESS_DEMO_EVENTS;
    const now = new Date();

    return entries.map((entry) => {
        const eventDate = new Date(now);
        eventDate.setDate(eventDate.getDate() - entry.daysAgo);
        return {
            id: crypto.randomUUID(),
            ...entry,
            source: entry.category === "weather" ? "open-meteo" : "gdelt",
            start_date: eventDate.toISOString(),
            end_date: eventDate.toISOString(),
            created_at: now.toISOString(),
            updated_at: now.toISOString(),
            industry,
        };
    });
}

/**
 * Mocks the `anomaly_stats` aggregate route endpoint providing dynamic 
 * categories explicitly tied to the current industry configuration.
 *
 * @param {string} industry - The target dashboard industry string.
 * @returns {Object} JSON mapping reflecting the standard `/api/v1/events/stats/summary` schema.
 */
export function generateDemoStats(industry = "wireless_retail") {
    const isPizza = industry.startsWith("pizza");

    if (isPizza) {
        return {
            industry,
            categories: {
                weather: { count: 38, avg_severity: 0.65 },
                competitor_promo: { count: 15, avg_severity: 0.68 },
                holiday: { count: 28, avg_severity: 0.55 },
                delivery_disruption: { count: 12, avg_severity: 0.62 },
                food_safety: { count: 6, avg_severity: 0.78 },
                supply_chain: { count: 9, avg_severity: 0.58 },
                labor: { count: 7, avg_severity: 0.52 },
                local_event: { count: 16, avg_severity: 0.48 },
            },
        };
    }

    return {
        industry,
        categories: {
            weather: { count: 47, avg_severity: 0.68 },
            competitor_promo: { count: 23, avg_severity: 0.72 },
            outage: { count: 8, avg_severity: 0.81 },
            holiday: { count: 34, avg_severity: 0.52 },
            news: { count: 19, avg_severity: 0.41 },
        },
    };
}
