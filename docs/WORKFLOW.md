# MotoSphere – Development workflow

CLAUDE.md sets the rules: one small task at a time, 100% of applicable tests
passing before the next task starts. This document describes how that rule is
carried out by three separate roles.

Since 2026-11-27, by the owner's decision, the work runs on two tracks
side by side: track A is the data store and the published data
(`backend/`), track B the globe (`frontend/`). The rule holds on each
track. `TASKS.md` ("Two tracks") says how they are kept apart.

Since 2026-11-28, by the owner's decision, the independent test of a
finished task is a role of its own. Until then the planner tested every
pull request itself. The planner still tries every task out before it
writes the plan, and writes a test plan beside it; a tester thread tests
the builder's pull request against that test plan and reports; the
planner merges and records (`PROGRESS.md`, PLAN-055).

## Roles

| Role | Who | Does |
|---|---|---|
| **Planner** | One long-lived planning thread | Owns TASKS.md, PROGRESS.md and `docs/plans/`. Breaks work into tasks, tries each task out, writes one implementation plan and one test plan per task, merges the tested task, records the result, then hands over the next task. |
| **Tester** | One long-lived testing thread | Tests each builder's pull request against the planner's test plan, independently of the builder's report, and reports to the planner. Changes nothing: it does not fix, merge, push or record. |
| **Builder** | A new thread for every task | Implements exactly one task from its plan, with tests, on its own branch, and opens a pull request to `main`. |

Only one task of a track is in progress at any time, and so at most two in all.
A builder has one task, and does not touch what the other track changes.

## The loop

1. **Plan.** The planner writes `docs/plans/<TASK-ID>.md` on `main` and sets
   the task to `IN PROGRESS` in TASKS.md. It writes the test plan of the
   task for the tester, with the defects it planted in its own trial and
   the results it got.
2. **Build.** A new builder thread reads CLAUDE.md, DESIGN.md, ARCHITECTURE.md,
   this file and the plan, then implements the task and its tests.
3. **Self-test.** The builder runs every command in the plan's "Verification"
   section until all pass, then opens a pull request to `main` with a test
   report in the description.
4. **Independent test.** The tester checks out the pull request in a clean
   environment and works through the test plan: that the change is the
   one the plan gives, every gate, the planted defects, the plan's
   prove-it steps, the application itself by hand, and the runs on
   GitHub. It reports to the planner: pass or fail, the numbers of every
   step, and every difference from the test plan.
5. **Fix.** If anything fails, the task becomes `FAILED – FIX REQUIRED` and the
   planner sends the findings back to the builder. Steps 3–5 repeat.
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
- One task per pull request, branched from the current `main`. While it is
  open, `main` may get the other track's task; the pull request is not
  rebased for that, and the planner tests it together with what `main` holds.
- The description contains a **Test report**: each verification command, its
  result and the pass/fail counts copied from real output, plus any deviation
  from the plan and why.

## Rules for the tester, and for the planner where it tests

- Test in a clean checkout of the pull request, not in the builder's
  environment.
- Run the whole suite, not only the new tests, before merging.
- Check behaviour, not just green output: read the diff, confirm the
  acceptance criteria one by one, and exercise the real feature (browser,
  HTTP, database) where the task has one.
- Record only numbers that came from a real run.
- The tester changes nothing. What fails is described, not repaired, and
  the planner decides what follows.

## Where the test plans are

The test plan of a task, the planted defects as the tester's tools run
them and the planner's own results are kept in the project's shared
folder, `testing/<TASK-ID>/`, with the tester's standing instructions
beside them. They are tools of the workshop and not part of the
application, so they are not in the repository. The work plan in
`docs/plans/` names the planted defects and the prove-it steps in
words, and `PROGRESS.md` records what the test gave.
