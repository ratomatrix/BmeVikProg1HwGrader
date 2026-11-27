#!/usr/bin/env python3
"""Automated Phase 3 homework checker for BMEVIHIAA01 (Windows + WSL2 Valgrind).

Runs non-destructive checks on a student's submission folder:
  1. Inventory of source, test data, and documentation files.
  2. Static heuristic scan of C sources (banned/suspicious patterns, main() size, comments).
  3. MinGW GCC compilation check on Windows (in a temporary directory).
  4. WSL2 GCC compilation + dos2unix + Valgrind leak/error check (in a temporary WSL dir).

Compatible with Python 3.11+ (standard library only).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SUSPICIOUS_PATTERNS: list[tuple[str, str]] = [
    (r"\bgets\s*\(", "Unsafe gets() call"),
    (r"\brewind\s*\(", "rewind() detected (check single-pass file read rule)"),
    (r"\bfseek\s*\([^)]*SEEK_END", "fseek(..., SEEK_END) detected (check file-size query rule)"),
    (r"\bstat\s*\(", "stat() detected (check OS file-size query rule)"),
    (r"\brealloc\s*\(", "realloc() detected (verify not used as main dynamic data structure)"),
    (r'#\s*include\s*[<"]conio\.h[>"]', "Non-standard <conio.h>"),
    (r'#\s*include\s*[<"]windows\.h[>"]', "Non-standard <windows.h>"),
    (r'#\s*include\s*[<"]debugmalloc\.h[>"]', "Uses debugmalloc.h"),
]


def run_cmd(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    timeout: int = 15,
) -> tuple[int, str, str, bool]:
    """Run a subprocess and return (returncode, stdout, stderr, timed_out)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
            False,
        )
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else ""
        err = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else ""
        return (-1, out, err, True)
    except FileNotFoundError as exc:
        return (-127, "", str(exc), False)


def estimate_main_lines(source: str) -> int | None:
    """Heuristically count lines inside main(...) brace block."""
    match = re.search(r"\bint\s+main\s*\([^)]*\)\s*\{", source)
    if not match:
        match = re.search(r"\bvoid\s+main\s*\([^)]*\)\s*\{", source)
    if not match:
        return None
    start_idx = match.end() - 1
    depth = 0
    lines = 1
    for ch in source[start_idx:]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return lines
        elif ch == "\n":
            lines += 1
    return lines


def scan_c_files(c_files: list[Path], h_files: list[Path]) -> dict[str, Any]:
    """Perform static heuristic checks on C source and header files."""
    findings: list[dict[str, Any]] = []
    total_lines = 0
    comment_lines = 0
    fopen_count = 0
    fclose_count = 0
    main_lines: dict[str, int] = {}

    for path in [*c_files, *h_files]:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        total_lines += len(lines)
        comment_lines += sum(
            1 for ln in lines if re.search(r"(^\s*//|/\*|\*/)", ln)
        )
        fopen_count += len(re.findall(r"\bfopen\s*\(", text))
        fclose_count += len(re.findall(r"\bfclose\s*\(", text))

        if path.suffix == ".c":
            m_len = estimate_main_lines(text)
            if m_len is not None:
                main_lines[path.name] = m_len

        for lineno, line in enumerate(lines, start=1):
            for pattern, desc in SUSPICIOUS_PATTERNS:
                if re.search(pattern, line):
                    findings.append(
                        {"file": path.name, "line": lineno, "issue": desc, "code": line.strip()}
                    )

    return {
        "total_lines": total_lines,
        "comment_lines": comment_lines,
        "fopen_count": fopen_count,
        "fclose_count": fclose_count,
        "main_lines": main_lines,
        "findings": findings,
    }


def check_mingw(
    c_files: list[Path], h_files: list[Path], include_dir: Path | None
) -> dict[str, Any]:
    """Compile student C files with MinGW GCC in a temp directory."""
    if not c_files:
        return {"status": "SKIP", "reason": "No .c files found"}

    with tempfile.TemporaryDirectory(prefix="prog1_mingw_") as tmp:
        tmp_path = Path(tmp)
        for f in [*c_files, *h_files]:
            shutil.copy2(f, tmp_path / f.name)

        base_cmd = ["gcc", *[f.name for f in c_files], "-Wall", "-Wextra"]
        if include_dir:
            base_cmd.extend(["-I", str(include_dir)])

        rc_strict, out_s, err_s, _ = run_cmd([*base_cmd, "-Werror", "-o", "hazi_strict.exe"], cwd=tmp_path)
        if rc_strict == 0:
            return {"status": "PASS", "strict_werror": True, "output": (out_s + err_s).strip()}

        rc_warn, out_w, err_w, _ = run_cmd([*base_cmd, "-o", "hazi.exe"], cwd=tmp_path)
        return {
            "status": "WARN" if rc_warn == 0 else "FAIL",
            "strict_werror": False,
            "returncode": rc_warn,
            "output": (out_w + err_w).strip(),
        }


def to_wsl_path(win_path: Path) -> str:
    """Convert a Windows path to a WSL /mnt/... path using wslpath."""
    rc, out, _, _ = run_cmd(["wsl", "wslpath", "-a", str(win_path.resolve())])
    if rc == 0 and out.strip():
        return out.strip()
    drive = win_path.resolve().drive.rstrip(":").lower()
    rest = win_path.resolve().as_posix().split(":", 1)[-1]
    return f"/mnt/{drive}{rest}"


def parse_valgrind(stderr: str) -> dict[str, Any]:
    """Extract key leak and error counts from Valgrind output."""
    summary: dict[str, Any] = {}
    for key in ("definitely lost", "indirectly lost", "possibly lost", "still reachable"):
        m = re.search(rf"{key}:\s*([\d,]+)\s+bytes\s+in\s+([\d,]+)\s+blocks", stderr)
        if m:
            summary[key] = {"bytes": int(m.group(1).replace(",", "")), "blocks": int(m.group(2).replace(",", ""))}
    err_m = re.search(r"ERROR SUMMARY:\s*(\d+)\s+errors", stderr)
    if err_m:
        summary["errors"] = int(err_m.group(1))
    return summary


def check_wsl_valgrind(
    sub_dir: Path,
    c_files: list[Path],
    cli_args: list[str],
    stdin_bytes: bytes | None,
    include_dir: Path | None,
    timeout: int,
) -> dict[str, Any]:
    """Copy submission to a temp WSL dir, run dos2unix, compile with gcc, and run Valgrind."""
    if not c_files:
        return {"status": "SKIP", "reason": "No .c files found"}

    wsl_sub = to_wsl_path(sub_dir)
    wsl_inc = to_wsl_path(include_dir) if include_dir else None

    c_names = " ".join(shlex.quote(f.name) for f in c_files)
    inc_flag = f"-I{shlex.quote(wsl_inc)}" if wsl_inc else ""
    args_str = " ".join(shlex.quote(a) for a in cli_args)

    compile_script = (
        f"set -e; "
        f"WORK=$(mktemp -d /tmp/prog1_vg_XXXXXX); "
        f"trap 'rm -rf \"$WORK\"' EXIT; "
        f"cp -r {shlex.quote(wsl_sub)}/. \"$WORK/\"; "
        f"cd \"$WORK\"; "
        f"if command -v dos2unix >/dev/null 2>&1; then dos2unix -q *.txt 2>/dev/null || true; fi; "
        f"gcc -Wall -Wextra -g -O0 {inc_flag} {c_names} -o hazi_vg -lm; "
        f"valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes --error-exitcode=42 ./hazi_vg {args_str}"
    )

    rc, out, err, timed_out = run_cmd(
        ["wsl", "bash", "-lc", compile_script],
        input_bytes=stdin_bytes,
        timeout=timeout,
    )

    if timed_out:
        return {"status": "TIMEOUT", "timeout_seconds": timeout, "stdout": out, "stderr": err}

    vg_stats = parse_valgrind(err)
    has_leaks = any(
        vg_stats.get(k, {}).get("bytes", 0) > 0
        for k in ("definitely lost", "indirectly lost", "possibly lost")
    )
    has_errors = vg_stats.get("errors", 0) > 0

    if rc == 0 and not has_leaks and not has_errors:
        status = "PASS"
    elif rc == 42 or has_leaks or has_errors:
        status = "FAIL"
    else:
        status = f"EXIT_{rc}"

    return {
        "status": status,
        "returncode": rc,
        "valgrind": vg_stats,
        "stdout": out[:2000],
        "stderr": err[-4000:],
    }


def convert_docx_to_pdf(doc_files: list[Path], timeout: int = 30) -> list[dict[str, str]]:
    """Convert .docx documentation files to .pdf via Microsoft Word COM on Windows."""
    docx_files = [p for p in doc_files if p.suffix.lower() == ".docx"]
    if not docx_files:
        return []

    results: list[dict[str, str]] = []
    if sys.platform != "win32" or not shutil.which("powershell"):
        for p in docx_files:
            results.append({"docx": p.name, "pdf": p.with_suffix(".pdf").name, "status": "SKIPPED (Windows PowerShell required)"})
        return results

    ps_script = (
        "$word = $null; $doc = $null; "
        "try { "
        "  $word = New-Object -ComObject Word.Application; "
        "  $word.Visible = $false; "
        "  $word.DisplayAlerts = 0; "
        "  $doc = $word.Documents.Open($env:DOCX_PATH, $false, $true); "
        "  $doc.SaveAs([ref]$env:PDF_PATH, [ref]17); "
        "} finally { "
        "  if ($doc -ne $null) { $doc.Close([ref]$false) } "
        "  if ($word -ne $null) { $word.Quit() } "
        "}"
    )

    for docx_path in docx_files:
        pdf_path = docx_path.with_suffix(".pdf")
        if pdf_path.exists():
            results.append({"docx": docx_path.name, "pdf": pdf_path.name, "status": "EXISTS"})
            continue

        env = os.environ.copy()
        env["DOCX_PATH"] = str(docx_path.resolve())
        env["PDF_PATH"] = str(pdf_path.resolve())
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode == 0 and pdf_path.is_file():
                results.append({"docx": docx_path.name, "pdf": pdf_path.name, "status": "CONVERTED"})
            else:
                err = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
                results.append({"docx": docx_path.name, "pdf": pdf_path.name, "status": f"FAILED ({err[:120]})"})
        except subprocess.TimeoutExpired:
            results.append({"docx": docx_path.name, "pdf": pdf_path.name, "status": f"TIMEOUT ({timeout}s)"})
        except Exception as exc:
            results.append({"docx": docx_path.name, "pdf": pdf_path.name, "status": f"ERROR ({exc})"})

    return results


def print_human_report(report: dict[str, Any]) -> None:
    """Print a concise human-readable summary of all checks."""
    inv = report["inventory"]
    print(f"=== Submission: {report['submission_dir']} ===")
    print(f"Sources (.c): {', '.join(inv['c_files']) or 'NONE'}")
    print(f"Headers (.h): {', '.join(inv['h_files']) or 'none'}")
    print(f"Text data (.txt): {', '.join(inv['txt_files']) or 'NONE'}")
    print(f"Docs (.pdf/.docx/.zip): {', '.join(inv['doc_files']) or 'NONE'}")
    for conv in report.get("docx_conversion", []):
        print(f"  [DOCX->PDF] {conv['docx']} -> {conv['pdf']}: {conv['status']}")

    st = report["static_scan"]
    print("\n--- Static Heuristic Scan ---")
    print(
        f"Lines: {st['total_lines']} (comment lines: {st['comment_lines']}) | "
        f"fopen: {st['fopen_count']}, fclose: {st['fclose_count']}"
    )
    if st["main_lines"]:
        print(f"Estimated main() lines: {st['main_lines']}")
    if st["findings"]:
        for f in st["findings"]:
            print(f"  [!] {f['file']}:{f['line']} - {f['issue']}: {f['code']}")
    else:
        print("  No suspicious patterns matched.")

    mg = report["mingw"]
    print(f"\n--- MinGW GCC Compile: {mg['status']} ---")
    if mg.get("output"):
        print(mg["output"])

    vg = report["wsl_valgrind"]
    print(f"\n--- WSL2 GCC + Valgrind: {vg['status']} ---")
    if "valgrind" in vg and vg["valgrind"]:
        print(f"Valgrind summary: {vg['valgrind']}")
    if vg["status"] != "PASS" and vg.get("stderr"):
        print("Valgrind/Compiler stderr (tail):")
        print(vg["stderr"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a student's Prog1 Phase 3 submission.")
    parser.add_argument("submission_dir", type=Path, help="Path to student submission folder")
    parser.add_argument("--args", nargs="*", default=[], help="CLI arguments for the compiled program")
    parser.add_argument("--stdin-text", default=None, help="String to feed as stdin")
    parser.add_argument("--stdin-file", type=Path, default=None, help="File to feed as stdin")
    parser.add_argument(
        "--include-dir",
        type=Path,
        default=None,
        help="Extra include dir (defaults to ./grading_includes if present)",
    )
    parser.add_argument("--timeout", type=int, default=10, help="Execution timeout in seconds (default: 10)")
    parser.add_argument("--skip-wsl", action="store_true", help="Skip WSL2 Valgrind check")
    parser.add_argument("--no-docx-convert", action="store_true", help="Skip .docx to .pdf conversion via Word")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    sub_dir = args.submission_dir.resolve()
    if not sub_dir.is_dir():
        print(f"Error: not a directory: {sub_dir}", file=sys.stderr)
        return 2

    c_files = sorted(sub_dir.glob("*.c"))
    h_files = sorted(sub_dir.glob("*.h"))
    txt_files = sorted(sub_dir.glob("*.txt"))
    doc_files = sorted([*sub_dir.glob("*.pdf"), *sub_dir.glob("*.docx"), *sub_dir.glob("*.zip")])
    docx_conversion = [] if args.no_docx_convert else convert_docx_to_pdf(doc_files)
    if docx_conversion:
        doc_files = sorted([*sub_dir.glob("*.pdf"), *sub_dir.glob("*.docx"), *sub_dir.glob("*.zip")])

    include_dir = args.include_dir
    if include_dir is None:
        default_inc = Path(__file__).resolve().parents[4] / "grading_includes"
        if default_inc.is_dir():
            include_dir = default_inc

    stdin_bytes: bytes | None = None
    if args.stdin_file:
        stdin_bytes = args.stdin_file.read_bytes()
    elif args.stdin_text is not None:
        stdin_bytes = args.stdin_text.encode("utf-8")

    report: dict[str, Any] = {
        "submission_dir": str(sub_dir),
        "inventory": {
            "c_files": [p.name for p in c_files],
            "h_files": [p.name for p in h_files],
            "txt_files": [p.name for p in txt_files],
            "doc_files": [p.name for p in doc_files],
        },
        "docx_conversion": docx_conversion,
        "static_scan": scan_c_files(c_files, h_files),
        "mingw": check_mingw(c_files, h_files, include_dir),
        "wsl_valgrind": (
            {"status": "SKIP", "reason": "--skip-wsl"}
            if args.skip_wsl
            else check_wsl_valgrind(sub_dir, c_files, args.args, stdin_bytes, include_dir, args.timeout)
        ),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
