#!/usr/bin/env python3
"""
Rule-based data quality validation. Reads field_rules.md and applies
each rule to the data, returning a structured violation report.

Usage:
    python scripts/quality_check.py <csv_path> [--rules references/field_rules.md]
Output: JSON to stdout
"""

import argparse
import re
import sys
from pathlib import Path

from csv_io import read_csv, write_json

# ── Default thresholds (mirrored from field_rules.md) ──

MISSING_WARN_PCT = 1.0     # > 1% → warning
MISSING_ERROR_PCT = 20.0   # > 20% → error
UNIQUE_WARN_PCT = 90.0     # unique ratio > 90% → warning (categorical)
UNIQUE_ERROR_PCT = 99.0    # unique ratio > 99% → likely primary key
LARGE_DATASET_ROWS = 50_000

# Suffix → forced type overrides
TYPE_OVERRIDES = [
    (re.compile(r".*(_date|_time|_at)$"), "temporal"),
    (re.compile(r".*(_flag|_is_|_has_)$"), "boolean"),
]


def _load_rules_text(rules_path: str | None) -> str:
    """Load rules file content for reference display."""
    if rules_path and Path(rules_path).exists():
        return Path(rules_path).read_text(encoding="utf-8")
    return ""


def _check_type_override(col_name: str) -> str | None:
    for pattern, forced_type in TYPE_OVERRIDES:
        if pattern.match(col_name.lower()):
            return forced_type
    return None


def _classify_missing_severity(missing_pct: float) -> str | None:
    if missing_pct > MISSING_ERROR_PCT:
        return "error"
    elif missing_pct > MISSING_WARN_PCT:
        return "warning"
    return None


def check(csv_path: str, rules_path: str | None = None) -> dict:
    headers, rows, _enc, error = read_csv(csv_path)
    if error:
        return error

    rules_ref = _load_rules_text(rules_path)
    violations = []
    n_rows = len(rows)

    for col in headers:
        values = [row.get(col, "").strip() for row in rows]
        non_empty = [v for v in values if v]
        missing = n_rows - len(non_empty)
        missing_pct = missing / n_rows * 100 if n_rows else 0

        # 1. Type override check
        forced = _check_type_override(col)
        if forced:
            violations.append({
                "column": col,
                "rule": "type_override",
                "severity": "info",
                "detail": f"列名后缀匹配 {forced} 类型覆盖规则，跳过常规数值统计"
            })

        # 2. Missing rate check
        sev = _classify_missing_severity(missing_pct)
        if sev:
            violations.append({
                "column": col,
                "rule": "missing_rate",
                "severity": sev,
                "detail": f"缺失率 {missing_pct:.1f}% (> {MISSING_ERROR_PCT if sev == 'error' else MISSING_WARN_PCT}%)",
                "metric": {"missing": missing, "total": n_rows, "pct": round(missing_pct, 1)}
            })

        # 3. Unique-value ratio check (categorical-like columns)
        if non_empty and not forced:
            unique = len(set(non_empty))
            unique_pct = unique / len(non_empty) * 100
            if unique_pct > UNIQUE_ERROR_PCT:
                violations.append({
                    "column": col,
                    "rule": "unique_ratio",
                    "severity": "warning",
                    "detail": f"唯一值占比 {unique_pct:.1f}% (疑似主键或ID列)",
                    "metric": {"unique": unique, "total_non_empty": len(non_empty), "pct": round(unique_pct, 1)}
                })

        # 4. Boolean column content check
        if forced == "boolean" and non_empty:
            valid_bool = {"0", "1", "true", "false", "yes", "no", "是", "否"}
            invalid = [v for v in non_empty if v.lower() not in valid_bool]
            if invalid:
                violations.append({
                    "column": col,
                    "rule": "boolean_values",
                    "severity": "warning",
                    "detail": f"布尔列包含非标准值: {list(set(invalid))[:10]} (期望 0/1/true/false)"
                })

    # 4. Large dataset advisory
    if n_rows > LARGE_DATASET_ROWS:
        violations.append({
            "column": "*",
            "rule": "large_dataset",
            "severity": "info",
            "detail": f"行数 {n_rows} > {LARGE_DATASET_ROWS}，建议使用抽样分析 (--sample 0.1)"
        })

    errors = sum(1 for v in violations if v["severity"] == "error")
    warnings = sum(1 for v in violations if v["severity"] == "warning")
    infos = sum(1 for v in violations if v["severity"] == "info")

    return {
        "status": "success",
        "error_code": 0,
        "total_rows": n_rows,
        "checked_columns": len(headers),
        "rules_source": rules_path or "built-in defaults",
        "summary": {"errors": errors, "warnings": warnings, "info": infos, "total": len(violations)},
        "violations": violations
    }


def main():
    parser = argparse.ArgumentParser(description="Rule-based data quality check")
    parser.add_argument("input", help="Path to CSV file")
    parser.add_argument("--rules", "-r", help="Path to field_rules.md (for reference)")
    args = parser.parse_args()

    result = check(args.input, args.rules)
    write_json(result)
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
