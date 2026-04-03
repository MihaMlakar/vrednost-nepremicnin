"""GURS transaction matching algorithm."""

import aiosqlite
from datetime import date, timedelta
from backend.models.schemas import GURSTransaction, TrendPoint


async def find_comparables(
    db: aiosqlite.Connection,
    neighborhood: str,
    size_m2: float,
    size_tolerance: float = 0.10,
    months_back: int = 24,
    limit: int = 10,
) -> list[GURSTransaction]:
    """
    Find GURS transactions matching the listing criteria.

    Matching rules:
    - Same neighborhood (exact match on normalized name)
    - Size within +/- tolerance (default 10%)
    - Transaction date within last N months
    - Sorted by: closest size match, then most recent
    """
    min_size = size_m2 * (1 - size_tolerance)
    max_size = size_m2 * (1 + size_tolerance)
    cutoff_date = (date.today() - timedelta(days=months_back * 30)).isoformat()

    cursor = await db.execute(
        """
        SELECT id, transaction_date, municipality, neighborhood, property_type,
               size_m2, price_eur, price_per_m2, year_built, floor, total_floors
        FROM gurs_transactions
        WHERE neighborhood = ?
          AND size_m2 BETWEEN ? AND ?
          AND transaction_date >= ?
        ORDER BY ABS(size_m2 - ?) ASC, transaction_date DESC
        LIMIT ?
        """,
        (neighborhood, min_size, max_size, cutoff_date, size_m2, limit),
    )

    rows = await cursor.fetchall()
    return [
        GURSTransaction(
            id=row[0],
            transaction_date=row[1],
            municipality=row[2],
            neighborhood=row[3],
            property_type=row[4],
            size_m2=row[5],
            price_eur=row[6],
            price_per_m2=row[7],
            year_built=row[8],
            floor=row[9],
            total_floors=row[10],
        )
        for row in rows
    ]


async def get_price_trend(
    db: aiosqlite.Connection,
    neighborhood: str,
    months_back: int = 24,
) -> list[TrendPoint]:
    """
    Get monthly average price/m2 for a neighborhood.
    Returns data points for the sparkline chart.
    """
    cutoff_date = (date.today() - timedelta(days=months_back * 30)).isoformat()

    cursor = await db.execute(
        """
        SELECT strftime('%Y-%m', transaction_date) as month,
               ROUND(AVG(price_per_m2), 0) as avg_price_m2,
               COUNT(*) as num_transactions
        FROM gurs_transactions
        WHERE neighborhood = ?
          AND transaction_date >= ?
        GROUP BY strftime('%Y-%m', transaction_date)
        ORDER BY month ASC
        """,
        (neighborhood, cutoff_date),
    )

    rows = await cursor.fetchall()
    return [
        TrendPoint(
            month=row[0],
            avg_price_m2=row[1],
            num_transactions=row[2],
        )
        for row in rows
    ]
