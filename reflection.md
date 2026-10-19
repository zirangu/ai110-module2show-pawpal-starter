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

- **Greedy first-fit, not a globally optimal packer.** `_sort_by_constraint` picks an order once, then `generate_plan` places each task into the *first* window it fits and moves on — it never looks ahead or reconsiders an earlier placement to see if a different arrangement would've scheduled more tasks overall. An exact solver (e.g. trying all placements, or a DP/ILP formulation) could occasionally pack more tasks into the day. I accepted this because a pet owner's daily task list is small (a handful of tasks per pet), so the gap between "good enough" and "provably optimal" is negligible, while an exact solver adds real implementation and reasoning complexity for a benefit that would rarely show up in practice.
- **Most-constrained-first ordering is computed once, up front, not recalculated as windows shrink.** `_sort_by_constraint` counts how many of the *original* free windows each task could fit into, then sorts by that count before placing anything. As tasks get placed and windows shrink, a task's real remaining options change, but the order doesn't adapt mid-run. This fixes the specific starvation case I was worried about (a flexible task grabbing the one slot a narrowly-windowed task needed) without the added bookkeeping of re-sorting after every placement — a reasonable tradeoff since getting the *first* ordering right already prevents the most common failure mode.
- **A task with a `preferred_time_window` that doesn't overlap any free window is skipped entirely, never best-effort placed elsewhere.** `_fits_in_window` treats the preferred window as a hard constraint, not a soft preference — so "medication at 8pm" won't get silently rescheduled to 10am just because that's when time opens up. I chose correctness over always-scheduling-something, since silently moving a task like medication to a time the owner didn't ask for could be actively harmful, whereas a clearly reported skip (`DailyPlan.skipped_tasks` + `explain()`) at least tells the owner something needs their attention.
- **Conflict detection (`DailyPlan.find_conflicts`) is a naive O(n²) pairwise comparison**, not a sweep-line algorithm. Since the scheduler's own greedy placement already prevents overlaps by construction, this check only matters as a safety net for a small daily task list, where the quadratic cost is irrelevant — a more complex O(n log n) approach wasn't worth the trouble for a list that small.

---

## 3. AI Collaboration

**a. How you used AI**

I used AI throughout the whole pipeline: brainstorming the core classes before drawing the UML, drafting the Mermaid diagram itself, generating the class skeletons in `pawpal_system.py`, implementing the scheduling logic, writing `main.py` and the pytest tests, and adding docstrings. The most useful prompts weren't "write the code" requests — they were asking the AI to critique a skeleton I already had ("review this for anything missing or potentially a problem") before any logic existed. That surfaced real issues early (untyped priority/category strings, no `Owner`→`Pet` link, duplicate state in the scheduler) instead of discovering them after the logic was built on top of a shaky skeleton.

**b. Judgment and verification**

One suggestion I didn't accept as-is was the original `Owner.available_minutes_per_day: int` field. The AI's first draft modeled availability as a single number of free minutes, but I pushed back because a real day isn't one uninterrupted block — it has gaps (e.g. a work shift in the middle). I asked for it to be reworked into explicit `TimeBlock`s (`day_start_time`, `day_end_time`, `busy_blocks`) so the scheduler could reason about *when* someone is free, not just *how much* total time they have. I verified the fix actually worked by writing `main.py` with an owner who has a 9am–5pm work block and pets with morning/evening-preferred tasks, then checking the printed schedule placed tasks only in the gaps around that block rather than anywhere in the day.

**c. AI Strategy**

*Which features were most effective:* The single most effective pattern was asking the assistant to critique something I already had *before* adding more to it — "review this skeleton for anything missing or potentially a problem," "is there a better algorithm, and what's one limitation of the current one," "is this actually implemented, make sure" — rather than asking it to generate large pieces of new code outright. That caught real structural problems (the `available_minutes_per_day` issue above, the `Owner`→`Pet` link gap, the starvation bug in task ordering) while they were still cheap to fix, and it caught cases later where I'd *claimed* something was tested or implemented but actually wasn't (e.g. conflict detection existed on `DailyPlan` but had never actually been exercised through `Scheduler.check_conflicts` in a test). Asking it to verify my own claims against the code was more valuable than asking it to write code from scratch.

*An example I rejected or modified:* Besides the availability-modeling rework above, I also pushed back on the first version of the "most constrained first" scheduling fix — the AI's initial instinct was to delete `_sort_by_priority` entirely once it was superseded. I asked it to keep the old method in the file (unused, but documented as superseded) instead of deleting it, since having the simpler baseline visible alongside the improved version makes the *reason* for the improvement legible to a reader, rather than erasing the "before" state.

*Working in one continuous session rather than separate chats:* In practice this project stayed in one continuous conversation rather than being split across separate chat sessions per phase. What kept it organized wasn't separate sessions but explicit phase boundaries I set myself — brainstorm classes, then draft UML, then skeleton, then review-before-implementing, then implement, then test, then wire up the UI, then document — and stopping to review/approve at each boundary before moving to the next. The lesson is less about session boundaries and more about never letting the AI run two phases at once (e.g. implementing logic *and* redesigning the schema in the same step), since conflating phases is what makes a change hard to review or roll back.

*Being the "lead architect":* The biggest thing I learned is that the AI is a very fast implementer of a design but a mediocre judge of which design is *right* for this specific problem — it will confidently build whatever skeleton you hand it. The value I added wasn't writing code, it was making the calls that required actually caring about the pet owner using this (availability has gaps, a missed medication shouldn't be silently rescheduled, a conflict warning should name both tasks and the exact time rather than just saying "conflict detected"). Treating the AI as an extremely capable pair of hands that still needs a human deciding *what* "correct" means for this domain, rather than as a source of correctness itself, was the main shift in how I worked.

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
