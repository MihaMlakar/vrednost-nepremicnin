"""FastAPI application: Real Estate Valuation Copilot for Slovenia."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import get_db, get_stats, init_db
from backend.models.schemas import (
    AnalyzeRequest,
    ErrorResponse,
    HealthResponse,
    ListingData,
    ValuationReport,
)
from backend.services.comparison import find_comparables, get_price_trend
from backend.services.scraper import (
    ExtractionError,
    InvalidURLError,
    ScrapeError,
    scrape_listing,
)
from backend.services.valuation import calculate_valuation

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Vrednost Nepremičnin",
    description="AI-driven real estate valuation for Slovenia",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin(s). Comma-separated for multiple.
frontend_origins = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
origins = [o.strip() for o in frontend_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Simple in-memory rate limiter
_request_counts: dict[str, list[float]] = {}
RATE_LIMIT = 10  # requests per minute


@app.post("/api/analyze", response_model=ValuationReport)
async def analyze_listing(request: AnalyzeRequest):
    """
    Analyze a real estate listing and return a valuation report.

    Accepts either a nepremicnine.net URL or manual listing data.
    """
    db = await get_db()
    try:
        # Get known neighborhoods for the extraction schema
        stats = await get_stats()
        known_neighborhoods = stats.get("neighborhoods", [])

        # Extract listing data from URL or manual input
        cached = False
        if request.url:
            try:
                listing, cached = await scrape_listing(
                    request.url, db, known_neighborhoods
                )
            except InvalidURLError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except ScrapeError as e:
                raise HTTPException(status_code=502, detail=str(e))
            except ExtractionError as e:
                raise HTTPException(status_code=422, detail=str(e))

        elif request.manual:
            listing = ListingData(
                price_eur=request.manual.price_eur,
                city="Ljubljana",
                neighborhood=request.manual.neighborhood,
                size_m2=request.manual.size_m2,
                year_built=request.manual.year_built,
                floor=request.manual.floor,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'url' or 'manual' input is required",
            )

        # Find comparable GURS transactions
        comps = await find_comparables(
            db=db,
            neighborhood=listing.neighborhood,
            size_m2=listing.size_m2,
        )

        # Get price trend data
        trend = await get_price_trend(
            db=db,
            neighborhood=listing.neighborhood,
        )

        # Calculate valuation
        report = calculate_valuation(
            listing=listing,
            comps=comps,
            trend=trend,
            cached=cached,
        )

        return report

    finally:
        await db.close()


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check with database statistics."""
    stats = await get_stats()
    return HealthResponse(
        status="ok",
        gurs_transactions=stats["gurs_transactions"],
        cache_entries=stats["cache_entries"],
        known_neighborhoods=len(stats["neighborhoods"]),
    )
