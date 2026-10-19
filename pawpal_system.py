"""Backend logic layer for PawPal+: owners, pets, tasks, and the scheduler."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class Category(str, Enum):
    WALK = "walk"
    FEED = "feed"
    MEDS = "meds"
    ENRICHMENT = "enrichment"
    GROOMING = "grooming"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Frequency(str, Enum):
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"


_RECURRENCE_DELTA = {
    Frequency.DAILY: timedelta(days=1),
    Frequency.WEEKLY: timedelta(weeks=1),
}


def _to_datetime(t: time) -> datetime:
    """Anchor a bare `time` to a fixed date so it supports datetime arithmetic."""
    return datetime.combine(date.min, t)


def _minutes_between(start: time, end: time) -> int:
    """Return the number of whole minutes between two times."""
    return int((_to_datetime(end) - _to_datetime(start)).total_seconds() // 60)


def _add_minutes(t: time, minutes: int) -> time:
    """Return the time that is `minutes` minutes after `t`."""
    return (_to_datetime(t) + timedelta(minutes=minutes)).time()


def _time_ranges_overlap(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    """Return True if the two [start, end) time ranges overlap."""
    return start_a < end_b and start_b < end_a


@dataclass
class TimeBlock:
    start_time: time
    end_time: time
    label: str = ""

    def overlaps(self, other: "TimeBlock") -> bool:
        """Return True if this block overlaps `other`."""
        return _time_ranges_overlap(self.start_time, self.end_time, other.start_time, other.end_time)


@dataclass
class Task:
    title: str
    category: Category
    duration_minutes: int
    priority: Priority
    preferred_time_window: TimeBlock | None = None
    is_required: bool = False
    status: str = "pending"
    due_date: date = field(default_factory=date.today)
    frequency: Frequency = Frequency.ONE_TIME
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def mark_complete(self) -> None:
        """Mark this task's status as completed. Does not create the next occurrence —
        see `Pet.complete_task` for recurring tasks."""
        self.status = "completed"

    def next_occurrence(self) -> "Task | None":
        """Return a fresh pending copy of this task due on its next occurrence, or None if one-time."""
        delta = _RECURRENCE_DELTA.get(self.frequency)
        if delta is None:
            return None
        return replace(
            self,
            id=str(uuid.uuid4()),
            status="pending",
            due_date=self.due_date + delta,
        )


@dataclass
class Pet:
    name: str
    species: str
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def complete_task(self, task_id: str) -> Task | None:
        """Mark the task with `task_id` complete and, if it recurs, add and return its next occurrence."""
        task = next(t for t in self.tasks if t.id == task_id)
        task.mark_complete()

        next_task = task.next_occurrence()
        if next_task is not None:
            self.add_task(next_task)
        return next_task


@dataclass
class Owner:
    name: str
    preferences: dict = field(default_factory=dict)
    day_start_time: time = time(7, 0)
    day_end_time: time = time(21, 0)
    busy_blocks: list[TimeBlock] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def filter_tasks(self, status: str | None = None, pet_name: str | None = None) -> list[Task]:
        """Return tasks across all pets, optionally filtered by status and/or owning pet's name."""
        return [
            task
            for pet in self.pets
            for task in pet.tasks
            if (status is None or task.status == status)
            and (pet_name is None or pet.name == pet_name)
        ]


@dataclass
class ScheduledTask:
    task: Task
    start_time: time
    end_time: time

    def overlaps(self, other: "ScheduledTask") -> bool:
        """Return True if this scheduled task's time range overlaps `other`."""
        return _time_ranges_overlap(self.start_time, self.end_time, other.start_time, other.end_time)


@dataclass
class DailyPlan:
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)

    @property
    def total_minutes_used(self) -> int:
        """Return the total minutes consumed by all scheduled tasks."""
        return sum(st.task.duration_minutes for st in self.scheduled_tasks)

    def find_conflicts(self) -> list[tuple[ScheduledTask, ScheduledTask]]:
        """Return pairs of scheduled tasks whose time ranges overlap, regardless of which pet owns them."""
        conflicts = []
        for i, first in enumerate(self.scheduled_tasks):
            for second in self.scheduled_tasks[i + 1 :]:
                if first.overlaps(second):
                    conflicts.append((first, second))
        return conflicts

    def conflict_warnings(self) -> list[str]:
        """Return a human-readable warning message for each detected scheduling conflict."""
        return [
            f"WARNING: '{first.task.title}' ({first.start_time.strftime('%H:%M')}-"
            f"{first.end_time.strftime('%H:%M')}) overlaps with '{second.task.title}' "
            f"({second.start_time.strftime('%H:%M')}-{second.end_time.strftime('%H:%M')})."
            for first, second in self.find_conflicts()
        ]

    def explain(self) -> str:
        """Return a human-readable explanation of what was scheduled or skipped and why."""
        lines = []
        for st in self.scheduled_tasks:
            lines.append(
                f"{st.start_time.strftime('%H:%M')}-{st.end_time.strftime('%H:%M')}: "
                f"{st.task.title} (priority={st.task.priority.value}) — scheduled because it fit in an "
                f"available window{' and is required' if st.task.is_required else ''}."
            )
        for task in self.skipped_tasks:
            lines.append(
                f"SKIPPED: {task.title} (priority={task.priority.value}) — no free window was "
                f"large enough to fit its {task.duration_minutes} minute duration."
            )
        return "\n".join(lines) if lines else "No tasks were scheduled or skipped."

    def to_display_format(self) -> dict:
        """Return this plan as a plain dict shape suitable for the UI to render."""
        return {
            "scheduled": [
                {
                    "title": st.task.title,
                    "category": st.task.category.value,
                    "priority": st.task.priority.value,
                    "start_time": st.start_time.strftime("%H:%M"),
                    "end_time": st.end_time.strftime("%H:%M"),
                }
                for st in self.scheduled_tasks
            ],
            "skipped": [
                {
                    "title": task.title,
                    "category": task.category.value,
                    "priority": task.priority.value,
                    "duration_minutes": task.duration_minutes,
                }
                for task in self.skipped_tasks
            ],
            "total_minutes_used": self.total_minutes_used,
        }


class Scheduler:
    def check_conflicts(self, plan: DailyPlan) -> list[str]:
        """Return warning messages for any overlapping scheduled tasks in `plan`, without raising."""
        return plan.conflict_warnings()

    def generate_plan(self, tasks: list[Task], owner: Owner) -> DailyPlan:
        """Build a DailyPlan for today by fitting the most constrained, still-pending, due-today tasks
        first into the owner's free time windows."""
        due_today_tasks = self._due_today(tasks)
        free_windows = self._get_free_windows(owner)
        sorted_tasks = self._sort_by_constraint(due_today_tasks, free_windows)

        scheduled_tasks: list[ScheduledTask] = []
        skipped_tasks: list[Task] = []

        for task in sorted_tasks:
            window_index = next(
                (i for i, window in enumerate(free_windows) if self._fits_in_window(task, window)),
                None,
            )
            if window_index is None:
                skipped_tasks.append(task)
                continue

            window = free_windows[window_index]
            start_time = window.start_time
            end_time = _add_minutes(start_time, task.duration_minutes)
            scheduled_tasks.append(ScheduledTask(task=task, start_time=start_time, end_time=end_time))

            if end_time < window.end_time:
                free_windows[window_index] = TimeBlock(end_time, window.end_time, window.label)
            else:
                free_windows.pop(window_index)

        scheduled_tasks.sort(key=lambda st: st.start_time)
        return DailyPlan(scheduled_tasks=scheduled_tasks, skipped_tasks=skipped_tasks)

    def _due_today(self, tasks: list[Task]) -> list[Task]:
        """Return only the tasks that are still pending and due today."""
        today = date.today()
        return [task for task in tasks if task.status == "pending" and task.due_date == today]

    def _get_free_windows(self, owner: Owner) -> list[TimeBlock]:
        """Return the gaps left in the owner's day after subtracting their busy blocks."""
        busy_blocks = sorted(owner.busy_blocks, key=lambda b: b.start_time)
        free_windows: list[TimeBlock] = []
        cursor = owner.day_start_time

        for block in busy_blocks:
            if block.start_time > cursor:
                free_windows.append(TimeBlock(cursor, block.start_time))
            if block.end_time > cursor:
                cursor = block.end_time

        if cursor < owner.day_end_time:
            free_windows.append(TimeBlock(cursor, owner.day_end_time))

        return free_windows

    def _sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered with required tasks first, then by priority (high to low).

        Kept for reference/comparison — superseded by `_sort_by_constraint`, which `generate_plan`
        actually uses, since this ordering alone can let a flexible task starve a constrained one.
        """
        return sorted(
            tasks,
            key=lambda task: (
                0 if task.is_required else 1,
                _PRIORITY_ORDER.get(task.priority.value, len(_PRIORITY_ORDER)),
            ),
        )

    def _sort_by_constraint(self, tasks: list[Task], free_windows: list[TimeBlock]) -> list[Task]:
        """Return tasks ordered with the most constrained tasks first, so flexible tasks don't claim a
        window that only a narrowly-windowed task could have used. Ties break by required, then priority."""
        fit_counts = {
            task.id: sum(1 for window in free_windows if self._fits_in_window(task, window)) for task in tasks
        }
        return sorted(
            tasks,
            key=lambda task: (
                fit_counts[task.id],
                0 if task.is_required else 1,
                _PRIORITY_ORDER.get(task.priority.value, len(_PRIORITY_ORDER)),
            ),
        )

    def _fits_in_window(self, task: Task, window: TimeBlock) -> bool:
        """Return True if the task's duration fits in the window and respects its preferred time, if any."""
        if task.duration_minutes > _minutes_between(window.start_time, window.end_time):
            return False

        if task.preferred_time_window is not None:
            return _time_ranges_overlap(
                window.start_time,
                window.end_time,
                task.preferred_time_window.start_time,
                task.preferred_time_window.end_time,
            )

        return True
