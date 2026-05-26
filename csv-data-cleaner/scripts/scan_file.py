#!/usr/bin/env python3
"""
Quick file scan: encoding detection, dimensions, headers, basic health.
Always the cheapest first step — call this before any other tool.

Usage:
    python scripts/scan_file.py <csv_path>
Output: JSON to stdout
"""

import argparse
import os
import sys

from csv_io import read_csv, write_json


def scan(csv_path: str) -> dict:
    headers, rows, encoding, error = read_csv(csv_path)
    if error:
        return error

    file_size = round(os.path.getsize(csv_path) / 1024, 1)

    empty_cols = []
    for col in headers:
        if all((row.get(col) or "").strip() == "" for row in rows):
            empty_cols.append(col)

    dupes = list({h for h in headers if headers.count(h) > 1})

    return {
        "status": "success",
        "error_code": 0,
        "file_path": os.path.abspath(csv_path),
        "file_size_kb": file_size,
        "encoding": encoding,
        "row_count": len(rows),
        "col_count": len(headers),
        "headers": headers,
        "empty_columns": empty_cols,
        "duplicate_headers": dupes
    }


def main():
    parser = argparse.ArgumentParser(description="Quick CSV file structure scan")
    parser.add_argument("input", help="Path to CSV file")
    args = parser.parse_args()

    result = scan(args.input)
    write_json(result)
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
