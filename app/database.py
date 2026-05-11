# app/database.py
"""
SQLite database layer for fast car search queries.
Loads processed CSV data into an indexed SQLite DB for instant search.
"""

import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger("database")

DB_PATH = "data/cars.db"
CSV_PATH = "data/processed/listings.csv"


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    try:
        yield conn
    finally:
        conn.close()


def init_database(csv_path=None):
    """
    Initialize SQLite database from processed CSV.
    Creates indexes for fast search performance.
    """
    csv_path = csv_path or CSV_PATH

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No processed data at {csv_path}. Run the pipeline first.")

    logger.info(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Clean column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Ensure required columns exist
    required = ["brand", "model", "year", "price"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Add search-optimized columns
    df["title_search"] = (
        df["brand"].fillna("") + " " +
        df["model"].fillna("") + " " +
        df["year"].fillna("").astype(str)
    ).str.lower().str.strip()

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")

    # Drop rows without price
    df = df[df["price"].notna()]

    # Add unique ID
    df = df.reset_index(drop=True)
    df["id"] = range(1, len(df) + 1)

    # Write to SQLite
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_db() as conn:
        # Drop old table
        conn.execute("DROP TABLE IF EXISTS listings")
        conn.execute("DROP TABLE IF EXISTS metadata")

        # Write listings
        df.to_sql("listings", conn, index=False, if_exists="replace")

        # Create indexes for fast queries
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_brand ON listings(brand)",
            "CREATE INDEX IF NOT EXISTS idx_model ON listings(model)",
            "CREATE INDEX IF NOT EXISTS idx_year ON listings(year)",
            "CREATE INDEX IF NOT EXISTS idx_price ON listings(price)",
            "CREATE INDEX IF NOT EXISTS idx_body_type ON listings(body_type)",
            "CREATE INDEX IF NOT EXISTS idx_fuel_type ON listings(fuel_type)",
            "CREATE INDEX IF NOT EXISTS idx_source ON listings(source)",
            "CREATE INDEX IF NOT EXISTS idx_brand_model ON listings(brand, model)",
            "CREATE INDEX IF NOT EXISTS idx_brand_price ON listings(brand, price)",
            "CREATE INDEX IF NOT EXISTS idx_title_search ON listings(title_search)",
        ]
        for idx_sql in indexes:
            conn.execute(idx_sql)

        # Store metadata
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)",
                      ("last_updated", datetime.now().isoformat()))
        conn.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)",
                      ("total_listings", str(len(df))))

        conn.commit()

    logger.info(f"Database initialized: {len(df)} listings with indexes")
    return len(df)


def get_filter_options():
    """Get all unique values for filter dropdowns."""
    with get_db() as conn:
        options = {}

        # Brands with count
        rows = conn.execute("""
            SELECT brand, COUNT(*) as cnt
            FROM listings
            WHERE brand IS NOT NULL AND brand != 'Unknown' AND brand != ''
            GROUP BY brand
            ORDER BY cnt DESC
        """).fetchall()
        options["brands"] = [{"name": r["brand"], "count": r["cnt"]} for r in rows]

        # Models per brand
        rows = conn.execute("""
            SELECT brand, model, COUNT(*) as cnt
            FROM listings
            WHERE model IS NOT NULL AND model != 'Unknown' AND model != ''
            GROUP BY brand, model
            ORDER BY brand, cnt DESC
        """).fetchall()
        brand_models = {}
        for r in rows:
            brand_models.setdefault(r["brand"], []).append({
                "name": r["model"], "count": r["cnt"]
            })
        options["models_by_brand"] = brand_models

        # Body types
        rows = conn.execute("""
            SELECT body_type, COUNT(*) as cnt
            FROM listings
            WHERE body_type IS NOT NULL AND body_type != 'Unknown'
            GROUP BY body_type ORDER BY cnt DESC
        """).fetchall()
        options["body_types"] = [{"name": r["body_type"], "count": r["cnt"]} for r in rows]

        # Fuel types
        rows = conn.execute("""
            SELECT fuel_type, COUNT(*) as cnt
            FROM listings
            WHERE fuel_type IS NOT NULL AND fuel_type != 'Unknown'
            GROUP BY fuel_type ORDER BY cnt DESC
        """).fetchall()
        options["fuel_types"] = [{"name": r["fuel_type"], "count": r["cnt"]} for r in rows]

        # Year range
        row = conn.execute("""
            SELECT MIN(year) as min_year, MAX(year) as max_year,
                   MIN(price) as min_price, MAX(price) as max_price
            FROM listings
            WHERE year IS NOT NULL AND price IS NOT NULL
        """).fetchone()
        options["year_range"] = {"min": int(row["min_year"] or 1990), "max": int(row["max_year"] or 2025)}
        options["price_range"] = {"min": int(row["min_price"] or 0), "max": int(row["max_price"] or 10000000)}

        # Sources
        rows = conn.execute("""
            SELECT source, COUNT(*) as cnt FROM listings
            WHERE source IS NOT NULL GROUP BY source
        """).fetchall()
        options["sources"] = [{"name": r["source"], "count": r["cnt"]} for r in rows]

        # Metadata
        row = conn.execute("SELECT value FROM metadata WHERE key='last_updated'").fetchone()
        options["last_updated"] = row["value"] if row else None

        row = conn.execute("SELECT value FROM metadata WHERE key='total_listings'").fetchone()
        options["total_listings"] = int(row["value"]) if row else 0

    return options
