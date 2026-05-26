#!/usr/bin/env python3
"""
PII / sensitive data detection in CSV files.
Checks both column names and content patterns.

Usage:
    python scripts/pii_detect.py <csv_path> [--sample 50]
Output: JSON to stdout
"""

import argparse
import re
import sys

from csv_io import read_csv, write_json

# Column-name patterns → PII type
_NAME_PATTERNS = [
    (["email", "e-mail", "mail", "邮箱", "电子邮件"], "email"),
    (["phone", "tel", "mobile", "cell", "电话", "手机", "联系电话"], "phone"),
    (["id_card", "idcard", "id_number", "身份证", "证件号", "ssn"], "id_card"),
    (["name", "姓名", "名字", "full_name", "fullname", "real_name"], "person_name"),
    (["address", "addr", "地址", "住址", "location"], "address"),
    (["password", "passwd", "pwd", "secret", "token", "密码", "密钥"], "credential"),
]

# Content regex patterns → PII type
_CONTENT_PATTERNS = [
    (re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"), "email"),
    (re.compile(r"^1[3-9]\d{9}$"), "phone_cn"),
    (re.compile(r"^\d{17}[\dXx]$"), "id_card_cn"),
]

_SEVERITY = {
    "credential": "error",
    "id_card": "error",
    "email": "warning",
    "phone": "warning",
    "phone_cn": "warning",
    "id_card_cn": "error",
    "person_name": "warning",
    "address": "warning",
}

_RECOMMENDATIONS = {
    "credential": "疑似密码/密钥列，强烈建议移除",
    "id_card": "疑似身份证号，建议脱敏或移除",
    "id_card_cn": "内容匹配身份证格式，建议脱敏",
    "email": "疑似邮箱地址，建议评估是否需脱敏",
    "phone": "疑似电话号码，建议评估是否需脱敏",
    "phone_cn": "内容匹配手机号格式，建议评估是否需脱敏",
    "person_name": "疑似姓名列，建议评估隐私风险",
    "address": "疑似地址列，建议评估隐私风险",
}


def detect(csv_path: str, sample_size: int = 50) -> dict:
    headers, rows, _enc, error = read_csv(csv_path)
    if error:
        return error

    findings = []

    for col in headers:
        col_lower = col.lower().strip()
        found = None

        # 1. Column-name match
        for keywords, pii_type in _NAME_PATTERNS:
            if any(kw in col_lower for kw in keywords):
                found = {
                    "column": col,
                    "pii_type": pii_type,
                    "method": "column_name",
                    "severity": _SEVERITY.get(pii_type, "warning"),
                    "recommendation": _RECOMMENDATIONS.get(pii_type, "疑似敏感信息"),
                }
                break

        # 2. Content-pattern match (sample)
        if not found:
            samples = [
                row.get(col, "").strip()
                for row in rows[:sample_size]
                if row.get(col, "").strip()
            ]
            if samples:
                for pattern, pii_type in _CONTENT_PATTERNS:
                    matches = sum(1 for s in samples if pattern.match(s))
                    if matches / len(samples) > 0.5:
                        found = {
                            "column": col,
                            "pii_type": pii_type,
                            "method": "content_pattern",
                            "match_rate": f"{matches}/{len(samples)}",
                            "severity": _SEVERITY.get(pii_type, "warning"),
                            "recommendation": _RECOMMENDATIONS.get(pii_type, "疑似敏感数据"),
                        }
                        break

        if found:
            findings.append(found)

    return {
        "status": "success",
        "error_code": 0,
        "total_columns": len(headers),
        "pii_count": len(findings),
        "verdict": "clean" if not findings else "pii_found",
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Detect PII/sensitive data in CSV")
    parser.add_argument("input", help="Path to CSV file")
    parser.add_argument("--sample", type=int, default=50, help="Rows to sample for content check")
    args = parser.parse_args()

    result = detect(args.input, args.sample)
    write_json(result)
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
