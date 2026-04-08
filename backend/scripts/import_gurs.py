#!/usr/bin/env python3
"""
Import GURS ETN transaction data from CSV into SQLite.

Usage:
    python scripts/import_gurs.py [path_to_csv]
    python scripts/import_gurs.py --generate-sample

If no CSV path given, generates realistic sample data for Ljubljana.
"""

import argparse
import csv
import os
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

# Add parent dir to path so we can import from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

# Realistic Ljubljana neighborhood data
# Prices reflect actual 2024-2025 GURS market data: median ~2920 EUR/m2
# weight = relative transaction volume (higher = more apartments sold)
# new_build_premium = multiplier for apartments built after 2015
NEIGHBORHOODS = {
    "Bežigrad": {"base_price_m2": 3200, "variance": 400, "weight": 12, "new_build_premium": 1.15},
    "Center": {"base_price_m2": 3800, "variance": 600, "weight": 8, "new_build_premium": 1.10},
    "Šiška": {"base_price_m2": 2900, "variance": 350, "weight": 14, "new_build_premium": 1.20},
    "Vič": {"base_price_m2": 3100, "variance": 400, "weight": 10, "new_build_premium": 1.15},
    "Moste": {"base_price_m2": 2600, "variance": 300, "weight": 9, "new_build_premium": 1.25},
    "Polje": {"base_price_m2": 2400, "variance": 300, "weight": 5, "new_build_premium": 1.20},
    "Fužine": {"base_price_m2": 2500, "variance": 300, "weight": 7, "new_build_premium": 1.20},
    "Trnovo": {"base_price_m2": 3400, "variance": 450, "weight": 6, "new_build_premium": 1.10},
    "Črnuče": {"base_price_m2": 2700, "variance": 350, "weight": 5, "new_build_premium": 1.20},
    "Šentvid": {"base_price_m2": 2800, "variance": 350, "weight": 4, "new_build_premium": 1.15},
    "Dravlje": {"base_price_m2": 2700, "variance": 300, "weight": 5, "new_build_premium": 1.20},
    "Kodeljevo": {"base_price_m2": 3000, "variance": 400, "weight": 4, "new_build_premium": 1.15},
    "Rožna dolina": {"base_price_m2": 3500, "variance": 500, "weight": 3, "new_build_premium": 1.10},
    "Rudnik": {"base_price_m2": 2300, "variance": 300, "weight": 3, "new_build_premium": 1.25},
    "Jarše": {"base_price_m2": 2800, "variance": 350, "weight": 5, "new_build_premium": 1.20},
    "Ježica": {"base_price_m2": 3000, "variance": 400, "weight": 3, "new_build_premium": 1.20},
    "Koseze": {"base_price_m2": 3200, "variance": 400, "weight": 3, "new_build_premium": 1.15},
    "Murgle": {"base_price_m2": 3600, "variance": 500, "weight": 2, "new_build_premium": 1.10},
    "Štepanjsko naselje": {"base_price_m2": 2800, "variance": 350, "weight": 4, "new_build_premium": 1.20},
    "Zelena jama": {"base_price_m2": 2700, "variance": 300, "weight": 3, "new_build_premium": 1.20},
}


def normalize_neighborhood(raw: str) -> str:
    """
    Normalize GURS administrative neighborhood names to short form.
    'MO Ljubljana, Šiška' → 'Šiška'
    'Šiška' → 'Šiška' (already short)
    """
    # Strip common prefixes
    prefixes = [
        "MO Ljubljana, ",
        "MO Ljubljana - ",
        "Mestna občina Ljubljana, ",
        "Ljubljana - ",
        "Ljubljana, ",
    ]
    result = raw.strip()
    for prefix in prefixes:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break
    return result.strip()


def generate_sample_data(num_records: int = 2500) -> list[dict]:
    """
    Generate realistic sample GURS transaction data for Ljubljana.

    Uses weighted neighborhood distribution, realistic apartment size
    profiles, new-build premiums, floor/building correlations, and
    time-based price appreciation (~5%/year based on 2024-2025 GURS stats).
    """
    records = []
    today = date.today()

    # Build weighted neighborhood list
    weighted_neighborhoods = []
    for name, info in NEIGHBORHOODS.items():
        weighted_neighborhoods.extend([name] * info["weight"])

    # Realistic apartment size distribution for Ljubljana:
    # garsonjere (studios): 20-35 m2 (~15%)
    # 1-sobna (1-room): 30-50 m2 (~25%)
    # 2-sobna (2-room): 45-75 m2 (~30%)
    # 3-sobna (3-room): 65-100 m2 (~20%)
    # 4+ sobna (4+ room): 90-180 m2 (~10%)
    size_profiles = [
        (0.15, 27, 5, 20, 38),     # garsonjera
        (0.25, 40, 6, 28, 52),     # 1-sobna
        (0.30, 58, 8, 42, 78),     # 2-sobna
        (0.20, 78, 10, 62, 105),   # 3-sobna
        (0.10, 120, 25, 85, 200),  # 4+ sobna
    ]

    # Year built distribution (matches Ljubljana building stock)
    year_weights = (
        [(y, 1) for y in range(1920, 1945)]     # pre-war (rare)
        + [(y, 3) for y in range(1945, 1965)]    # post-war blocks
        + [(y, 8) for y in range(1965, 1985)]    # socialist era (most common)
        + [(y, 5) for y in range(1985, 2000)]    # transition
        + [(y, 4) for y in range(2000, 2015)]    # modern
        + [(y, 6) for y in range(2015, 2027)]    # new builds
    )
    years_pool = [y for y, w in year_weights for _ in range(w)]

    for _ in range(num_records):
        neighborhood = random.choice(weighted_neighborhoods)
        info = NEIGHBORHOODS[neighborhood]

        # Random date in last 36 months (3 years of data)
        days_ago = random.randint(1, 1095)
        txn_date = today - timedelta(days=days_ago)

        # Pick size from realistic distribution
        r = random.random()
        cumulative = 0
        for prob, mean, std, lo, hi in size_profiles:
            cumulative += prob
            if r <= cumulative:
                size = round(random.gauss(mean, std), 1)
                size = max(lo, min(hi, size))
                break

        # Year built (80% chance of having data, 20% unknown)
        year_built = random.choice(years_pool) if random.random() < 0.8 else None

        # Price per m2: base + variance + time trend + new-build premium + size discount
        months_ago = days_ago / 30
        time_factor = 1 - (months_ago * 0.004)  # ~5% annual appreciation
        base = info["base_price_m2"] * time_factor

        # New builds command a premium
        if year_built and year_built >= 2015:
            base *= info["new_build_premium"]

        # Larger apartments have slightly lower price/m2
        if size > 100:
            base *= 0.92
        elif size > 80:
            base *= 0.96

        # Ground floor discount, top floor premium
        price_m2 = round(random.gauss(base, info["variance"]), 0)
        price_m2 = max(1500, price_m2)

        total_price = round(price_m2 * size, 0)

        # Building characteristics correlated with year built
        if year_built and year_built >= 2000:
            total_floors = random.choice([4, 5, 6, 7, 8, 10, 12])
        elif year_built and year_built >= 1965:
            total_floors = random.choice([4, 5, 8, 10, 12, 14])
        else:
            total_floors = random.choice([2, 3, 4, 5])

        floor = random.randint(0, total_floors)

        records.append(
            {
                "transaction_date": txn_date.isoformat(),
                "municipality": "Ljubljana",
                "neighborhood": neighborhood,
                "property_type": "apartment",
                "size_m2": size,
                "price_eur": total_price,
                "price_per_m2": price_m2,
                "year_built": year_built,
                "floor": floor,
                "total_floors": total_floors,
                "source_file": "sample_data",
            }
        )

    return records


def import_csv(filepath: str, conn: sqlite3.Connection) -> dict:
    """Import GURS ETN CSV into SQLite. Returns import stats."""
    stats = {"imported": 0, "skipped": 0, "duplicates": 0, "errors": 0}

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row_num, row in enumerate(reader, 1):
            try:
                # Map Slovenian field names (adjust based on actual GURS CSV format)
                neighborhood = normalize_neighborhood(
                    row.get("Lokacija", row.get("neighborhood", ""))
                )
                if not neighborhood:
                    stats["skipped"] += 1
                    continue

                size = float(
                    row.get("Površina", row.get("size_m2", "0")).replace(",", ".")
                )
                price = float(
                    row.get("Cena", row.get("price_eur", "0")).replace(",", ".")
                )

                if size <= 0 or price <= 0:
                    stats["skipped"] += 1
                    continue

                price_m2 = round(price / size, 2)
                txn_date = row.get(
                    "Datum", row.get("transaction_date", date.today().isoformat())
                )

                year_built_raw = row.get("Leto izgradnje", row.get("year_built"))
                year_built = int(year_built_raw) if year_built_raw else None

                floor_raw = row.get("Nadstropje", row.get("floor"))
                floor = int(floor_raw) if floor_raw else None

                conn.execute(
                    """INSERT OR IGNORE INTO gurs_transactions
                    (transaction_date, municipality, neighborhood, property_type,
                     size_m2, price_eur, price_per_m2, year_built, floor, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        txn_date,
                        row.get("Občina", row.get("municipality", "Ljubljana")),
                        neighborhood,
                        row.get("Vrsta", row.get("property_type", "apartment")),
                        size,
                        price,
                        price_m2,
                        year_built,
                        floor,
                        os.path.basename(filepath),
                    ),
                )

                if conn.total_changes > 0:
                    stats["imported"] += 1
                else:
                    stats["duplicates"] += 1

            except (ValueError, KeyError) as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"  Row {row_num}: {e}")

    conn.commit()
    return stats


def import_sample_data(conn: sqlite3.Connection) -> dict:
    """Import generated sample data."""
    records = generate_sample_data(2500)
    stats = {"imported": 0, "duplicates": 0, "errors": 0}

    for record in records:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO gurs_transactions
                (transaction_date, municipality, neighborhood, property_type,
                 size_m2, price_eur, price_per_m2, year_built, floor,
                 total_floors, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record["transaction_date"],
                    record["municipality"],
                    record["neighborhood"],
                    record["property_type"],
                    record["size_m2"],
                    record["price_eur"],
                    record["price_per_m2"],
                    record["year_built"],
                    record["floor"],
                    record["total_floors"],
                    record["source_file"],
                ),
            )
            stats["imported"] += 1
        except sqlite3.IntegrityError:
            stats["duplicates"] += 1
        except Exception as e:
            stats["errors"] += 1
            print(f"  Error: {e}")

    conn.commit()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import GURS ETN data")
    parser.add_argument("csv_path", nargs="?", help="Path to GURS ETN CSV file")
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate sample data for Ljubljana",
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA_SQL)

    if args.csv_path:
        print(f"Importing from {args.csv_path}...")
        stats = import_csv(args.csv_path, conn)
    else:
        print("No CSV provided. Generating 2,500 sample transactions for Ljubljana...")
        stats = import_sample_data(conn)

    # Print stats
    print(f"\nImport complete:")
    print(f"  Imported:   {stats['imported']}")
    print(f"  Duplicates: {stats.get('duplicates', 0)}")
    print(f"  Errors:     {stats.get('errors', 0)}")

    # Print neighborhood distribution
    cursor = conn.execute(
        """SELECT neighborhood, COUNT(*), ROUND(AVG(price_per_m2), 0)
           FROM gurs_transactions
           GROUP BY neighborhood
           ORDER BY COUNT(*) DESC"""
    )
    print(f"\nNeighborhood distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]:20s}  {row[1]:4d} transactions  avg {row[2]:,.0f} EUR/m2")

    total = conn.execute("SELECT COUNT(*) FROM gurs_transactions").fetchone()[0]
    print(f"\nTotal transactions in database: {total}")

    conn.close()


if __name__ == "__main__":
    main()
