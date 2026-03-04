import json
import re
import pandas as pd
from urllib.parse import urlparse

# ============================================================
# Brand & Model Reference Data
# ============================================================

BRANDS = {
    'toyota': 'Toyota', 'lexus': 'Lexus', 'nissan': 'Nissan', 'infiniti': 'Infiniti',
    'honda': 'Honda', 'hyundai': 'Hyundai', 'kia': 'Kia', 'genesis': 'Genesis',
    'mercedes-benz': 'Mercedes-Benz', 'mercedes': 'Mercedes-Benz', 'bmw': 'BMW',
    'audi': 'Audi', 'volkswagen': 'Volkswagen', 'porsche': 'Porsche',
    'land-rover': 'Land Rover', 'land rover': 'Land Rover', 'jaguar': 'Jaguar',
    'rolls-royce': 'Rolls-Royce', 'rolls royce': 'Rolls-Royce', 'bentley': 'Bentley',
    'ferrari': 'Ferrari', 'lamborghini': 'Lamborghini', 'maserati': 'Maserati',
    'aston-martin': 'Aston Martin', 'aston martin': 'Aston Martin',
    'mclaren': 'McLaren', 'bugatti': 'Bugatti', 'koenigsegg': 'Koenigsegg',
    'ford': 'Ford', 'chevrolet': 'Chevrolet', 'cadillac': 'Cadillac',
    'gmc': 'GMC', 'jeep': 'Jeep', 'dodge': 'Dodge', 'chrysler': 'Chrysler',
    'lincoln': 'Lincoln', 'ram': 'RAM',
    'volvo': 'Volvo', 'peugeot': 'Peugeot', 'renault': 'Renault',
    'fiat': 'Fiat', 'alfa-romeo': 'Alfa Romeo', 'mini': 'Mini',
    'mazda': 'Mazda', 'subaru': 'Subaru', 'mitsubishi': 'Mitsubishi',
    'suzuki': 'Suzuki', 'isuzu': 'Isuzu', 'daihatsu': 'Daihatsu',
    'byd': 'BYD', 'chery': 'Chery', 'gac': 'GAC', 'geely': 'Geely',
    'haval': 'Haval', 'mg': 'MG', 'changan': 'Changan', 'rox': 'ROX',
    'yangwang': 'Yangwang', 'brabus': 'Brabus', 'jetour': 'Jetour',
    'tank': 'Tank', 'gwm': 'GWM', 'ora': 'ORA', 'exeed': 'EXEED',
    'tesla': 'Tesla', 'rivian': 'Rivian', 'lucid': 'Lucid',
    'polestar': 'Polestar', 'nio': 'NIO',
}

# Luxury tier thresholds (AED)
LUXURY_TIERS = [
    (0,      50_000,  'Budget'),
    (50_000, 100_000, 'Mid-Range'),
    (100_000, 200_000, 'Premium'),
    (200_000, 500_000, 'Luxury'),
    (500_000, float('inf'), 'Ultra Luxury'),
]

# Model → body type mapping (common UAE market models)
BODY_TYPES = {
    # SUVs
    'land cruiser': 'SUV', 'prado': 'SUV', 'fortuner': 'SUV', 'rav4': 'SUV',
    'highlander': 'SUV', 'sequoia': 'SUV', '4runner': 'SUV', 'frontlander': 'SUV',
    'patrol': 'SUV', 'pathfinder': 'SUV', 'x-trail': 'SUV', 'xtrail': 'SUV',
    'kicks': 'SUV', 'x5': 'SUV', 'x3': 'SUV', 'x4': 'SUV', 'x6': 'SUV', 'x7': 'SUV',
    'ix3': 'SUV', 'ix5': 'SUV', 'ixm': 'SUV',
    'q5': 'SUV', 'q7': 'SUV', 'q8': 'SUV', 'q3': 'SUV',
    'gle': 'SUV', 'glc': 'SUV', 'gls': 'SUV', 'gla': 'SUV', 'glb': 'SUV',
    'g-class': 'SUV', 'g class': 'SUV', 'g63': 'SUV', 'g500': 'SUV',
    'g700': 'SUV', 'g800': 'SUV',
    'range rover': 'SUV', 'velar': 'SUV', 'discovery': 'SUV', 'defender': 'SUV',
    'evoque': 'SUV', 'sport': 'SUV',
    'cullinan': 'SUV', 'bentayga': 'SUV', 'urus': 'SUV', 'dbx': 'SUV',
    'cayenne': 'SUV', 'macan': 'SUV',
    'wrangler': 'SUV', 'grand cherokee': 'SUV', 'cherokee': 'SUV',
    'escalade': 'SUV', 'tahoe': 'SUV', 'suburban': 'SUV', 'yukon': 'SUV',
    'explorer': 'SUV', 'expedition': 'SUV', 'bronco': 'SUV',
    'teramont': 'SUV', 'tiguan': 'SUV', 'touareg': 'SUV',
    'tucson': 'SUV', 'santa fe': 'SUV', 'palisade': 'SUV', 'creta': 'SUV',
    'sportage': 'SUV', 'sorento': 'SUV', 'seltos': 'SUV', 'telluride': 'SUV',
    'outlander': 'SUV', 'pajero': 'SUV', 'montero': 'SUV',
    'jimny': 'SUV', 'vitara': 'SUV',
    'song plus': 'SUV', 'song l': 'SUV', 'leopard': 'SUV', 'xia': 'SUV',
    'tiggo': 'SUV', 'emzoom': 'SUV', 'u8': 'SUV',
    'f-pace': 'SUV', 'e-pace': 'SUV',
    'xc90': 'SUV', 'xc60': 'SUV', 'xc40': 'SUV',
    'ecosport': 'SUV', 'countryman': 'SUV', 'dx9': 'SUV',
    'model x': 'SUV', 'model y': 'SUV',
    # Sedans
    'camry': 'Sedan', 'corolla': 'Sedan', 'avalon': 'Sedan', 'yaris': 'Sedan',
    'altima': 'Sedan', 'maxima': 'Sedan', 'sentra': 'Sedan', 'sunny': 'Sedan',
    'civic': 'Sedan', 'accord': 'Sedan',
    'elantra': 'Sedan', 'sonata': 'Sedan', 'azera': 'Sedan', 'veloster': 'Sedan',
    'cerato': 'Sedan', 'optima': 'Sedan', 'k5': 'Sedan', 'rio': 'Sedan',
    'g80': 'Sedan', 'g70': 'Sedan', 'g90': 'Sedan',
    '3 series': 'Sedan', '5 series': 'Sedan', '7 series': 'Sedan',
    'a3': 'Sedan', 'a4': 'Sedan', 'a5': 'Sedan', 'a6': 'Sedan', 'a7': 'Sedan', 'a8': 'Sedan',
    'rs7': 'Sedan', 'rs6': 'Sedan', 'rs3': 'Sedan',
    's-class': 'Sedan', 'e-class': 'Sedan', 'c-class': 'Sedan', 'a-class': 'Sedan',
    'eqs': 'Sedan', 'cle': 'Sedan',
    'ghost': 'Sedan', 'phantom': 'Sedan', 'flying spur': 'Sedan',
    'continental': 'Coupe',
    'panamera': 'Sedan', 'taycan': 'Sedan',
    'charger': 'Sedan', 'fusion': 'Sedan',
    'passat': 'Sedan', 'jetta': 'Sedan',
    'mazda 6': 'Sedan', 'mazda 3': 'Sedan',
    'attrage': 'Sedan', 'lancer': 'Sedan',
    'mg5': 'Sedan', 'arrizo': 'Sedan',
    'han': 'Sedan', 'seal': 'Sedan',
    'model 3': 'Sedan', 'model s': 'Sedan',
    '2008': 'SUV', '5008': 'SUV', '3008': 'SUV',
    # Coupes/Sports
    '911': 'Coupe', 'carrera': 'Coupe', 'gt3': 'Coupe', 'boxster': 'Convertible',
    'm4': 'Coupe', 'm3': 'Sedan', 'm2': 'Coupe', 'm8': 'Coupe',
    'gle-coupe': 'Coupe', 'gle coupe': 'Coupe', 'cle coupe': 'Coupe',
    'mustang': 'Coupe', 'challenger': 'Coupe',
    'wraith': 'Coupe', 'dawn': 'Convertible',
    'huracan': 'Coupe', 'aventador': 'Coupe', 'evo': 'Coupe',
    '488': 'Coupe', 'f8': 'Coupe', 'sf90': 'Coupe', 'roma': 'Coupe',
    '500': 'Hatchback',
    # Pickups
    'hilux': 'Pickup', 'tundra': 'Pickup', 'tacoma': 'Pickup',
    'f-150': 'Pickup', 'f-250': 'Pickup', 'f-350': 'Pickup', 'f-550': 'Pickup',
    'ranger': 'Pickup', 'l200': 'Pickup', 'navara': 'Pickup', 'dmax': 'Pickup',
    'silverado': 'Pickup', 'sierra': 'Pickup', 'colorado': 'Pickup',
    'bongo': 'Pickup', 'k2700': 'Pickup', 'k4000': 'Pickup',
    'cybertruck': 'Pickup',
    # Vans/Buses
    'hiace': 'Van', 'coaster': 'Bus', 'rosa': 'Bus', 'vito': 'Van', 'savana': 'Van',
    'carnival': 'Van', 'starex': 'Van', 'urvan': 'Van',
}

# Common color keywords
COLOR_KEYWORDS = {
    'white': 'White', 'pearl white': 'White', 'solid white': 'White',
    'black': 'Black', 'carbon black': 'Black', 'obsidian black': 'Black',
    'silver': 'Silver', 'metallic silver': 'Silver', 'nardo grey': 'Grey',
    'grey': 'Grey', 'gray': 'Grey', 'graphite': 'Grey',
    'red': 'Red', 'burgundy': 'Red', 'maroon': 'Red', 'crimson': 'Red',
    'blue': 'Blue', 'navy': 'Blue', 'cobalt': 'Blue', 'midnight blue': 'Blue',
    'green': 'Green', 'racing green': 'Green', 'olive': 'Green',
    'gold': 'Gold', 'golden': 'Gold', 'champagne': 'Gold',
    'beige': 'Beige', 'cream': 'Beige', 'ivory': 'Beige',
    'orange': 'Orange', 'amber': 'Orange',
    'brown': 'Brown', 'bronze': 'Brown', 'copper': 'Brown',
    'yellow': 'Yellow',
}

# ============================================================
# Cleaning Utilities
# ============================================================

def clean_price(price_str):
    """Extract numeric price from string like 'AED 245,000' or '469,000'."""
    if not isinstance(price_str, str):
        return None
    digits = re.sub(r'[^\d]', '', price_str)
    val = int(digits) if digits else None
    # Sanity check: filter out nonsense prices
    if val is not None and (val < 1000 or val > 50_000_000):
        return None
    return val


def clean_mileage(km_str):
    """Extract numeric mileage from string like '61,240 km'."""
    if not isinstance(km_str, str):
        return None
    digits = re.sub(r'[^\d]', '', km_str)
    val = int(digits) if digits else None
    if val is not None and val > 2_000_000:
        return None
    return val


def clean_year(year_str):
    """Extract 4-digit year from string like '2020' or 'New Toyota Tundra 2025'."""
    if isinstance(year_str, float):
        if year_str != year_str:  # NaN check
            return None
        y = int(year_str)
        return y if 1980 <= y <= 2030 else None
    if isinstance(year_str, int):
        return year_str if 1980 <= year_str <= 2030 else None
    if not isinstance(year_str, str):
        return None
    match = re.search(r'(19|20)\d{2}', year_str)
    return int(match.group(0)) if match else None


# ============================================================
# Brand & Model Extraction
# ============================================================

def extract_brand_from_url(url):
    """Extract brand from URL path segments.
    
    Dubizzle: /motors/used-cars/toyota/land-cruiser/...
    Dubicars: /2025-toyota-land-cruiser-...
    """
    if not isinstance(url, str):
        return None, None

    # Dubizzle pattern: /motors/used-cars/{brand}/{model}/
    dubizzle_match = re.search(r'/motors/used-cars/([^/]+)/([^/]+)/', url)
    if dubizzle_match:
        brand_slug = dubizzle_match.group(1)
        model_slug = dubizzle_match.group(2)
        brand = BRANDS.get(brand_slug, brand_slug.replace('-', ' ').title())
        model = model_slug.replace('-', ' ').title()
        return brand, model

    # Dubicars pattern: /YYYY-brand-model-...
    dubicars_match = re.search(r'dubicars\.com/\d{4}-([a-z0-9-]+?)(?:-\d)', url)
    if dubicars_match:
        slug = dubicars_match.group(1)
        # Try to match known brands from the beginning of the slug
        for brand_key in sorted(BRANDS.keys(), key=len, reverse=True):
            normalized = brand_key.replace(' ', '-')
            if slug.startswith(normalized + '-') or slug == normalized:
                brand = BRANDS[brand_key]
                model_part = slug[len(normalized)+1:] if slug.startswith(normalized + '-') else ''
                model = model_part.replace('-', ' ').title() if model_part else None
                return brand, model
    
    return None, None


def extract_brand_from_title(title):
    """Fallback: try to find brand name in the title string."""
    if not isinstance(title, str):
        return None
    title_lower = title.lower()
    for key, brand_name in sorted(BRANDS.items(), key=lambda x: len(x[0]), reverse=True):
        if key in title_lower:
            return brand_name
    return None


# ============================================================
# Feature Detection
# ============================================================

def detect_fuel_type(title, url):
    """Detect fuel type from title and URL keywords."""
    combined = f"{title or ''} {url or ''}".lower()
    
    if any(kw in combined for kw in ['electric', ' ev ', ' ev-', '-ev ', 'bev', 'battery electric', 'zero emission']):
        return 'Electric'
    if any(kw in combined for kw in ['plug-in', 'plugin', 'phev']):
        return 'Plug-in Hybrid'
    if any(kw in combined for kw in ['hybrid', 'hev', 'dm-i', 'dm i', 'i-force max', 'self-charging']):
        return 'Hybrid'
    if any(kw in combined for kw in ['diesel', 'deisel', 'cdi', 'tdi', 'crdi', 'd4d']):
        return 'Diesel'
    if any(kw in combined for kw in ['petrol', 'gasoline', 'benzin', 'tfsi', 'turbo',
                                      'v8', 'v6', 'v4', 'v12', 'gdi', 'tsi',
                                      'ecoboost', 'skyactiv', 'supercharged']):
        return 'Petrol'
    return None


def detect_body_type(model, title, url):
    """Detect vehicle body type from model name and contextual clues."""
    combined = f"{model or ''} {title or ''} {url or ''}".lower()
    
    for keyword, body in sorted(BODY_TYPES.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in combined:
            return body
    
    # Generic fallbacks
    if any(kw in combined for kw in ['convertible', 'cabriolet', 'spider', 'roadster']):
        return 'Convertible'
    if any(kw in combined for kw in ['coupe', 'coupé']):
        return 'Coupe'
    if any(kw in combined for kw in ['sedan', 'saloon']):
        return 'Sedan'
    if any(kw in combined for kw in ['suv', 'crossover', '4wd', '4x4', 'awd']):
        return 'SUV'
    if any(kw in combined for kw in ['pickup', 'pick-up', 'truck', 'cabin']):
        return 'Pickup'
    if any(kw in combined for kw in ['van', 'bus', 'minibus', 'commuter']):
        return 'Van'
    if any(kw in combined for kw in ['hatchback', 'hatch']):
        return 'Hatchback'
    
    return None


def detect_specs_origin(title):
    """Detect if the car is GCC spec or imported."""
    if not isinstance(title, str):
        return None
    title_upper = title.upper()
    if 'GCC' in title_upper:
        return 'GCC'
    if any(kw in title_upper for kw in ['USA', 'US SPEC', 'AMERICAN', 'USA SPEC', 'JAPAN', 'JAPANESE', 'KOREAN', 'CHINA', 'CHINESE', 'EUROPEAN', 'EURO SPEC']):
        return 'Import'
    return None


def detect_condition(title, mileage_km, year_raw):
    """Detect if the car is new or used."""
    combined = f"{title or ''} {year_raw or ''}".upper()
    if any(kw in combined for kw in ['BRAND NEW', 'NEW CAR', '0KM', '0 KM', 'ZERO KM']):
        return 'New'
    if mileage_km is not None and mileage_km <= 100:
        return 'New'
    if mileage_km is not None and mileage_km > 500:
        return 'Used'
    if 'USED' in combined:
        return 'Used'
    return None


def detect_transmission(title):
    """Detect transmission type from title."""
    if not isinstance(title, str):
        return None
    t = title.upper()
    if any(kw in t for kw in ['MANUAL', 'MT ', ' MT', '6-SPEED MANUAL', '5-SPEED MANUAL']):
        return 'Manual'
    if any(kw in t for kw in ['AUTOMATIC', 'AUTO ', 'AT ', ' AT', 'CVT', 'TIPTRONIC', 'PDK', 'DCT', 'DSG']):
        return 'Automatic'
    return None


def detect_color(title):
    """Detect vehicle color from listing title."""
    if not isinstance(title, str):
        return None
    title_lower = title.lower()
    # Try multi-word colors first (longer keys first)
    for kw, color in sorted(COLOR_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if kw in title_lower:
            return color
    return None


def classify_tier(price_aed):
    """Classify vehicle into market tier based on price."""
    if price_aed is None or pd.isna(price_aed):
        return None
    for lo, hi, tier in LUXURY_TIERS:
        if lo <= price_aed < hi:
            return tier
    return 'Ultra Luxury'


def data_quality_score(row):
    """Calculate data completeness percentage (0-100)."""
    fields = ['title', 'brand', 'model', 'year', 'price_aed', 'mileage_km', 'location', 'link']
    filled = sum(1 for f in fields if pd.notna(row.get(f)) and row.get(f) not in [None, '', 0])
    return round(filled / len(fields) * 100)


# ============================================================
# Source-specific Fixups
# ============================================================

def fix_dubicars_data(row):
    """Fix Dubicars-specific issues: title is 'Premium', real name is in year field."""
    title = row.get('title', '')
    year_raw = row.get('year', '')
    
    if title == 'Premium' and isinstance(year_raw, str):
        # year field contains e.g. "New Toyota Tundra 2025" or "Used Nissan XTrail 2022"
        real_title = re.sub(r'^(New|Used)\s+', '', year_raw).strip()
        # Remove trailing year
        real_title = re.sub(r'\s+\d{4}$', '', real_title).strip()
        row['title'] = real_title if real_title else year_raw
    
    return row


# ============================================================
# Main Processing Pipeline
# ============================================================

def process_file(filename, source_name):
    """Load and process a single JSON data file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        if df.empty:
            print(f"  ⚠ {filename} is empty.")
            return df
            
        print(f"  ✓ Loaded {len(df)} records from {filename}")
        return df
    except FileNotFoundError:
        print(f"  ✗ File not found: {filename}")
        return pd.DataFrame()
    except Exception as e:
        print(f"  ✗ Error processing {filename}: {e}")
        return pd.DataFrame()


def enrich_dataframe(df):
    """Apply all enrichment steps to the combined dataframe."""
    
    # ---- Step 1: Fix Dubicars data ----
    dubicars_mask = df['source'] == 'Dubicars'
    if dubicars_mask.any():
        print("  → Fixing Dubicars title extraction...")
        for idx in df[dubicars_mask].index:
            row = df.loc[idx].to_dict()
            fixed = fix_dubicars_data(row)
            df.at[idx, 'title'] = fixed['title']
    
    # ---- Step 2: Clean numeric fields ----
    print("  → Cleaning price, mileage, year...")
    df['price_aed'] = df['price'].apply(clean_price)
    df['mileage_km'] = df['mileage'].apply(clean_mileage)
    df['year_clean'] = df['year'].apply(clean_year)
    
    # ---- Step 3: Extract brand & model from URL ----
    print("  → Extracting brand & model from URLs...")
    url_data = df['link'].apply(lambda u: pd.Series(extract_brand_from_url(u), index=['brand', 'model']))
    df['brand'] = url_data['brand']
    df['model'] = url_data['model']
    
    # Fallback: extract brand from title if URL extraction failed
    no_brand = df['brand'].isna()
    if no_brand.any():
        df.loc[no_brand, 'brand'] = df.loc[no_brand, 'title'].apply(extract_brand_from_title)
    
    # ---- Step 4: Feature Detection ----
    print("  → Detecting fuel type, body type, specs, condition...")
    df['fuel_type'] = df.apply(lambda r: detect_fuel_type(r.get('title'), r.get('link')), axis=1)
    df['body_type'] = df.apply(lambda r: detect_body_type(r.get('model'), r.get('title'), r.get('link')), axis=1)
    df['specs_origin'] = df['title'].apply(detect_specs_origin)
    df['condition'] = df.apply(lambda r: detect_condition(r.get('title'), r.get('mileage_km'), r.get('year')), axis=1)
    
    # ---- Step 5: New enrichments ----
    print("  → Detecting transmission, color, market tier...")
    df['transmission'] = df['title'].apply(detect_transmission)
    df['color'] = df['title'].apply(detect_color)
    df['year'] = df['year_clean']
    df['market_tier'] = df['price_aed'].apply(classify_tier)

    # Improve condition using year for listings with no mileage data
    current_year = 2026
    no_cond = df['condition'].isna()
    new_enough = df['year'] >= (current_year - 1)
    df.loc[no_cond & new_enough & df['mileage_km'].isna(), 'condition'] = 'New'
    
    # ---- Step 6: Deduplication ----
    before = len(df)
    df = df.drop_duplicates(subset=['link'], keep='first')
    dupes = before - len(df)
    if dupes:
        print(f"  → Removed {dupes} duplicate listings")
    
    # ---- Step 7: Data quality score ----
    df['data_quality'] = df.apply(data_quality_score, axis=1)
    
    # ---- Step 8: Drop raw/temp columns ----
    df.drop(columns=['price', 'mileage', 'year_clean'], inplace=True, errors='ignore')
    
    return df


def main():
    print("=" * 60)
    print("  UAE Car Market Data — Processing Pipeline")
    print("=" * 60)
    
    # Load raw data
    print("\n📂 Loading raw data...")
    df_dubizzle = process_file('dubizzle_cars.json', 'Dubizzle')
    df_dubicars = process_file('dubicars_cars.json', 'Dubicars')
    
    # Combine
    combined = pd.concat([df_dubizzle, df_dubicars], ignore_index=True)
    print(f"\n📊 Combined: {len(combined)} total listings")
    
    if combined.empty:
        print("❌ No data to process.")
        return
    
    # Enrich
    print("\n🔧 Enriching data...")
    enriched = enrich_dataframe(combined)
    
    # Reorder columns
    col_order = [
        'source', 'brand', 'model', 'title', 'year', 'price_aed', 'mileage_km',
        'condition', 'fuel_type', 'body_type', 'transmission', 'color',
        'specs_origin', 'market_tier', 'location', 'data_quality', 'link'
    ]
    col_order = [c for c in col_order if c in enriched.columns]
    enriched = enriched[col_order]
    
    # Save
    output = "uae_cars_market_data.csv"
    enriched.to_csv(output, index=False, encoding='utf-8')
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"  ✅ Saved {len(enriched)} records to {output}")
    print(f"{'=' * 60}")
    print(f"\n📈 Dataset Summary:")
    print(f"  Sources:        {enriched['source'].value_counts().to_dict()}")
    print(f"  Brands found:   {enriched['brand'].notna().sum()} / {len(enriched)}")
    print(f"  Models found:   {enriched['model'].notna().sum()} / {len(enriched)}")
    print(f"  With price:     {enriched['price_aed'].notna().sum()} / {len(enriched)}")
    print(f"  With mileage:   {enriched['mileage_km'].notna().sum()} / {len(enriched)}")
    print(f"  Avg quality:    {enriched['data_quality'].mean():.0f}%")
    
    if enriched['brand'].notna().any():
        print(f"\n🏷️  Top 10 Brands:")
        for brand, count in enriched['brand'].value_counts().head(10).items():
            avg_price = enriched.loc[enriched['brand'] == brand, 'price_aed'].mean()
            price_str = f"AED {avg_price:,.0f}" if pd.notna(avg_price) else "N/A"
            print(f"    {brand:20s}  {count:3d} listings  |  Avg: {price_str}")
    
    print(f"\n📋 Sample Data:")
    print(enriched[['brand', 'model', 'year', 'price_aed', 'condition', 'body_type', 'market_tier']].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
