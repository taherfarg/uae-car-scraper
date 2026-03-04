"""
UAE Car Market — Interactive Analytics Dashboard Generator (v2)
Reads the processed CSV and generates a self-contained HTML dashboard.
"""

import pandas as pd
import json
import os
from datetime import datetime


def generate_dashboard(csv_path="uae_cars_market_data.csv", output_path="dashboard.html"):
    print(f"📊 Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    if df.empty:
        print("❌ No data found in CSV.")
        return
    print(f"  ✓ {len(df)} records loaded")

    wp = df['price_aed'].notna()
    total        = len(df)
    avg_price    = int(df.loc[wp, 'price_aed'].mean())   if wp.any() else 0
    median_price = int(df.loc[wp, 'price_aed'].median()) if wp.any() else 0
    min_price    = int(df.loc[wp, 'price_aed'].min())    if wp.any() else 0
    max_price    = int(df.loc[wp, 'price_aed'].max())    if wp.any() else 0
    brands_found = int(df['brand'].nunique())             if 'brand' in df.columns else 0
    avg_quality  = int(df['data_quality'].mean())         if 'data_quality' in df.columns else 0
    source_counts = df['source'].value_counts().to_dict()

    # Top brands
    top_brands   = df['brand'].value_counts().head(15)
    brand_labels = top_brands.index.tolist()
    brand_counts = top_brands.values.tolist()

    # Avg price by brand
    bp = df[wp].groupby('brand')['price_aed'].agg(['mean','count'])
    bp = bp[bp['count'] >= 2].sort_values('mean', ascending=False).head(12)
    price_brand_labels = bp.index.tolist()
    price_brand_values = [int(v) for v in bp['mean']]

    # Price histogram
    bins       = [0,25000,50000,75000,100000,150000,200000,300000,500000,1000000,float('inf')]
    bin_labels = ['<25K','25-50K','50-75K','75-100K','100-150K','150-200K','200-300K','300-500K','500K-1M','1M+']
    hist_counts = pd.cut(df.loc[wp,'price_aed'], bins=bins, labels=bin_labels).value_counts().reindex(bin_labels).fillna(0).astype(int).tolist() if wp.any() else []

    # Year dist
    yd = df['year'].dropna().astype(int).value_counts().sort_index() if 'year' in df.columns else pd.Series()
    year_labels = [str(y) for y in yd.index.tolist()]
    year_counts = yd.values.tolist()

    # Avg price by year (depreciation)
    if 'year' in df.columns and wp.any():
        yp = df[wp].groupby(df.loc[wp,'year'].astype(int))['price_aed'].mean().sort_index()
        yp = yp[yp.index >= 2010]
        dep_years  = [str(y) for y in yp.index.tolist()]
        dep_values = [int(v) for v in yp.values]
    else:
        dep_years, dep_values = [], []

    # Condition
    cond = df['condition'].value_counts() if 'condition' in df.columns else pd.Series()
    cond_labels = cond.index.tolist(); cond_counts = cond.values.tolist()

    # Body type
    body = df['body_type'].value_counts().head(8) if 'body_type' in df.columns else pd.Series()
    body_labels = body.index.tolist(); body_counts = body.values.tolist()

    # Fuel type
    fuel = df['fuel_type'].value_counts() if 'fuel_type' in df.columns else pd.Series()
    fuel_labels = fuel.index.tolist(); fuel_counts = fuel.values.tolist()

    # Market tier
    tier = df['market_tier'].value_counts() if 'market_tier' in df.columns else pd.Series()
    tier_order  = ['Budget','Mid-Range','Premium','Luxury','Ultra Luxury']
    tier_labels = [t for t in tier_order if t in tier.index]
    tier_counts = [int(tier.get(t, 0)) for t in tier_labels]

    # GCC vs Import
    specs = df['specs_origin'].value_counts() if 'specs_origin' in df.columns else pd.Series()
    specs_labels = specs.index.tolist(); specs_counts = specs.values.tolist()

    # Transmission
    trans = df['transmission'].value_counts() if 'transmission' in df.columns else pd.Series()
    trans_labels = trans.index.tolist(); trans_counts = trans.values.tolist()

    # Scatter data (sample 800 pts for performance)
    scatter_data = []
    if wp.any() and 'mileage_km' in df.columns:
        sdf = df[wp & df['mileage_km'].notna() & (df['mileage_km'] > 100)].sample(min(800, int((wp & df['mileage_km'].notna() & (df['mileage_km'] > 100)).sum())), random_state=42)
        for _, row in sdf.iterrows():
            yr = int(row['year']) if pd.notna(row.get('year')) else '?'
            scatter_data.append({'x': int(row['mileage_km']), 'y': int(row['price_aed']),
                                  'label': f"{row.get('brand','?')} {row.get('model','?')} {yr}"})

    # Brand → model drill-down data
    drill_data = {}
    if 'brand' in df.columns and 'model' in df.columns:
        for brand in brand_labels[:12]:
            models = df[df['brand'] == brand]['model'].value_counts().head(8)
            drill_data[brand] = {'labels': models.index.tolist(), 'counts': models.values.tolist()}

    # Top 10 most/cheapest listings
    if wp.any():
        top_exp = df[wp].nlargest(10, 'price_aed')[['brand','model','year','price_aed','mileage_km','condition','link']].fillna('—')
        top_chp = df[wp].nsmallest(10, 'price_aed')[['brand','model','year','price_aed','mileage_km','condition','link']].fillna('—')
        def rows_to_json(sub):
            return [{'brand': str(r.brand), 'model': str(r.model),
                     'year': str(r.year), 'price': int(r.price_aed) if pd.notna(r.price_aed) else 0,
                     'km': str(r.mileage_km), 'cond': str(r.condition), 'link': str(r.link)}
                    for r in sub.itertuples()]
        exp_rows = rows_to_json(top_exp)
        chp_rows = rows_to_json(top_chp)
    else:
        exp_rows = chp_rows = []

    # Full table data (max 2000 rows for browser performance)
    table_cols = ['brand','model','year','price_aed','mileage_km','condition','body_type','fuel_type','transmission','market_tier','specs_origin','source']
    table_cols = [c for c in table_cols if c in df.columns]
    table_df = df[table_cols].copy().head(2000)
    table_df = table_df.where(pd.notnull(table_df), None)
    table_data = table_df.values.tolist()
    table_headers = table_cols

    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")

    # ------------------------------------------------------------------ HTML
    html = _build_html(
        timestamp=timestamp, total=total, avg_price=avg_price,
        median_price=median_price, min_price=min_price, max_price=max_price,
        brands_found=brands_found, avg_quality=avg_quality,
        source_counts=source_counts,
        brand_labels=brand_labels, brand_counts=brand_counts,
        price_brand_labels=price_brand_labels, price_brand_values=price_brand_values,
        bin_labels=bin_labels, hist_counts=hist_counts,
        year_labels=year_labels, year_counts=year_counts,
        dep_years=dep_years, dep_values=dep_values,
        cond_labels=cond_labels, cond_counts=cond_counts,
        body_labels=body_labels, body_counts=body_counts,
        fuel_labels=fuel_labels, fuel_counts=fuel_counts,
        tier_labels=tier_labels, tier_counts=tier_counts,
        specs_labels=specs_labels, specs_counts=specs_counts,
        trans_labels=trans_labels, trans_counts=trans_counts,
        scatter_data=scatter_data, drill_data=drill_data,
        exp_rows=exp_rows, chp_rows=chp_rows,
        table_headers=table_headers, table_data=table_data,
    )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✅ Dashboard saved to {output_path}")
    print(f"  📂 Open in browser: file:///{os.path.abspath(output_path).replace(os.sep, '/')}")


def _build_html(**d):
    J = json.dumps
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UAE Car Market Intelligence Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#07090f;--bg2:#0d1117;--card:#111827;--card2:#161f2e;
  --border:#1e2d42;--border2:#243348;
  --txt:#e8edf5;--txt2:#8899b4;--txt3:#566a87;
  --blue:#3b82f6;--purple:#8b5cf6;--cyan:#06b6d4;--green:#10b981;
  --amber:#f59e0b;--red:#ef4444;--pink:#ec4899;--orange:#f97316;
  --g1:linear-gradient(135deg,#3b82f6,#8b5cf6);
  --g2:linear-gradient(135deg,#06b6d4,#10b981);
  --g3:linear-gradient(135deg,#f59e0b,#ef4444);
  --g4:linear-gradient(135deg,#8b5cf6,#ec4899);
  --g5:linear-gradient(135deg,#10b981,#06b6d4);
}}
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--txt);min-height:100vh;overflow-x:hidden}}

/* ── NAV ── */
.nav{{position:sticky;top:0;z-index:100;background:rgba(7,9,15,0.92);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:0 24px;display:flex;align-items:center;gap:0;height:56px}}
.nav-brand{{font-weight:800;font-size:1rem;background:var(--g1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-right:32px;white-space:nowrap}}
.nav-links{{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}}
.nav-links::-webkit-scrollbar{{display:none}}
.nav-link{{padding:6px 14px;border-radius:8px;font-size:0.8rem;font-weight:500;color:var(--txt2);cursor:pointer;border:none;background:none;white-space:nowrap;transition:all .2s}}
.nav-link:hover,.nav-link.active{{background:rgba(59,130,246,.12);color:var(--blue)}}

/* ── HERO ── */
.hero{{background:linear-gradient(135deg,#070c18 0%,#0f1629 40%,#0a0f1e 100%);padding:60px 24px 48px;text-align:center;position:relative;overflow:hidden;border-bottom:1px solid var(--border)}}
.hero::before{{content:'';position:absolute;inset:0;background:
  radial-gradient(ellipse 60% 60% at 20% 50%,rgba(59,130,246,.07) 0%,transparent 70%),
  radial-gradient(ellipse 50% 70% at 80% 30%,rgba(139,92,246,.07) 0%,transparent 70%),
  radial-gradient(ellipse 40% 40% at 50% 80%,rgba(6,182,212,.05) 0%,transparent 60%);
  animation:breathe 10s ease-in-out infinite}}
@keyframes breathe{{0%,100%{{opacity:1}}50%{{opacity:.6}}}}
.hero-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.25);border-radius:999px;padding:4px 14px;font-size:.75rem;font-weight:600;color:var(--blue);margin-bottom:20px;position:relative}}
.hero h1{{font-size:clamp(2rem,5vw,3.5rem);font-weight:900;line-height:1.1;position:relative;margin-bottom:12px}}
.hero h1 span{{background:linear-gradient(135deg,#60a5fa,#a78bfa,#67e8f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-size:200%;animation:shimmer 4s linear infinite}}
@keyframes shimmer{{0%{{background-position:0%}}100%{{background-position:200%}}}}
.hero p{{color:var(--txt2);font-size:1rem;position:relative}}

/* ── LAYOUT ── */
.wrap{{max-width:1440px;margin:0 auto;padding:32px 20px}}
.section{{margin-bottom:48px;scroll-margin-top:72px}}
.section-title{{font-size:1.1rem;font-weight:700;color:var(--txt);margin-bottom:20px;display:flex;align-items:center;gap:10px}}
.section-title::after{{content:'';flex:1;height:1px;background:var(--border)}}

/* ── STAT CARDS ── */
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:32px}}
.stat{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px 20px;position:relative;overflow:hidden;transition:all .3s;cursor:default}}
.stat::before{{content:'';position:absolute;inset:0;opacity:0;transition:opacity .3s;background:linear-gradient(135deg,rgba(59,130,246,.06),rgba(139,92,246,.06))}}
.stat:hover{{transform:translateY(-3px);border-color:rgba(59,130,246,.35);box-shadow:0 12px 40px rgba(59,130,246,.12)}}
.stat:hover::before{{opacity:1}}
.stat-icon{{font-size:1.5rem;margin-bottom:10px}}
.stat-label{{font-size:.72rem;color:var(--txt3);text-transform:uppercase;letter-spacing:.06em;font-weight:600;margin-bottom:6px}}
.stat-val{{font-size:1.65rem;font-weight:800;line-height:1}}
.s0 .stat-val{{background:var(--g1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.s1 .stat-val{{background:var(--g2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.s2 .stat-val{{background:var(--g3);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.s3 .stat-val{{background:var(--g4);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.s4 .stat-val{{background:var(--g5);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.s5 .stat-val{{background:var(--g1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.s6 .stat-val{{background:var(--g2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}

/* ── CHART CARDS ── */
.grid2{{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
.full{{grid-column:1/-1}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;transition:border-color .3s}}
.card:hover{{border-color:var(--border2)}}
.card-title{{font-size:.9rem;font-weight:600;color:var(--txt);margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.chart-wrap{{position:relative;height:300px}}
.chart-wrap.tall{{height:380px}}
.chart-wrap.short{{height:240px}}

/* ── FILTER BAR ── */
.filter-bar{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;margin-bottom:24px;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}}
.filter-group{{display:flex;flex-direction:column;gap:6px;min-width:150px}}
.filter-group label{{font-size:.72rem;color:var(--txt3);text-transform:uppercase;letter-spacing:.05em;font-weight:600}}
.filter-group select,.filter-group input{{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:8px 12px;color:var(--txt);font-size:.85rem;font-family:inherit;outline:none;transition:border-color .2s}}
.filter-group select:focus,.filter-group input:focus{{border-color:var(--blue)}}
.filter-group input[type=range]{{padding:6px 0;accent-color:var(--blue)}}
.range-display{{font-size:.75rem;color:var(--blue);font-weight:600;text-align:center}}
.btn{{padding:9px 20px;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;border:none;transition:all .2s}}
.btn-primary{{background:var(--g1);color:#fff}}
.btn-primary:hover{{opacity:.85;transform:translateY(-1px)}}
.btn-ghost{{background:transparent;border:1px solid var(--border);color:var(--txt2)}}
.btn-ghost:hover{{border-color:var(--blue);color:var(--blue)}}

/* ── DATA TABLE ── */
.table-wrap{{overflow:auto;border-radius:12px;border:1px solid var(--border)}}
table{{width:100%;border-collapse:collapse;font-size:.8rem}}
thead th{{background:rgba(59,130,246,.08);color:var(--blue);padding:10px 14px;text-align:left;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border);white-space:nowrap;cursor:pointer;user-select:none}}
thead th:hover{{background:rgba(59,130,246,.14)}}
thead th .sort-icon{{margin-left:4px;opacity:.5}}
tbody tr{{border-bottom:1px solid var(--border);transition:background .15s}}
tbody tr:hover{{background:var(--card2)}}
tbody td{{padding:9px 14px;color:var(--txt2);white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis}}
.badge{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}}
.b-new{{background:rgba(16,185,129,.15);color:#10b981}}
.b-used{{background:rgba(245,158,11,.15);color:#f59e0b}}
.b-gcc{{background:rgba(59,130,246,.15);color:#3b82f6}}
.b-imp{{background:rgba(239,68,68,.15);color:#ef4444}}
.b-bud{{background:rgba(100,116,139,.15);color:#94a3b8}}
.b-mid{{background:rgba(6,182,212,.15);color:#06b6d4}}
.b-pre{{background:rgba(139,92,246,.15);color:#8b5cf6}}
.b-lux{{background:rgba(245,158,11,.15);color:#f59e0b}}
.b-ult{{background:rgba(239,68,68,.15);color:#ef4444}}
.pagination{{display:flex;gap:8px;align-items:center;justify-content:flex-end;margin-top:16px;flex-wrap:wrap}}
.pagination button{{background:var(--card);border:1px solid var(--border);color:var(--txt2);padding:6px 12px;border-radius:8px;cursor:pointer;font-size:.8rem;transition:all .2s}}
.pagination button:hover,.pagination button.active{{border-color:var(--blue);color:var(--blue);background:rgba(59,130,246,.08)}}
.pagination .pg-info{{color:var(--txt3);font-size:.8rem}}

/* ── TOP CARS ── */
.cars-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}}
.car-card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;transition:all .3s}}
.car-card:hover{{border-color:var(--border2);transform:translateY(-2px)}}
.car-brand{{font-size:.7rem;color:var(--txt3);text-transform:uppercase;letter-spacing:.06em;font-weight:600}}
.car-name{{font-size:1rem;font-weight:700;margin:2px 0 8px}}
.car-price{{font-size:1.4rem;font-weight:800;background:var(--g1);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.car-meta{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}
.car-meta span{{font-size:.72rem;color:var(--txt2)}}
.car-link{{display:block;margin-top:10px;font-size:.75rem;color:var(--blue);text-decoration:none;font-weight:600}}
.car-link:hover{{text-decoration:underline}}

/* ── DRILL-DOWN ── */
.drill-brands{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}}
.drill-btn{{padding:6px 14px;border-radius:8px;font-size:.8rem;font-weight:600;cursor:pointer;border:1px solid var(--border);background:var(--bg2);color:var(--txt2);transition:all .2s}}
.drill-btn:hover,.drill-btn.active{{background:rgba(59,130,246,.12);border-color:var(--blue);color:var(--blue)}}

/* ── MISC ── */
.source-pill{{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:999px;font-size:.75rem;font-weight:600;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.2);color:var(--blue)}}
.footer{{text-align:center;padding:32px;color:var(--txt3);font-size:.8rem;border-top:1px solid var(--border)}}
@media(max-width:900px){{.grid2,.grid3{{grid-template-columns:1fr}}.full{{grid-column:1}}}}
@media(max-width:600px){{.stats{{grid-template-columns:repeat(2,1fr)}}.hero h1{{font-size:1.8rem}}}}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-brand">🚗 UAE Cars</div>
  <div class="nav-links">
    <button class="nav-link active" onclick="scrollTo('overview')">Overview</button>
    <button class="nav-link" onclick="scrollTo('brands')">Brands</button>
    <button class="nav-link" onclick="scrollTo('prices')">Prices</button>
    <button class="nav-link" onclick="scrollTo('market')">Market Mix</button>
    <button class="nav-link" onclick="scrollTo('depreciation')">Depreciation</button>
    <button class="nav-link" onclick="scrollTo('toplists')">Top Lists</button>
    <button class="nav-link" onclick="scrollTo('explorer')">Data Explorer</button>
  </div>
</nav>

<div class="hero">
  <div class="hero-badge">🇦🇪 Live Market Data</div>
  <h1><span>UAE Car Market</span><br>Intelligence Dashboard</h1>
  <p>Scraped from Dubizzle &amp; Dubicars · {d['timestamp']}</p>
</div>

<div class="wrap">

<!-- OVERVIEW -->
<div class="section" id="overview">
  <div class="section-title">📊 Overview</div>
  <div class="stats">
    <div class="stat s0"><div class="stat-icon">📋</div><div class="stat-label">Total Listings</div><div class="stat-val">{d['total']:,}</div></div>
    <div class="stat s1"><div class="stat-icon">💵</div><div class="stat-label">Average Price</div><div class="stat-val">AED {d['avg_price']:,}</div></div>
    <div class="stat s2"><div class="stat-icon">📍</div><div class="stat-label">Median Price</div><div class="stat-val">AED {d['median_price']:,}</div></div>
    <div class="stat s3"><div class="stat-icon">🏷️</div><div class="stat-label">Brands</div><div class="stat-val">{d['brands_found']}</div></div>
    <div class="stat s4"><div class="stat-icon">⬇️</div><div class="stat-label">Min Price</div><div class="stat-val">AED {d['min_price']:,}</div></div>
    <div class="stat s5"><div class="stat-icon">⬆️</div><div class="stat-label">Max Price</div><div class="stat-val">AED {d['max_price']:,}</div></div>
    <div class="stat s6"><div class="stat-icon">✅</div><div class="stat-label">Data Quality</div><div class="stat-val">{d['avg_quality']}%</div></div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-title">📊 Price Distribution (AED)</div>
      <div class="chart-wrap"><canvas id="priceHist"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">📅 Listings by Model Year</div>
      <div class="chart-wrap"><canvas id="yearDist"></canvas></div>
    </div>
  </div>
</div>

<!-- BRANDS -->
<div class="section" id="brands">
  <div class="section-title">🏷️ Brand Analysis</div>
  <div class="grid2">
    <div class="card">
      <div class="card-title">🔢 Top 15 Brands by Listings</div>
      <div class="chart-wrap tall"><canvas id="topBrands"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">💰 Average Price by Brand (Top 12)</div>
      <div class="chart-wrap tall"><canvas id="priceByBrand"></canvas></div>
    </div>
  </div>
  <div class="card" style="margin-top:20px">
    <div class="card-title">🔍 Brand → Model Drill-Down</div>
    <div class="drill-brands" id="drillBtns"></div>
    <div class="chart-wrap"><canvas id="drillChart"></canvas></div>
  </div>
</div>

<!-- PRICES -->
<div class="section" id="prices">
  <div class="section-title">💰 Price Deep Dive</div>
  <div class="grid2">
    <div class="card">
      <div class="card-title">🏅 Market Tier Distribution</div>
      <div class="chart-wrap"><canvas id="tierChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">📉 Mileage vs Price (Depreciation Scatter)</div>
      <div class="chart-wrap"><canvas id="scatter"></canvas></div>
    </div>
  </div>
</div>

<!-- MARKET MIX -->
<div class="section" id="market">
  <div class="section-title">🔀 Market Mix</div>
  <div class="grid3">
    <div class="card">
      <div class="card-title">🏁 Condition</div>
      <div class="chart-wrap short"><canvas id="condPie"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">🚙 Body Type</div>
      <div class="chart-wrap short"><canvas id="bodyChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">⛽ Fuel Type</div>
      <div class="chart-wrap short"><canvas id="fuelChart"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">🌍 GCC vs Import</div>
      <div class="chart-wrap short"><canvas id="specsPie"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">⚙️ Transmission</div>
      <div class="chart-wrap short"><canvas id="transPie"></canvas></div>
    </div>
    <div class="card">
      <div class="card-title">📡 Data Source</div>
      <div class="chart-wrap short"><canvas id="sourcePie"></canvas></div>
    </div>
  </div>
</div>

<!-- DEPRECIATION -->
<div class="section" id="depreciation">
  <div class="section-title">📉 Price Depreciation by Year</div>
  <div class="card full">
    <div class="card-title">Average Listing Price by Model Year</div>
    <div class="chart-wrap tall"><canvas id="depChart"></canvas></div>
  </div>
</div>

<!-- TOP LISTS -->
<div class="section" id="toplists">
  <div class="section-title">🏆 Top Lists</div>
  <div class="card-title" style="margin-bottom:14px">💎 10 Most Expensive Listings</div>
  <div class="cars-grid" id="expGrid"></div>
  <div class="card-title" style="margin:28px 0 14px">💸 10 Cheapest Listings</div>
  <div class="cars-grid" id="chpGrid"></div>
</div>

<!-- DATA EXPLORER -->
<div class="section" id="explorer">
  <div class="section-title">🔭 Data Explorer</div>
  <div class="filter-bar">
    <div class="filter-group">
      <label>Search</label>
      <input type="text" id="fSearch" placeholder="Brand, model..." oninput="applyFilters()">
    </div>
    <div class="filter-group">
      <label>Brand</label>
      <select id="fBrand" onchange="applyFilters()"><option value="">All</option></select>
    </div>
    <div class="filter-group">
      <label>Body Type</label>
      <select id="fBody" onchange="applyFilters()"><option value="">All</option></select>
    </div>
    <div class="filter-group">
      <label>Condition</label>
      <select id="fCond" onchange="applyFilters()"><option value="">All</option></select>
    </div>
    <div class="filter-group">
      <label>Fuel</label>
      <select id="fFuel" onchange="applyFilters()"><option value="">All</option></select>
    </div>
    <div class="filter-group">
      <label>Market Tier</label>
      <select id="fTier" onchange="applyFilters()"><option value="">All</option></select>
    </div>
    <div class="filter-group">
      <label>Source</label>
      <select id="fSource" onchange="applyFilters()"><option value="">All</option></select>
    </div>
    <button class="btn btn-ghost" onclick="resetFilters()">Reset</button>
  </div>
  <div id="filterCount" style="font-size:.8rem;color:var(--txt3);margin-bottom:12px"></div>
  <div class="table-wrap">
    <table id="dataTable">
      <thead id="tableHead"></thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
  <div class="pagination" id="pager"></div>
</div>

</div><!-- /wrap -->

<div class="footer">
  UAE Car Market Intelligence · {d['total']:,} listings from Dubizzle & Dubicars · Generated {d['timestamp']}
</div>

<script>
// ── DATA ──
const PALETTE = ['#3b82f6','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16','#e879f9','#22d3ee','#a3e635','#fb923c'];
Chart.defaults.color = '#8899b4';
Chart.defaults.borderColor = '#1e2d42';
Chart.defaults.font.family = 'Inter, sans-serif';
const fmtAED = v => 'AED ' + Number(v).toLocaleString();
const fmtKm  = v => Number(v).toLocaleString() + ' km';

function mkChart(id, type, labels, data, opts={{}}) {{
  const datasets = Array.isArray(data[0]) ? data : [{{
    label: opts.label||'',
    data,
    backgroundColor: opts.single ? opts.single : (type==='line' ? 'transparent' : PALETTE.slice(0, labels.length)),
    borderColor: type==='line' ? (opts.lineColor||'#3b82f6') : undefined,
    borderWidth: type==='line' ? 2 : 0,
    borderRadius: (type==='bar') ? 6 : undefined,
    pointRadius: type==='line' ? 4 : undefined,
    pointHoverRadius: type==='line' ? 7 : undefined,
    fill: type==='line' ? (opts.fill||false) : undefined,
    hoverOffset: type==='doughnut' ? 8 : undefined,
    tension: type==='line' ? 0.4 : undefined,
  }}];
  return new Chart(document.getElementById(id), {{
    type, data:{{labels, datasets}},
    options:{{
      responsive:true, maintainAspectRatio:false,
      indexAxis: opts.horizontal ? 'y' : 'x',
      cutout: type==='doughnut' ? '58%' : undefined,
      plugins:{{
        legend:{{display: type==='doughnut' || !!opts.legend, position:'bottom', labels:{{boxWidth:12,padding:12}}}},
        tooltip:{{callbacks:{{label: opts.tooltip || (ctx=>ctx.dataset.label + ': ' + ctx.parsed.y?.toLocaleString() ?? ctx.parsed.toLocaleString())}}}}
      }},
      scales: type!=='doughnut' ? {{
        x:{{grid:{{color:'#1e2d42', display: opts.horizontal ? true : !opts.noXGrid}}, ticks:{{callback: opts.xTick||undefined}}}},
        y:{{grid:{{color:'#1e2d42', display: opts.horizontal ? false : true}}, ticks:{{callback: opts.yTick||undefined}}}}
      }} : undefined,
      ...opts.extra
    }}
  }});
}}

// ── CHARTS ──
mkChart('priceHist','bar',{J(d['bin_labels'])},{J(d['hist_counts'])},{{single:PALETTE.slice(0,10),noXGrid:true}});
mkChart('yearDist','bar',{J(d['year_labels'])},{J(d['year_counts'])},{{single:'rgba(6,182,212,0.7)',noXGrid:true}});
mkChart('topBrands','bar',{J(d['brand_labels'])},{J(d['brand_counts'])},{{horizontal:true}});
mkChart('priceByBrand','bar',{J(d['price_brand_labels'])},{J(d['price_brand_values'])},{{horizontal:true,single:'rgba(139,92,246,0.7)',xTick:v=>'AED '+v.toLocaleString()}});
mkChart('condPie','doughnut',{J(d['cond_labels'])},{J(d['cond_counts'])},{{legend:true}});
mkChart('bodyChart','doughnut',{J(d['body_labels'])},{J(d['body_counts'])},{{legend:true}});
mkChart('fuelChart','doughnut',{J(d['fuel_labels'])},{J(d['fuel_counts'])},{{legend:true}});
mkChart('specsPie','doughnut',{J(d['specs_labels'])},{J(d['specs_counts'])},{{legend:true}});
mkChart('transPie','doughnut',{J(d['trans_labels'])},{J(d['trans_counts'])},{{legend:true}});
mkChart('sourcePie','doughnut',{J(list(d['source_counts'].keys()))},{J(list(d['source_counts'].values()))},{{legend:true}});
mkChart('tierChart','bar',{J(d['tier_labels'])},{J(d['tier_counts'])},{{single:PALETTE.slice(0,5),noXGrid:true}});
mkChart('depChart','line',{J(d['dep_years'])},{J(d['dep_values'])},{{lineColor:'#3b82f6',yTick:v=>'AED '+v.toLocaleString(),extra:{{fill:true}}}});

// Scatter
new Chart(document.getElementById('scatter'),{{
  type:'scatter',
  data:{{datasets:[{{label:'Car',data:{J(d['scatter_data'])},backgroundColor:'rgba(59,130,246,0.45)',borderColor:'#3b82f6',borderWidth:1,pointRadius:4,pointHoverRadius:7}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
    scales:{{x:{{grid:{{color:'#1e2d42'}},title:{{display:true,text:'Mileage (km)',color:'#8899b4'}},ticks:{{callback:v=>v.toLocaleString()+' km'}}}},
             y:{{grid:{{color:'#1e2d42'}},title:{{display:true,text:'Price (AED)',color:'#8899b4'}},ticks:{{callback:v=>'AED '+v.toLocaleString()}}}}}},
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.raw.label+' — '+fmtAED(ctx.raw.y)+' | '+fmtKm(ctx.raw.x)}}}}}}
  }}
}});

// ── DRILL DOWN ──
const drillData = {J(d['drill_data'])};
let drillChart = null;
const drillBtns = document.getElementById('drillBtns');
const drillBrands = Object.keys(drillData);
drillBrands.forEach((b,i) => {{
  const btn = document.createElement('button');
  btn.className = 'drill-btn' + (i===0?' active':'');
  btn.textContent = b;
  btn.onclick = () => {{
    document.querySelectorAll('.drill-btn').forEach(x=>x.classList.remove('active'));
    btn.classList.add('active');
    loadDrill(b);
  }};
  drillBtns.appendChild(btn);
}});
function loadDrill(brand) {{
  if(drillChart) drillChart.destroy();
  const d2 = drillData[brand];
  drillChart = new Chart(document.getElementById('drillChart'), {{
    type:'bar',
    data:{{labels:d2.labels,datasets:[{{label:'Listings',data:d2.counts,backgroundColor:PALETTE.slice(0,d2.labels.length),borderRadius:6,borderWidth:0}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{grid:{{color:'#1e2d42'}}}},x:{{grid:{{display:false}}}}}}}}
  }});
}}
if(drillBrands.length) loadDrill(drillBrands[0]);

// ── TOP CAR CARDS ──
function tierClass(t) {{ return {{Budget:'b-bud','Mid-Range':'b-mid',Premium:'b-pre',Luxury:'b-lux','Ultra Luxury':'b-ult'}}[t]||''; }}
function renderCarCards(arr, containerId) {{
  const grid = document.getElementById(containerId);
  grid.innerHTML = arr.map(r => `
    <div class="car-card">
      <div class="car-brand">${{r.brand}}</div>
      <div class="car-name">${{r.model}} ${{r.year!=='—'?r.year:''}}</div>
      <div class="car-price">AED ${{Number(r.price).toLocaleString()}}</div>
      <div class="car-meta">
        <span>📏 ${{r.km!=='—'?Number(r.km).toLocaleString()+' km':'—'}}</span>
        <span class="badge ${{r.cond==='New'?'b-new':'b-used'}}">${{r.cond}}</span>
      </div>
      <a class="car-link" href="${{r.link}}" target="_blank">View Listing →</a>
    </div>`).join('');
}}
renderCarCards({J(d['exp_rows'])}, 'expGrid');
renderCarCards({J(d['chp_rows'])}, 'chpGrid');

// ── DATA TABLE ──
const TABLE_DATA  = {J(d['table_data'])};
const TABLE_HEADS = {J(d['table_headers'])};
const HEAD_LABELS = {J({h: h.replace('_',' ').title() for h in d['table_headers']})};
const PAGE_SIZE = 25;
let filteredData = [...TABLE_DATA];
let currentPage  = 1;
let sortCol = -1, sortAsc = true;

// Build filter dropdowns
function colIdx(name) {{ return TABLE_HEADS.indexOf(name); }}
function uniqueVals(col) {{
  const idx = colIdx(col); if(idx<0) return [];
  return [...new Set(TABLE_DATA.map(r=>r[idx]).filter(v=>v!=null&&v!==''))].sort();
}}
[['fBrand','brand'],['fBody','body_type'],['fCond','condition'],['fFuel','fuel_type'],['fTier','market_tier'],['fSource','source']].forEach(([id,col])=>{{
  const sel = document.getElementById(id);
  uniqueVals(col).forEach(v=>{{
    const o=document.createElement('option'); o.value=v; o.textContent=v; sel.appendChild(o);
  }});
}});

function applyFilters() {{
  const s = document.getElementById('fSearch').value.toLowerCase();
  const brand = document.getElementById('fBrand').value;
  const body  = document.getElementById('fBody').value;
  const cond  = document.getElementById('fCond').value;
  const fuel  = document.getElementById('fFuel').value;
  const tier  = document.getElementById('fTier').value;
  const src   = document.getElementById('fSource').value;
  const bi=colIdx('brand'),mi=colIdx('model'),boi=colIdx('body_type'),ci=colIdx('condition'),fi=colIdx('fuel_type'),ti=colIdx('market_tier'),si=colIdx('source');
  filteredData = TABLE_DATA.filter(r => {{
    if(s && !String(r[bi]||'').toLowerCase().includes(s) && !String(r[mi]||'').toLowerCase().includes(s)) return false;
    if(brand && r[bi]!==brand) return false;
    if(body  && r[boi]!==body) return false;
    if(cond  && r[ci]!==cond)  return false;
    if(fuel  && r[fi]!==fuel)  return false;
    if(tier  && r[ti]!==tier)  return false;
    if(src   && r[si]!==src)   return false;
    return true;
  }});
  currentPage = 1;
  if(sortCol>=0) sortData();
  renderTable();
}}
function resetFilters() {{
  ['fSearch','fBrand','fBody','fCond','fFuel','fTier','fSource'].forEach(id=>{{
    const el=document.getElementById(id); if(el.tagName==='INPUT') el.value=''; else el.value='';
  }});
  filteredData=[...TABLE_DATA]; currentPage=1; sortCol=-1; renderTable();
}}
function sortData() {{
  filteredData.sort((a,b)=>{{
    let va=a[sortCol],vb=b[sortCol];
    if(va==null) return 1; if(vb==null) return -1;
    va = isNaN(va)?String(va):Number(va);
    vb = isNaN(vb)?String(vb):Number(vb);
    return (va<vb?-1:va>vb?1:0)*(sortAsc?1:-1);
  }});
}}

function badgeCell(val, col) {{
  if(col==='condition') return `<span class="badge ${{val==='New'?'b-new':'b-used'}}">${{val}}</span>`;
  if(col==='specs_origin') return `<span class="badge ${{val==='GCC'?'b-gcc':'b-imp'}}">${{val}}</span>`;
  if(col==='market_tier') return `<span class="badge ${{tierClass(val)}}">${{val}}</span>`;
  if(col==='price_aed') return val!=null?'AED '+Number(val).toLocaleString():'—';
  if(col==='mileage_km') return val!=null?Number(val).toLocaleString()+' km':'—';
  return val!=null?val:'—';
}}

function renderTable() {{
  // Header
  const head = document.getElementById('tableHead');
  head.innerHTML = '<tr>'+TABLE_HEADS.map((h,i)=>
    `<th onclick="sortBy(${{i}})">${{HEAD_LABELS[h]||h}} <span class="sort-icon">${{sortCol===i?(sortAsc?'▲':'▼'):'⇅'}}</span></th>`
  ).join('')+'</tr>';
  // Body
  const start = (currentPage-1)*PAGE_SIZE;
  const page  = filteredData.slice(start, start+PAGE_SIZE);
  const body  = document.getElementById('tableBody');
  body.innerHTML = page.map(row=>
    '<tr>'+TABLE_HEADS.map((h,i)=>`<td title="${{row[i]??''}}">${{badgeCell(row[i], h)}}</td>`).join('')+'</tr>'
  ).join('');
  // Count
  document.getElementById('filterCount').textContent = `Showing ${{Math.min(filteredData.length, PAGE_SIZE*(currentPage))}} of ${{filteredData.length}} results`;
  // Pager
  const pages = Math.ceil(filteredData.length/PAGE_SIZE);
  const pager = document.getElementById('pager');
  let btns='';
  btns+=`<button onclick="goPage(1)" ${{currentPage===1?'disabled':''}}>«</button>`;
  btns+=`<button onclick="goPage(${{currentPage-1}})" ${{currentPage===1?'disabled':''}}>‹</button>`;
  const lo=Math.max(1,currentPage-2), hi=Math.min(pages,currentPage+2);
  for(let p=lo;p<=hi;p++) btns+=`<button class="${{p===currentPage?'active':''}}" onclick="goPage(${{p}})">${{p}}</button>`;
  btns+=`<button onclick="goPage(${{currentPage+1}})" ${{currentPage===pages?'disabled':''}}>›</button>`;
  btns+=`<button onclick="goPage(${{pages}})" ${{currentPage===pages?'disabled':''}}>»</button>`;
  btns+=`<span class="pg-info">Page ${{currentPage}} / ${{pages}}</span>`;
  pager.innerHTML=btns;
}}
function sortBy(i) {{ sortCol=i; sortAsc=(sortCol===i)?!sortAsc:true; sortData(); renderTable(); }}
function goPage(p) {{
  const pages=Math.ceil(filteredData.length/PAGE_SIZE);
  currentPage=Math.max(1,Math.min(p,pages)); renderTable();
}}
renderTable();

// ── NAV SCROLL ──
function scrollTo(id) {{
  document.getElementById(id).scrollIntoView({{behavior:'smooth'}});
  document.querySelectorAll('.nav-link').forEach(l=>l.classList.remove('active'));
  event.target.classList.add('active');
}}
window.addEventListener('scroll',()=>{{
  const sections=['overview','brands','prices','market','depreciation','toplists','explorer'];
  sections.forEach((id,i)=>{{
    const el=document.getElementById(id);
    if(!el) return;
    const top=el.getBoundingClientRect().top;
    if(top<=100) document.querySelectorAll('.nav-link')[i]?.classList.add('active');
    else document.querySelectorAll('.nav-link')[i]?.classList.remove('active');
  }});
}});
</script>
</body>
</html>"""


if __name__ == "__main__":
    generate_dashboard()
