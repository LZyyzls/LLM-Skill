#!/usr/bin/env python3
"""
Per-column profiling: type inference, missing stats, numeric distributions,
categorical top-N values.

Usage:
    python scripts/column_profile.py <csv_path> [--columns col1,col2]
    If --columns is omitted, profiles all columns.
Output: JSON to stdout
"""

import argparse
import math
import sys
from collections import Counter

from csv_io import read_csv, write_json


def _safe_float(val: str) -> float | None:
    try:
        return float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def _detect_type(values: list) -> str:
    if not values:
        return "empty"
    numeric = sum(1 for v in values if _safe_float(v) is not None)
    return "numeric" if numeric / len(values) > 0.7 else "categorical"


def _numeric_stats(nums: list) -> dict:
    if not nums:
        return {}
    n = len(nums)
    mean = sum(nums) / n
    variance = sum((x - mean) ** 2 for x in nums) / n if n > 1 else 0
    return {
        "min": round(min(nums), 2),
        "max": round(max(nums), 2),
        "mean": round(mean, 2),
        "std": round(math.sqrt(variance), 2),
        "median": round(sorted(nums)[n // 2], 2),
        "count": n
    }


def _categorical_stats(values: list) -> dict:
    non_empty = [v.strip() for v in values if v.strip()]
    counter = Counter(non_empty)
    total = len(non_empty)
    top10 = [
        {"value": v, "count": c, "pct": f"{c / total * 100:.1f}%"}
        for v, c in counter.most_common(10)
    ]
    return {
        "unique_count": len(counter),
        "top_values": top10,
        "count": total
    }


def _profile_one(values: list) -> dict:
    non_empty = [v for v in values if v.strip()]
    missing = len(values) - len(non_empty)
    col_type = _detect_type(non_empty)

    result = {
        "type": col_type,
        "total": len(values),
        "missing": missing,
        "missing_pct": round(missing / len(values) * 100, 1) if values else 0
    }

    if col_type == "numeric":
        nums = [_safe_float(v) for v in non_empty]
        nums = [n for n in nums if n is not None]
        result.update(_numeric_stats(nums))
    elif col_type == "categorical":
        result.update(_categorical_stats(non_empty))

    return result


def profile(csv_path: str, focus_columns: list | None = None) -> dict:
    headers, rows, _enc, error = read_csv(csv_path)
    if error:
        return error

    targets = focus_columns if focus_columns else headers
    targets = [c for c in targets if c in headers]

    if not targets:
        return {
            "status": "error", "error_code": 3,
            "message": f"指定列不存在，可用列: {headers}"
        }

    columns = {}
    for col in targets:
        values = [row.get(col, "") for row in rows]
        columns[col] = _profile_one(values)

    return {
        "status": "success",
        "error_code": 0,
        "total_rows": len(rows),
        "profiled_columns": len(columns),
        "columns": columns
    }


def main():
    parser = argparse.ArgumentParser(description="Per-column statistical profiling")
    parser.add_argument("input", help="Path to CSV file")
    parser.add_argument("--columns", "-c", help="Comma-separated column names (default: all)")
    args = parser.parse_args()

    focus = [c.strip() for c in args.columns.split(",")] if args.columns else None
    result = profile(args.input, focus)
    write_json(result)
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
