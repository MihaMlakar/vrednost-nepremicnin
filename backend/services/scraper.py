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


def _extract_from_markdown(markdown: str, known_neighborhoods: list[str]) -> dict | None:
    """
    Fallback: extract listing data from scraped markdown using regex.
    Works for nepremicnine.net page structure.
    """
    data: dict = {}

    # Price: look for EUR amounts like "185.000 €" or "185000 EUR" or "185.000,00 €"
    price_patterns = [
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)\s*(?:€|EUR)",
        r"(\d{4,7}(?:,\d{2})?)\s*(?:€|EUR)",
        r"[Cc]ena[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)?",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, markdown)
        if match:
            price_str = match.group(1).replace(".", "").replace(",", ".")
            try:
                price = float(price_str)
                if 10000 <= price <= 5000000:
                    data["price_eur"] = price
                    break
            except ValueError:
                continue

    # Size: look for m2/m² amounts
    size_patterns = [
        r"(\d{2,4}(?:[,.]\d{1,2})?)\s*m[²2]",
        r"[Pp]ovršina[:\s]*(\d{2,4}(?:[,.]\d{1,2})?)",
        r"(\d{2,4}(?:[,.]\d{1,2})?)\s*(?:kvadrat|sqm)",
    ]
    for pattern in size_patterns:
        match = re.search(pattern, markdown)
        if match:
            size_str = match.group(1).replace(",", ".")
            try:
                size = float(size_str)
                if 10 <= size <= 2000:
                    data["size_m2"] = size
                    break
            except ValueError:
                continue

    # Neighborhood: check if any known neighborhood appears in text
    for neighborhood in known_neighborhoods:
        if neighborhood.lower() in markdown.lower():
            data["neighborhood"] = neighborhood
            break

    # City: default to Ljubljana
    data["city"] = "Ljubljana"

    # Year built
    year_match = re.search(r"[Ll]eto\s+(?:izgradnje|gradnje)[:\s]*(\d{4})", markdown)
    if not year_match:
        year_match = re.search(r"[Zz]grajeno[:\s]*(\d{4})", markdown)
    if year_match:
        year = int(year_match.group(1))
        if 1800 <= year <= 2026:
            data["year_built"] = year

    # Floor
    floor_match = re.search(r"(\d{1,2})\.\s*(?:nadstropje|etaža)", markdown)
    if floor_match:
        data["floor"] = int(floor_match.group(1))

    # Validate we have minimum required fields
    if "price_eur" in data and "size_m2" in data and "neighborhood" in data:
        return data

    return None


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

        # Use scrape() to get markdown, then extract() for structured data
        # Try extract first (async LLM extraction), fall back to scrape + regex
        extracted = None

        try:
            result = app.extract(
                urls=[url],
                prompt=(
                    "Extract real estate listing details from this Slovenian "
                    "real estate listing page. Return the asking price in EUR, "
                    "city, neighborhood/district, living area in m2, year built, "
                    "floor number, and a brief description."
                ),
                schema=extraction_schema,
            )

            # Handle various response formats
            if hasattr(result, "data") and result.data:
                extracted = result.data
            elif isinstance(result, dict):
                extracted = result.get("data") or result.get("results")

            # Unwrap list
            if isinstance(extracted, list) and extracted:
                extracted = extracted[0]

            # Convert objects to dict
            if extracted and hasattr(extracted, "model_dump"):
                extracted = extracted.model_dump()
            elif extracted and hasattr(extracted, "__dict__") and not isinstance(extracted, dict):
                extracted = {k: v for k, v in extracted.__dict__.items() if not k.startswith("_")}

        except Exception as extract_err:
            print(f"extract() failed, falling back to scrape(): {extract_err}")
            extracted = None

        # Fallback: scrape markdown and parse with regex
        if not extracted or not isinstance(extracted, dict) or "price_eur" not in extracted:
            print("Using scrape() fallback with regex extraction")
            doc = app.scrape(url, formats=["markdown"])

            markdown = ""
            if hasattr(doc, "markdown"):
                markdown = doc.markdown or ""
            elif isinstance(doc, dict):
                markdown = doc.get("markdown", "")

            if len(markdown) < 50:
                raise ExtractionError(
                    "Could not access this listing. The page may require a CAPTCHA or be unavailable."
                )

            extracted = _extract_from_markdown(markdown, known_neighborhoods)

        if not extracted:
            raise ExtractionError("Could not extract listing details from this page.")

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
