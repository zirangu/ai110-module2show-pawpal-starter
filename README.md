# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🏗️ Implementation Summary

All backend logic lives in `pawpal_system.py`. The core data classes — `Owner`, `Pet`, `Task`, and `TimeBlock` — just hold state: an `Owner` has a day start/end time and a list of busy `TimeBlock`s (e.g. work hours), a `Pet` holds a list of `Task`s, and a `Task` has a duration, `Priority`, `Category`, and an optional preferred `TimeBlock`.

The `Scheduler` class contains all the planning logic and is kept stateless on purpose — it takes a list of tasks and an `Owner` and returns a `DailyPlan`, rather than holding any data itself. Internally it:

1. Calls `_due_today(tasks)` to drop anything already completed or not due today.
2. Calls `_get_free_windows(owner)` to subtract the owner's busy blocks from their day, producing the actual gaps of free time.
3. Calls `_sort_by_constraint(tasks, free_windows)` so the most constrained tasks (fewest windows they could fit into) go first, ties broken by required, then priority high → medium → low.
4. Walks the sorted tasks and uses `_fits_in_window(task, window)` to place each one into the first free window it fits (respecting its preferred time window, if it has one), shrinking that window as it's consumed.
5. Anything that doesn't fit anywhere is collected into `skipped_tasks` instead of being dropped silently.

The result is a `DailyPlan`, which separates *what was built* from *how it was built* — the UI and `main.py` only ever call `plan.explain()` (a human-readable reasoning string) or `plan.to_display_format()` (a plain dict), without needing to know anything about the `Scheduler` that produced it.

## 🖥️ Sample Output

Output from running `python main.py`, which builds an `Owner` with two `Pet`s and four `Task`s, then generates a plan via `Scheduler.generate_plan()`:

```
=== Today's Schedule ===
07:00-07:30: Morning walk (priority=high) — scheduled because it fit in an available window and is required.
07:30-07:40: Give medication (priority=high) — scheduled because it fit in an available window and is required.
07:40-07:55: Brushing / grooming (priority=low) — scheduled because it fit in an available window.
17:00-17:30: Evening walk (priority=medium) — scheduled because it fit in an available window.
```

## 🧪 Testing PawPal+

Run the test suite with:

```bash
python -m pytest
```

`tests/test_pawpal.py` (30 tests) covers:

- **Core behaviors**: marking a task complete, adding a task to a pet.
- **Filtering**: `Owner.filter_tasks()` by status, by pet name, both together, with no filters, and on an owner with no pets.
- **Scheduler placement edge cases**: an owner/pet with no tasks, a task longer than any free window, a task that exactly fills a window, busy blocks given out of order or overlapping, and a preferred time window entirely outside the owner's day.
- **Due-today filtering**: completed tasks and tasks due on a future date are excluded from today's plan.
- **Sorting correctness**: tasks fed into `generate_plan()` out of order come back sorted chronologically by start time.
- **Recurrence logic**: `next_occurrence()` for one-time (returns `None`), daily (+1 day), and weekly (+7 days) tasks; `Pet.complete_task()` on a daily task appends exactly one new pending task due the following day.
- **Conflict detection**: an empty plan, a single scheduled task, and adjacent (touching) tasks all report no conflicts; three tasks where only two overlap report exactly that one pair; and `Scheduler.check_conflicts()` correctly flags two tasks scheduled at the exact same time with a warning message, without raising.

Sample test output:

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\z_gu0\Documents\github_io\ai110-module2show-pawpal-starter
plugins: anyio-4.12.1, jaxtyping-0.3.11, typeguard-4.6.0
collected 30 items

tests/test_pawpal.py::test_mark_complete_changes_task_status PASSED      [  3%]
tests/test_pawpal.py::test_adding_task_increases_pet_task_count PASSED   [  6%]
tests/test_pawpal.py::test_filter_tasks_by_status PASSED                 [ 10%]
tests/test_pawpal.py::test_filter_tasks_by_pet_name PASSED               [ 13%]
tests/test_pawpal.py::test_filter_tasks_by_status_and_pet_name PASSED    [ 16%]
tests/test_pawpal.py::test_pet_with_no_tasks_contributes_nothing PASSED  [ 20%]
tests/test_pawpal.py::test_owner_with_no_pets_generates_empty_plan PASSED [ 23%]
tests/test_pawpal.py::test_owner_with_no_busy_blocks_has_one_free_window_spanning_the_day PASSED [ 26%]
tests/test_pawpal.py::test_task_longer_than_any_window_is_skipped_not_crashed PASSED [ 30%]
tests/test_pawpal.py::test_task_exactly_fills_window PASSED              [ 33%]
tests/test_pawpal.py::test_busy_blocks_given_out_of_order_still_produce_correct_free_windows PASSED [ 36%]
tests/test_pawpal.py::test_overlapping_busy_blocks_are_merged_without_a_negative_window PASSED [ 40%]
tests/test_pawpal.py::test_scheduled_tasks_are_returned_in_chronological_order PASSED [ 43%]
tests/test_pawpal.py::test_preferred_window_entirely_outside_the_day_is_skipped PASSED [ 46%]
tests/test_pawpal.py::test_completed_task_excluded_from_todays_plan PASSED [ 50%]
tests/test_pawpal.py::test_task_due_tomorrow_excluded_from_todays_plan PASSED [ 53%]
tests/test_pawpal.py::test_one_time_task_has_no_next_occurrence PASSED   [ 56%]
tests/test_pawpal.py::test_daily_task_next_occurrence_advances_one_day PASSED [ 60%]
tests/test_pawpal.py::test_weekly_task_next_occurrence_advances_seven_days PASSED [ 63%]
tests/test_pawpal.py::test_completing_recurring_task_appends_exactly_one_new_task PASSED [ 66%]
tests/test_pawpal.py::test_completing_daily_task_creates_task_due_the_following_day PASSED [ 70%]
tests/test_pawpal.py::test_completing_one_time_task_does_not_append_anything PASSED [ 73%]
tests/test_pawpal.py::test_filter_tasks_with_no_filters_returns_everything PASSED [ 76%]
tests/test_pawpal.py::test_filter_tasks_on_owner_with_no_pets_returns_empty_list PASSED [ 80%]
tests/test_pawpal.py::test_empty_plan_has_no_conflicts PASSED            [ 83%]
tests/test_pawpal.py::test_single_scheduled_task_has_no_conflicts PASSED [ 86%]
tests/test_pawpal.py::test_adjacent_tasks_touching_at_the_boundary_are_not_a_conflict PASSED [ 90%]
tests/test_pawpal.py::test_only_the_actually_overlapping_pair_is_reported_among_three_tasks PASSED [ 93%]
tests/test_pawpal.py::test_scheduler_flags_duplicate_times_with_a_warning PASSED [ 96%]
tests/test_pawpal.py::test_scheduler_reports_no_conflicts_for_a_non_overlapping_plan PASSED [100%]

============================= 30 passed in 0.03s ==============================
```

**Confidence Level: ⭐⭐⭐⭐☆ (4/5)**

All core scheduling, filtering, recurrence, and conflict-detection behaviors are covered and passing, including boundary cases (exact-fit windows, adjacent tasks, overlapping busy blocks). I'm not giving it a 5th star because the scheduler's greedy, first-fit placement is tested for correctness on the cases we wrote, not proven optimal — and we haven't yet tested the Streamlit UI layer (`app.py`) itself, only the backend it calls into.

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler._sort_by_constraint()` | Orders tasks by how many free windows they could fit into (fewest first), then by `is_required`, then `Priority` (high → low). Prevents a flexible task from grabbing the one slot a narrowly-windowed task needed. An earlier, simpler version (`Scheduler._sort_by_priority()`, required-then-priority only) is kept in the file for reference/comparison. |
| Filtering | `Owner.filter_tasks(status, pet_name)` | Filters tasks across all of an owner's pets by completion status and/or which pet owns them. `Scheduler._due_today()` also filters internally so `generate_plan()` only ever considers tasks that are `pending` and due today. |
| Conflict handling | `DailyPlan.find_conflicts()`, `DailyPlan.conflict_warnings()`, `Scheduler.check_conflicts()` | Pairwise-checks scheduled tasks for overlapping time ranges (regardless of which pet they belong to) and returns human-readable warning strings instead of raising — the scheduler's own placement logic shouldn't produce conflicts, but this acts as a safety net and is demonstrated in `main.py` against a hand-built conflicting plan. |
| Recurring tasks | `Task.next_occurrence()`, `Pet.complete_task()` | A `Task` has a `Frequency` (`ONE_TIME`, `DAILY`, `WEEKLY`) and a `due_date`. `Pet.complete_task(task_id)` marks a task complete and, if it recurs, clones it into a new pending `Task` whose `due_date` is advanced by a day or a week (via `datetime.timedelta`) and adds it to the pet's task list. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
