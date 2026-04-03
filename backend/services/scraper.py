"""Scraper service: Firecrawl extract() + caching."""

import json
import os
import re
from datetime import datetime, timedelta

import aiosqlite
from firecrawl import FirecrawlApp

from backend.models.schemas import ListingData

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
CACHE_TTL_HOURS = 24


class InvalidURLError(Exception):
    pass


class ScrapeError(Exception):
    pass


class ExtractionError(Exception):
    pass


def validate_url(url: str) -> str:
    """Validate that the URL is a nepremicnine.net listing."""
    if not url:
        raise InvalidURLError("URL is required")

    url = url.strip()

    # Accept both www and non-www
    pattern = r"^https?://(www\.)?nepremicnine\.net/"
    if not re.match(pattern, url):
        raise InvalidURLError(
            "Please enter a valid nepremicnine.net URL"
        )

    return url


async def get_cached(db: aiosqlite.Connection, url: str) -> ListingData | None:
    """Check cache for a previously scraped URL."""
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "SELECT extracted_data FROM scrape_cache WHERE url = ? AND expires_at > ?",
        (url, now),
    )
    row = await cursor.fetchone()
    if row:
        data = json.loads(row[0])
        return ListingData(**data)
    return None


async def save_to_cache(
    db: aiosqlite.Connection, url: str, listing: ListingData
) -> None:
    """Save extracted data to cache."""
    now = datetime.utcnow()
    expires = now + timedelta(hours=CACHE_TTL_HOURS)
    await db.execute(
        """INSERT OR REPLACE INTO scrape_cache (url, extracted_data, scraped_at, expires_at)
           VALUES (?, ?, ?, ?)""",
        (url, listing.model_dump_json(), now.isoformat(), expires.isoformat()),
    )
    await db.commit()


async def scrape_listing(
    url: str,
    db: aiosqlite.Connection,
    known_neighborhoods: list[str],
) -> tuple[ListingData, bool]:
    """
    Scrape a nepremicnine.net listing and extract structured data.

    Returns (ListingData, cached: bool).

    Uses Firecrawl extract() which handles scraping + LLM extraction
    in a single API call. The Pydantic schema with neighborhood enum
    constraint ensures the LLM picks from known GURS neighborhoods.
    """
    url = validate_url(url)

    # Check cache first
    cached = await get_cached(db, url)
    if cached:
        return cached, True

    # Build extraction schema with known neighborhoods
    neighborhood_enum = known_neighborhoods if known_neighborhoods else None

    extraction_schema = {
        "type": "object",
        "properties": {
            "price_eur": {
                "type": "number",
                "description": "Asking price in EUR",
            },
            "city": {
                "type": "string",
                "description": "City name, e.g. Ljubljana",
            },
            "neighborhood": {
                "type": "string",
                "description": "Neighborhood/district name",
            },
            "size_m2": {
                "type": "number",
                "description": "Living area in square meters (not total area)",
            },
            "year_built": {
                "type": "number",
                "description": "Year the building was constructed, or null",
            },
            "floor": {
                "type": "number",
                "description": "Floor number the apartment is on, or null",
            },
            "total_floors": {
                "type": "number",
                "description": "Total number of floors in the building, or null",
            },
            "num_rooms": {
                "type": "number",
                "description": "Number of rooms, or null",
            },
            "description_summary": {
                "type": "string",
                "description": "1-2 sentence summary of the listing in English",
            },
        },
        "required": ["price_eur", "city", "neighborhood", "size_m2"],
    }

    # Add enum constraint for neighborhoods if available
    if neighborhood_enum:
        extraction_schema["properties"]["neighborhood"]["enum"] = neighborhood_enum
        extraction_schema["properties"]["neighborhood"]["description"] = (
            f"Neighborhood name. Must be one of the known neighborhoods: "
            f"{', '.join(neighborhood_enum[:10])}..."
        )

    try:
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        result = app.scrape_url(
            url,
            params={
                "formats": ["extract"],
                "extract": {
                    "schema": extraction_schema,
                    "prompt": (
                        "Extract real estate listing details from this page. "
                        "Focus on the asking price, location, and apartment size. "
                        "The price should be in EUR. Size should be the living area "
                        "(uporabna površina), not the total area."
                    ),
                },
            },
        )

        if not result or "extract" not in result:
            raise ExtractionError("Firecrawl returned no extraction data")

        extracted = result["extract"]
        if not extracted:
            raise ExtractionError("Extraction returned empty data")

        # Validate with Pydantic + range checks
        listing = ListingData(**extracted)

        # Cache the result
        await save_to_cache(db, url, listing)

        return listing, False

    except InvalidURLError:
        raise
    except ExtractionError:
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "rate" in error_str:
            raise ScrapeError("Too many requests. Please try again in a minute.")
        elif "timeout" in error_str:
            raise ScrapeError(
                "The listing took too long to load. Please try again."
            )
        elif "404" in error_str or "not found" in error_str:
            raise ScrapeError(
                "Could not access this listing. It may have been removed."
            )
        else:
            raise ScrapeError(f"Could not scrape listing: {e}")
