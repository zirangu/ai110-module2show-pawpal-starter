"""Temporary testing ground for verifying pawpal_system logic in the terminal."""

from datetime import time

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task, TimeBlock

owner = Owner(
    name="Jordan",
    day_start_time=time(7, 0),
    day_end_time=time(21, 0),
    busy_blocks=[TimeBlock(time(9, 0), time(17, 0), label="work")],
)

mochi = Pet(name="Mochi", species="dog")
whiskers = Pet(name="Whiskers", species="cat")
owner.pets = [mochi, whiskers]

mochi.tasks = [
    Task(
        title="Morning walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
        preferred_time_window=TimeBlock(time(7, 0), time(9, 0)),
        is_required=True,
    ),
    Task(
        title="Evening walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        preferred_time_window=TimeBlock(time(17, 0), time(20, 0)),
    ),
]

whiskers.tasks = [
    Task(
        title="Give medication",
        category=Category.MEDS,
        duration_minutes=10,
        priority=Priority.HIGH,
        is_required=True,
    ),
    Task(
        title="Brushing / grooming",
        category=Category.GROOMING,
        duration_minutes=15,
        priority=Priority.LOW,
    ),
]

scheduler = Scheduler()
plan = scheduler.generate_plan(owner.all_tasks(), owner)

print("=== Today's Schedule ===")
print(plan.explain())
