#!/usr/bin/env python3
"""
Phase 1: Project structure scan.
Always run first — cheap, no file parsing beyond directory walking.

Usage:
    python scripts/scan_structure.py <project_path>
Output: JSON to stdout
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Directories/files to skip
SKIP_DIRS = {"__pycache__", ".git", ".svn", ".hg", "node_modules",
             ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
             "dist", "build", ".eggs", "*.egg-info"}
SKIP_FILES = {".DS_Store", "Thumbs.db"}

# Files that indicate dependency management
DEP_FILES = ["requirements.txt", "setup.py", "setup.cfg",
             "pyproject.toml", "Pipfile", "Pipfile.lock", "poetry.lock"]

# Files that indicate project health
HEALTH_FILES = [".gitignore", "README.md", "README.rst",
                "Makefile", "Dockerfile", "docker-compose.yml",
                ".editorconfig", ".pre-commit-config.yaml"]


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.endswith(".egg-info")


def scan(project_path: str) -> dict:
    root = Path(project_path).resolve()
    if not root.is_dir():
        return {"status": "error", "error_code": 1,
                "message": f"目录不存在: {project_path}"}

    py_files = []
    dep_files_found = []
    health_files_found = []
    dir_tree_lines = []
    total_py_lines = 0
    dir_count = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skipped dirs in-place
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]

        rel_path = Path(dirpath).relative_to(root)
        depth = len(rel_path.parts) if rel_path != Path(".") else 0

        if depth <= 3:
            indent = "  " * depth
            name = rel_path.name if rel_path != Path(".") else root.name
            dir_tree_lines.append(f"{indent}{'├── ' if depth > 0 else ''}{name}/")
            dir_count += 1

        for fname in sorted(filenames):
            if fname in SKIP_FILES:
                continue

            file_path = Path(dirpath) / fname

            if fname.endswith(".py"):
                try:
                    line_count = len(file_path.read_text(encoding="utf-8").splitlines())
                except Exception:
                    line_count = 0
                total_py_lines += line_count
                py_files.append({
                    "path": str(file_path.relative_to(root)).replace("\\", "/"),
                    "lines": line_count,
                    "size_kb": round(file_path.stat().st_size / 1024, 1)
                })

            if fname in DEP_FILES:
                dep_files_found.append(fname)
            if fname in HEALTH_FILES:
                health_files_found.append(fname)

    py_files.sort(key=lambda f: f["lines"], reverse=True)

    return {
        "status": "success",
        "error_code": 0,
        "project_path": str(root.resolve()),
        "project_name": root.name,
        "py_file_count": len(py_files),
        "total_py_lines": total_py_lines,
        "dir_count": dir_count,
        "dep_files": dep_files_found,
        "health_files": health_files_found,
        "top_files": py_files[:10],
        "has_python_code": len(py_files) > 0,
        "dir_tree": "\n".join(dir_tree_lines[:30])  # Limit tree depth
    }


def main():
    parser = argparse.ArgumentParser(description="Scan Python project structure")
    parser.add_argument("input", help="Path to project directory")
    args = parser.parse_args()

    result = scan(args.input)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.exit(result["error_code"])


if __name__ == "__main__":
    main()
