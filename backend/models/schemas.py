"""Pydantic models for all data structures."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# Known Ljubljana neighborhoods — populated from GURS data at runtime
# This is the initial seed list; import_gurs.py updates it
KNOWN_NEIGHBORHOODS = [
    "Bežigrad",
    "Center",
    "Črnuče",
    "Dravlje",
    "Fužine",
    "Galjevica",
    "Glince",
    "Jarše",
    "Ježica",
    "Kodeljevo",
    "Koseze",
    "Moste",
    "Murgle",
    "Polje",
    "Rožna dolina",
    "Rudnik",
    "Šentvid",
    "Šiška",
    "Šmarna gora",
    "Štepanjsko naselje",
    "Trnovo",
    "Vič",
    "Vodmat",
    "Zelena jama",
]


class ListingData(BaseModel):
    """Data extracted from a nepremicnine.net listing."""

    price_eur: float = Field(ge=10000, le=5000000, description="Asking price in EUR")
    city: str = Field(description="City name, e.g. Ljubljana")
    neighborhood: str = Field(description="Neighborhood name, e.g. Šiška, Bežigrad")
    size_m2: float = Field(ge=10, le=500, description="Living area in square meters")
    year_built: Optional[int] = Field(
        ge=1800, le=2026, default=None, description="Year the building was constructed"
    )
    floor: Optional[int] = Field(default=None, description="Floor number")
    total_floors: Optional[int] = Field(
        default=None, description="Total floors in building"
    )
    num_rooms: Optional[float] = Field(default=None, description="Number of rooms")
    description_summary: Optional[str] = Field(
        default=None, description="1-2 sentence summary"
    )


class ManualListingInput(BaseModel):
    """Manual input from the user (no scraping needed)."""

    price_eur: float = Field(ge=10000, le=5000000)
    neighborhood: str
    size_m2: float = Field(ge=10, le=500)
    year_built: Optional[int] = Field(ge=1800, le=2026, default=None)
    floor: Optional[int] = None


class GURSTransaction(BaseModel):
    """A single GURS ETN transaction record."""

    id: Optional[int] = None
    transaction_date: date
    municipality: str
    neighborhood: str
    property_type: str
    size_m2: float
    price_eur: float
    price_per_m2: float
    year_built: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None


class TrendPoint(BaseModel):
    """A single point in the price trend."""

    month: str  # "2025-01"
    avg_price_m2: float
    num_transactions: int


class ValuationReport(BaseModel):
    """The complete valuation report returned to the user."""

    listing: ListingData
    truth_score: float  # percentage: negative = overpriced
    negotiation_lever: str  # human-readable summary
    avg_gurs_price_per_m2: float
    asking_price_per_m2: float
    num_comps: int
    confidence: str  # "high", "medium", "low"
    comps: list[GURSTransaction]
    trend: list[TrendPoint]
    cached: bool = False


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze."""

    url: Optional[str] = Field(
        default=None, description="nepremicnine.net listing URL"
    )
    manual: Optional[ManualListingInput] = Field(
        default=None, description="Manual listing data (alternative to URL)"
    )


class HealthResponse(BaseModel):
    """Response for GET /api/health."""

    status: str
    gurs_transactions: int
    cache_entries: int
    known_neighborhoods: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
