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

1. Calls `_get_free_windows(owner)` to subtract the owner's busy blocks from their day, producing the actual gaps of free time.
2. Calls `_sort_by_priority(tasks)` so required tasks go first, then tasks are ordered high → medium → low priority.
3. Walks the sorted tasks and uses `_fits_in_window(task, window)` to place each one into the first free window it fits (respecting its preferred time window, if it has one), shrinking that window as it's consumed.
4. Anything that doesn't fit anywhere is collected into `skipped_tasks` instead of being dropped silently.

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

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
