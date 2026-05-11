import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime

logger = logging.getLogger("analyzer")


class EnhancedAnalyzer:
    """
    Advanced market analytics engine with:
    - Statistical deal scoring
    - Market competitiveness index
    - Depreciation curve modeling
    - Supply/Demand imbalance detection
    - Brand loyalty & dominance metrics
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.insights = {}

    def run_full_analysis(self):
        """Run all analyses and return insights dict."""
        self.insights["market_overview"] = self._market_overview()
        self.insights["brand_intelligence"] = self._brand_intelligence()
        self.insights["best_value_deals"] = self._find_best_value_deals()
        self.insights["depreciation_curves"] = self._depreciation_analysis()
        self.insights["market_supply"] = self._supply_analysis()
        self.insights["price_competitiveness"] = self._price_competitiveness()
        self.insights["segment_analysis"] = self._segment_analysis()
        self.insights["location_analysis"] = self._location_analysis()
        self.insights["electric_market"] = self._ev_market_analysis()
        self.insights["chinese_brands"] = self._chinese_brands_analysis()
        return self.insights

    def _market_overview(self):
        """High-level market statistics."""
        return {
            "total_listings": len(self.df),
            "unique_brands": self.df[self.df["brand"] != "Unknown"]["brand"].nunique(),
            "unique_models": self.df[self.df["model"] != "Unknown"]["model"].nunique(),
            "avg_price": round(self.df["price"].mean(), 2),
            "median_price": round(self.df["price"].median(), 2),
            "avg_year": round(self.df["year"].mean(), 1),
            "avg_mileage": round(self.df["mileage"].mean(), 0),
            "avg_quality_score": round(self.df["quality_score"].mean(), 1),
            "source_split": self.df["source"].value_counts().to_dict(),
            "price_tiers": self.df["price_tier"].value_counts().to_dict(),
            "condition_split": {
                "New/Near-New (0-1yr)": int((self.df["car_age"] <= 1).sum()),
                "Recent (2-3yr)": int(((self.df["car_age"] >= 2) & (self.df["car_age"] <= 3)).sum()),
                "Mid-Life (4-7yr)": int(((self.df["car_age"] >= 4) & (self.df["car_age"] <= 7)).sum()),
                "Aging (8-12yr)": int(((self.df["car_age"] >= 8) & (self.df["car_age"] <= 12)).sum()),
                "Classic (13yr+)": int((self.df["car_age"] >= 13).sum()),
            },
            "body_type_mix": self.df[self.df["body_type"] != "Unknown"]["body_type"]
                .value_counts().to_dict(),
            "fuel_type_mix": self.df["fuel_type"].value_counts().to_dict(),
            "specs_origin_mix": self.df[self.df["specs_origin"] != "Unknown"]["specs_origin"]
                .value_counts().to_dict(),
        }

    def _brand_intelligence(self):
        """Deep brand-level analysis."""
        brand_df = self.df[self.df["brand"] != "Unknown"]
        brands = {}

        for brand in brand_df["brand"].unique():
            b = brand_df[brand_df["brand"] == brand]
            if len(b) < 2:
                continue

            brands[brand] = {
                "total_listings": len(b),
                "market_share_pct": round(len(b) / len(brand_df) * 100, 2),
                "avg_price": round(b["price"].mean(), 0),
                "median_price": round(b["price"].median(), 0),
                "min_price": round(b["price"].min(), 0),
                "max_price": round(b["price"].max(), 0),
                "price_range": round(b["price"].max() - b["price"].min(), 0),
                "std_price": round(b["price"].std(), 0),
                "avg_year": round(b["year"].mean(), 1),
                "avg_mileage": round(b["mileage"].mean(), 0) if b["mileage"].notna().any() else None,
                "top_models": b["model"].value_counts().head(5).to_dict(),
                "body_types": b[b["body_type"] != "Unknown"]["body_type"].value_counts().to_dict(),
                "source_split": b["source"].value_counts().to_dict(),
                "tier": b["brand_tier"].iloc[0] if "brand_tier" in b.columns else "Unknown",
                "origin": b["brand_origin"].iloc[0] if "brand_origin" in b.columns else "Unknown",
                "deals_count": int((b["cross_source_flag"].str.contains("Deal|Below", na=False)).sum()),
            }

        # Sort by listings count
        brands = dict(sorted(brands.items(), key=lambda x: x[1]["total_listings"], reverse=True))
        return brands

    def _find_best_value_deals(self):
        """
        Find the best value deals using a composite scoring system.
        Score = f(price_vs_market, quality_score, mileage_efficiency, age)
        """
        df = self.df.copy()
        df = df[df["brand"] != "Unknown"]
        df = df[df["price_vs_market"].notna()]

        # Normalize components to 0-1
        def min_max_norm(series, invert=False):
            mn, mx = series.min(), series.max()
            if mx == mn:
                return pd.Series(0.5, index=series.index)
            normed = (series - mn) / (mx - mn)
            return 1 - normed if invert else normed

        df["_price_score"] = min_max_norm(df["price_vs_market"], invert=True)  # Lower = better
        df["_quality_norm"] = min_max_norm(df["quality_score"])
        df["_age_score"] = min_max_norm(df["car_age"], invert=True)  # Newer = better
        df["_mileage_score"] = min_max_norm(df["mileage"].fillna(df["mileage"].median()), invert=True)

        # Composite deal score (weighted)
        df["deal_score"] = (
            df["_price_score"] * 0.40 +
            df["_quality_norm"] * 0.15 +
            df["_age_score"] * 0.25 +
            df["_mileage_score"] * 0.20
        ) * 100

        # Top deals
        top_deals = df.nlargest(50, "deal_score")[
            ["brand", "model", "year", "price", "mileage", "body_type",
             "fuel_type", "source", "url", "deal_score", "price_vs_market",
             "cross_source_flag", "quality_score"]
        ].round(1)

        return {
            "top_50_deals": json.loads(top_deals.to_json(orient="records")),
            "avg_deal_score": round(df["deal_score"].mean(), 1),
        }

    def _depreciation_analysis(self):
        """Analyze depreciation curves by brand."""
        results = {}
        brand_df = self.df[(self.df["brand"] != "Unknown") & (self.df["year"].notna())]

        for brand in brand_df["brand"].value_counts().head(20).index:
            b = brand_df[brand_df["brand"] == brand]
            if len(b) < 5:
                continue

            yearly = b.groupby("year")["price"].agg(["median", "mean", "count"]).reset_index()
            yearly = yearly[yearly["count"] >= 2]
            yearly = yearly.sort_values("year")

            if len(yearly) < 3:
                continue

            # Calculate year-over-year depreciation
            yearly["yoy_depreciation_pct"] = yearly["median"].pct_change() * -100

            results[brand] = {
                "yearly_prices": yearly[["year", "median", "mean", "count"]].to_dict("records"),
                "avg_annual_depreciation_pct": round(yearly["yoy_depreciation_pct"].mean(), 1),
                "best_value_year": int(yearly.loc[yearly["median"].idxmin(), "year"])
                    if len(yearly) > 0 else None,
            }

        return results

    def _supply_analysis(self):
        """Analyze which cars are most/least abundant."""
        brand_model = self.df[
            (self.df["brand"] != "Unknown") & (self.df["model"] != "Unknown")
        ]

        supply = brand_model.groupby(["brand", "model"]).agg(
            count=("price", "size"),
            avg_price=("price", "mean"),
            min_price=("price", "min"),
        ).reset_index().sort_values("count", ascending=False)

        return {
            "most_available": json.loads(
                supply.head(30).round(0).to_json(orient="records")
            ),
            "least_available": json.loads(
                supply[supply["count"] <= 2].round(0).to_json(orient="records")
            ),
            "total_unique_models": len(supply),
        }

    def _price_competitiveness(self):
        """
        Calculate which brand/models are priced most competitively
        compared to their segment average.
        """
        df = self.df[(self.df["brand"] != "Unknown") & (self.df["body_type"] != "Unknown")]

        # Segment average (same body type, similar year range)
        segment_median = df.groupby(["body_type", "brand_tier"])["price"].median()

        results = []
        for (body, tier), median in segment_median.items():
            segment = df[(df["body_type"] == body) & (df["brand_tier"] == tier)]
            brand_medians = segment.groupby("brand")["price"].median()

            for brand, brand_median in brand_medians.items():
                pct_diff = ((brand_median - median) / median) * 100
                results.append({
                    "brand": brand,
                    "body_type": body,
                    "tier": tier,
                    "brand_median_price": round(brand_median, 0),
                    "segment_median_price": round(median, 0),
                    "pct_vs_segment": round(pct_diff, 1),
                    "verdict": "Competitive" if pct_diff < -5 else "Premium" if pct_diff > 5 else "Average",
                })

        return sorted(results, key=lambda x: x["pct_vs_segment"])

    def _segment_analysis(self):
        """Analyze market segments (SUV vs Sedan vs etc.)."""
        df = self.df[self.df["body_type"] != "Unknown"]
        segments = {}

        for body_type in df["body_type"].unique():
            seg = df[df["body_type"] == body_type]
            segments[body_type] = {
                "count": len(seg),
                "market_share_pct": round(len(seg) / len(df) * 100, 1),
                "avg_price": round(seg["price"].mean(), 0),
                "median_price": round(seg["price"].median(), 0),
                "top_brands": seg["brand"].value_counts().head(5).to_dict(),
                "avg_year": round(seg["year"].mean(), 1),
                "price_range": {
                    "min": round(seg["price"].min(), 0),
                    "max": round(seg["price"].max(), 0),
                },
            }

        return segments

    def _location_analysis(self):
        """Analyze price and availability by location (Emirate)."""
        df = self.df[self.df["location"].notna()]
        if len(df) == 0:
            return {}

        # Standardize emirates
        EMIRATES_MAP = {
            "dubai": "Dubai", "abu dhabi": "Abu Dhabi", "sharjah": "Sharjah",
            "ajman": "Ajman", "ras al khaimah": "Ras Al Khaimah",
            "fujairah": "Fujairah", "umm al quwain": "Umm Al Quwain",
            "al ain": "Al Ain",
        }

        def map_emirate(loc):
            loc_lower = str(loc).lower()
            for key, val in EMIRATES_MAP.items():
                if key in loc_lower:
                    return val
            return "Other"

        df["emirate"] = df["location"].apply(map_emirate)
        df = df[df["emirate"] != "Other"]

        location_stats = {}
        for emirate in df["emirate"].unique():
            e = df[df["emirate"] == emirate]
            location_stats[emirate] = {
                "count": len(e),
                "avg_price": round(e["price"].mean(), 0),
                "median_price": round(e["price"].median(), 0),
                "top_brands": e["brand"].value_counts().head(5).to_dict(),
                "price_tier_mix": e["price_tier"].value_counts().to_dict(),
            }

        return location_stats

    def _ev_market_analysis(self):
        """Specific analysis for the growing EV market in UAE."""
        ev = self.df[self.df["fuel_type"] == "Electric"]
        hybrid = self.df[self.df["fuel_type"] == "Hybrid"]

        if len(ev) == 0 and len(hybrid) == 0:
            return {"note": "No EV/Hybrid listings found"}

        result = {
            "ev_count": len(ev),
            "hybrid_count": len(hybrid),
            "total_electrified": len(ev) + len(hybrid),
            "electrified_pct": round((len(ev) + len(hybrid)) / len(self.df) * 100, 2),
        }

        if len(ev) > 0:
            result["ev_stats"] = {
                "avg_price": round(ev["price"].mean(), 0),
                "median_price": round(ev["price"].median(), 0),
                "cheapest_ev": ev.nsmallest(5, "price")[
                    ["brand", "model", "year", "price"]
                ].to_dict("records"),
                "top_ev_brands": ev["brand"].value_counts().to_dict(),
            }

        if len(hybrid) > 0:
            result["hybrid_stats"] = {
                "avg_price": round(hybrid["price"].mean(), 0),
                "top_hybrid_brands": hybrid["brand"].value_counts().to_dict(),
            }

        return result

    def _chinese_brands_analysis(self):
        """Track the growing presence of Chinese brands in UAE market."""
        chinese_brands = [b for b, info in BRAND_MODEL_DB.items() if info.get("origin") == "Chinese"]
        chinese = self.df[self.df["brand"].isin(chinese_brands)]

        if len(chinese) == 0:
            return {"note": "No Chinese brand listings found"}

        return {
            "total_listings": len(chinese),
            "market_share_pct": round(len(chinese) / len(self.df) * 100, 2),
            "brands": chinese["brand"].value_counts().to_dict(),
            "avg_price": round(chinese["price"].mean(), 0),
            "vs_market_avg": round(
                (chinese["price"].mean() - self.df["price"].mean()) / self.df["price"].mean() * 100, 1
            ),
            "avg_year": round(chinese["year"].mean(), 1),
            "most_popular_models": chinese.groupby(["brand", "model"]).size()
                .sort_values(ascending=False).head(10).to_dict(),
        }


    # ═══════════════════════════════════════════════════
    # DASHBOARD HTML GENERATOR
    # ═══════════════════════════════════════════════════

    def generate_dashboard(self, output_path="dashboard.html"):
        """Generate a premium interactive dashboard."""

        insights = self.run_full_analysis()
        overview = insights["market_overview"]
        brands = insights["brand_intelligence"]
        deals = insights["best_value_deals"]
        supply = insights["market_supply"]
        segments = insights["segment_analysis"]
        ev = insights["electric_market"]

        # Prepare chart data
        top_brands = list(brands.keys())[:15]
        brand_counts = [brands[b]["total_listings"] for b in top_brands]
        brand_avg_prices = [brands[b]["avg_price"] for b in top_brands]

        body_labels = list(overview.get("body_type_mix", {}).keys())
        body_values = list(overview.get("body_type_mix", {}).values())

        fuel_labels = list(overview.get("fuel_type_mix", {}).keys())
        fuel_values = list(overview.get("fuel_type_mix", {}).values())

        tier_labels = list(overview.get("price_tiers", {}).keys())
        tier_values = list(overview.get("price_tiers", {}).values())

        # Top deals table rows
        deal_rows = ""
        for d in deals["top_50_deals"][:25]:
            flag_class = ""
            if "Deal" in str(d.get("cross_source_flag", "")):
                flag_class = "deal-hot"
            elif "Below" in str(d.get("cross_source_flag", "")):
                flag_class = "deal-good"

            deal_rows += f"""
            <tr class="{flag_class}">
                <td>{d.get('brand','')}</td>
                <td>{d.get('model','')}</td>
                <td>{int(d.get('year',0))}</td>
                <td>AED {int(d.get('price',0)):,}</td>
                <td>{int(d.get('mileage',0)):,} km</td>
                <td>{d.get('body_type','')}</td>
                <td>{d.get('cross_source_flag','')}</td>
                <td>{d.get('deal_score',0):.0f}</td>
                <td><a href="{d.get('url','#')}" target="_blank">🔗</a></td>
            </tr>"""

        # Most available cars
        supply_rows = ""
        for s in supply["most_available"][:20]:
            supply_rows += f"""
            <tr>
                <td>{s.get('brand','')}</td>
                <td>{s.get('model','')}</td>
                <td>{int(s.get('count',0))}</td>
                <td>AED {int(s.get('avg_price',0)):,}</td>
                <td>AED {int(s.get('min_price',0)):,}</td>
            </tr>"""

        # Build full interactive explorer data
        explorer_data = json.dumps(
            self.df.head(2000)[
                ["brand", "model", "year", "price", "mileage", "body_type",
                 "fuel_type", "transmission", "specs_origin", "location",
                 "source", "quality_score", "cross_source_flag", "url"]
            ].fillna("").to_dict("records"),
            default=str
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🇦🇪 UAE Car Market Intelligence Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: #1a2332;
            --bg-card-hover: #1f2b3d;
            --text-primary: #f0f4f8;
            --text-secondary: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
            --border: #1e293b;
            --gradient-1: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --gradient-2: linear-gradient(135deg, #06b6d4, #10b981);
            --gradient-3: linear-gradient(135deg, #f59e0b, #ef4444);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        .dashboard-header {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            padding: 2rem;
            text-align: center;
            border-bottom: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }}
        .dashboard-header::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(ellipse at 50% 0%, rgba(59,130,246,0.15), transparent 70%);
        }}
        .dashboard-header h1 {{
            font-size: 2.2rem;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
        }}
        .dashboard-header p {{
            color: var(--text-secondary);
            margin-top: 0.5rem;
            position: relative;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 1.5rem; }}

        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .kpi-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        .kpi-card .kpi-value {{
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0.5rem 0;
        }}
        .kpi-card .kpi-label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .kpi-card.blue .kpi-value {{ color: var(--accent-blue); }}
        .kpi-card.green .kpi-value {{ color: var(--accent-green); }}
        .kpi-card.amber .kpi-value {{ color: var(--accent-amber); }}
        .kpi-card.cyan .kpi-value {{ color: var(--accent-cyan); }}
        .kpi-card.purple .kpi-value {{ color: var(--accent-purple); }}
        .kpi-card.red .kpi-value {{ color: var(--accent-red); }}

        /* Section */
        .section {{
            margin-bottom: 2rem;
        }}
        .section-title {{
            font-size: 1.4rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 1.5rem;
        }}
        .chart-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
        }}
        .chart-card h3 {{
            margin-bottom: 1rem;
            font-size: 1rem;
            color: var(--text-secondary);
        }}
        canvas {{ max-height: 350px; }}

        /* Tables */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        .data-table th {{
            background: var(--bg-secondary);
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 2px solid var(--border);
            position: sticky;
            top: 0;
        }}
        .data-table td {{
            padding: 0.65rem 0.75rem;
            border-bottom: 1px solid var(--border);
        }}
        .data-table tr:hover {{
            background: var(--bg-card-hover);
        }}
        .deal-hot {{ background: rgba(239, 68, 68, 0.1) !important; }}
        .deal-good {{ background: rgba(16, 185, 129, 0.1) !important; }}

        /* Explorer */
        .filter-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }}
        .filter-bar select, .filter-bar input {{
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            font-size: 0.85rem;
        }}
        .table-scroll {{
            max-height: 500px;
            overflow-y: auto;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-deal {{ background: rgba(16,185,129,0.2); color: var(--accent-green); }}
        .badge-overpriced {{ background: rgba(239,68,68,0.2); color: var(--accent-red); }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
        }}

        @media (max-width: 768px) {{
            .chart-grid {{ grid-template-columns: 1fr; }}
            .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>

<div class="dashboard-header">
    <h1>🇦🇪 UAE Car Market Intelligence</h1>
    <p>Live market data from Dubizzle & Dubicars · Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
</div>

<div class="container">

    <!-- KPI CARDS -->
    <div class="kpi-grid">
        <div class="kpi-card blue">
            <div class="kpi-label">Total Listings</div>
            <div class="kpi-value">{overview['total_listings']:,}</div>
        </div>
        <div class="kpi-card green">
            <div class="kpi-label">Unique Brands</div>
            <div class="kpi-value">{overview['unique_brands']}</div>
        </div>
        <div class="kpi-card amber">
            <div class="kpi-label">Average Price</div>
            <div class="kpi-value">AED {overview['avg_price']:,.0f}</div>
        </div>
        <div class="kpi-card cyan">
            <div class="kpi-label">Median Price</div>
            <div class="kpi-value">AED {overview['median_price']:,.0f}</div>
        </div>
        <div class="kpi-card purple">
            <div class="kpi-label">Avg Year</div>
            <div class="kpi-value">{overview['avg_year']}</div>
        </div>
        <div class="kpi-card red">
            <div class="kpi-label">Data Quality</div>
            <div class="kpi-value">{overview['avg_quality_score']}/100</div>
        </div>
    </div>

    <!-- CHARTS ROW 1: Brand Intelligence -->
    <div class="section">
        <h2 class="section-title">📊 Brand Intelligence</h2>
        <div class="chart-grid">
            <div class="chart-card">
                <h3>Top 15 Brands by Volume</h3>
                <canvas id="brandVolumeChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Average Price by Brand</h3>
                <canvas id="brandPriceChart"></canvas>
            </div>
        </div>
    </div>

    <!-- CHARTS ROW 2: Market Mix -->
    <div class="section">
        <h2 class="section-title">🧩 Market Mix</h2>
        <div class="chart-grid">
            <div class="chart-card">
                <h3>Body Type Distribution</h3>
                <canvas id="bodyTypeChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Fuel Type Distribution</h3>
                <canvas id="fuelTypeChart"></canvas>
            </div>
        </div>
    </div>

    <!-- CHARTS ROW 3: Price & Tiers -->
    <div class="section">
        <h2 class="section-title">💰 Price Analysis</h2>
        <div class="chart-grid">
            <div class="chart-card">
                <h3>Market Price Tiers</h3>
                <canvas id="tierChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>EV & Electrified Market</h3>
                <div style="padding: 1rem; color: var(--text-secondary);">
                    <p>⚡ Electric Vehicles: <strong style="color:var(--accent-green)">{ev.get('ev_count', 0)}</strong></p>
                    <p>🔋 Hybrids: <strong style="color:var(--accent-cyan)">{ev.get('hybrid_count', 0)}</strong></p>
                    <p>📈 Electrified Market Share: <strong style="color:var(--accent-amber)">{ev.get('electrified_pct', 0)}%</strong></p>
                </div>
            </div>
        </div>
    </div>

    <!-- TOP DEALS TABLE -->
    <div class="section">
        <h2 class="section-title">🔥 Top 25 Best Value Deals</h2>
        <div class="chart-card">
            <div class="table-scroll">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Brand</th><th>Model</th><th>Year</th>
                            <th>Price</th><th>Mileage</th><th>Body</th>
                            <th>Flag</th><th>Score</th><th>Link</th>
                        </tr>
                    </thead>
                    <tbody>{deal_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- MOST AVAILABLE -->
    <div class="section">
        <h2 class="section-title">📦 Most Available Cars in Market</h2>
        <div class="chart-card">
            <div class="table-scroll">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Brand</th><th>Model</th><th>Listings</th>
                            <th>Avg Price</th><th>Min Price</th>
                        </tr>
                    </thead>
                    <tbody>{supply_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- INTERACTIVE EXPLORER -->
    <div class="section">
        <h2 class="section-title">🔍 Interactive Explorer</h2>
        <div class="chart-card">
            <div class="filter-bar">
                <select id="filterBrand" onchange="filterExplorer()">
                    <option value="">All Brands</option>
                </select>
                <select id="filterBody" onchange="filterExplorer()">
                    <option value="">All Body Types</option>
                </select>
                <select id="filterFuel" onchange="filterExplorer()">
                    <option value="">All Fuel Types</option>
                </select>
                <select id="filterSource" onchange="filterExplorer()">
                    <option value="">All Sources</option>
                    <option value="dubizzle">Dubizzle</option>
                    <option value="dubicars">Dubicars</option>
                </select>
                <input type="number" id="filterMinPrice" placeholder="Min Price" onchange="filterExplorer()">
                <input type="number" id="filterMaxPrice" placeholder="Max Price" onchange="filterExplorer()">
                <input type="number" id="filterMinYear" placeholder="Min Year" onchange="filterExplorer()">
            </div>
            <div id="explorerCount" style="margin-bottom:0.5rem;color:var(--text-secondary);font-size:0.85rem;"></div>
            <div class="table-scroll" id="explorerTableWrap">
                <table class="data-table" id="explorerTable">
                    <thead>
                        <tr>
                            <th onclick="sortExplorer('brand')">Brand ↕</th>
                            <th onclick="sortExplorer('model')">Model ↕</th>
                            <th onclick="sortExplorer('year')">Year ↕</th>
                            <th onclick="sortExplorer('price')">Price ↕</th>
                            <th onclick="sortExplorer('mileage')">Mileage ↕</th>
                            <th>Body</th>
                            <th>Fuel</th>
                            <th>Source</th>
                            <th>Flag</th>
                            <th>Link</th>
                        </tr>
                    </thead>
                    <tbody id="explorerBody"></tbody>
                </table>
            </div>
        </div>
    </div>

</div>

<div class="footer">
    UAE Car Market Intelligence Dashboard · Data sourced from Dubizzle & Dubicars<br>
    Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} · {overview['total_listings']:,} listings analyzed
</div>

<script>
    // ═══ Chart.js Global Config ═══
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = '#1e293b';
    Chart.defaults.font.family = 'Inter, sans-serif';

    const COLORS = ['#3b82f6','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6',
                    '#ec4899','#14b8a6','#f97316','#6366f1','#84cc16','#e11d48',
                    '#0ea5e9','#a855f7','#22d3ee'];

    // Brand Volume Chart
    new Chart(document.getElementById('brandVolumeChart'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(top_brands)},
            datasets: [{{
                label: 'Listings',
                data: {json.dumps(brand_counts)},
                backgroundColor: COLORS,
                borderRadius: 6,
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
        }}
    }});

    // Brand Price Chart
    new Chart(document.getElementById('brandPriceChart'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(top_brands)},
            datasets: [{{
                label: 'Avg Price (AED)',
                data: {json.dumps(brand_avg_prices)},
                backgroundColor: COLORS.slice().reverse(),
                borderRadius: 6,
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ x: {{ ticks: {{ callback: v => 'AED ' + v.toLocaleString() }} }} }}
        }}
    }});

    // Body Type Doughnut
    new Chart(document.getElementById('bodyTypeChart'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(body_labels)},
            datasets: [{{ data: {json.dumps(body_values)}, backgroundColor: COLORS, borderWidth: 0 }}]
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ position: 'right' }} }} }}
    }});

    // Fuel Type Doughnut
    new Chart(document.getElementById('fuelTypeChart'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(fuel_labels)},
            datasets: [{{ data: {json.dumps(fuel_values)}, backgroundColor: COLORS.slice(5), borderWidth: 0 }}]
        }},
        options: {{ responsive: true, plugins: {{ legend: {{ position: 'right' }} }} }}
    }});

    // Price Tiers
    new Chart(document.getElementById('tierChart'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(tier_labels)},
            datasets: [{{
                label: 'Listings',
                data: {json.dumps(tier_values)},
                backgroundColor: ['#10b981','#06b6d4','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#ec4899'],
                borderRadius: 6,
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
        }}
    }});

    // ═══ Interactive Explorer ═══
    const explorerData = {explorer_data};
    let sortField = 'price';
    let sortAsc = true;

    function initExplorer() {{
        const brands = [...new Set(explorerData.map(d => d.brand).filter(Boolean))].sort();
        const bodies = [...new Set(explorerData.map(d => d.body_type).filter(Boolean))].sort();
        const fuels = [...new Set(explorerData.map(d => d.fuel_type).filter(Boolean))].sort();

        const brandSel = document.getElementById('filterBrand');
        brands.forEach(b => {{ const o = document.createElement('option'); o.value = b; o.text = b; brandSel.add(o); }});

        const bodySel = document.getElementById('filterBody');
        bodies.forEach(b => {{ const o = document.createElement('option'); o.value = b; o.text = b; bodySel.add(o); }});

        const fuelSel = document.getElementById('filterFuel');
        fuels.forEach(f => {{ const o = document.createElement('option'); o.value = f; o.text = f; fuelSel.add(o); }});

        filterExplorer();
    }}

    function filterExplorer() {{
        const brand = document.getElementById('filterBrand').value;
        const body = document.getElementById('filterBody').value;
        const fuel = document.getElementById('filterFuel').value;
        const source = document.getElementById('filterSource').value;
        const minPrice = parseFloat(document.getElementById('filterMinPrice').value) || 0;
        const maxPrice = parseFloat(document.getElementById('filterMaxPrice').value) || Infinity;
        const minYear = parseInt(document.getElementById('filterMinYear').value) || 0;

        let filtered = explorerData.filter(d => {{
            if (brand && d.brand !== brand) return false;
            if (body && d.body_type !== body) return false;
            if (fuel && d.fuel_type !== fuel) return false;
            if (source && d.source !== source) return false;
            if (d.price < minPrice || d.price > maxPrice) return false;
            if (d.year < minYear) return false;
            return true;
        }});

        filtered.sort((a, b) => {{
            let va = a[sortField], vb = b[sortField];
            if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortAsc ? (va||0) - (vb||0) : (vb||0) - (va||0);
        }});

        document.getElementById('explorerCount').textContent = `Showing ${{filtered.length}} of ${{explorerData.length}} listings`;

        const tbody = document.getElementById('explorerBody');
        tbody.innerHTML = filtered.slice(0, 200).map(d => {{
            let flagBadge = '';
            if (d.cross_source_flag && d.cross_source_flag.includes('Deal')) flagBadge = '<span class="badge badge-deal">' + d.cross_source_flag + '</span>';
            else if (d.cross_source_flag && d.cross_source_flag.includes('Over')) flagBadge = '<span class="badge badge-overpriced">' + d.cross_source_flag + '</span>';
            else flagBadge = d.cross_source_flag || '';

            return `<tr>
                <td>${{d.brand}}</td><td>${{d.model}}</td><td>${{d.year || ''}}</td>
                <td>AED ${{(d.price||0).toLocaleString()}}</td>
                <td>${{d.mileage ? d.mileage.toLocaleString() + ' km' : ''}}</td>
                <td>${{d.body_type}}</td><td>${{d.fuel_type}}</td>
                <td>${{d.source}}</td><td>${{flagBadge}}</td>
                <td><a href="${{d.url}}" target="_blank" style="color:var(--accent-blue)">🔗</a></td>
            </tr>`;
        }}).join('');
    }}

    function sortExplorer(field) {{
        if (sortField === field) sortAsc = !sortAsc;
        else {{ sortField = field; sortAsc = true; }}
        filterExplorer();
    }}

    initExplorer();
</script>
</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Dashboard generated: {output_path}")
        return output_path
