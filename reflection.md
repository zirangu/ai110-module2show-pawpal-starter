# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I started from the three core actions a user needs to perform: (1) set up an owner/pet profile and mark when they're actually free during the day, (2) manage a list of care tasks, and (3) generate and review a daily plan with reasoning. Each class in the UML maps to one of these actions or to a supporting concept they both need.

A detailed description:

Three core actions that a user should be able to perform.
1. Set up owner & pet profile — enter owner name/preferences and pet info (species, name) that the plan will be generated for.

2. Manage care tasks — add/edit/remove tasks with duration, priority, and category (walk, feed, meds, enrichment, grooming).

3. Generate & review the daily plan — trigger the scheduler given a time budget, and see the resulting ordered schedule with a reasoning/explanation for why each task was placed where it was.

- **Owner** — holds the pet owner's name, preferences, and their daily availability (`day_start_time`, `day_end_time`, and a list of `busy_blocks` for things like work hours). I didn't want availability to be a single "minutes free" number, because a real day isn't one uninterrupted block of free time — it has gaps. Modeling it as explicit time blocks lets the scheduler reason about *when* a pet owner is free, not just *how much* time they have in total.
- **Pet** — holds basic pet info (name, species, notes) and owns the list of `Task`s that need to be done for that pet. Keeping `Pet` separate from `Owner` matters because a household could have multiple pets with different care needs under one owner.
- **TimeBlock** — a small reusable value object representing a start time, end time, and label. I factored this out instead of duplicating start/end fields everywhere, since both `Owner.busy_blocks` (e.g. "work, 9am-5pm") and `Task.preferred_time_window` (e.g. "morning walk should happen before 9am") are really the same concept: a span of time with a meaning attached.
- **Task** — represents a single care task: title, category (walk/feed/meds/enrichment/grooming), duration, priority, an optional preferred time window, and whether it's required (e.g. medication can't just be skipped the way a nice-to-have enrichment activity can).
- **Scheduler** — the engine. It takes an owner's availability and a list of tasks and produces a plan. I made this its own class instead of a method on `Owner` or `Pet`, because scheduling is a distinct piece of logic (sorting by priority, fitting tasks into free windows) that doesn't belong to the data it operates on.
- **DailyPlan** — the result object returned by the scheduler: which tasks got scheduled (as `ScheduledTask`s with concrete start/end times), which were skipped and why, and an `explain()` method to surface the reasoning. Separating the *result* from the *engine* means the UI can just display a `DailyPlan` without knowing anything about how it was built.
- **ScheduledTask** — a thin wrapper that pairs a `Task` with the concrete `start_time`/`end_time` it was given in the plan, keeping that scheduling detail out of `Task` itself (a `Task` on its own doesn't know when it will run — only its `ScheduledTask` does).




**b. Design changes**

Writing the skeleton in code surfaced a few problems that weren't obvious from the diagram alone:

- **`category` and `priority` became enums (`Category`, `Priority`) instead of free strings.** With plain strings, a typo like `priority="urgent"` would silently fail to sort correctly instead of raising an error, since the scheduler branches on these exact values. Enums make invalid values impossible to construct.
- **Added `Owner.pets: list[Pet]` and `Owner.all_tasks()`.** The original UML showed an `Owner "1" --> "1..*" Pet` relationship, but nothing in the actual classes stored that link — there was no way to go from an `Owner` to "all tasks across all of their pets," which the scheduler needs as its input.
- **Added `id` fields to `Task` and `Pet`.** Once tasks are added/edited/removed through the Streamlit UI, matching a task by its title and duration isn't reliable — two "Morning walk, 20 min" tasks for different pets would be indistinguishable. A generated UUID gives each one a stable identity.
- **`Scheduler` lost its constructor-held `self.tasks` and became stateless.** The original skeleton had both a `tasks` parameter passed into the constructor *and* into `generate_plan()`, with `_sort_by_priority()` only reading from `self.tasks`. That's two sources of truth for the same list, which invites bugs where the scheduler sorts a stale list instead of the one it was just asked to plan. Making the scheduler a pure function of its arguments (no stored state) removes that ambiguity.
- **`DailyPlan.total_minutes_used` became a computed `@property` instead of a stored field.** It's fully derivable from `scheduled_tasks`, so storing it separately just creates a chance that someone updates `scheduled_tasks` and forgets to update the count, leaving them out of sync.
- **`TimeBlock.overlaps` and `ScheduledTask.overlaps` now share one helper function (`_time_ranges_overlap`).** Both methods were doing the identical start/end comparison on two different classes; factoring it out means the overlap logic only has to be implemented and tested once.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

I used AI throughout the whole pipeline: brainstorming the core classes before drawing the UML, drafting the Mermaid diagram itself, generating the class skeletons in `pawpal_system.py`, implementing the scheduling logic, writing `main.py` and the pytest tests, and adding docstrings. The most useful prompts weren't "write the code" requests — they were asking the AI to critique a skeleton I already had ("review this for anything missing or potentially a problem") before any logic existed. That surfaced real issues early (untyped priority/category strings, no `Owner`→`Pet` link, duplicate state in the scheduler) instead of discovering them after the logic was built on top of a shaky skeleton.

**b. Judgment and verification**

One suggestion I didn't accept as-is was the original `Owner.available_minutes_per_day: int` field. The AI's first draft modeled availability as a single number of free minutes, but I pushed back because a real day isn't one uninterrupted block — it has gaps (e.g. a work shift in the middle). I asked for it to be reworked into explicit `TimeBlock`s (`day_start_time`, `day_end_time`, `busy_blocks`) so the scheduler could reason about *when* someone is free, not just *how much* total time they have. I verified the fix actually worked by writing `main.py` with an owner who has a 9am–5pm work block and pets with morning/evening-preferred tasks, then checking the printed schedule placed tasks only in the gaps around that block rather than anywhere in the day.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
