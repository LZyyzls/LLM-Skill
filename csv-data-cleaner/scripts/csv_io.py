#!/usr/bin/env python3
"""Shared CSV I/O: encoding detection and safe reading. Used by all tool scripts."""

import csv
import json
import os
import sys
from typing import Optional


def read_csv(csv_path: str) -> tuple[Optional[list], Optional[list], Optional[str], Optional[dict]]:
    """
    Read a CSV file with automatic encoding detection.

    Returns:
        (headers, rows, encoding, error_dict)
        On success: (headers, rows, encoding, None)
        On failure: (None, None, None, {"status": "error", "error_code": N, "message": "..."})
    """
    if not os.path.isfile(csv_path):
        return None, None, None, {
            "status": "error", "error_code": 1,
            "message": f"文件不存在: {csv_path}"
        }

    encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]

    for enc in encodings:
        try:
            with open(csv_path, "r", encoding=enc) as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)
            return headers, rows, enc, None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return None, None, None, {
                "status": "error", "error_code": 2,
                "message": f"读取失败 ({enc}): {e}"
            }

    return None, None, None, {
        "status": "error", "error_code": 2,
        "message": "无法识别文件编码，请转换为 UTF-8 后重试"
    }


def write_json(data: dict, fp=None) -> None:
    """
    Output JSON to stdout with proper UTF-8 encoding.
    Works around Windows console GBK default by reconfiguring stdout.
    """
    if fp is None:
        fp = sys.stdout

    # Reconfigure stdout for UTF-8 on Windows (Python 3.7+)
    if hasattr(fp, "reconfigure"):
        try:
            fp.reconfigure(encoding="utf-8")
        except Exception:
            pass

    json.dump(data, fp, ensure_ascii=False, indent=2)
    fp.write("\n")
