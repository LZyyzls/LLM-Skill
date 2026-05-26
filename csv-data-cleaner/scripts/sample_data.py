#!/usr/bin/env python3
"""
Return the first N rows of a CSV as structured JSON for preview.
Useful for the LLM to "see" actual data before deciding next steps.

Usage:
    python scripts/sample_data.py <csv_path> [--n 10] [--columns col1,col2]
Output: JSON to stdout
"""

import argparse
import sys

from csv_io import read_csv, write_json


def sample(csv_path: str, n: int = 10, focus_columns: list | None = None) -> dict:
    headers, rows, encoding, error = read_csv(csv_path)
    if error:
        return error

    sample_rows = rows[:n]

    if focus_columns:
        focus_columns = [c for c in focus_columns if c in headers]
        sample_rows = [{c: row.get(c, "") for c in focus_columns} for row in sample_rows]

    return {
        "status": "success",
        "error_code": 0,
        "encoding": encoding,
        "total_rows": len(rows),
        "total_columns": len(headers),
        "headers_shown": focus_columns if focus_columns else headers,
        "sample_size": len(sample_rows),
        "rows": sample_rows
    }


def main():
    parser = argparse.ArgumentParser(description="Preview first N rows of a CSV")
    parser.add_argument("input", help="Path to CSV file")
    parser.add_argument("--n", type=int, default=10, help="Number of rows to return")
    parser.add_argument("--columns", "-c", help="Comma-separated columns to include")
    args = parser.parse_args()

    focus = [c.strip() for c in args.columns.split(",")] if args.columns else None
    result = sample(args.input, args.n, focus)
    write_json(result)
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
