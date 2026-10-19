from datetime import time

import streamlit as st

from pawpal_system import Category, Owner, Pet, Priority, Scheduler, Task, TimeBlock

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+** — a pet care planning assistant. Set up your availability, add your
pets and their care tasks, then generate a daily plan with reasoning.
"""
)

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")

owner: Owner = st.session_state.owner

st.divider()

st.subheader("Owner Info & Availability")
col1, col2, col3 = st.columns(3)
with col1:
    owner.name = st.text_input("Owner name", value=owner.name)
with col2:
    owner.day_start_time = st.time_input("Day starts", value=owner.day_start_time)
with col3:
    owner.day_end_time = st.time_input("Day ends", value=owner.day_end_time)

st.caption("Add blocks of the day you're unavailable (e.g. work hours).")
busy_col1, busy_col2, busy_col3, busy_col4 = st.columns([2, 2, 2, 1])
with busy_col1:
    busy_label = st.text_input("Busy block label", value="work")
with busy_col2:
    busy_start = st.time_input("Busy start", value=time(9, 0))
with busy_col3:
    busy_end = st.time_input("Busy end", value=time(17, 0))
with busy_col4:
    st.write("")
    if st.button("Add busy block"):
        owner.busy_blocks.append(TimeBlock(busy_start, busy_end, busy_label))

if owner.busy_blocks:
    st.table(
        [
            {"label": b.label, "start": b.start_time.strftime("%H:%M"), "end": b.end_time.strftime("%H:%M")}
            for b in owner.busy_blocks
        ]
    )

st.divider()

st.subheader("Pets")
pet_col1, pet_col2, pet_col3 = st.columns([2, 2, 1])
with pet_col1:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with pet_col2:
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
with pet_col3:
    st.write("")
    if st.button("Add pet"):
        owner.pets.append(Pet(name=new_pet_name, species=new_pet_species))

if not owner.pets:
    st.info("No pets yet. Add one above.")
else:
    st.write("Current pets:")
    st.table([{"name": p.name, "species": p.species, "tasks": len(p.tasks)} for p in owner.pets])

st.divider()

st.subheader("Tasks")

if not owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]
    selected_pet_name = st.selectbox("Pet", pet_names)
    selected_pet = next(p for p in owner.pets if p.name == selected_pet_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", [p.value for p in Priority], index=2)

    col4, col5, col6 = st.columns(3)
    with col4:
        category = st.selectbox("Category", [c.value for c in Category])
    with col5:
        is_required = st.checkbox("Required (can't be skipped)")
    with col6:
        use_preferred_window = st.checkbox("Has a preferred time window")

    preferred_window = None
    if use_preferred_window:
        win_col1, win_col2 = st.columns(2)
        with win_col1:
            window_start = st.time_input("Preferred start", value=time(7, 0))
        with win_col2:
            window_end = st.time_input("Preferred end", value=time(9, 0))
        preferred_window = TimeBlock(window_start, window_end)

    if st.button("Add task"):
        selected_pet.add_task(
            Task(
                title=task_title,
                category=Category(category),
                duration_minutes=int(duration),
                priority=Priority(priority),
                preferred_time_window=preferred_window,
                is_required=is_required,
            )
        )

    all_tasks = owner.all_tasks()
    if all_tasks:
        st.write("Current tasks:")
        st.table(
            [
                {
                    "pet": next(p.name for p in owner.pets if task in p.tasks),
                    "title": task.title,
                    "category": task.category.value,
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority.value,
                    "required": task.is_required,
                }
                for task in all_tasks
            ]
        )
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")

if st.button("Generate schedule"):
    all_tasks = owner.all_tasks()
    if not all_tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler()
        plan = scheduler.generate_plan(all_tasks, owner)

        if plan.scheduled_tasks:
            st.write("### Today's Schedule")
            st.table(
                [
                    {
                        "start": st_task.start_time.strftime("%H:%M"),
                        "end": st_task.end_time.strftime("%H:%M"),
                        "task": st_task.task.title,
                        "priority": st_task.task.priority.value,
                    }
                    for st_task in plan.scheduled_tasks
                ]
            )

        if plan.skipped_tasks:
            st.write("### Skipped")
            st.table(
                [
                    {"task": task.title, "priority": task.priority.value, "duration_minutes": task.duration_minutes}
                    for task in plan.skipped_tasks
                ]
            )

        st.write("### Why this plan?")
        st.text(plan.explain())
