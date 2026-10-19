"""Temporary testing ground for verifying pawpal_system logic in the terminal."""

from datetime import time

from pawpal_system import Category, DailyPlan, Owner, Pet, Priority, ScheduledTask, Scheduler, Task, TimeBlock

owner = Owner(
    name="Jordan",
    day_start_time=time(7, 0),
    day_end_time=time(21, 0),
    busy_blocks=[TimeBlock(time(9, 0), time(17, 0), label="work")],
)

mochi = Pet(name="Mochi", species="dog")
whiskers = Pet(name="Whiskers", species="cat")
owner.pets = [mochi, whiskers]

# Tasks are added out of order (not grouped by pet, not in schedule order)
# to exercise sorting/filtering independently of insertion order.
mochi.add_task(
    Task(
        title="Evening walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        preferred_time_window=TimeBlock(time(17, 0), time(20, 0)),
    )
)
whiskers.add_task(
    Task(
        title="Brushing / grooming",
        category=Category.GROOMING,
        duration_minutes=15,
        priority=Priority.LOW,
    )
)
mochi.add_task(
    Task(
        title="Morning walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
        preferred_time_window=TimeBlock(time(7, 0), time(9, 0)),
        is_required=True,
    )
)
whiskers.add_task(
    Task(
        title="Give medication",
        category=Category.MEDS,
        duration_minutes=10,
        priority=Priority.HIGH,
        is_required=True,
    )
)

# Mark one task complete before filtering, to prove status filtering works.
whiskers.tasks[0].mark_complete()

scheduler = Scheduler()
plan = scheduler.generate_plan(owner.all_tasks(), owner)

print("=== Today's Schedule ===")
print(plan.explain())

print("\n=== Sorted (most constrained first) ===")
for task in scheduler._sort_by_constraint(owner.all_tasks(), scheduler._get_free_windows(owner)):
    print(f"{task.title} (priority={task.priority.value}, required={task.is_required})")

print("\n=== Filter: pending tasks only ===")
for task in owner.filter_tasks(status="pending"):
    print(f"{task.title} (status={task.status})")

print("\n=== Filter: tasks for Mochi only ===")
for task in owner.filter_tasks(pet_name="Mochi"):
    print(f"{task.title}")

# --- Conflict detection demo ---
# The scheduler's own greedy placement never double-books a window, so to actually
# exercise conflict detection we build a plan by hand with two tasks (different pets)
# overlapping at the same time.
conflict_task_a = Task(title="Walk Mochi", category=Category.WALK, duration_minutes=30, priority=Priority.HIGH)
conflict_task_b = Task(title="Walk Whiskers", category=Category.WALK, duration_minutes=30, priority=Priority.MEDIUM)

conflicting_plan = DailyPlan(
    scheduled_tasks=[
        ScheduledTask(task=conflict_task_a, start_time=time(8, 0), end_time=time(8, 30)),
        ScheduledTask(task=conflict_task_b, start_time=time(8, 15), end_time=time(8, 45)),
    ]
)

print("\n=== Conflict detection demo ===")
warnings = scheduler.check_conflicts(conflicting_plan)
if warnings:
    for warning in warnings:
        print(warning)
else:
    print("No conflicts detected.")
