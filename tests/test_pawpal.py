from pawpal_system import Category, Pet, Priority, Task


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
