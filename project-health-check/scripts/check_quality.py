#!/usr/bin/env python3
"""
Phase 2: Code quality check.
Only runs if Phase 1 found Python files. Scores each file across 8 dimensions.

Usage:
    python scripts/check_quality.py <project_path>
Output: JSON to stdout
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", ".svn", ".hg", ".venv", "venv", ".tox"}

# ── Individual check functions ──

def _check_line_length(lines: list) -> dict:
    max_len = max((len(l) for l in lines), default=0)
    over_100 = sum(1 for l in lines if len(l) > 100)
    score = 100 if max_len <= 100 else max(0, 100 - over_100 * 2)
    return {"max_line": max_len, "over_100_count": over_100, "score": min(100, score)}


def _check_function_length(lines: list) -> dict:
    """Estimate function body lengths by tracking def lines and indentation."""
    func_lens = []
    current_func_start = None
    current_func_indent = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect function definition
        if stripped.startswith("def ") and not stripped.startswith("def __"):
            # Skip dunder methods
            pass
        if stripped.startswith("def "):
            indent = len(line) - len(line.lstrip())
            # Close previous function
            if current_func_start is not None:
                func_lens.append(i - current_func_start)
            current_func_start = i
            current_func_indent = indent
        # Detect end of function (line at same or lower indent that's not blank/comment)
        elif current_func_start is not None and stripped and not stripped.startswith("#"):
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= current_func_indent:
                func_lens.append(i - current_func_start)
                current_func_start = None
                current_func_indent = None

    # Don't forget last function
    if current_func_start is not None:
        func_lens.append(len(lines) - current_func_start)

    if not func_lens:
        return {"count": 0, "avg_len": 0, "max_len": 0, "over_30": 0, "score": 100}

    avg = sum(func_lens) / len(func_lens)
    over_30 = sum(1 for fl in func_lens if fl > 30)
    score = max(0, 100 - over_30 * 10 - max(0, (avg - 15)) * 2)
    return {
        "count": len(func_lens), "avg_len": round(avg, 1),
        "max_len": max(func_lens), "over_30": over_30,
        "score": round(min(100, score))
    }


def _check_docstrings(lines: list) -> dict:
    """Check for docstring presence after def/class lines."""
    def_lines = 0
    with_doc = 0
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            def_lines += 1
            # Check next non-empty line for docstring
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith("#"):
                    if next_line.startswith('"""') or next_line.startswith("'''"):
                        with_doc += 1
                    break
        i += 1

    pct = round(with_doc / def_lines * 100) if def_lines else 100
    score = min(100, pct)
    return {"def_count": def_lines, "with_docstring": with_doc, "pct": pct, "score": score}


def _check_type_hints(lines: list) -> dict:
    """Check for type annotations in function signatures."""
    text = "\n".join(lines)
    # Find function signatures
    sigs = re.findall(r'def \w+\(([^)]*)\)', text)
    total = len(sigs)
    with_hints = 0
    for sig in sigs:
        # Has type annotation: contains ': ' or '->'
        if ': ' in sig or re.search(r'def \w+\([^)]*\)\s*->', text):
            # Simple check: look for : in the parameter list
            if any(':' in param for param in sig.split(',')):
                with_hints += 1

    # Simpler approach: count def lines with '->' or param ':'
    def_lines_with_hints = 0
    def_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def "):
            def_count += 1
            if "->" in stripped:
                def_lines_with_hints += 1
            elif re.search(r':\s*\w+\s*[,\)]', stripped):
                # Contains a parameter type annotation
                def_lines_with_hints += 1

    pct = round(def_lines_with_hints / def_count * 100) if def_count else 100
    score = min(100, pct * 2)  # 50% coverage = 100 score
    return {"def_count": def_count, "with_hints": def_lines_with_hints,
            "pct": pct, "score": min(100, score)}


def _check_comments(lines: list) -> dict:
    total = len(lines)
    comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
    blank_lines = sum(1 for l in lines if not l.strip())
    code_lines = total - comment_lines - blank_lines

    ratio = round(comment_lines / total * 100, 1) if total else 0
    # Optimal: 5-15% comments
    score = 100
    if ratio < 5:
        score = ratio * 20  # 0% → 0, 5% → 100
    elif ratio > 30:
        score = max(0, 100 - (ratio - 30) * 5)
    return {
        "total": total, "comment_lines": comment_lines,
        "blank_lines": blank_lines, "code_lines": code_lines,
        "ratio_pct": ratio, "score": round(score)
    }


def _check_imports(lines: list) -> dict:
    has_import_star = any("import *" in l for l in lines)
    import_lines = [l for l in lines if l.strip().startswith(("import ", "from "))]
    score = 100
    if has_import_star:
        score -= 50
    if len(import_lines) > 20:
        score -= 10
    return {
        "import_count": len(import_lines),
        "has_import_star": has_import_star,
        "score": max(0, score)
    }


def _check_todos(lines: list) -> dict:
    count = sum(1 for l in lines if "TODO" in l.upper() or "FIXME" in l.upper())
    score = 100 - min(count * 5, 100)
    return {"count": count, "score": score}


def _check_file_structure(lines: list) -> dict:
    """Check for module docstring, shebang, encoding declaration."""
    has_shebang = lines[0].startswith("#!") if lines else False
    has_encoding = any("coding" in l and "utf" in l.lower() for l in lines[:3])
    has_module_doc = False
    for l in lines[:5]:
        if l.strip().startswith('"""') or l.strip().startswith("'''"):
            has_module_doc = True
            break
    score = 70  # base
    if has_module_doc:
        score += 20
    if has_shebang or has_encoding:
        score += 10
    return {
        "has_shebang": has_shebang, "has_encoding_decl": has_encoding,
        "has_module_docstring": has_module_doc, "score": min(100, score)
    }


# ── Main ──

WEIGHTS = {
    "line_length": 0.10, "func_length": 0.20, "docstrings": 0.20,
    "type_hints": 0.15, "comments": 0.10, "imports": 0.10,
    "todos": 0.05, "file_struct": 0.10
}


def check(project_path: str) -> dict:
    root = Path(project_path)
    if not root.is_dir():
        return {"status": "error", "error_code": 1,
                "message": f"目录不存在: {project_path}"}

    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname.endswith(".py"):
                py_files.append(Path(dirpath) / fname)

    if not py_files:
        return {"status": "success", "error_code": 0,
                "has_python_code": False, "message": "项目中没有 Python 文件"}

    file_results = []
    total_scores = {k: 0.0 for k in WEIGHTS}

    for fpath in py_files:
        try:
            lines = fpath.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        rel = str(fpath.relative_to(root)).replace("\\", "/")

        checks = {
            "line_length": _check_line_length(lines),
            "func_length": _check_function_length(lines),
            "docstrings": _check_docstrings(lines),
            "type_hints": _check_type_hints(lines),
            "comments": _check_comments(lines),
            "imports": _check_imports(lines),
            "todos": _check_todos(lines),
            "file_struct": _check_file_structure(lines),
        }

        file_score = sum(c["score"] * WEIGHTS[k] for k, c in checks.items())

        file_results.append({
            "file": rel,
            "lines": len(lines),
            "score": round(file_score, 1),
            "details": checks
        })

        for k in WEIGHTS:
            total_scores[k] += checks[k]["score"]

    n = len(file_results)
    avg_scores = {k: round(total_scores[k] / n, 1) for k in WEIGHTS}
    overall = round(sum(avg_scores[k] * WEIGHTS[k] for k in WEIGHTS), 1)

    # Determine grade
    if overall >= 90:
        grade = "A"
    elif overall >= 75:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    else:
        grade = "D"

    # Collect top issues
    issues = []
    if avg_scores["docstrings"] < 60:
        issues.append({"dimension": "文档覆盖", "score": avg_scores["docstrings"],
                       "detail": f"docstring 覆盖率低 ({avg_scores['docstrings']}分)"})
    if avg_scores["type_hints"] < 50:
        issues.append({"dimension": "类型注解", "score": avg_scores["type_hints"],
                       "detail": "类型注解使用不足"})
    if avg_scores["func_length"] < 70:
        issues.append({"dimension": "函数长度", "score": avg_scores["func_length"],
                       "detail": "存在过多长函数"})
    if avg_scores["todos"] < 80:
        issues.append({"dimension": "TODO/FIXME", "score": avg_scores["todos"],
                       "detail": "未完成标记过多"})

    return {
        "status": "success",
        "error_code": 0,
        "has_python_code": True,
        "project_path": str(root.resolve()),
        "files_checked": n,
        "overall_score": overall,
        "grade": grade,
        "dimension_scores": avg_scores,
        "weights": WEIGHTS,
        "top_issues": issues,
        "file_details": file_results[:15],
        "needs_remediation": overall < 60
    }


def main():
    parser = argparse.ArgumentParser(description="Check Python code quality")
    parser.add_argument("input", help="Path to project directory")
    args = parser.parse_args()

    result = check(args.input)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
