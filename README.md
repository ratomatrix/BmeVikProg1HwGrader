# BME VIK Prog1 Homework Grading Toolkit (BMEVIHIAA01)

Tools, checklists, and grading guidelines for evaluating **1st-year Programming 1 (A programozás alapjai 1 — BMEVIHIAA01)** C homework submissions on Windows using **MinGW GCC** and **WSL2 (GCC + Valgrind)**.

It combines the power of deterministic tools (like mentioned above) with AI-based support for human-like understanding of the overall tasks.

> [!NOTE]
> This toolkit is designed to be **AI-vendor-independent** (using the open `.agents/skills/*/SKILL.md` format alongside a standalone, stdlib-only Python CLI), and was mainly written by **Gemini 4 Hydrogen** (as of November 2026).

---

## Repository Structure

| File / Folder | Purpose |
| :--- | :--- |
| [environment-setup.md](./environment-setup.md) | Step-by-step setup for MinGW GCC, Python 3.11+, WSL2 (`gcc`, `valgrind`, `dos2unix`, `cppcheck`), `debugmalloc.h`, and alternative Windows tools. |
| [grading-checklist-and-rubric.md](./grading-checklist-and-rubric.md) | Code verification commands, manual code & documentation check aspects, and the 10-point grading rubric (4-point pass threshold, max 2 points for documentation). |
| [requirements/](./requirements/) | Original BMEVIHIAA01 course requirement PDFs (`hf_kovetelmenyek_*.pdf`) used to extract the `.md` checklist and rubric files. |
| [grading_includes/](./grading_includes/) | Shared grading headers (including BME VIK InfoC's `debugmalloc.h`) used with `--include-dir` when a student `#include`s `debugmalloc.h` without bundling it. |
| [.agents/skills/grade-student/SKILL.md](./.agents/skills/grade-student/SKILL.md) | AI-vendor-independent `SKILL.md` workspace skill that orchestrates automated and manual grading of a student's submission folder. |
| [.agents/skills/grade-student/scripts/check_submission.py](./.agents/skills/grade-student/scripts/check_submission.py) | Standalone Python 3.11+ script (stdlib-only) that runs file inventory, static C pattern scans, MinGW compilation, and WSL2 Valgrind memory-leak checks. |
| [.agents/skills/grade-all-students/SKILL.md](./.agents/skills/grade-all-students/SKILL.md) | AI-vendor-independent `SKILL.md` workspace skill that runs `grade-student` across all `input/` subfolders and then invokes `summarize-gradings`. |
| [.agents/skills/grade-all-students/scripts/batch_check_submissions.py](./.agents/skills/grade-all-students/scripts/batch_check_submissions.py) | Standalone Python 3.11+ batch runner that executes `check_submission.py` in parallel across all student folders in `input/`. |
| [.agents/skills/summarize-gradings/SKILL.md](./.agents/skills/summarize-gradings/SKILL.md) | AI-vendor-independent `SKILL.md` workspace skill that collects `grade-student` reports and builds a summary table (student, topic, grade, and key remarks). |
| [.gitignore](./.gitignore) | Ignores `input/`, `output/`, compiled binaries, and Python caches so student data is never committed. |
| [LICENSE](./LICENSE) | MIT License for the toolkit scripts and documentation. |

---

## Folder Convention (`input/` & `output/`)

Both `input/` and `output/` are listed in `.gitignore` to keep student submissions and grading reports private:

- **`input/<student_folder>/`**: Place each student's submission folder under `input/` (e.g., `input/kiss_janos_ABC123/`).
- **`output/`**: Individual grading reports are saved here (e.g., `output/kiss_janos_ABC123.md`), along with the aggregated summary table (`output/grading-summary.md`).

> [!NOTE]
> When downloading submissions from Moodle (*Download submissions in folders*), extract each student's folder into `input/<student_folder>/`. If code and documentation were uploaded to separate Moodle activities, merge each student's documentation file (`.pdf`, `.docx`, or `.zip`) into their `input/<student_folder>/` directory.

---

## Quick Start

1. **Set up your environment** by following [environment-setup.md](./environment-setup.md).
2. **Place student submissions** in subfolders under `input/` (e.g., `input/<student_folder>/`).
3. **Run automated checks** on a student's submission folder:
   ```powershell
   python .agents/skills/grade-student/scripts/check_submission.py "input/<student_folder>"
   ```
   *(Pass `--args ...`, `--stdin-text "..."`, or `--include-dir "./grading_includes"` as needed; run with `--help` for all options.)*
4. **Complete manual code, documentation, and defense checks** using [grading-checklist-and-rubric.md](./grading-checklist-and-rubric.md) (or invoke the `grade-student` skill), saving reports to `output/<student_folder>.md`.
5. **Or batch-grade everything** by running `python .agents/skills/grade-all-students/scripts/batch_check_submissions.py` (or invoking the `grade-all-students` skill), which evaluates all `input/` subfolders and produces `output/grading-summary.md` via `summarize-gradings`.

---

## Authors

*Initiated and created by Tamás Rózsa, 2026.*
