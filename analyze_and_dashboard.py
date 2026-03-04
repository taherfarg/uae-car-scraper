"""
UAE Car Market — Interactive Analytics Dashboard Generator
Reads the processed CSV and generates a self-contained HTML dashboard with Chart.js.
"""

import pandas as pd
import json
import os
from datetime import datetime


def generate_dashboard(csv_path="uae_cars_market_data.csv", output_path="dashboard.html"):
    """Generate an interactive HTML dashboard from the processed CSV."""
    
    print(f"📊 Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    if df.empty:
        print("❌ No data found in CSV.")
        return
    
    print(f"  ✓ {len(df)} records loaded")
    
    # ---- Prepare chart data ----
    
    # 1. Overview stats
    total = len(df)
    with_price = df['price_aed'].notna()
    avg_price = int(df.loc[with_price, 'price_aed'].mean()) if with_price.any() else 0
    min_price = int(df.loc[with_price, 'price_aed'].min()) if with_price.any() else 0
    max_price = int(df.loc[with_price, 'price_aed'].max()) if with_price.any() else 0
    median_price = int(df.loc[with_price, 'price_aed'].median()) if with_price.any() else 0
    source_counts = df['source'].value_counts().to_dict()
    avg_quality = int(df['data_quality'].mean()) if 'data_quality' in df.columns else 0
    brands_found = int(df['brand'].nunique()) if 'brand' in df.columns else 0
    
    # 2. Top brands
    if 'brand' in df.columns:
        top_brands = df['brand'].value_counts().head(15)
        brand_labels = top_brands.index.tolist()
        brand_counts = top_brands.values.tolist()
    else:
        brand_labels, brand_counts = [], []
    
    # 3. Average price by brand (top 12 with enough data)
    if 'brand' in df.columns and with_price.any():
        brand_price = df[with_price].groupby('brand')['price_aed'].agg(['mean', 'count'])
        brand_price = brand_price[brand_price['count'] >= 2].sort_values('mean', ascending=False).head(12)
        price_by_brand_labels = brand_price.index.tolist()
        price_by_brand_values = [int(v) for v in brand_price['mean'].values.tolist()]
    else:
        price_by_brand_labels, price_by_brand_values = [], []
    
    # 4. Price distribution (histogram buckets)
    if with_price.any():
        prices = df.loc[with_price, 'price_aed']
        bins = [0, 25000, 50000, 75000, 100000, 150000, 200000, 300000, 500000, 1000000, float('inf')]
        bin_labels = ['<25K', '25-50K', '50-75K', '75-100K', '100-150K', '150-200K', '200-300K', '300-500K', '500K-1M', '1M+']
        hist_counts = pd.cut(prices, bins=bins, labels=bin_labels).value_counts().reindex(bin_labels).fillna(0).astype(int).tolist()
    else:
        bin_labels, hist_counts = [], []
    
    # 5. Year distribution
    if 'year' in df.columns:
        year_dist = df['year'].dropna().astype(int).value_counts().sort_index()
        year_labels = [str(y) for y in year_dist.index.tolist()]
        year_counts = year_dist.values.tolist()
    else:
        year_labels, year_counts = [], []
    
    # 6. Condition split (New vs Used)
    if 'condition' in df.columns:
        cond = df['condition'].value_counts()
        cond_labels = cond.index.tolist()
        cond_counts = cond.values.tolist()
        unknown = total - sum(cond_counts)
        if unknown > 0:
            cond_labels.append('Unknown')
            cond_counts.append(unknown)
    else:
        cond_labels, cond_counts = ['Unknown'], [total]
    
    # 7. Body type distribution
    if 'body_type' in df.columns:
        body = df['body_type'].value_counts().head(8)
        body_labels = body.index.tolist()
        body_counts = body.values.tolist()
    else:
        body_labels, body_counts = [], []
    
    # 8. Fuel type distribution
    if 'fuel_type' in df.columns:
        fuel = df['fuel_type'].value_counts()
        fuel_labels = fuel.index.tolist()
        fuel_counts = fuel.values.tolist()
    else:
        fuel_labels, fuel_counts = [], []
    
    # 9. Mileage vs Price scatter (for used cars)
    scatter_data = []
    if with_price.any() and 'mileage_km' in df.columns:
        scatter_df = df[with_price & df['mileage_km'].notna() & (df['mileage_km'] > 100)]
        for _, row in scatter_df.iterrows():
            year_val = int(row['year']) if pd.notna(row.get('year')) else '?'
            scatter_data.append({
                'x': int(row['mileage_km']),
                'y': int(row['price_aed']),
                'label': f"{row.get('brand', '?')} {row.get('model', '?')} {year_val}"
            })
    
    # 10. Source split
    source_labels = list(source_counts.keys())
    source_values = list(source_counts.values())
    
    # ---- Generate HTML ----
    
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UAE Car Market Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0e1a;
            --bg-card: #111827;
            --bg-card-hover: #1a2332;
            --border: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-1: #3b82f6;
            --accent-2: #8b5cf6;
            --accent-3: #06b6d4;
            --accent-4: #10b981;
            --accent-5: #f59e0b;
            --accent-6: #ef4444;
            --gradient-1: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --gradient-2: linear-gradient(135deg, #06b6d4, #10b981);
            --gradient-3: linear-gradient(135deg, #f59e0b, #ef4444);
            --gradient-4: linear-gradient(135deg, #8b5cf6, #ec4899);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }}
        
        .hero {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            padding: 48px 24px;
            text-align: center;
            border-bottom: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }}
        
        .hero::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 30% 50%, rgba(59,130,246,0.08) 0%, transparent 50%),
                        radial-gradient(circle at 70% 50%, rgba(139,92,246,0.08) 0%, transparent 50%);
            animation: pulse 8s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .hero h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa, #a78bfa, #60a5fa);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s linear infinite;
            position: relative;
            margin-bottom: 8px;
        }}
        
        @keyframes shimmer {{
            0% {{ background-position: 0% center; }}
            100% {{ background-position: 200% center; }}
        }}
        
        .hero .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            position: relative;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px 24px;
        }}
        
        /* Stat cards */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-1);
            box-shadow: 0 8px 32px rgba(59, 130, 246, 0.15);
        }}
        
        .stat-card .stat-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .stat-card .stat-value {{
            font-size: 1.8rem;
            font-weight: 800;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stat-card:nth-child(2) .stat-value {{ background: var(--gradient-2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stat-card:nth-child(3) .stat-value {{ background: var(--gradient-3); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stat-card:nth-child(4) .stat-value {{ background: var(--gradient-4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stat-card:nth-child(5) .stat-value {{ background: var(--gradient-1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stat-card:nth-child(6) .stat-value {{ background: var(--gradient-2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        
        /* Chart grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 32px;
        }}
        
        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s ease;
        }}
        
        .chart-card:hover {{
            border-color: rgba(59, 130, 246, 0.3);
        }}
        
        .chart-card.full-width {{
            grid-column: 1 / -1;
        }}
        
        .chart-card h3 {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .chart-card h3 .icon {{
            font-size: 1.2rem;
        }}
        
        .chart-container {{
            position: relative;
            height: 320px;
        }}
        
        .chart-container.tall {{
            height: 400px;
        }}
        
        /* Table styles */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        
        .data-table th {{
            text-align: left;
            padding: 12px 16px;
            background: rgba(59, 130, 246, 0.1);
            color: var(--accent-1);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.75rem;
            border-bottom: 1px solid var(--border);
        }}
        
        .data-table td {{
            padding: 10px 16px;
            border-bottom: 1px solid var(--border);
            color: var(--text-secondary);
        }}
        
        .data-table tr:hover td {{
            background: var(--bg-card-hover);
            color: var(--text-primary);
        }}
        
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-new {{ background: rgba(16, 185, 129, 0.15); color: #10b981; }}
        .badge-used {{ background: rgba(245, 158, 11, 0.15); color: #f59e0b; }}
        .badge-gcc {{ background: rgba(59, 130, 246, 0.15); color: #3b82f6; }}
        .badge-import {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; }}
        
        .footer {{
            text-align: center;
            padding: 24px;
            color: var(--text-secondary);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
        }}
        
        @media (max-width: 768px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .hero h1 {{ font-size: 1.8rem; }}
        }}
    </style>
</head>
<body>

<div class="hero">
    <h1>🚗 UAE Car Market Dashboard</h1>
    <p class="subtitle">Market intelligence from Dubizzle & Dubicars — {timestamp}</p>
</div>

<div class="container">
    <!-- Stats -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Listings</div>
            <div class="stat-value">{total:,}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Average Price</div>
            <div class="stat-value">AED {avg_price:,}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Median Price</div>
            <div class="stat-value">AED {median_price:,}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Price Range</div>
            <div class="stat-value">AED {min_price:,} — {max_price:,}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Brands Identified</div>
            <div class="stat-value">{brands_found}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Data Quality</div>
            <div class="stat-value">{avg_quality}%</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid">
        <div class="chart-card">
            <h3><span class="icon">📊</span> Price Distribution (AED)</h3>
            <div class="chart-container"><canvas id="priceHist"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">🏷️</span> Top Brands by Listings</h3>
            <div class="chart-container"><canvas id="topBrands"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">💰</span> Average Price by Brand</h3>
            <div class="chart-container"><canvas id="priceByBrand"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">📅</span> Listings by Model Year</h3>
            <div class="chart-container"><canvas id="yearDist"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">🆕</span> Condition Split</h3>
            <div class="chart-container"><canvas id="conditionPie"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">🚙</span> Body Type Distribution</h3>
            <div class="chart-container"><canvas id="bodyType"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">⛽</span> Fuel Type Distribution</h3>
            <div class="chart-container"><canvas id="fuelType"></canvas></div>
        </div>
        <div class="chart-card">
            <h3><span class="icon">📡</span> Source Distribution</h3>
            <div class="chart-container"><canvas id="sourcePie"></canvas></div>
        </div>
        <div class="chart-card full-width">
            <h3><span class="icon">📉</span> Mileage vs Price (Depreciation View)</h3>
            <div class="chart-container tall"><canvas id="scatterPlot"></canvas></div>
        </div>
    </div>
</div>

<div class="footer">
    UAE Car Market Dashboard — Generated from {total} listings scraped from Dubizzle & Dubicars
</div>

<script>
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = '#1e293b';
    Chart.defaults.font.family = 'Inter, sans-serif';

    const palette = ['#3b82f6','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16','#e879f9','#22d3ee','#a3e635','#fb923c'];

    // Price histogram
    new Chart(document.getElementById('priceHist'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(bin_labels)},
            datasets: [{{ label: 'Listings', data: {json.dumps(hist_counts)}, backgroundColor: palette.slice(0, {len(bin_labels)}), borderRadius: 6, borderWidth: 0 }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }}, x: {{ grid: {{ display: false }} }} }} }}
    }});

    // Top brands
    new Chart(document.getElementById('topBrands'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(brand_labels)},
            datasets: [{{ label: 'Listings', data: {json.dumps(brand_counts)}, backgroundColor: palette.slice(0, {len(brand_labels)}), borderRadius: 6, borderWidth: 0 }}]
        }},
        options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#1e293b' }} }}, y: {{ grid: {{ display: false }} }} }} }}
    }});

    // Price by brand
    new Chart(document.getElementById('priceByBrand'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(price_by_brand_labels)},
            datasets: [{{ label: 'Avg Price (AED)', data: {json.dumps(price_by_brand_values)}, backgroundColor: 'rgba(139,92,246,0.6)', borderColor: '#8b5cf6', borderWidth: 1, borderRadius: 6 }}]
        }},
        options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ callback: v => 'AED ' + v.toLocaleString() }} }}, y: {{ grid: {{ display: false }} }} }} }}
    }});

    // Year distribution
    new Chart(document.getElementById('yearDist'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(year_labels)},
            datasets: [{{ label: 'Listings', data: {json.dumps(year_counts)}, backgroundColor: 'rgba(6,182,212,0.6)', borderColor: '#06b6d4', borderWidth: 1, borderRadius: 6 }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ grid: {{ color: '#1e293b' }} }}, x: {{ grid: {{ display: false }} }} }} }}
    }});

    // Condition pie
    new Chart(document.getElementById('conditionPie'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(cond_labels)},
            datasets: [{{ data: {json.dumps(cond_counts)}, backgroundColor: ['#10b981','#f59e0b','#64748b','#ef4444'], borderWidth: 0, hoverOffset: 8 }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: {{ legend: {{ position: 'bottom' }} }} }}
    }});

    // Body type
    new Chart(document.getElementById('bodyType'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(body_labels)},
            datasets: [{{ data: {json.dumps(body_counts)}, backgroundColor: palette.slice(0, {len(body_labels)}), borderWidth: 0, hoverOffset: 8 }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: {{ legend: {{ position: 'bottom' }} }} }}
    }});

    // Fuel type
    new Chart(document.getElementById('fuelType'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(fuel_labels)},
            datasets: [{{ data: {json.dumps(fuel_counts)}, backgroundColor: ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6'], borderWidth: 0, hoverOffset: 8 }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: {{ legend: {{ position: 'bottom' }} }} }}
    }});

    // Source pie
    new Chart(document.getElementById('sourcePie'), {{
        type: 'doughnut',
        data: {{
            labels: {json.dumps(source_labels)},
            datasets: [{{ data: {json.dumps(source_values)}, backgroundColor: ['#3b82f6','#8b5cf6'], borderWidth: 0, hoverOffset: 8 }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: {{ legend: {{ position: 'bottom' }} }} }}
    }});

    // Scatter: Mileage vs Price
    new Chart(document.getElementById('scatterPlot'), {{
        type: 'scatter',
        data: {{
            datasets: [{{
                label: 'Cars',
                data: {json.dumps(scatter_data)},
                backgroundColor: 'rgba(59,130,246,0.5)',
                borderColor: '#3b82f6',
                borderWidth: 1,
                pointRadius: 5,
                pointHoverRadius: 8
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                x: {{ title: {{ display: true, text: 'Mileage (km)', color: '#94a3b8' }}, grid: {{ color: '#1e293b' }}, ticks: {{ callback: v => v.toLocaleString() + ' km' }} }},
                y: {{ title: {{ display: true, text: 'Price (AED)', color: '#94a3b8' }}, grid: {{ color: '#1e293b' }}, ticks: {{ callback: v => 'AED ' + v.toLocaleString() }} }}
            }},
            plugins: {{
                tooltip: {{
                    callbacks: {{
                        label: ctx => ctx.raw.label + ' — AED ' + ctx.raw.y.toLocaleString() + ' | ' + ctx.raw.x.toLocaleString() + ' km'
                    }}
                }},
                legend: {{ display: false }}
            }}
        }}
    }});
</script>

</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  ✅ Dashboard saved to {output_path}")
    print(f"  📂 Open in browser: file:///{os.path.abspath(output_path).replace(os.sep, '/')}")


if __name__ == "__main__":
    generate_dashboard()
