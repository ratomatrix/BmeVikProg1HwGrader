---
name: grade-all-students
description: >-
  Batch-evaluate all student BMEVIHIAA01 (Programming 1) Phase 3 C homework
  submissions under input/, running grade-student for each subfolder and then
  summarize-gradings to produce output/grading-summary.md. Use when asked to
  grade all students or process the entire input/ directory.
---

# Grade All Students (BMEVIHIAA01)

Orchestrates batch grading for every student submission subfolder in `input/`, saving individual reports to `output/<student>.md` and generating `output/grading-summary.md`.

---

## Workflow

### 1. Run Batch Automated Checks (Recommended)
Run [batch_check_submissions.py](./scripts/batch_check_submissions.py) once to execute `check_submission.py` in parallel across all student subfolders in `input/`:

```powershell
python .agents/skills/grade-all-students/scripts/batch_check_submissions.py
```

Useful flags:
- `--skip-existing` — Skip students that already have `output/<student>.md` (ideal for resuming).
- `--include-dir "<path>"` — Override the default `./grading_includes` directory.
- `--skip-wsl` — Skip WSL2 Valgrind checks when running a quick Windows-only pass.
- `--json-out output/_batch_checks.json` — Save full JSON diagnostics for reference during manual review.

### 2. Grade Each Student (`grade-student`)
Iterate over every non-hidden subfolder `input/<student_folder>/` (skipping any already graded if resuming):

1. Follow the **`grade-student`** skill (`.agents/skills/grade-student/SKILL.md`) for that student:
   - Use the automated check results from Step 1 (and re-run `check_submission.py` with custom `--args` or `--stdin-text` if the student's program requires specific CLI arguments or interactive input).
   - Inspect the C source files manually (Section 1.B of `grading-checklist-and-rubric.md`, including **AI-generated code indicators**).
   - Inspect the documentation (`.pdf`, `.docx`, or `.zip` Doxygen HTML) against Section 2.
   - Apply the 10-point rubric (Section 3).
2. Save the student's report to `output/<student_folder>.md` (or `output/<student_folder>_<Student_Name>.md` if `<student_folder>` does not contain the student's name in any way and the name is known).

> [!TIP]
> If your AI agent supports parallel subagents, you may run independent `grade-student` evaluations concurrently; otherwise, process them sequentially in a loop.

### 3. Summarize All Gradings (`summarize-gradings`)
Once all student reports are saved in `output/`, follow the **`summarize-gradings`** skill (`.agents/skills/summarize-gradings/SKILL.md`) to collect all `output/*.md` reports (excluding `grading-summary.md`) and write the consolidated summary table to `output/grading-summary.md`.
