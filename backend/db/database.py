"""SQLite database connection and initialization."""

import aiosqlite
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/vrednost.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS gurs_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date DATE NOT NULL,
    municipality TEXT NOT NULL,
    neighborhood TEXT NOT NULL,
    property_type TEXT NOT NULL,
    size_m2 REAL NOT NULL,
    price_eur REAL NOT NULL,
    price_per_m2 REAL NOT NULL,
    year_built INTEGER,
    floor INTEGER,
    total_floors INTEGER,
    source_file TEXT,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_cache (
    url TEXT PRIMARY KEY,
    extracted_data JSON NOT NULL,
    scraped_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_gurs_dedup
    ON gurs_transactions(transaction_date, neighborhood, size_m2, price_eur);
CREATE INDEX IF NOT EXISTS idx_gurs_neighborhood
    ON gurs_transactions(neighborhood);
CREATE INDEX IF NOT EXISTS idx_gurs_size
    ON gurs_transactions(size_m2);
CREATE INDEX IF NOT EXISTS idx_gurs_date
    ON gurs_transactions(transaction_date);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection with WAL mode and busy timeout."""
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DATABASE_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
    finally:
        await db.close()


async def get_stats() -> dict:
    """Get database statistics."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM gurs_transactions")
        row = await cursor.fetchone()
        gurs_count = row[0]

        cursor = await db.execute("SELECT COUNT(*) FROM scrape_cache")
        row = await cursor.fetchone()
        cache_count = row[0]

        cursor = await db.execute(
            "SELECT DISTINCT neighborhood FROM gurs_transactions ORDER BY neighborhood"
        )
        neighborhoods = [row[0] for row in await cursor.fetchall()]

        return {
            "gurs_transactions": gurs_count,
            "cache_entries": cache_count,
            "neighborhoods": neighborhoods,
        }
    finally:
        await db.close()
