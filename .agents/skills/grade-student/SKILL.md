---
name: grade-student
description: >-
  Evaluate and grade a student's BMEVIHIAA01 (Programming 1) Phase 3 C homework
  submission folder containing source code, test files, and documentation.
  Use when asked to check, evaluate, or grade a student's assignment folder.
---

# Grade Programming 1 (BMEVIHIAA01) Phase 3 Homework

Evaluate a student's submission folder (C sources, test data, and documentation) using the workspace references:
- [environment-setup.md](../../../environment-setup.md) — Toolchain setup (MinGW GCC + WSL2 Valgrind)
- [grading-checklist-and-rubric.md](../../../grading-checklist-and-rubric.md) — Full checklist, documentation aspects, and 10-point rubric

---

## Workflow

> [!IMPORTANT]
> **Overwrite Guard:** Before starting or saving the report, check whether `output/<student_folder>.md` (or the target report file) already exists. If it does, **stop and ask the user for confirmation** before overwriting it (unless the user already explicitly asked to overwrite/re-grade).

### 1. Run Automated Checks
Execute [check_submission.py](./scripts/check_submission.py) on the student's folder (typically located under `input/<student_folder>`):

```powershell
python .agents/skills/grade-student/scripts/check_submission.py "input/<student_folder>"
```

Useful flags:
- `--args <arg1> <arg2> ...` — CLI arguments expected by the student's program (e.g., input `.txt` filenames).
- `--stdin-text "<input>"` or `--stdin-file "<path>"` — Standard input to feed during the Valgrind run.
- `--include-dir "<path>"` — Path containing `debugmalloc.h` if the student `#include`d it without submitting it.
- `--timeout 10` — Execution timeout in seconds (default: 10).

Review the script's output for:
- File inventory (`.c`/`.h`, `.txt`, `.pdf`/`.docx`/`.zip` documentation).
- MinGW GCC compilation status and warnings.
- WSL2 `gcc` + `valgrind` memory-leak and error summary.
- Static heuristic flags (e.g., `realloc`, `rewind`, `fseek(..., SEEK_END)`, `gets`, `conio.h`, `main()` length, `fopen`/`fclose` balance, comment ratio).

### 2. Inspect Code Manually
Read the student's `.c`/`.h` files and verify all manual aspects in **Section 1.B** of [grading-checklist-and-rubric.md](../../../grading-checklist-and-rubric.md):
- Single-pass sequential file reading (no OS file-size queries or double passes).
- Real dynamic data structure (no resizing arrays) and no duplicate/universal-struct storage.
- Proper decomposition (no ~100-line `main()`, I/O separated from logic, no code duplication).
- Comments (file, custom types/structs, and functions) and meaningful identifiers.
- **AI-generated code indicators** (Section 1.B.5 of [grading-checklist-and-rubric.md](../../../grading-checklist-and-rubric.md)): Watch for overly advanced C constructs for a 1st-year student, typical AI-written comment/boilerplate style, or mismatches between the code and the student's documentation.
- Run additional manual edge-case tests (missing file, spaces in input, multiple datasets) if not already covered by step 1.

### 3. Inspect Documentation
Verify the submitted `.pdf`, `.docx` (automatically converted to `.pdf` by `check_submission.py` via Microsoft Word when available), or `.zip` (Doxygen HTML) against **Section 2** of [grading-checklist-and-rubric.md](../../../grading-checklist-and-rubric.md):
- User documentation + Phase 1 specification.
- Programmer documentation + Phase 2 diagrams/algorithms matching actual code types and functions.
- Test documentation (text-form test data + edge-case coverage + expected vs. actual results).

### 4. Produce the Grade & Feedback
Apply the **10-point rubric** in **Section 3** of [grading-checklist-and-rubric.md](../../../grading-checklist-and-rubric.md):
1. Check **Hard Gates** first (compiles, commented, core requirements met).
2. Verify **Base 4 Points** criteria.
3. Score the **Remaining 6 Points** (capping Documentation Quality at **max 2 points**).
4. Summarize:
   - **Student & Topic** (student name/identifier and homework topic).
   - **Total Score (X / 10)** and Pass/Fail status (min 4 to pass).
   - **AI-Authorship Suspicion Highlight** (whenever suspicious): Place a prominent callout/section (e.g., `> [!WARNING] Suspected AI-Generated Code`) near the top of the report detailing the exact files, line ranges, and constructs/style patterns that appear AI-written or too advanced for a 1st-year student.
   - **Automated Check Results** (MinGW, Valgrind, static flags).
   - **Code & Documentation Findings** (strengths, deductions, and issues to fix).
   - **Suggested Defense (*Védés*) Questions** tailored to the student's implementation (including targeted authorship-verification questions for any AI-flagged constructs).
5. Save the grading report as `output/<student_folder>.md` (creating `output/` if it does not exist) unless the user specifies a different output path or asks for chat-only output.
