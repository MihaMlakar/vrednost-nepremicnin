"""GURS transaction matching algorithm."""

import aiosqlite
from datetime import date, timedelta
from typing import List, Optional

from backend.models.schemas import GURSTransaction, TrendPoint


# Geographic adjacency for Ljubljana neighborhoods
# Each neighborhood maps to its geographic neighbors
ADJACENT_NEIGHBORHOODS = {
    "Šiška": ["Dravlje", "Šentvid", "Vič", "Center"],
    "Bežigrad": ["Šiška", "Center", "Jarše", "Črnuče", "Ježica", "Stožice"],
    "Center": ["Šiška", "Bežigrad", "Trnovo", "Moste", "Kodeljevo", "Vič",
               "Ljubljana Mesto", "Karlovško Predmestje"],
    "Vič": ["Šiška", "Center", "Trnovo", "Rožna dolina", "Koseze", "Dravlje", "Brdo"],
    "Moste": ["Center", "Kodeljevo", "Fužine", "Polje", "Jarše", "Štepanjsko naselje"],
    "Trnovo": ["Center", "Vič", "Rudnik", "Murgle", "Rožna dolina"],
    "Črnuče": ["Bežigrad", "Ježica", "Šentvid", "Stožice"],
    "Dravlje": ["Šiška", "Šentvid", "Koseze", "Vič"],
    "Fužine": ["Moste", "Polje", "Štepanjsko naselje", "Kodeljevo"],
    "Jarše": ["Bežigrad", "Moste", "Polje", "Črnuče", "Stožice"],
    "Polje": ["Moste", "Fužine", "Jarše", "Kašelj"],
    "Šentvid": ["Šiška", "Dravlje", "Črnuče", "Vižmarje"],
    "Kodeljevo": ["Center", "Moste", "Fužine", "Zelena jama"],
    "Rudnik": ["Trnovo", "Murgle", "Vič"],
    "Ježica": ["Bežigrad", "Črnuče", "Stožice"],
    "Koseze": ["Vič", "Dravlje", "Šiška"],
    "Murgle": ["Trnovo", "Rudnik", "Vič"],
    "Rožna dolina": ["Vič", "Trnovo"],
    "Zelena jama": ["Kodeljevo", "Moste", "Fužine"],
    "Štepanjsko naselje": ["Moste", "Fužine", "Polje"],
    "Kašelj": ["Polje", "Jarše"],
    "Udmat": ["Center", "Kodeljevo"],
    "Ljubljana Mesto": ["Center", "Karlovško Predmestje"],
    "Karlovško Predmestje": ["Center", "Ljubljana Mesto", "Trnovo"],
    "Vižmarje": ["Šentvid", "Dravlje"],
    "Brdo": ["Vič", "Rožna dolina"],
    "Stožice": ["Bežigrad", "Jarše", "Črnuče", "Ježica"],
    "Tacen": ["Šentvid", "Vižmarje"],
    "Dobrova": ["Vič", "Brdo"],
    "Gameljne": ["Črnuče", "Tacen"],
    "Nadgorica": ["Črnuče", "Gameljne"],
    "Stanežiče": ["Šentvid", "Vižmarje"],
    "Šujica": ["Vič", "Brdo", "Dobrova"],
    "Dobrunje": ["Polje", "Kašelj"],
    "Golovec": ["Kodeljevo", "Moste"],
    "Šmartno Pod Šmarno Goro": ["Tacen", "Šentvid"],
    "Sostro": ["Dobrunje", "Polje"],
    "Tomišelj": ["Rudnik"],
}

LJUBLJANA_NAMES = {"ljubljana", "lj", "lj.", "mol"}


def _normalize_neighborhood(neighborhood: str) -> list:
    """Normalize neighborhood name, handling prefixes and comma separation."""
    variants = set()
    variants.add(neighborhood.strip())

    if "," in neighborhood:
        for part in neighborhood.split(","):
            variants.add(part.strip())

    expanded = set()
    for n in variants:
        expanded.add(n)
        for prefix in ["Lj. ", "Lj.", "LJ. ", "LJ.", "MB. ", "MB.",
                        "Ljubljana - ", "Ljubljana "]:
            if n.startswith(prefix):
                expanded.add(n[len(prefix):].strip())
    return list(expanded)


def get_wider_neighborhoods(neighborhood: str) -> list:
    """
    Get the wider area neighborhoods for a given neighborhood.
    For Ljubljana: the neighborhood itself + all adjacent neighborhoods.
    Returns a list of neighborhood names.
    """
    normalized = _normalize_neighborhood(neighborhood)

    wider = set(normalized)
    for n in normalized:
        # Direct lookup
        if n in ADJACENT_NEIGHBORHOODS:
            wider.update(ADJACENT_NEIGHBORHOODS[n])
        # Reverse lookup: find neighborhoods that list this one as adjacent
        for key, adjacents in ADJACENT_NEIGHBORHOODS.items():
            if n in adjacents:
                wider.add(key)

    return list(wider)


async def get_wider_neighborhoods_for_municipality(
    db: aiosqlite.Connection,
    neighborhood: str,
    municipality: str,
) -> list:
    """
    For non-Ljubljana municipalities, get all neighborhoods in the same municipality.
    For Ljubljana, use the geographic adjacency mapping.
    """
    if municipality.lower().strip() in LJUBLJANA_NAMES:
        return get_wider_neighborhoods(neighborhood)

    # For non-Ljubljana: all neighborhoods in the same municipality
    cursor = await db.execute(
        "SELECT DISTINCT neighborhood FROM gurs_transactions WHERE municipality = ?",
        (municipality,),
    )
    rows = await cursor.fetchall()
    all_in_municipality = [row[0] for row in rows]

    if all_in_municipality:
        return all_in_municipality

    # Fallback: just the normalized variants
    return _normalize_neighborhood(neighborhood)


async def find_comparables(
    db: aiosqlite.Connection,
    neighborhood: str,
    size_m2: float,
    size_tolerance: float = 0.25,
    months_back: int = 24,
    limit: int = 10,
) -> list:
    """
    Find GURS transactions matching the listing criteria (exact neighborhood).
    """
    min_size = size_m2 * (1 - size_tolerance)
    max_size = size_m2 * (1 + size_tolerance)
    cutoff_date = (date.today() - timedelta(days=months_back * 30)).isoformat()

    neighborhood_variants = _normalize_neighborhood(neighborhood)

    placeholders = ",".join(["?" for _ in neighborhood_variants])
    params = neighborhood_variants + [min_size, max_size, cutoff_date, size_m2, limit]

    cursor = await db.execute(
        f"""
        SELECT id, transaction_date, municipality, neighborhood, property_type,
               size_m2, price_eur, price_per_m2, year_built, floor, total_floors
        FROM gurs_transactions
        WHERE neighborhood IN ({placeholders})
          AND size_m2 BETWEEN ? AND ?
          AND transaction_date >= ?
        ORDER BY ABS(size_m2 - ?) ASC, transaction_date DESC
        LIMIT ?
        """,
        params,
    )

    rows = await cursor.fetchall()
    return [
        GURSTransaction(
            id=row[0], transaction_date=row[1], municipality=row[2],
            neighborhood=row[3], property_type=row[4], size_m2=row[5],
            price_eur=row[6], price_per_m2=row[7], year_built=row[8],
            floor=row[9], total_floors=row[10],
        )
        for row in rows
    ]


async def find_wider_area_comparables(
    db: aiosqlite.Connection,
    wider_neighborhoods: list,
    size_m2: float,
    size_tolerance: float = 0.25,
    months_back: int = 24,
    limit: int = 20,
) -> list:
    """
    Find GURS transactions across the wider area (neighborhood + adjacent).
    """
    min_size = size_m2 * (1 - size_tolerance)
    max_size = size_m2 * (1 + size_tolerance)
    cutoff_date = (date.today() - timedelta(days=months_back * 30)).isoformat()

    if not wider_neighborhoods:
        return []

    placeholders = ",".join(["?" for _ in wider_neighborhoods])
    params = wider_neighborhoods + [min_size, max_size, cutoff_date, size_m2, limit]

    cursor = await db.execute(
        f"""
        SELECT id, transaction_date, municipality, neighborhood, property_type,
               size_m2, price_eur, price_per_m2, year_built, floor, total_floors
        FROM gurs_transactions
        WHERE neighborhood IN ({placeholders})
          AND size_m2 BETWEEN ? AND ?
          AND transaction_date >= ?
        ORDER BY ABS(size_m2 - ?) ASC, transaction_date DESC
        LIMIT ?
        """,
        params,
    )

    rows = await cursor.fetchall()
    return [
        GURSTransaction(
            id=row[0], transaction_date=row[1], municipality=row[2],
            neighborhood=row[3], property_type=row[4], size_m2=row[5],
            price_eur=row[6], price_per_m2=row[7], year_built=row[8],
            floor=row[9], total_floors=row[10],
        )
        for row in rows
    ]


async def get_price_trend(
    db: aiosqlite.Connection,
    neighborhood: str,
    months_back: int = 24,
) -> list:
    """Get monthly average price/m2 for a neighborhood."""
    cutoff_date = (date.today() - timedelta(days=months_back * 30)).isoformat()
    neighborhood_variants = _normalize_neighborhood(neighborhood)

    placeholders = ",".join(["?" for _ in neighborhood_variants])
    params = neighborhood_variants + [cutoff_date]

    cursor = await db.execute(
        f"""
        SELECT strftime('%Y-%m', transaction_date) as month,
               ROUND(AVG(price_per_m2), 0) as avg_price_m2,
               COUNT(*) as num_transactions
        FROM gurs_transactions
        WHERE neighborhood IN ({placeholders})
          AND transaction_date >= ?
        GROUP BY strftime('%Y-%m', transaction_date)
        ORDER BY month ASC
        """,
        params,
    )

    rows = await cursor.fetchall()
    return [
        TrendPoint(month=row[0], avg_price_m2=row[1], num_transactions=row[2])
        for row in rows
    ]
