#!/usr/bin/env python3
"""Batch automated pre-checker for all student folders in input/.

Runs check_submission.py --json in parallel across every student subfolder in
input/ and prints a concise summary table + per-student diagnostics.

Compatible with Python 3.11+ (standard library only).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
CHECK_SCRIPT = REPO_ROOT / ".agents" / "skills" / "grade-student" / "scripts" / "check_submission.py"


def run_single_check(
    student_dir: Path,
    include_dir: Path | None,
    skip_wsl: bool,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    """Run check_submission.py --json on one student folder."""
    cmd = [sys.executable, str(CHECK_SCRIPT), str(student_dir), "--json", "--timeout", str(timeout)]
    if include_dir is not None:
        cmd.extend(["--include-dir", str(include_dir)])
    if skip_wsl:
        cmd.append("--skip-wsl")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
        if not proc.stdout.strip():
            return student_dir.name, {
                "error": proc.stderr.strip() or f"Empty output (exit code {proc.returncode})"
            }
        return student_dir.name, json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return student_dir.name, {"error": f"Batch worker timed out after {timeout + 30}s"}
    except Exception as exc:
        return student_dir.name, {"error": str(exc)}


def format_table(rows: list[list[str]], headers: list[str]) -> str:
    """Format a simple Markdown-compatible table."""
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    lines = [
        "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |",
        sep,
    ]
    for r in rows:
        lines.append("| " + " | ".join(r[i].ljust(widths[i]) for i, _ in enumerate(headers)) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch pre-check all student submissions in input/.")
    parser.add_argument("--input-dir", type=Path, default=REPO_ROOT / "input", help="Input directory (default: input/)")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "output", help="Output directory (default: output/)")
    parser.add_argument("--include-dir", type=Path, default=None, help="Extra include dir (defaults to ./grading_includes if present)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip students that already have output/<student>.md")
    parser.add_argument("--skip-wsl", action="store_true", help="Skip WSL2 Valgrind checks")
    parser.add_argument("--timeout", type=int, default=10, help="Per-student execution timeout in seconds (default: 10)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel worker threads (default: 4)")
    parser.add_argument("--json", action="store_true", help="Print full JSON results instead of summary table")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional path to save full JSON results")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"Error: input directory not found: {args.input_dir}", file=sys.stderr)
        return 2

    include_dir = args.include_dir
    if include_dir is None:
        default_inc = REPO_ROOT / "grading_includes"
        if default_inc.is_dir():
            include_dir = default_inc

    student_dirs = sorted(
        p for p in args.input_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    if not student_dirs:
        print(f"No student subfolders found in {args.input_dir}")
        return 0

    if args.skip_existing and args.output_dir.is_dir():
        pending = [p for p in student_dirs if not (args.output_dir / f"{p.name}.md").is_file()]
        skipped = len(student_dirs) - len(pending)
        if skipped:
            print(f"Skipping {skipped} already-graded student(s) with existing reports in {args.output_dir}.")
        student_dirs = pending

    if not student_dirs:
        print("All students already have reports.")
        return 0

    results: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(run_single_check, d, include_dir, args.skip_wsl, args.timeout): d.name
            for d in student_dirs
        }
        for fut in concurrent.futures.as_completed(futures):
            name, data = fut.result()
            results[name] = data

    ordered_results = {name: results[name] for name in sorted(results)}

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(ordered_results, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(ordered_results, indent=2))
        return 0

    rows: list[list[str]] = []
    for name, data in ordered_results.items():
        if "error" in data:
            rows.append([name, "?", "?", "?", "?", "ERROR", "ERROR", data["error"][:40]])
            continue
        inv = data["inventory"]
        st = data["static_scan"]
        mg = data["mingw"]["status"]
        vg = data["wsl_valgrind"]["status"]
        report_exists = "yes" if (args.output_dir / f"{name}.md").is_file() else "no"
        rows.append([
            name,
            str(len(inv["c_files"])),
            str(len(inv["txt_files"])),
            str(len(inv["doc_files"])),
            str(len(st["findings"])),
            mg,
            vg,
            report_exists,
        ])

    headers = ["Student", ".c", ".txt", "Docs", "Flags", "MinGW", "Valgrind", "Report"]
    print(format_table(rows, headers))

    print("\n--- Notable Findings & Errors ---")
    for name, data in ordered_results.items():
        if "error" in data:
            print(f"\n[{name}] ERROR: {data['error']}")
            continue
        findings = data["static_scan"]["findings"]
        mg = data["mingw"]
        vg = data["wsl_valgrind"]
        if findings or mg["status"] != "PASS" or vg["status"] not in ("PASS", "SKIPPED"):
            print(f"\n[{name}]")
            for f in findings:
                print(f"  - Static: {f['file']}:{f['line']} {f['issue']}")
            if mg["status"] != "PASS":
                print(f"  - MinGW ({mg['status']}): {mg.get('output', '')[:200]}")
            if vg["status"] not in ("PASS", "SKIPPED"):
                print(f"  - Valgrind ({vg['status']}): {vg.get('valgrind') or vg.get('stderr', '')[:200]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
