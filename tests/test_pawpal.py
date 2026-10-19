import json
import os
import tempfile
from datetime import date, time, timedelta

from pawpal_system import (
    Category,
    DailyPlan,
    Frequency,
    Owner,
    Pet,
    Priority,
    ScheduledTask,
    Scheduler,
    Task,
    TimeBlock,
)


def test_mark_complete_changes_task_status():
    task = Task(
        title="Morning walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
    )

    assert task.status == "pending"
    assert task.completed_date is None
    task.mark_complete()
    assert task.status == "completed"
    assert task.completed_date == date.today()
    print("PASSED: test_mark_complete_changes_task_status")


def test_adding_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0

    task = Task(
        title="Feeding",
        category=Category.FEED,
        duration_minutes=10,
        priority=Priority.HIGH,
    )
    pet.add_task(task)

    assert len(pet.tasks) == 1
    print("PASSED: test_adding_task_increases_pet_task_count")


def _make_owner_with_two_pets():
    owner = Owner(name="Jordan")
    mochi = Pet(name="Mochi", species="dog")
    whiskers = Pet(name="Whiskers", species="cat")
    owner.pets = [mochi, whiskers]

    mochi.add_task(
        Task(title="Walk", category=Category.WALK, duration_minutes=20, priority=Priority.HIGH)
    )
    whiskers.add_task(
        Task(title="Grooming", category=Category.GROOMING, duration_minutes=15, priority=Priority.LOW)
    )
    whiskers.add_task(
        Task(title="Meds", category=Category.MEDS, duration_minutes=5, priority=Priority.HIGH)
    )
    return owner, mochi, whiskers


def test_filter_tasks_by_status():
    owner, _, whiskers = _make_owner_with_two_pets()
    whiskers.tasks[0].mark_complete()

    pending = owner.filter_tasks(status="pending")
    completed = owner.filter_tasks(status="completed")

    assert [task.title for task in pending] == ["Walk", "Meds"]
    assert [task.title for task in completed] == ["Grooming"]
    print("PASSED: test_filter_tasks_by_status")


def test_filter_tasks_by_pet_name():
    owner, _, _ = _make_owner_with_two_pets()

    mochi_tasks = owner.filter_tasks(pet_name="Mochi")
    whiskers_tasks = owner.filter_tasks(pet_name="Whiskers")

    assert [task.title for task in mochi_tasks] == ["Walk"]
    assert [task.title for task in whiskers_tasks] == ["Grooming", "Meds"]
    print("PASSED: test_filter_tasks_by_pet_name")


def test_filter_tasks_by_status_and_pet_name():
    owner, _, whiskers = _make_owner_with_two_pets()
    whiskers.tasks[1].mark_complete()  # Meds

    result = owner.filter_tasks(status="completed", pet_name="Whiskers")

    assert [task.title for task in result] == ["Meds"]
    print("PASSED: test_filter_tasks_by_status_and_pet_name")


# --- Pet/Owner structure edge cases ---

def test_add_pet_rejects_duplicate_name_case_insensitively():
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Mochi", species="dog"))

    try:
        owner.add_pet(Pet(name="mochi", species="cat"))
        assert False, "expected ValueError for duplicate pet name"
    except ValueError:
        pass

    assert len(owner.pets) == 1
    print("PASSED: test_add_pet_rejects_duplicate_name_case_insensitively")


def test_add_pet_allows_distinct_names():
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Mochi", species="dog"))
    owner.add_pet(Pet(name="Whiskers", species="cat"))

    assert [p.name for p in owner.pets] == ["Mochi", "Whiskers"]
    print("PASSED: test_add_pet_allows_distinct_names")


def test_pet_with_no_tasks_contributes_nothing():
    owner = Owner(name="Jordan")
    empty_pet = Pet(name="Biscuit", species="dog")
    owner.pets = [empty_pet]

    assert owner.all_tasks() == []

    plan = Scheduler().generate_plan(owner.all_tasks(), owner)
    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    print("PASSED: test_pet_with_no_tasks_contributes_nothing")


def test_owner_with_no_pets_generates_empty_plan():
    owner = Owner(name="Jordan")

    plan = Scheduler().generate_plan(owner.all_tasks(), owner)

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    print("PASSED: test_owner_with_no_pets_generates_empty_plan")


def test_owner_with_no_busy_blocks_has_one_free_window_spanning_the_day():
    owner = Owner(name="Jordan", day_start_time=time(7, 0), day_end_time=time(21, 0))

    windows = Scheduler()._get_free_windows(owner)

    assert len(windows) == 1
    assert windows[0].start_time == time(7, 0)
    assert windows[0].end_time == time(21, 0)
    print("PASSED: test_owner_with_no_busy_blocks_has_one_free_window_spanning_the_day")


# --- Scheduler placement edge cases ---

def test_task_longer_than_any_window_is_skipped_not_crashed():
    owner = Owner(name="Jordan", day_start_time=time(9, 0), day_end_time=time(9, 30))
    task = Task(title="Long walk", category=Category.WALK, duration_minutes=60, priority=Priority.HIGH)

    plan = Scheduler().generate_plan([task], owner)

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == [task]
    print("PASSED: test_task_longer_than_any_window_is_skipped_not_crashed")


def test_task_exactly_fills_window():
    owner = Owner(name="Jordan", day_start_time=time(9, 0), day_end_time=time(9, 30))
    task = Task(title="Walk", category=Category.WALK, duration_minutes=30, priority=Priority.HIGH)

    plan = Scheduler().generate_plan([task], owner)

    assert len(plan.scheduled_tasks) == 1
    scheduled = plan.scheduled_tasks[0]
    assert scheduled.start_time == time(9, 0)
    assert scheduled.end_time == time(9, 30)
    print("PASSED: test_task_exactly_fills_window")


def test_busy_blocks_given_out_of_order_still_produce_correct_free_windows():
    owner = Owner(
        name="Jordan",
        day_start_time=time(7, 0),
        day_end_time=time(21, 0),
        busy_blocks=[
            TimeBlock(time(17, 0), time(18, 0), label="dinner"),
            TimeBlock(time(9, 0), time(12, 0), label="work"),
        ],
    )

    windows = Scheduler()._get_free_windows(owner)

    assert [(w.start_time, w.end_time) for w in windows] == [
        (time(7, 0), time(9, 0)),
        (time(12, 0), time(17, 0)),
        (time(18, 0), time(21, 0)),
    ]
    print("PASSED: test_busy_blocks_given_out_of_order_still_produce_correct_free_windows")


def test_overlapping_busy_blocks_are_merged_without_a_negative_window():
    owner = Owner(
        name="Jordan",
        day_start_time=time(7, 0),
        day_end_time=time(21, 0),
        busy_blocks=[
            TimeBlock(time(9, 0), time(13, 0), label="work"),
            TimeBlock(time(11, 0), time(15, 0), label="meeting"),
        ],
    )

    windows = Scheduler()._get_free_windows(owner)

    assert [(w.start_time, w.end_time) for w in windows] == [
        (time(7, 0), time(9, 0)),
        (time(15, 0), time(21, 0)),
    ]
    print("PASSED: test_overlapping_busy_blocks_are_merged_without_a_negative_window")


def test_scheduled_tasks_are_returned_in_chronological_order():
    owner = Owner(
        name="Jordan",
        day_start_time=time(7, 0),
        day_end_time=time(21, 0),
        busy_blocks=[TimeBlock(time(9, 0), time(17, 0), label="work")],
    )
    evening = Task(
        title="Evening walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.MEDIUM,
        preferred_time_window=TimeBlock(time(17, 0), time(20, 0)),
    )
    morning = Task(
        title="Morning walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
        preferred_time_window=TimeBlock(time(7, 0), time(9, 0)),
    )

    # Passed in out of chronological order (evening before morning).
    plan = Scheduler().generate_plan([evening, morning], owner)

    start_times = [st.start_time for st in plan.scheduled_tasks]
    assert start_times == sorted(start_times)
    assert [st.task.title for st in plan.scheduled_tasks] == ["Morning walk", "Evening walk"]
    print("PASSED: test_scheduled_tasks_are_returned_in_chronological_order")


def test_preferred_window_entirely_outside_the_day_is_skipped():
    owner = Owner(name="Jordan", day_start_time=time(7, 0), day_end_time=time(21, 0))
    task = Task(
        title="Late night snack",
        category=Category.FEED,
        duration_minutes=10,
        priority=Priority.LOW,
        preferred_time_window=TimeBlock(time(22, 0), time(23, 0)),
    )

    plan = Scheduler().generate_plan([task], owner)

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == [task]
    print("PASSED: test_preferred_window_entirely_outside_the_day_is_skipped")


# --- Due-today / status filtering in generate_plan ---

def test_completed_task_excluded_from_todays_plan():
    owner = Owner(name="Jordan")
    task = Task(title="Walk", category=Category.WALK, duration_minutes=20, priority=Priority.HIGH)
    task.mark_complete()

    plan = Scheduler().generate_plan([task], owner)

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    print("PASSED: test_completed_task_excluded_from_todays_plan")


def test_task_due_tomorrow_excluded_from_todays_plan():
    owner = Owner(name="Jordan")
    task = Task(
        title="Walk",
        category=Category.WALK,
        duration_minutes=20,
        priority=Priority.HIGH,
        due_date=date.today() + timedelta(days=1),
    )

    plan = Scheduler().generate_plan([task], owner)

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    print("PASSED: test_task_due_tomorrow_excluded_from_todays_plan")


# --- Recurring task edge cases ---

def test_one_time_task_has_no_next_occurrence():
    task = Task(title="Vet visit", category=Category.GROOMING, duration_minutes=30, priority=Priority.HIGH)

    assert task.next_occurrence() is None
    print("PASSED: test_one_time_task_has_no_next_occurrence")


def test_daily_task_next_occurrence_advances_one_day():
    today = date.today()
    task = Task(
        title="Feed",
        category=Category.FEED,
        duration_minutes=10,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        due_date=today,
    )

    next_task = task.next_occurrence()

    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.status == "pending"
    assert next_task.id != task.id
    print("PASSED: test_daily_task_next_occurrence_advances_one_day")


def test_weekly_task_next_occurrence_advances_seven_days():
    today = date.today()
    task = Task(
        title="Grooming",
        category=Category.GROOMING,
        duration_minutes=30,
        priority=Priority.LOW,
        frequency=Frequency.WEEKLY,
        due_date=today,
    )

    next_task = task.next_occurrence()

    assert next_task.due_date == today + timedelta(weeks=1)
    print("PASSED: test_weekly_task_next_occurrence_advances_seven_days")


def test_completing_recurring_task_appends_exactly_one_new_task():
    pet = Pet(name="Mochi", species="dog")
    task = Task(
        title="Feed",
        category=Category.FEED,
        duration_minutes=10,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
    )
    pet.add_task(task)

    next_task = pet.complete_task(task.id)

    assert len(pet.tasks) == 2
    assert next_task is not None
    assert next_task.id != task.id
    assert task.status == "completed"
    assert next_task.status == "pending"
    print("PASSED: test_completing_recurring_task_appends_exactly_one_new_task")


def test_completing_daily_task_creates_task_due_the_following_day():
    today = date.today()
    pet = Pet(name="Mochi", species="dog")
    task = Task(
        title="Feed",
        category=Category.FEED,
        duration_minutes=10,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        due_date=today,
    )
    pet.add_task(task)

    next_task = pet.complete_task(task.id)

    assert next_task.due_date == today + timedelta(days=1)
    assert next_task in pet.tasks
    assert task.completed_date == today
    assert next_task.completed_date is None
    print("PASSED: test_completing_daily_task_creates_task_due_the_following_day")


def test_completing_one_time_task_does_not_append_anything():
    pet = Pet(name="Mochi", species="dog")
    task = Task(title="Vet visit", category=Category.GROOMING, duration_minutes=30, priority=Priority.HIGH)
    pet.add_task(task)

    next_task = pet.complete_task(task.id)

    assert next_task is None
    assert len(pet.tasks) == 1
    print("PASSED: test_completing_one_time_task_does_not_append_anything")


# --- Filtering edge cases ---

def test_filter_tasks_with_no_filters_returns_everything():
    owner, _, _ = _make_owner_with_two_pets()

    result = owner.filter_tasks()

    assert len(result) == 3
    print("PASSED: test_filter_tasks_with_no_filters_returns_everything")


def test_filter_tasks_on_owner_with_no_pets_returns_empty_list():
    owner = Owner(name="Jordan")

    assert owner.filter_tasks() == []
    assert owner.filter_tasks(status="pending") == []
    assert owner.filter_tasks(pet_name="Mochi") == []
    print("PASSED: test_filter_tasks_on_owner_with_no_pets_returns_empty_list")


# --- Conflict detection edge cases ---

def test_empty_plan_has_no_conflicts():
    plan = DailyPlan()

    assert plan.find_conflicts() == []
    assert plan.conflict_warnings() == []
    print("PASSED: test_empty_plan_has_no_conflicts")


def test_single_scheduled_task_has_no_conflicts():
    task = Task(title="Walk", category=Category.WALK, duration_minutes=30, priority=Priority.HIGH)
    plan = DailyPlan(scheduled_tasks=[ScheduledTask(task=task, start_time=time(8, 0), end_time=time(8, 30))])

    assert plan.find_conflicts() == []
    print("PASSED: test_single_scheduled_task_has_no_conflicts")


def test_adjacent_tasks_touching_at_the_boundary_are_not_a_conflict():
    task_a = Task(title="Walk", category=Category.WALK, duration_minutes=30, priority=Priority.HIGH)
    task_b = Task(title="Feed", category=Category.FEED, duration_minutes=15, priority=Priority.MEDIUM)
    plan = DailyPlan(
        scheduled_tasks=[
            ScheduledTask(task=task_a, start_time=time(8, 0), end_time=time(8, 30)),
            ScheduledTask(task=task_b, start_time=time(8, 30), end_time=time(8, 45)),
        ]
    )

    assert plan.find_conflicts() == []
    print("PASSED: test_adjacent_tasks_touching_at_the_boundary_are_not_a_conflict")


def test_only_the_actually_overlapping_pair_is_reported_among_three_tasks():
    task_a = Task(title="Walk Mochi", category=Category.WALK, duration_minutes=30, priority=Priority.HIGH)
    task_b = Task(title="Walk Whiskers", category=Category.WALK, duration_minutes=30, priority=Priority.MEDIUM)
    task_c = Task(title="Grooming", category=Category.GROOMING, duration_minutes=15, priority=Priority.LOW)
    plan = DailyPlan(
        scheduled_tasks=[
            ScheduledTask(task=task_a, start_time=time(8, 0), end_time=time(8, 30)),
            ScheduledTask(task=task_b, start_time=time(8, 15), end_time=time(8, 45)),
            ScheduledTask(task=task_c, start_time=time(10, 0), end_time=time(10, 15)),
        ]
    )

    conflicts = plan.find_conflicts()

    assert len(conflicts) == 1
    titles = {conflicts[0][0].task.title, conflicts[0][1].task.title}
    assert titles == {"Walk Mochi", "Walk Whiskers"}
    print("PASSED: test_only_the_actually_overlapping_pair_is_reported_among_three_tasks")


def test_scheduler_flags_duplicate_times_with_a_warning():
    task_a = Task(title="Walk Mochi", category=Category.WALK, duration_minutes=30, priority=Priority.HIGH)
    task_b = Task(title="Walk Whiskers", category=Category.WALK, duration_minutes=30, priority=Priority.MEDIUM)
    plan = DailyPlan(
        scheduled_tasks=[
            ScheduledTask(task=task_a, start_time=time(8, 0), end_time=time(8, 30)),
            ScheduledTask(task=task_b, start_time=time(8, 0), end_time=time(8, 30)),
        ]
    )

    warnings = Scheduler().check_conflicts(plan)

    assert len(warnings) == 1
    assert "Walk Mochi" in warnings[0]
    assert "Walk Whiskers" in warnings[0]
    print("PASSED: test_scheduler_flags_duplicate_times_with_a_warning")


def test_scheduler_reports_no_conflicts_for_a_non_overlapping_plan():
    owner = Owner(name="Jordan")
    task_a = Task(title="Walk", category=Category.WALK, duration_minutes=20, priority=Priority.HIGH)
    task_b = Task(title="Feed", category=Category.FEED, duration_minutes=10, priority=Priority.MEDIUM)

    plan = Scheduler().generate_plan([task_a, task_b], owner)

    assert Scheduler().check_conflicts(plan) == []
    print("PASSED: test_scheduler_reports_no_conflicts_for_a_non_overlapping_plan")


# --- Persistence edge cases ---

def test_task_round_trips_through_dict_including_nested_time_block():
    task = Task(
        title="Morning walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
        preferred_time_window=TimeBlock(time(7, 0), time(9, 0), label="morning"),
        is_required=True,
        due_date=date(2026, 1, 1),
        frequency=Frequency.DAILY,
    )
    task.mark_complete()

    restored = Task.from_dict(task.to_dict())

    assert restored == task
    print("PASSED: test_task_round_trips_through_dict_including_nested_time_block")


def test_task_with_no_preferred_window_round_trips():
    task = Task(title="Feed", category=Category.FEED, duration_minutes=10, priority=Priority.LOW)

    restored = Task.from_dict(task.to_dict())

    assert restored == task
    assert restored.preferred_time_window is None
    assert restored.completed_date is None
    print("PASSED: test_task_with_no_preferred_window_round_trips")


def test_owner_with_pets_and_tasks_round_trips_through_dict():
    owner, _, _ = _make_owner_with_two_pets()
    owner.busy_blocks.append(TimeBlock(time(9, 0), time(17, 0), label="work"))

    restored = Owner.from_dict(owner.to_dict())

    assert restored.name == owner.name
    assert restored.day_start_time == owner.day_start_time
    assert [b.to_dict() for b in restored.busy_blocks] == [b.to_dict() for b in owner.busy_blocks]
    assert [p.name for p in restored.pets] == [p.name for p in owner.pets]
    assert [t.title for t in restored.all_tasks()] == [t.title for t in owner.all_tasks()]
    print("PASSED: test_owner_with_pets_and_tasks_round_trips_through_dict")


def test_save_and_load_json_round_trips_owner_data():
    owner, mochi, _ = _make_owner_with_two_pets()
    mochi.tasks[0].mark_complete()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "data.json")
        owner.save_to_json(path)

        assert os.path.exists(path)
        with open(path) as f:
            raw = json.load(f)
        assert raw["name"] == "Jordan"

        loaded = Owner.load_from_json(path)

    assert loaded.name == owner.name
    assert [p.name for p in loaded.pets] == [p.name for p in owner.pets]
    loaded_tasks = loaded.all_tasks()
    assert any(t.status == "completed" for t in loaded_tasks)
    print("PASSED: test_save_and_load_json_round_trips_owner_data")
