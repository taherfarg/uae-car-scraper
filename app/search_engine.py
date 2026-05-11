# app/search_engine.py
"""
Advanced search engine with full-text search, faceted filtering,
price comparison, and market intelligence.
"""

import time
import logging
from typing import Optional, List
from app.database import get_db
from app.models import SearchRequest, SortField

logger = logging.getLogger("search_engine")


class CarSearchEngine:
    SORT_MAP = {
        SortField.PRICE_ASC: "price ASC",
        SortField.PRICE_DESC: "price DESC",
        SortField.YEAR_DESC: "year DESC NULLS LAST",
        SortField.YEAR_ASC: "year ASC NULLS LAST",
        SortField.MILEAGE_ASC: "mileage ASC NULLS LAST",
        SortField.MILEAGE_DESC: "mileage DESC NULLS LAST",
        SortField.QUALITY_DESC: "quality_score DESC NULLS LAST",
    }

    def search(self, req: SearchRequest) -> dict:
        start = time.time()
        conditions, params = [], []

        if req.query:
            for word in req.query.lower().strip().split():
                conditions.append("title_search LIKE ?")
                params.append(f"%{word}%")

        filter_map = {
            "brand": req.brand, "model": req.model, "body_type": req.body_type,
            "fuel_type": req.fuel_type, "transmission": req.transmission,
            "source": req.source, "specs_origin": req.specs_origin,
        }
        for col, val in filter_map.items():
            if val:
                conditions.append(f"{col} = ?"); params.append(val)

        range_map = [
            ("year", ">=", req.min_year), ("year", "<=", req.max_year),
            ("price", ">=", req.min_price), ("price", "<=", req.max_price),
            ("mileage", ">=", req.min_mileage), ("mileage", "<=", req.max_mileage),
        ]
        for col, op, val in range_map:
            if val is not None:
                conditions.append(f"{col} {op} ?"); params.append(val)

        where = " AND ".join(conditions) if conditions else "1=1"
        sort = self.SORT_MAP.get(req.sort_by, "price ASC")
        offset = (req.page - 1) * req.per_page

        with get_db() as conn:
            total = conn.execute(f"SELECT COUNT(*) as total FROM listings WHERE {where}", params).fetchone()["total"]

            stats_sql = f"""SELECT COUNT(*) as count, MIN(price) as min_price, MAX(price) as max_price,
                AVG(price) as avg_price,
                (SELECT price FROM listings WHERE {where} ORDER BY price
                 LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM listings WHERE {where})) as median_price
                FROM listings WHERE {where}"""
            sr = conn.execute(stats_sql, params + params + params).fetchone()
            price_stats = {k: round(sr[k] or 0, 0) for k in ["count","min_price","max_price","avg_price","median_price"]}

            rows = conn.execute(
                f"SELECT * FROM listings WHERE {where} ORDER BY {sort} LIMIT ? OFFSET ?",
                params + [req.per_page, offset]
            ).fetchall()
            listings = [dict(r) for r in rows]

        return {
            "listings": listings, "total": total, "page": req.page,
            "per_page": req.per_page, "total_pages": max(1, -(-total // req.per_page)),
            "query_time_ms": round((time.time() - start) * 1000, 2), "price_stats": price_stats,
        }

    def autocomplete(self, query: str, limit: int = 10) -> List[dict]:
        q = query.lower().strip()
        if not q: return []
        with get_db() as conn:
            brands = conn.execute(
                "SELECT brand, COUNT(*) as cnt FROM listings WHERE LOWER(brand) LIKE ? AND brand != 'Unknown' GROUP BY brand ORDER BY cnt DESC LIMIT ?",
                (f"%{q}%", limit)
            ).fetchall()
            models = conn.execute(
                "SELECT brand, model, COUNT(*) as cnt, MIN(price) as min_price FROM listings WHERE (LOWER(model) LIKE ? OR LOWER(brand)||' '||LOWER(model) LIKE ?) AND model != 'Unknown' GROUP BY brand, model ORDER BY cnt DESC LIMIT ?",
                (f"%{q}%", f"%{q}%", limit)
            ).fetchall()

        suggestions = []
        for r in brands:
            suggestions.append({"type":"brand","text":r["brand"],"label":f"{r['brand']} ({r['cnt']} listings)","brand":r["brand"],"count":r["cnt"]})
        for r in models:
            suggestions.append({"type":"model","text":f"{r['brand']} {r['model']}","label":f"{r['brand']} {r['model']} ({r['cnt']}, from AED {int(r['min_price']):,})","brand":r["brand"],"model":r["model"],"count":r["cnt"],"min_price":r["min_price"]})

        seen, unique = set(), []
        for s in suggestions:
            if s["text"] not in seen: seen.add(s["text"]); unique.append(s)
        return unique[:limit]

    def compare_prices(self, brand: str, model: str, min_year: Optional[int] = None, max_year: Optional[int] = None) -> dict:
        conds, params = ["brand = ?", "model = ?"], [brand, model]
        if min_year: conds.append("year >= ?"); params.append(min_year)
        if max_year: conds.append("year <= ?"); params.append(max_year)
        where = " AND ".join(conds)

        with get_db() as conn:
            ov = conn.execute(f"SELECT COUNT(*) as cnt, AVG(price) as avg, MIN(price) as mn, MAX(price) as mx, MIN(year) as min_yr, MAX(year) as max_yr FROM listings WHERE {where}", params).fetchone()
            if ov["cnt"] == 0: return {"error": "No listings found", "total_listings": 0}

            source_stats = {}
            for src_row in conn.execute(f"SELECT DISTINCT source FROM listings WHERE {where}", params).fetchall():
                src = src_row["source"]
                st = conn.execute(f"SELECT COUNT(*) as count, MIN(price) as min_price, MAX(price) as max_price, AVG(price) as avg_price, AVG(mileage) as avg_mileage FROM listings WHERE {where} AND source=?", params+[src]).fetchone()
                ch = conn.execute(f"SELECT * FROM listings WHERE {where} AND source=? ORDER BY price ASC LIMIT 1", params+[src]).fetchone()
                source_stats[src] = {"count":st["count"],"min_price":round(st["min_price"] or 0),"max_price":round(st["max_price"] or 0),"avg_price":round(st["avg_price"] or 0),"avg_mileage":round(st["avg_mileage"] or 0),"cheapest_listing":dict(ch) if ch else None}

            yearly_data = {}
            for r in conn.execute(f"SELECT year, source, COUNT(*) as cnt, AVG(price) as avg_price, MIN(price) as min_price FROM listings WHERE {where} AND year IS NOT NULL GROUP BY year, source ORDER BY year DESC", params).fetchall():
                yearly_data.setdefault(int(r["year"]), {})[r["source"]] = {"count":r["cnt"],"avg_price":round(r["avg_price"]),"min_price":round(r["min_price"])}

            best = conn.execute(f"SELECT * FROM listings WHERE {where} ORDER BY price ASC LIMIT 1", params).fetchone()

        return {"brand":brand,"model":model,"year_range":f"{int(ov['min_yr'])}-{int(ov['max_yr'])}" if ov["min_yr"] else "N/A","total_listings":ov["cnt"],"market_average":round(ov["avg"] or 0),"source_comparison":source_stats,"yearly_prices":yearly_data,"best_deal":dict(best) if best else None}

    def get_trending(self, limit: int = 10) -> dict:
        with get_db() as conn:
            ml = conn.execute("SELECT brand, model, COUNT(*) as cnt, ROUND(AVG(price)) as avg_price, ROUND(MIN(price)) as min_price FROM listings WHERE brand!='Unknown' AND model!='Unknown' GROUP BY brand, model ORDER BY cnt DESC LIMIT ?", (limit,)).fetchall()
            cb = conn.execute("SELECT body_type, brand, model, year, price, source, url FROM listings WHERE body_type!='Unknown' AND price=(SELECT MIN(price) FROM listings l2 WHERE l2.body_type=listings.body_type) GROUP BY body_type ORDER BY price ASC").fetchall()
            cbr = conn.execute("SELECT l.brand, l.model, l.year, l.price, l.mileage, l.source, l.url FROM listings l INNER JOIN (SELECT brand, MIN(price) as min_price FROM listings WHERE brand!='Unknown' GROUP BY brand HAVING COUNT(*)>=3) m ON l.brand=m.brand AND l.price=m.min_price GROUP BY l.brand ORDER BY l.price ASC LIMIT 20").fetchall()
        return {"most_listed":[dict(r) for r in ml],"cheapest_by_body_type":[dict(r) for r in cb],"cheapest_by_brand":[dict(r) for r in cbr]}
