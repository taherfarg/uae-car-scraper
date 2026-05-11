# app/main.py
"""
FastAPI backend for the UAE Car Market Search UI.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import logging

from app.database import init_database, get_filter_options
from app.search_engine import CarSearchEngine
from app.models import SearchRequest, SortField

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="UAE Car Market Search", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

engine = CarSearchEngine()


@app.on_event("startup")
async def startup():
    try:
        if not os.path.exists("data/cars.db"):
            logger.info("Initializing database from CSV...")
            init_database()
        logger.info("Database ready.")
    except FileNotFoundError:
        logger.warning("No processed data found. API will return empty results.")


static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def home():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>UAE Car Market Search</h1><p>Static files not found.</p>")


@app.get("/api/filters")
async def get_filters():
    try:
        return get_filter_options()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/search")
async def search_cars(
    q: Optional[str] = Query(None), brand: Optional[str] = None,
    model: Optional[str] = None, min_year: Optional[int] = None,
    max_year: Optional[int] = None, min_price: Optional[float] = None,
    max_price: Optional[float] = None, min_mileage: Optional[int] = None,
    max_mileage: Optional[int] = None, body_type: Optional[str] = None,
    fuel_type: Optional[str] = None, transmission: Optional[str] = None,
    source: Optional[str] = None, specs_origin: Optional[str] = None,
    sort: Optional[str] = "price_asc", page: int = 1, per_page: int = 24,
):
    try:
        sort_field = SortField(sort) if sort else SortField.PRICE_ASC
    except ValueError:
        sort_field = SortField.PRICE_ASC

    req = SearchRequest(
        query=q, brand=brand, model=model, min_year=min_year, max_year=max_year,
        min_price=min_price, max_price=max_price, min_mileage=min_mileage,
        max_mileage=max_mileage, body_type=body_type, fuel_type=fuel_type,
        transmission=transmission, source=source, specs_origin=specs_origin,
        sort_by=sort_field, page=page, per_page=per_page,
    )
    return engine.search(req)


@app.get("/api/autocomplete")
async def autocomplete(q: str = Query(..., min_length=1), limit: int = Query(8, ge=1, le=20)):
    return {"suggestions": engine.autocomplete(q, limit)}


@app.get("/api/compare")
async def compare_prices(
    brand: str = Query(...), model: str = Query(...),
    min_year: Optional[int] = None, max_year: Optional[int] = None,
):
    result = engine.compare_prices(brand, model, min_year, max_year)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/api/trending")
async def trending(limit: int = Query(10, ge=1, le=50)):
    return engine.get_trending(limit)


@app.post("/api/reload")
async def reload_data():
    try:
        count = init_database()
        return {"status": "ok", "listings_loaded": count}
    except Exception as e:
        raise HTTPException(500, str(e))
