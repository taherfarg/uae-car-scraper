# app/models.py
"""
Request/Response models for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class SortField(str, Enum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    YEAR_DESC = "year_desc"
    YEAR_ASC = "year_asc"
    MILEAGE_ASC = "mileage_asc"
    MILEAGE_DESC = "mileage_desc"
    QUALITY_DESC = "quality_desc"


class SearchRequest(BaseModel):
    """Search request with all filter criteria."""
    query: Optional[str] = Field(None, description="Free text search (brand, model, etc.)")
    brand: Optional[str] = None
    model: Optional[str] = None
    min_year: Optional[int] = Field(None, ge=1990, le=2027)
    max_year: Optional[int] = Field(None, ge=1990, le=2027)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    min_mileage: Optional[int] = Field(None, ge=0)
    max_mileage: Optional[int] = Field(None, ge=0)
    body_type: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    source: Optional[str] = None
    specs_origin: Optional[str] = None
    sort_by: SortField = SortField.PRICE_ASC
    page: int = Field(1, ge=1)
    per_page: int = Field(24, ge=1, le=100)


class CarListing(BaseModel):
    """Single car listing response."""
    id: int
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price: float
    mileage: Optional[int] = None
    body_type: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    specs_origin: Optional[str] = None
    quality_score: Optional[float] = None
    cross_source_flag: Optional[str] = None
    price_tier: Optional[str] = None
    brand_origin: Optional[str] = None
    car_age: Optional[int] = None
    dealer: Optional[str] = None
    publish_date: Optional[str] = None


class SearchResponse(BaseModel):
    """Search results response."""
    listings: List[CarListing]
    total: int
    page: int
    per_page: int
    total_pages: int
    query_time_ms: float
    price_stats: dict


class PriceCompareResponse(BaseModel):
    """Price comparison across sources for a specific car."""
    brand: str
    model: str
    year_range: str
    dubizzle: Optional[dict] = None
    dubicars: Optional[dict] = None
    best_deal: Optional[dict] = None
    market_average: float
    total_listings: int


class AutocompleteResponse(BaseModel):
    """Autocomplete suggestions."""
    suggestions: List[dict]
