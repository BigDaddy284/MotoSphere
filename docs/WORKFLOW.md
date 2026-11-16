# MotoSphere – Development workflow

CLAUDE.md sets the rules: one small task at a time, 100% of applicable tests
passing before the next task starts. This document describes how that rule is
carried out by two separate roles.

## Roles

| Role | Who | Does |
|---|---|---|
| **Planner / tester** | One long-lived planning thread | Owns TASKS.md, PROGRESS.md and `docs/plans/`. Breaks work into tasks, writes one implementation plan per task, independently tests each finished task, merges it, records the result, then hands over the next task. |
| **Builder** | A new thread for every task | Implements exactly one task from its plan, with tests, on its own branch, and opens a pull request to `main`. |

Only one task is in progress at any time.

## The loop

1. **Plan.** The planner writes `docs/plans/<TASK-ID>.md` on `main` and sets
   the task to `IN PROGRESS` in TASKS.md.
2. **Build.** A new builder thread reads CLAUDE.md, DESIGN.md, ARCHITECTURE.md,
   this file and the plan, then implements the task and its tests.
3. **Self-test.** The builder runs every command in the plan's "Verification"
   section until all pass, then opens a pull request to `main` with a test
   report in the description.
4. **Independent test.** The planner checks out the pull request in a clean
   environment and re-runs every gate plus the plan's acceptance checks.
5. **Fix.** If anything fails, the task becomes `FAILED – FIX REQUIRED` and the
   findings go back to the builder. Steps 3–5 repeat.
6. **Merge and record.** At 100% the planner squash-merges the pull request
   (one commit per task on `main`), sets the task to `PASSED – VERIFIED` with
   the real counts and commit hash, and adds a report to PROGRESS.md.
7. **Next.** The planner writes the next plan and the loop starts again.

## Rules for builders

- Implement **only** the task in your plan. If something else looks wrong,
  report it; do not fix it in this task.
- Do **not** edit CLAUDE.md, DESIGN.md, TASKS.md, PROGRESS.md or anything under
  `docs/plans/`. The planner records status and results. Do update the other
  documents your task affects (README.md, ARCHITECTURE.md, TESTING.md,
  DATABASE.md, DATA_SOURCES.md, CHANGELOG.md) when the plan says so.
- Never weaken, skip or delete a test to get a pass. Never replace real
  behaviour with a mock to get a pass. Fix the cause.
- Never fabricate data, test results or commit references.
- No secrets in the repository. No generated files (`node_modules`, build
  output, caches, virtual environments).
- Everything must work on Windows 11 and Linux: no shell-only assumptions in
  code that the application or its tests depend on.
- If the plan is wrong, impossible or ambiguous in a way that changes the
  outcome, stop and say so in your report rather than guessing silently. Small
  ordinary implementation choices are yours to make; note them in the report.

## Pull request format

- Title: `<TASK-ID>: <task name>`.
- One task per pull request, branched from the current `main`.
- The description contains a **Test report**: each verification command, its
  result and the pass/fail counts copied from real output, plus any deviation
  from the plan and why.

## Rules for the planner / tester

- Test in a clean checkout of the pull request, not in the builder's
  environment.
- Run the whole suite, not only the new tests, before merging.
- Check behaviour, not just green output: read the diff, confirm the
  acceptance criteria one by one, and exercise the real feature (browser,
  HTTP, database) where the task has one.
- Record only numbers that came from a real run.
