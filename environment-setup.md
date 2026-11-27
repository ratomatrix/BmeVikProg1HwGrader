# Grading Environment Setup (WSL + GCC + Valgrind)

This guide sets up the grading environment for **BMEVIHIAA01 (A programozás alapjai 1)** Phase 3 C homework submissions on Windows, using **MinGW GCC** (to verify the official compilation requirement), **Python 3.11+** (to run the automated grading script), and **WSL2 with GCC + Valgrind** (for memory-leak and runtime verification).

---

## 1. AI / Agentic Workflow Setup (Primary Options)

It is proposed to install and use VS Code as the main application for the agentic workflow.

The repository's grading skills live under `.agents/skills/` using the open, AI-vendor-independent `SKILL.md` convention. The two primary ways to run the agentic grading workflow are:

1. **VS Code + Antigravity extension** *(or Antigravity IDE)*:
   - Open the `BmeVikProg1HwGrader` folder in VS Code with the Antigravity extension enabled (or directly in Antigravity).
   - Workspace skills (`grade-student`, `grade-all-students`, `summarize-gradings`) are discovered automatically from `.agents/skills/`.
2. **VS Code + Codex extension** *(or Codex CLI)*:
   - Open the `BmeVikProg1HwGrader` folder in VS Code with the Codex extension (or launch `codex` from the integrated terminal in the repo root).
   - Codex natively supports `.agents/skills/*/SKILL.md` workspace skills.

> [!TIP]
> **Once this step is done, you can let the AI handle the rest of the setup!** Ask your agent to check what is missing and install/configure the toolchain in **Section 2** (MinGW GCC, Python 3.11+, WSL2 Ubuntu, `valgrind`, `dos2unix`, etc.) on your machine.

*(Other `SKILL.md`-compatible agents such as Claude Code, Cursor, or Gemini CLI also work with the same `.agents/skills/` directory, and `check_submission.py` / `batch_check_submissions.py` can always be run standalone without an AI agent.)*

### Typical Prompts
- **Environment check / setup**: *"Check my environment against `environment-setup.md` and help install anything missing."*
- **Single student**: *"Grade `input/<student_folder>`"* (uses `grade-student`, saves `output/<student_folder>.md`).
- **Batch grading**: *"Grade all students in `input/`"* (uses `grade-all-students` → `grade-student` → `summarize-gradings`, producing `output/grading-summary.md`).
- **Summary only**: *"Summarize the grading reports in `output/`"* (uses `summarize-gradings`).

*(Optional on Windows: if **Microsoft Word** is installed, `check_submission.py` automatically converts `.docx` documentation to `.pdf` so diagrams can be reviewed visually.)*

---

## 2. Toolchain Setup (Windows + WSL2)

### A. Windows Side: MinGW GCC & Python 3.11+
1. **MinGW-w64 GCC**: Students' programs must compile with MinGW GCC. Ensure `gcc` is available in PowerShell:
   ```powershell
   gcc --version
   ```
   If not installed, install via [MSYS2](https://www.msys2.org/) (`pacman -S mingw-w64-ucrt-x86_64-gcc`) and add `C:\msys64\ucrt64\bin` to your Windows `PATH`.

2. **Python 3.11+**: Required to run the automated submission checker script (`check_submission.py`, standard-library only — no `pip install` needed). Verify in PowerShell:
   ```powershell
   python --version
   ```
   If not installed or older than 3.11, install via `winget`:
   ```powershell
   winget install Python.Python.3.11
   ```

### B. WSL2 Side: Ubuntu + GCC + Valgrind + Helpers
1. Open PowerShell as Administrator and install WSL2 (if not already installed):
   ```powershell
   wsl --install
   ```
2. Open the Ubuntu (WSL2) terminal and install the required tools:
   ```bash
   sudo apt update
   sudo apt install -y gcc valgrind dos2unix cppcheck
   ```
   - `gcc`: Compiles C submissions with debug symbols and strict warnings/sanitizers.
   - `valgrind`: Detects memory leaks, invalid reads/writes, double-frees, and uninitialized memory usage.
   - `dos2unix`: **Essential** for converting student-uploaded `.txt` test files from Windows (`\r\n`) to Unix (`\n`) line endings before running under Linux/WSL.
   - `cppcheck`: Optional fast static analyzer for catching unclosed `FILE*` handles, null dereferences, and dead code.

3. **Recommended `~/.valgrindrc` config** (in WSL2):
   Create `~/.valgrindrc` so you don't have to type the full flags every time:
   ```text
   --leak-check=full
   --show-leak-kinds=all
   --track-origins=yes
   ```
   Verify installation:
   ```bash
   gcc --version
   valgrind --version
   dos2unix --version
   ```

### C. `debugmalloc.h` (Already Included)
Per the instructor guidelines (`4.x. Oktatói tudnivalók`), many students leave `#include "debugmalloc.h"` in their `.c` files without submitting `debugmalloc.h`.
- A copy downloaded from the **infoc** portal is already included in this repository at [grading_includes/debugmalloc.h](./grading_includes/debugmalloc.h).
- Both `check_submission.py` and `batch_check_submissions.py` automatically use `./grading_includes` as `--include-dir` when present (or you can pass `-I./grading_includes` manually when compiling) without editing students' source files.

---

## 3. Accessing Windows Files from WSL2

Your Windows workspace `C:\Users\<user>\Repos\BmeVikProg1HwGrader` is automatically mounted in WSL2 at:
```bash
cd /mnt/c/Users/<user>/Repos/BmeVikProg1HwGrader
```
*(Tip: For faster I/O when running Valgrind on large datasets, you can copy a student's folder to `/tmp/grade_tmp` inside WSL2, run tests there, and delete it afterwards.)*

---

## 4. Alternative Options (For Reference)

If WSL2 cannot be used for a particular submission (for example, if a student heavily relies on Windows-only headers like `<windows.h>` or `<conio.h>` that cannot easily be stripped):

1. **Native Windows: Dr. Memory**
   - Download from [drmemory.org](https://drmemory.org/).
   - Compile with MinGW using `-g -O0`, then run:
     ```powershell
     drmemory -brief -- .\hazi.exe <args>
     ```
   - Pros: Runs natively on Windows `.exe` binaries. Cons: Slightly noisier than Valgrind on Windows CRT allocations.

2. **LLVM-MinGW with AddressSanitizer + LeakSanitizer (`-fsanitize=address,undefined`)**
   - Standard MinGW-w64 GCC on Windows has limited ASan/LSan support, whereas **LLVM-MinGW** (`clang`) supports `-fsanitize=address,undefined` on Windows.
   - Pros: Very fast runtime checks. Cons: Separate toolchain from standard MinGW GCC.

3. **Static Analysis Only (`cppcheck` on Windows)**
   - Install via `winget install Cppcheck.Cppcheck`.
   - Useful as a quick pre-screen for resource leaks (`fopen` without `fclose`) and obvious bugs, but **does not** replace dynamic leak checking (Valgrind).
