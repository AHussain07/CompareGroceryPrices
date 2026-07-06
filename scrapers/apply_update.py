#!/usr/bin/env python3
"""
apply_update.py

Guard step for the scraper workflow. For each store, a freshly scraped CSV sits
in this directory (e.g. scrapers/aldi.csv) and last week's published copy lives
in app/public/<store>.csv.

We only publish the new file if its row count is within 10% of the previous
week's row count. This protects the site from a broken/partial scrape (site
layout change, anti-bot block, timeout) silently wiping most products.

Rules per store:
  * new file missing or empty        -> skip (keep last week's)
  * no previous file (first publish)  -> accept (nothing to compare against)
  * |new - old| / old <= 0.10         -> accept (copy into app/public/)
  * otherwise                         -> skip and report

Exit code is always 0: a rejected store is a normal outcome, not a build error.
"""

import csv
import shutil
import sys
from pathlib import Path

THRESHOLD = 0.10  # allowed fractional change vs. previous week

HERE = Path(__file__).resolve().parent          # scrapers/
PUBLIC = HERE.parent / "app" / "public"          # app/public/

STORES = ["aldi", "asda", "morrisons", "tesco"]


def row_count(path: Path) -> int:
    """Number of data rows (excludes header, tolerant of quoted newlines)."""
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as f:
        rows = sum(1 for _ in csv.reader(f))
    return max(0, rows - 1)


def main() -> int:
    updated, skipped = [], []

    for store in STORES:
        new_file = HERE / f"{store}.csv"
        old_file = PUBLIC / f"{store}.csv"

        new_rows = row_count(new_file)
        old_rows = row_count(old_file)

        if new_rows == 0:
            print(f"[skip] {store}: no new data "
                  f"(scrape missing or empty)")
            skipped.append(store)
            continue

        if old_rows == 0:
            print(f"[ok]   {store}: {new_rows} rows "
                  f"(no previous file, publishing first copy)")
            shutil.copyfile(new_file, old_file)
            updated.append(store)
            continue

        delta = abs(new_rows - old_rows) / old_rows
        if delta <= THRESHOLD:
            print(f"[ok]   {store}: {new_rows} rows "
                  f"(was {old_rows}, {delta:+.1%} within {THRESHOLD:.0%})")
            shutil.copyfile(new_file, old_file)
            updated.append(store)
        else:
            print(f"[skip] {store}: {new_rows} rows "
                  f"(was {old_rows}, {delta:.1%} exceeds {THRESHOLD:.0%}) "
                  f"-> keeping last week's file")
            skipped.append(store)

    print()
    print(f"Updated: {', '.join(updated) or '(none)'}")
    print(f"Skipped: {', '.join(skipped) or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
