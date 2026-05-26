#!/usr/bin/env python3
"""
Phase 3: Build report by merging scan + quality data into the template.
Reads assets/report_template.md and fills placeholders.

Usage:
    python scripts/build_report.py <scan_json_path> <quality_json_path> [--template assets/report_template.md]
Output: filled markdown report to stdout
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def build(scan_result: dict, quality_result: dict, template: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Calculate template values ──

    # Overview
    project_path = scan_result.get("project_path", "N/A")
    project_name = scan_result.get("project_name", "N/A")
    py_file_count = scan_result.get("py_file_count", 0)
    total_lines = scan_result.get("total_py_lines", 0)
    dir_count = scan_result.get("dir_count", 0)
    dep_files = ", ".join(scan_result.get("dep_files", [])) or "无"
    dir_tree = scan_result.get("dir_tree", "无数据")

    # Quality
    overall_score = quality_result.get("overall_score", "N/A")
    grade = quality_result.get("grade", "N/A")
    dims = quality_result.get("dimension_scores", {})
    weights = quality_result.get("weights", {})

    def _dim(dim_scores, dim_weights, key):
        s = dim_scores.get(key, 0)
        w = dim_weights.get(key, 0)
        return s, round(s * w, 1)

    func_len, func_len_w = _dim(dims, weights, "func_length")
    line_len, line_len_w = _dim(dims, weights, "line_length")
    doc_cov, doc_cov_w = _dim(dims, weights, "docstrings")
    type_ann, type_ann_w = _dim(dims, weights, "type_hints")
    comment_ratio, comment_ratio_w = _dim(dims, weights, "comments")
    todo_count, todo_w = _dim(dims, weights, "todos")
    import_quality, import_w = _dim(dims, weights, "imports")
    file_struct, file_struct_w = _dim(dims, weights, "file_struct")

    # Issues & recommendations
    issues = quality_result.get("top_issues", [])
    if issues:
        issues_text = "\n".join(
            f"- [{i['dimension']}] {i['detail']}（{i['score']}分）"
            for i in issues
        )
    else:
        issues_text = "未发现重大问题"

    if overall_score != "N/A" and overall_score < 60:
        recs = ("1. **紧急**：总体评分过低，建议逐项对照 remediation.md 修复\n"
                "2. 优先处理文档覆盖和类型注解问题\n"
                "3. 建立 CI 检查流程，防止质量退化")
    elif overall_score != "N/A" and overall_score < 75:
        recs = ("1. 关注低分维度，制定改进计划\n"
                "2. 考虑引入 pre-commit hooks 自动检查")
    else:
        recs = ("1. 整体质量良好，继续保持\n"
                "2. 可在 CI 中集成质量门禁 (score >= 75)")

    # ── Fill template ──
    report = template
    report = report.replace("{{project_path}}", project_path)
    report = report.replace("{{timestamp}}", now)
    report = report.replace("{{overall_score}}", str(overall_score))
    report = report.replace("{{grade}}", grade)
    report = report.replace("{{py_file_count}}", str(py_file_count))
    report = report.replace("{{total_lines}}", str(total_lines))
    report = report.replace("{{dir_count}}", str(dir_count))
    report = report.replace("{{dep_files}}", dep_files)
    report = report.replace("{{dir_tree}}", dir_tree)
    report = report.replace("{{func_len}}", str(func_len))
    report = report.replace("{{func_len_w}}", str(func_len_w))
    report = report.replace("{{line_len}}", str(line_len))
    report = report.replace("{{line_len_w}}", str(line_len_w))
    report = report.replace("{{doc_cov}}", str(doc_cov))
    report = report.replace("{{doc_cov_w}}", str(doc_cov_w))
    report = report.replace("{{type_ann}}", str(type_ann))
    report = report.replace("{{type_ann_w}}", str(type_ann_w))
    report = report.replace("{{comment_ratio}}", str(comment_ratio))
    report = report.replace("{{comment_ratio_w}}", str(comment_ratio_w))
    report = report.replace("{{todo_count}}", str(todo_count))
    report = report.replace("{{todo_w}}", str(todo_w))
    report = report.replace("{{import_quality}}", str(import_quality))
    report = report.replace("{{import_w}}", str(import_w))
    report = report.replace("{{file_struct}}", str(file_struct))
    report = report.replace("{{file_struct_w}}", str(file_struct_w))
    report = report.replace("{{issues_list}}", issues_text)
    report = report.replace("{{recommendations}}", recs)

    return report


def main():
    parser = argparse.ArgumentParser(description="Build project health report")
    parser.add_argument("scan_json", help="Path to scan_structure.py output JSON")
    parser.add_argument("quality_json", help="Path to check_quality.py output JSON")
    parser.add_argument("--template", "-t", default=None,
                        help="Path to report template (default: ../assets/report_template.md)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (default: print to stdout)")
    args = parser.parse_args()

    scan_data = json.loads(Path(args.scan_json).read_text(encoding="utf-8"))
    quality_data = json.loads(Path(args.quality_json).read_text(encoding="utf-8"))

    template_path = args.template or str(Path(__file__).parent.parent / "assets" / "report_template.md")
    template = Path(template_path).read_text(encoding="utf-8")

    report = build(scan_data, quality_data, template)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(args.output)  # print file path so caller knows where to read
    else:
        print(report)


if __name__ == "__main__":
    main()
