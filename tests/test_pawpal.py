from pawpal_system import Category, Owner, Pet, Priority, Task


def test_mark_complete_changes_task_status():
    task = Task(
        title="Morning walk",
        category=Category.WALK,
        duration_minutes=30,
        priority=Priority.HIGH,
    )

    assert task.status == "pending"
    task.mark_complete()
    assert task.status == "completed"


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


def test_filter_tasks_by_pet_name():
    owner, _, _ = _make_owner_with_two_pets()

    mochi_tasks = owner.filter_tasks(pet_name="Mochi")
    whiskers_tasks = owner.filter_tasks(pet_name="Whiskers")

    assert [task.title for task in mochi_tasks] == ["Walk"]
    assert [task.title for task in whiskers_tasks] == ["Grooming", "Meds"]


def test_filter_tasks_by_status_and_pet_name():
    owner, _, whiskers = _make_owner_with_two_pets()
    whiskers.tasks[1].mark_complete()  # Meds

    result = owner.filter_tasks(status="completed", pet_name="Whiskers")

    assert [task.title for task in result] == ["Meds"]
