#!/usr/bin/env python3
"""
Import REAL GURS ETN transaction data from the JGP portal CSV exports.

Usage:
    python scripts/import_real_gurs.py /path/to/ETN_061_2024_KPP_*.zip
    python scripts/import_real_gurs.py /path/to/extracted_folder/

The ZIP contains 4 files:
- *_POSLI_*.csv      — transactions (ID_POSLA, price, date)
- *_DELISTAVB_*.csv  — building parts (apartment details, joined by ID_POSLA)
- *_ZEMLJISCA_*.csv  — land parcels (skip)
- *_sifranti_*.csv   — code tables (property type codes etc.)

We join POSLI + DELISTAVB on ID_POSLA, filter for apartments (VRSTA_DELA_STAVBE=2),
and import into SQLite.
"""

import csv
import glob
import os
import re
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

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

# Cadastral community (KO) to neighborhood mapping for Ljubljana
# IME_KO values from GURS → friendly neighborhood names
KO_TO_NEIGHBORHOOD = {
    "ZGORNJA ŠIŠKA": "Šiška",
    "SPODNJA ŠIŠKA": "Šiška",
    "BEŽIGRAD": "Bežigrad",
    "DRAVLJE": "Dravlje",
    "ČRNUČE": "Črnuče",
    "ŠENTVID NAD LJUBLJANO": "Šentvid",
    "ŠENTVID": "Šentvid",
    "VIČ": "Vič",
    "TRNOVSKO PREDMESTJE": "Trnovo",
    "TRNOVO": "Trnovo",
    "MOSTE": "Moste",
    "POLJE": "Polje",
    "FUŽINE": "Fužine",
    "ŠENTPETER": "Center",
    "POLJANSKO PREDMESTJE": "Center",
    "AJDOVŠČINA": "Center",
    "KRAKOVSKO PREDMESTJE": "Center",
    "PRULE": "Center",
    "GRADIŠČE I": "Center",
    "GRADIŠČE II": "Center",
    "TABOR": "Center",
    "STOŽICE": "Bežigrad",
    "JEŽICA": "Ježica",
    "SELO PRI IHANU": "Polje",
    "KODELJEVO": "Kodeljevo",
    "RUDNIK": "Rudnik",
    "ZELENA JAMA": "Zelena jama",
    "KOSEZE": "Koseze",
    "SOSTRO": "Sostro",
    "BRINJE I": "Šiška",
    "BRINJE II": "Šiška",
    "ŠTEPANJA VAS": "Štepanjsko naselje",
    "SLAPE": "Vič",
    "GLINCE": "Vič",
    "ROŽNA DOLINA": "Rožna dolina",
    "MURGLE": "Murgle",
    "JARŠE": "Jarše",
    "PODGORICA": "Rudnik",
    "LAVRICA": "Rudnik",
    "ZADOBROVA": "Polje",
    "BIZOVIK": "Polje",
    "NOVE JARŠE": "Jarše",
    "NOVE FUŽINE": "Fužine",
    "SAVSKO NASELJE": "Bežigrad",
    "BRATOVŠEVA PLOŠČAD": "Bežigrad",
    "BS3": "Bežigrad",
}


def parse_date(date_str: str) -> str:
    """Parse DD.MM.YYYY to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d.%m.%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def normalize_ko(ime_ko: str) -> str:
    """Map cadastral community name to neighborhood."""
    if not ime_ko:
        return None
    upper = ime_ko.strip().upper()
    return KO_TO_NEIGHBORHOOD.get(upper, ime_ko.strip().title())


def find_csv_files(path: str) -> dict:
    """Find the CSV files in a directory or ZIP."""
    files = {}

    if path.endswith(".zip"):
        extract_dir = path.replace(".zip", "")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(extract_dir)
        path = extract_dir

    for f in glob.glob(os.path.join(path, "*.csv")):
        fname = os.path.basename(f).upper()
        if "POSLI" in fname:
            files["posli"] = f
        elif "DELISTAVB" in fname:
            files["delistavb"] = f
        elif "SIFRANTI" in fname:
            files["sifranti"] = f
        elif "ZEMLJISCA" in fname:
            files["zemljisca"] = f

    return files


def import_gurs_data(path: str, conn: sqlite3.Connection) -> dict:
    """Import real GURS ETN data from CSV files."""
    stats = {"imported": 0, "skipped": 0, "duplicates": 0, "errors": 0, "apartments": 0}

    files = find_csv_files(path)
    if "posli" not in files or "delistavb" not in files:
        print(f"ERROR: Could not find POSLI and DELISTAVB CSV files in {path}")
        print(f"  Found: {list(files.keys())}")
        return stats

    print(f"  POSLI:     {files['posli']}")
    print(f"  DELISTAVB: {files['delistavb']}")

    # Load transactions (POSLI) into a dict by ID_POSLA
    posli = {}
    with open(files["posli"], "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            posli[row["ID_POSLA"]] = row

    print(f"  Loaded {len(posli)} transactions from POSLI")

    # Process building parts (DELISTAVB), join with POSLI
    with open(files["delistavb"], "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, 1):
            try:
                # Filter: only apartments (VRSTA_DELA_STAVBE = 2)
                vrsta = row.get("VRSTA_DELA_STAVBE", "").strip()
                if vrsta != "2":
                    stats["skipped"] += 1
                    continue

                stats["apartments"] += 1

                id_posla = row["ID_POSLA"]
                posel = posli.get(id_posla)
                if not posel:
                    stats["skipped"] += 1
                    continue

                # Get neighborhood from cadastral community name
                neighborhood = normalize_ko(row.get("IME_KO", ""))
                if not neighborhood:
                    stats["skipped"] += 1
                    continue

                # Get size (use PRODANA_UPORABNA_POVRSINA first, fall back to POVRSINA)
                size_str = (
                    row.get("PRODANA_UPORABNA_POVRSINA", "").strip()
                    or row.get("UPORABNA_POVRSINA", "").strip()
                    or row.get("POVRSINA_DELA_STAVBE", "").strip()
                )
                if not size_str:
                    stats["skipped"] += 1
                    continue
                size = float(size_str.replace(",", "."))
                if size <= 0 or size > 500:
                    stats["skipped"] += 1
                    continue

                # Get price — use part-specific price if available, else total
                price_str = (
                    row.get("POGODBENA_CENA_DELA_STAVBE", "").strip()
                    or posel.get("POGODBENA_CENA_ODSKODNINA", "").strip()
                )
                if not price_str:
                    stats["skipped"] += 1
                    continue
                price = float(price_str.replace(",", "."))
                if price <= 0 or price > 10000000:
                    stats["skipped"] += 1
                    continue

                price_per_m2 = round(price / size, 2)

                # Get date
                date_str = parse_date(
                    posel.get("DATUM_SKLENITVE_POGODBE", "")
                    or posel.get("DATUM_UVELJAVITVE", "")
                )
                if not date_str:
                    stats["skipped"] += 1
                    continue

                # Year built
                year_str = row.get("LETO_IZGRADNJE_DELA_STAVBE", "").strip()
                year_built = int(year_str) if year_str and year_str.isdigit() else None

                # Floor
                floor_str = row.get("NADSTROPJE_DELA_STAVBE", "").strip()
                floor = None
                if floor_str:
                    # Map text to number
                    floor_map = {
                        "klet": -1, "pritličje": 0, "nadstropje": 1,
                        "mansarda": None, "podstreha": None,
                    }
                    floor = floor_map.get(floor_str.lower())
                    if floor is None and floor_str.isdigit():
                        floor = int(floor_str)

                # Municipality
                municipality = row.get("OBCINA", "LJUBLJANA").strip()

                source = os.path.basename(files["delistavb"])

                conn.execute(
                    """INSERT OR IGNORE INTO gurs_transactions
                    (transaction_date, municipality, neighborhood, property_type,
                     size_m2, price_eur, price_per_m2, year_built, floor, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        date_str,
                        municipality,
                        neighborhood,
                        "apartment",
                        size,
                        price,
                        price_per_m2,
                        year_built,
                        floor,
                        source,
                    ),
                )
                stats["imported"] += 1

            except (ValueError, KeyError) as e:
                stats["errors"] += 1
                if stats["errors"] <= 10:
                    print(f"  Row {row_num}: {e}")

    conn.commit()
    return stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_real_gurs.py <path_to_zip_or_folder> [more_paths...]")
        print("Example: python import_real_gurs.py ~/Downloads/ETN_061_2024_KPP_*.zip")
        sys.exit(1)

    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA_SQL)

    total_stats = {"imported": 0, "skipped": 0, "duplicates": 0, "errors": 0, "apartments": 0}

    for path in sys.argv[1:]:
        print(f"\nImporting from {path}...")
        stats = import_gurs_data(path, conn)
        for k in total_stats:
            total_stats[k] += stats[k]

    # Print stats
    print(f"\n{'='*50}")
    print(f"Import complete:")
    print(f"  Apartments found: {total_stats['apartments']}")
    print(f"  Imported:         {total_stats['imported']}")
    print(f"  Skipped:          {total_stats['skipped']}")
    print(f"  Duplicates:       {total_stats['duplicates']}")
    print(f"  Errors:           {total_stats['errors']}")

    # Print neighborhood distribution
    cursor = conn.execute(
        """SELECT neighborhood, COUNT(*), ROUND(AVG(price_per_m2), 0),
                  ROUND(MIN(price_per_m2), 0), ROUND(MAX(price_per_m2), 0)
           FROM gurs_transactions
           GROUP BY neighborhood
           ORDER BY COUNT(*) DESC"""
    )
    print(f"\nNeighborhood distribution:")
    print(f"  {'Neighborhood':25s}  {'Count':>5s}  {'Avg €/m²':>8s}  {'Min':>6s}  {'Max':>6s}")
    print(f"  {'-'*25}  {'-'*5}  {'-'*8}  {'-'*6}  {'-'*6}")
    for row in cursor.fetchall():
        print(f"  {row[0]:25s}  {row[1]:5d}  {row[2]:8,.0f}  {row[3]:6,.0f}  {row[4]:6,.0f}")

    total = conn.execute("SELECT COUNT(*) FROM gurs_transactions").fetchone()[0]
    print(f"\nTotal transactions in database: {total}")

    conn.close()


if __name__ == "__main__":
    main()
