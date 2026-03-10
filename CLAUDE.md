Python Coding Standards

This project uses **Python** with a strong emphasis on readability, correctness, and testability. Follow these rules for all AI-assisted changes.

***

## 1. Style & Structure (PEP 8)

- Follow PEP 8 for layout and naming (4-space indentation, 79–100 char lines, consistent spacing).[1][2][3][4]
- Use **snake_case** for functions and variables, `PascalCase` for classes, and UPPER_SNAKE_CASE for constants.[1]
- Organize code into small, focused modules instead of “god files” like `utils.py` when possible.[1]
- Prefer pure, side-effect-free functions; keep most functions under ~30–40 lines.

***

## 2. Project Layout

- Keep a clear structure (example):

  - `src/` or `app/`: application code  
  - `tests/`: all tests, mirroring the `src/` layout as much as possible.[5][6]
  - `config/` or `settings/`: configuration and environment handling  
  - `scripts/`: one-off tools and maintenance scripts  

- Each module should start with a short comment or docstring describing its purpose and responsibilities.

***

## 3. Naming & API Design

- Prefer explicit, descriptive names: `load_user_profile`, `calculate_discount`, `fetch_orders_for_user`.  
- Function signatures should use keyword arguments for most optional parameters.  
- Return consistent, well-defined types (avoid returning `None` sometimes and a dict other times from the same function).

***

## 4. Error Handling

- Use exceptions instead of error codes.  
- Raise errors at the lowest reasonable level; catch them at service or boundary layers.[7]
- Prefer specific exceptions over `Exception` (e.g., `ValueError`, `KeyError`, custom domain exceptions).[8][9][7]
- Keep `try` blocks small and focused; only wrap the lines that can actually fail.[8]
- Do not silently swallow exceptions. If you intentionally ignore one, add a short comment explaining why.[9]

***

## 5. Tests & Verification (pytest)

- Use **pytest** with a `tests/` directory that mirrors the source tree.[6][5]
- Each bug fix or new feature must include at least one test.  
- Follow these rules when generating tests:

  - Use the Arrange–Act–Assert structure inside tests.[6]
  - Write small, independent tests that each assert one behavior.[10][5][6]
  - Use fixtures for repeated setup; use parameterization for the same logic with different inputs.[5][10][6]

- When asked to “verify” changes:

  1. Generate or update tests.  
  2. Assume tests are run.  
  3. If tests conceptually fail, revise the code and explain what changed and why.

***

## 6. Documentation & Comments

- Every public function, class, and module must have a short docstring describing:

  - What it does  
  - Key arguments and return value  
  - Important edge cases or assumptions  

- Comments should explain the **why**, not restate the code.  
- When changing behavior, update any relevant docstrings and high-level docs (README, API docs, etc.).

***

## 7. Refactoring Rules

- When touching existing code, prefer improving it instead of just appending more logic.  
- Eliminate duplication by extracting helper functions or classes.  
- Break up long functions and deeply nested conditionals into smaller, composable pieces.  
- Keep imports clean and minimal; remove unused imports as you go.

***

## 8. AI Workflow Expectations

When writing or modifying Python code:

1. **Start in Plan Mode**  
   - Ask for or infer: file layout, relevant modules, data flows, dependencies, and edge cases.  
   - Propose a step-by-step plan before editing files.

2. **Use Skills / Reusable Patterns**  
   - If similar logic, patterns, or explanations appear more than once, generalize them into reusable helpers or skills for future sessions.

3. **Build a Verification Loop**  
   - After generating code, generate or update tests.  
   - Re-check logic for edge cases (empty inputs, `None`, large sizes, invalid types, external failures).  
   - Document what changed and what was learned so it can be fed back into skills or docs.

***

## 9. Definition of Done (Python)

A change is considered complete only when:

- Code follows this style guide and PEP 8 conventions.[3][4][1]
- All relevant tests (existing and newly added) pass conceptually.[5][6]
- Edge cases and error paths have been considered and handled appropriately.[7][9][8]
- Public interfaces are documented and any breaking changes are clearly communicated.  
