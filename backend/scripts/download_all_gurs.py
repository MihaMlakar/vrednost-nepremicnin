#!/usr/bin/env python3
"""
Download ALL GURS ETN transaction data for all Slovenian municipalities.

Usage:
    python scripts/download_all_gurs.py
    python scripts/download_all_gurs.py --years 2024,2025
    python scripts/download_all_gurs.py --municipality Ljubljana

Downloads ZIP files from the JGP portal API (no auth needed), then imports
apartment transaction data into SQLite.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "https://ipi.eprostor.gov.si/jgp-service-api"
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://ipi.eprostor.gov.si/jgp/data",
}
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/GURS_ETN")
GROUP_ID = 131
COMPOSITE_PRODUCT_ID = 323  # Kupoprodajni posli (KPP). 324 = Najemni posli (NP/rentals)


from typing import Optional, List

def get_municipalities(client: httpx.Client) -> List[dict]:
    """Fetch list of all 212 Slovenian municipalities."""
    resp = client.get(f"{BASE_URL}/municipalities", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def download_etl(
    client: httpx.Client,
    municipality_code: str,
    municipality_name: str,
    year: int,
    output_dir: str,
) -> str:
    """Download ETN ZIP for one municipality and year. Returns path or None."""

    # Step 1: Get file metadata + check if data exists
    result_url = (
        f"{BASE_URL}/display-views/groups/{GROUP_ID}"
        f"/composite-products/{COMPOSITE_PRODUCT_ID}/result"
        f"?filterParam=OBCINE&filterValue={municipality_code}&filterYear={year}"
    )
    try:
        resp = client.get(result_url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return None
        result = resp.json()
        if result.get("statusId") != 1:
            return None
    except Exception:
        return None

    file_name = result.get("file", {}).get("name", f"ETN_{municipality_code}_{year}.zip")
    file_path = os.path.join(output_dir, file_name)

    # Skip if already downloaded
    if os.path.exists(file_path):
        file_size = result.get("fileSize", 0)
        if os.path.getsize(file_path) >= file_size * 0.9:  # within 10%
            return file_path

    # Step 2: Get signed download URL
    file_url = (
        f"{BASE_URL}/display-views/groups/{GROUP_ID}"
        f"/composite-products/{COMPOSITE_PRODUCT_ID}/file"
        f"?filterParam=OBCINE&filterValue={municipality_code}&filterYear={year}"
    )
    try:
        resp = client.get(file_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        download_url = resp.json()["url"]
    except Exception as e:
        print(f"    Failed to get download URL: {e}")
        return None

    # Step 3: Download the ZIP
    try:
        resp = client.get(download_url, headers=HEADERS, timeout=120, follow_redirects=True)
        resp.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(resp.content)
        return file_path
    except Exception as e:
        print(f"    Download failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Download all GURS ETN data")
    parser.add_argument(
        "--years",
        default="2023,2024,2025,2026",
        help="Comma-separated years to download (default: 2023,2024,2025,2026)",
    )
    parser.add_argument(
        "--municipality",
        help="Download only this municipality (by name, e.g. 'Ljubljana')",
    )
    parser.add_argument(
        "--output-dir",
        default=DOWNLOAD_DIR,
        help=f"Output directory (default: {DOWNLOAD_DIR})",
    )
    parser.add_argument(
        "--import-db",
        action="store_true",
        help="Import downloaded data into SQLite after downloading",
    )
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")]
    os.makedirs(args.output_dir, exist_ok=True)

    client = httpx.Client(timeout=120, follow_redirects=True)

    # Get municipalities
    print("Fetching municipality list...")
    municipalities = get_municipalities(client)
    print(f"Found {len(municipalities)} municipalities")

    # Filter if requested
    if args.municipality:
        municipalities = [
            m for m in municipalities
            if args.municipality.lower() in m["name"].lower()
        ]
        if not municipalities:
            print(f"No municipality matching '{args.municipality}'")
            sys.exit(1)
        print(f"Filtered to: {[m['name'] for m in municipalities]}")

    # Download
    downloaded = []
    skipped = 0
    failed = 0
    total = len(municipalities) * len(years)

    for i, muni in enumerate(municipalities):
        code = muni["sifra"]
        name = muni["name"]

        for year in years:
            idx = i * len(years) + years.index(year) + 1
            print(f"[{idx}/{total}] {name} ({code}) {year}...", end=" ", flush=True)

            path = download_etl(client, code, name, year, args.output_dir)
            if path:
                size_kb = os.path.getsize(path) / 1024
                print(f"OK ({size_kb:.0f} KB)")
                downloaded.append(path)
            else:
                print("no data")
                skipped += 1

            # Be polite to the server
            time.sleep(0.5)

    client.close()

    print(f"\n{'='*50}")
    print(f"Download complete:")
    print(f"  Downloaded: {len(downloaded)} files")
    print(f"  Skipped:    {skipped} (no data)")
    print(f"  Failed:     {failed}")
    print(f"  Directory:  {args.output_dir}")

    # Import if requested
    if args.import_db and downloaded:
        print(f"\nImporting into database...")
        from backend.scripts.import_real_gurs import import_gurs_data, SCHEMA_SQL, DATABASE_PATH
        import sqlite3

        os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.executescript(SCHEMA_SQL)

        total_imported = 0
        for path in downloaded:
            stats = import_gurs_data(path, conn)
            total_imported += stats["imported"]

        total = conn.execute("SELECT COUNT(*) FROM gurs_transactions").fetchone()[0]
        print(f"\nTotal transactions in database: {total}")
        conn.close()


if __name__ == "__main__":
    main()
