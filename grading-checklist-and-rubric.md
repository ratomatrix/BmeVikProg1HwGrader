# Phase 3 Grading Checklist, Commands & Pointing Guideline

This document covers the **code verification commands**, **manual code inspection aspects**, **documentation check aspects**, and the **10-point grading guideline** for **BMEVIHIAA01** Phase 3 homework.

---

## 1. Code Checks (Commands & Technical Aspects)

### A. Commands to Run

#### Step 1: Verify MinGW GCC Compilation (Windows PowerShell)
Check that the submission compiles cleanly with MinGW GCC as required by `4. Leadás`:
```powershell
# Single file
gcc hazi.c -Wall -Werror -o hazi.exe

# Multiple files
gcc *.c -Wall -Werror -o hazi.exe
```
> [!NOTE]
> - **C standard**: Not tied to C90 (`for (int ...)`, declarations anywhere, `//` comments, `long long` are all allowed).
> - **Missing `debugmalloc.h`**: If the student left `#include "debugmalloc.h"` in the code, add `-I<path-to-debugmalloc-dir>` when compiling, or comment it out during Valgrind testing so Valgrind tracks allocations directly.
> - **Non-standard headers** (`conio.h`, `windows.h`): Try to compile or strip them out (e.g., `conio.h` is often only used for `getch()`).
> - If `-Werror` fails only on minor warnings, test without `-Werror` to see if it compiles and runs, and note the warnings for pointing.

#### Step 2: Prepare Text Files & Compile in WSL2 (Bash)
```bash
# 1. Fix Windows CRLF line endings in student-submitted test files
dos2unix *.txt

# 2. Compile for Valgrind (include -I~/grading_includes if debugmalloc.h is needed)
gcc -Wall -Wextra -g -O0 *.c -o hazi_vg

# 3. (Optional) Compile with AddressSanitizer + UBSan for fast overflow/UB checks
gcc -Wall -Wextra -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer *.c -o hazi_asan
```

#### Step 3: Run Memory Leak & Runtime Checks (WSL2)
```bash
# Run with Valgrind (uses ~/.valgrindrc or explicit flags)
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./hazi_vg <cli_args_if_any>

# Run ASan/UBSan build (if compiled)
./hazi_asan <cli_args_if_any>
```
**Runtime test cases to execute:**
- **Normal dataset(s)**: Pass expected CLI arguments (do **not** penalize if the program doesn't print a fancy `Usage:` message).
- **Multiple datasets**: Verify it doesn't only work on one hardcoded dataset or filename.
- **Spaces in input**: If the program reads names, addresses, or titles from `stdin` or files, test with multi-word strings containing spaces.
- **Missing / invalid file**: Pass a nonexistent filename — the program must exit cleanly without crashing (and without leaking already-allocated memory).
- **Case-sensitive filenames**: If the student developed on Windows and a file open fails on WSL2 solely due to filename casing (e.g., `"Adatok.txt"` vs. `"adatok.txt"`), do **not** penalize it (per `4.x. Oktatói tudnivalók`).
- **Invalid user input**: Test invalid menu choices (e.g., `-83`) or edge-case inputs (empty file, 1-element file).

#### Step 4: (Optional) Quick Static Check
```bash
cppcheck --enable=warning,performance,portability --inconclusive --quiet .
```

---

### B. Code Aspects to Check (Manual Inspection)

1. **Memory & Resource Safety**
   - Valgrind reports `0 bytes in 0 blocks` lost (`definitely lost`, `indirectly lost`, `possibly lost` = 0) on both normal execution and error-exit paths.
   - No invalid reads/writes, use-after-free, or uninitialized value errors.
   - Every `fopen()` is checked for `NULL` and paired with `fclose()`.

2. **Hard Course & Algorithmic Requirements**
   - **Text file handling**: Reads/writes text files properly.
   - **Single-pass sequential read**: Files are read **only once** sequentially. No `rewind()`, no double `fopen()` pass to count lines first, and **no** querying file size via OS (`stat()`) or `fseek(..., SEEK_END)` + `ftell()`.
   - **Valid dynamic data structure**: Uses a real dynamic data structure (linked list, comb list / *fésűs lista*, tree, hash table, etc.). **A dynamically resizing array (`realloc` array) is NOT accepted.**
   - **No duplicate storage**: Data is linked/referenced rather than stored redundantly multiple times.
   - **No universal catch-all type**: Purpose-built `struct`s matching the domain (not one generic type for everything).
   - **String processing**: Proper C string handling (handles spaces where expected, no `gets()`).

3. **Code Structure & Decomposition**
   - **No monolithic `main()`**: A ~100-line `main()` is not acceptable.
   - **Single-responsibility functions**: Separate file I/O, data structure building, searching/solving, and user interaction (do not mix input prompting, file reading, filtering, and output writing in one function).
   - **No unnecessary code duplication**: Repeated logic is factored into functions, loops, or arrays.

4. **Comments & Readability**
   - **File-level comments**: What the program/file does, author, etc.
   - **Type/struct comments**: Role of every custom `struct` / `typedef`.
   - **Function comments**: Parameters, return value, and behavior of every function.
   - **Meaningful identifiers** & consistent formatting. *(Completely uncommented code must not be accepted; do not expect professional style, just genuine effort to explain.)*

5. **AI-Generated Code Indicators (Authorship Check)**
   - **Overly complex / non-course constructs for a 1st-year student**: Unnecessary `void *` generic abstractions, function pointers/callbacks, `qsort`/`bsearch` with custom comparators, variadic functions, complex preprocessor macros, POSIX-only functions (`getline`, `strtok_r`), `errno`/`strerror`, or `stdint.h` types used where standard Prog1 C idioms are expected.
   - **Typical AI-written style**:
     - Unnaturally uniform Doxygen-style docstrings (`@brief`, `@param`, `@return`) on trivial helpers, or verbose "narrator" inline comments explaining obvious lines (`// Check if memory allocation succeeded`).
     - Consistent enterprise/defensive boilerplate rare in 1st-year code (e.g., strict `const`-correctness on every parameter, `size_t` + `SIZE_MAX` overflow guards, `enum` error-code returns everywhere, elaborate `snprintf`/input-flushing wrappers).
     - Language or style inconsistency (e.g., polished English comments/identifiers alongside Hungarian UI strings or documentation, or abrupt shifts between `snake_case` and `camelCase` across functions).
   - **Code–documentation mismatch**: Submitted code uses significantly more sophisticated patterns or different structures/algorithms than described in the student's Phase 2 documentation.
   - **Reporting requirement**: Stylistic suspicion alone is not an automatic fail, **but any suspected AI-written code must be clearly noted and highlighted in the grading report** (citing specific files/constructs) so it can be verified during the in-person defense (*védés*).

---

## 2. Documentation Check Aspects

Documentation is submitted as a **PDF**, **DOCX**, or a **ZIP containing Doxygen-generated HTML** (with a `mainpage`). Check that it covers all three required parts and matches the submitted code:

1. **User Documentation (Felhasználói dokumentáció)**
   - Clear description of what the program does and how to use it (CLI arguments, stdin inputs, expected output).
   - Includes the **Phase 1 detailed specification**:
     - Program goal
     - Meaning of data in each input file (with examples)
     - Relationships between the data
     - What the program computes/outputs

2. **Programmer Documentation (Programozói dokumentáció)**
   - Includes the **Phase 2 data model & algorithm descriptions**:
     - Diagrams of the chosen data structures and data relationships
     - Description of the key algorithms (building the data structure + solving the query) using structograms or pseudocode
   - **Code alignment**: References the **actual** `struct`s and function names used in the submitted C code. *(Does not replace in-code comments.)*

3. **Test Documentation (Tesztdokumentáció)**
   - Explains how the student verified the program works correctly.
   - Includes the **test data in text form** (even for any binary files) and explains the purpose of each test case.
   - Documents expected vs. actual test results, showing non-trivial / edge-case testing (not just one obvious happy path).

---

## 3. Grading / Pointing Guideline (Max: 10 Points, Pass: 4 Points)

> [!NOTE]
> **Grading Philosophy (Proportionality & Pedagogical Intent):**
> Do **not** apply this rubric overly rigidly. The goal is to verify that a 1st-year student genuinely understands and can apply the core course concepts (file I/O, dynamic memory/data structures, decomposition, and memory safety). If a requirement is only partially applied—for example, if the main data is stored in a proper linked list or dynamic structure while a secondary/auxiliary part uses a simpler approach, or if minor stylistic/edge-case flaws exist—**still award the corresponding points** when it is clear the student grasps the underlying concept, and document the gap as a **constructive remark** (with at most a modest quality-point deduction where appropriate) rather than failing the submission. Reserve hard-gate failures for genuinely missing core requirements (e.g., no real dynamic data structure anywhere, no file handling, crashes, or unverified authorship).

### A. Hard Gates (Must Pass Before Full Pointing)
- **Does not compile** with MinGW GCC (or crashes immediately on startup) → **Reject / 0 points** (cannot defend until fixed; student may need resubmission / *pótlás*).
- **Completely uncommented code** → **Do not accept**.
- **Missing core requirements** (no file handling, no dynamic data structure, uses resizing array instead of dynamic structure, or fails plagiarism / unacknowledged AI generation where the student cannot explain their own code at defense) → **Fail (< 4 points) / disciplinary if plagiarism**.
- **Suspected AI-generated code** → Flag and highlight prominently in the grading report for targeted verification at the defense (*védés*).

### B. Base 4 Points (Pass Threshold)
Award **4 points** if **all** of the following hold:
- [x] Compiles and runs without crashing.
- [x] Fulfills the agreed specification.
- [x] Contains text file handling and a valid dynamic data structure (no resizing array, single-pass read).
- [x] **No memory leaks** (clean Valgrind run).
- [x] Code is segmented into functions and commented.
- [x] Documentation is submitted.

### C. Remaining 6 Points (Quality & Completeness)
Distribute the remaining **6 points** according to the following criteria (guidelines from `4.x. Oktatói tudnivalók`):

| Criterion | Max Pts | Evaluation Focus |
| :--- | :---: | :--- |
| **1. Meaningful Segmentation** | **1.5** | Clear, single-responsibility functions; user I/O separated from logic; no 100-line `main()`; no unnecessary code duplication. |
| **2. Efficient Data Structure Implementation** | **1.5** | Well-chosen dynamic structure for the task; clean separation of payload data (`struct`) and list/tree administration; no duplicate data; efficient algorithms. |
| **3. Input & Error Handling** | **1.0** | Handles missing/unreadable files gracefully without crashing; handles invalid user/menu input (e.g., `-83`); handles spaces in string inputs properly. |
| **4. Identifiers, Comments & Structure** | **1.0** | Meaningful variable/function/type names; readable layout; file, type, and function comments clearly explain purpose, parameters, and return values. |
| **5. Documentation Quality** | **1.0 – 2.0** | **Max 2 points out of 10.** Clear user, programmer (diagrams + algorithms matching code), and test documentation (text-form test data + edge cases). |

*(Adjust weights within the 6-point pool flexibly as needed, keeping **Documentation Quality at max 2 points** and **Total = 10 points**.)*

### D. In-Person Defense (*Védés*) Quick Check
- Only allow a student to defend **after** you have seen/checked their submitted code.
- Have the student demonstrate the running program and explain key parts:
  - *"Where and how does it read until EOF?"*
  - *"Where does it insert/append an element to the list/structure?"*
  - *"Where would you modify the code if [requirement X] changed?"*
  - *(If suspicious / AI-flagged)* Ask the student why they chose specific advanced constructs or idioms (e.g., `void *`, function pointers, `const` patterns, `snprintf` wrappers), and delete 3 lines to ask them to restore the logic on the spot.
