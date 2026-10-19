from datetime import time

import pandas as pd
import streamlit as st

from pawpal_system import Category, Frequency, Owner, Pet, Priority, Scheduler, Task, TimeBlock

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to **PawPal+** — a pet care planning assistant. Set up your availability and pets in
the sidebar, then add care tasks and generate a daily plan with reasoning below.
"""
)

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")

owner: Owner = st.session_state.owner

with st.sidebar:
    st.header("💾 Save / Load")
    save_col, load_col = st.columns(2)
    with save_col:
        if st.button("💾 Save", use_container_width=True):
            owner.save_to_json(DATA_FILE)
            st.success(f"Saved to {DATA_FILE}.")
    with load_col:
        if st.button("📂 Load", use_container_width=True):
            try:
                st.session_state.owner = Owner.load_from_json(DATA_FILE)
                st.success(f"Loaded from {DATA_FILE}.")
                st.rerun()
            except FileNotFoundError:
                st.error(f"No saved data found at {DATA_FILE}.")

    st.divider()

    st.header("👤 Owner Info & Availability")
    owner.name = st.text_input("Owner name", value=owner.name)
    col1, col2 = st.columns(2)
    with col1:
        owner.day_start_time = st.time_input("Day starts", value=owner.day_start_time)
    with col2:
        owner.day_end_time = st.time_input("Day ends", value=owner.day_end_time)

    st.caption("Add blocks of the day you're unavailable (e.g. work hours).")
    busy_label = st.text_input("Busy block label", value="work")
    busy_col1, busy_col2 = st.columns(2)
    with busy_col1:
        busy_start = st.time_input("Busy start", value=time(9, 0))
    with busy_col2:
        busy_end = st.time_input("Busy end", value=time(17, 0))
    if st.button("🚧 Add busy block", use_container_width=True):
        owner.busy_blocks.append(TimeBlock(busy_start, busy_end, busy_label))

    if owner.busy_blocks:
        st.table(
            [
                {"label": b.label, "start": b.start_time.strftime("%H:%M"), "end": b.end_time.strftime("%H:%M")}
                for b in owner.busy_blocks
            ]
        )

    st.divider()

    st.header("🐶 Pets")
    new_pet_name = st.text_input("Pet name", value="Mochi")
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
    if st.button("➕ Add pet", type="primary", use_container_width=True):
        try:
            owner.add_pet(Pet(name=new_pet_name, species=new_pet_species))
            st.success(f"Added {new_pet_name}.")
        except ValueError as e:
            st.error(str(e))

    if not owner.pets:
        st.info("No pets yet. Add one above.")
    else:
        st.write("Current pets:")
        st.table([{"name": p.name, "species": p.species, "tasks": len(p.tasks)} for p in owner.pets])

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

    frequency = st.selectbox(
        "Repeats",
        [f.value for f in Frequency],
        format_func=lambda v: {"one_time": "One-time", "daily": "Daily", "weekly": "Weekly"}[v],
    )

    preferred_window = None
    if use_preferred_window:
        win_col1, win_col2 = st.columns(2)
        with win_col1:
            window_start = st.time_input("Preferred start", value=time(7, 0))
        with win_col2:
            window_end = st.time_input("Preferred end", value=time(9, 0))
        preferred_window = TimeBlock(window_start, window_end)

    if st.button("➕ Add task", type="primary"):
        selected_pet.add_task(
            Task(
                title=task_title,
                category=Category(category),
                duration_minutes=int(duration),
                priority=Priority(priority),
                preferred_time_window=preferred_window,
                is_required=is_required,
                frequency=Frequency(frequency),
            )
        )
        st.success(f"Added '{task_title}' for {selected_pet.name}.")

    all_tasks = owner.all_tasks()
    if not all_tasks:
        st.info("No tasks yet. Add one above.")
    else:
        st.write("#### Current tasks")

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            status_filter = st.selectbox("Filter by status", ["all", "pending", "completed"])
        with filter_col2:
            pet_filter = st.selectbox("Filter by pet", ["all"] + pet_names)

        filtered_tasks = owner.filter_tasks(
            status=None if status_filter == "all" else status_filter,
            pet_name=None if pet_filter == "all" else pet_filter,
        )

        if not filtered_tasks:
            st.info("No tasks match that filter.")
        else:
            st.table(
                [
                    {
                        "pet": next(p.name for p in owner.pets if task in p.tasks),
                        "title": task.title,
                        "category": task.category.value,
                        "duration_minutes": task.duration_minutes,
                        "priority": task.priority.value,
                        "required": task.is_required,
                        "status": task.status,
                        "repeats": task.frequency.value,
                        "due_date": task.due_date.strftime("%Y-%m-%d"),
                        "completed_date": (
                            task.completed_date.strftime("%Y-%m-%d") if task.completed_date else ""
                        ),
                    }
                    for task in filtered_tasks
                ]
            )

        def _task_label(index: int, task: Task) -> str:
            # Titles aren't required to be unique, so disambiguate with a row number and owning pet,
            # matching the plain 0, 1, 2... row numbering used elsewhere in the tables.
            owning_pet_name = next(p.name for p in owner.pets if task in p.tasks)
            return f"{index}_{owning_pet_name}_{task.title}"

        def _complete_task_and_report(task: Task) -> None:
            owning_pet = next(p for p in owner.pets if task in p.tasks)
            next_task = owning_pet.complete_task(task.id)
            if next_task is not None:
                st.success(
                    f"'{task.title}' marked complete. Next occurrence added, "
                    f"due {next_task.due_date.strftime('%Y-%m-%d')}."
                )
            else:
                st.success(f"'{task.title}' marked complete.")

        pending_tasks = [t for t in all_tasks if t.status == "pending"]
        if pending_tasks:
            label_to_task = {_task_label(i, t): t for i, t in enumerate(pending_tasks)}
            complete_col1, complete_col2 = st.columns([3, 1])
            with complete_col1:
                task_to_complete_label = st.selectbox("Mark a task complete", list(label_to_task.keys()))
            with complete_col2:
                st.write("")
                if st.button("✅ Mark complete", use_container_width=True):
                    _complete_task_and_report(label_to_task[task_to_complete_label])

st.divider()

st.subheader("Build Schedule")

if "schedule_generated" not in st.session_state:
    st.session_state.schedule_generated = False

if st.button("📅 Generate schedule", type="primary", use_container_width=True):
    st.session_state.schedule_generated = True

for message in st.session_state.pop("pending_messages", []):
    st.success(message)

if st.session_state.schedule_generated:
    all_tasks = owner.all_tasks()
    if not all_tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler()
        # Recomputed on every rerun (e.g. after marking a task complete below) so the
        # schedule always reflects the current task statuses rather than going stale.
        plan = scheduler.generate_plan(all_tasks, owner)

        # Conflicts shouldn't occur from the scheduler's own placement, but this is checked
        # and surfaced anyway as a safety net rather than silently trusting the scheduler.
        conflict_warnings = scheduler.check_conflicts(plan)
        if conflict_warnings:
            for warning in conflict_warnings:
                st.error(f"⚠️ Scheduling conflict: {warning}")
        else:
            st.success("✅ Schedule generated with no conflicts.")

        if plan.scheduled_tasks:
            st.write("### Today's Schedule")
            st.caption("Check off the tasks you've finished, then hit Confirm completion.")

            schedule_df = pd.DataFrame(
                [
                    {
                        "Done": False,
                        "Start": st_task.start_time.strftime("%H:%M"),
                        "End": st_task.end_time.strftime("%H:%M"),
                        "Task": st_task.task.title,
                        "Priority": st_task.task.priority.value,
                        "_task_id": st_task.task.id,
                    }
                    for st_task in plan.scheduled_tasks
                ]
            )

            edited_df = st.data_editor(
                schedule_df,
                column_config={
                    "Done": st.column_config.CheckboxColumn("Done"),
                    "_task_id": None,  # hide the internal id column
                },
                disabled=["Start", "End", "Task", "Priority"],
                hide_index=True,
                key="schedule_editor",
            )

            if st.button("✔️ Confirm completion", type="primary"):
                checked_task_ids = edited_df.loc[edited_df["Done"], "_task_id"].tolist()
                if not checked_task_ids:
                    st.info("No tasks were checked off.")
                else:
                    messages = []
                    for task_id in checked_task_ids:
                        scheduled_task = next(st_task for st_task in plan.scheduled_tasks if st_task.task.id == task_id)
                        owning_pet = next(p for p in owner.pets if scheduled_task.task in p.tasks)
                        next_task = owning_pet.complete_task(task_id)
                        if next_task is not None:
                            messages.append(
                                f"'{scheduled_task.task.title}' marked complete. Next occurrence due "
                                f"{next_task.due_date.strftime('%Y-%m-%d')}."
                            )
                        else:
                            messages.append(f"'{scheduled_task.task.title}' marked complete.")
                    # Completing a task changes what generate_plan() returns, but the table above
                    # was already drawn this run — rerun immediately so it reflects the new state
                    # without needing a second click. The success messages are queued through
                    # session_state since a rerun discards anything rendered after this point.
                    st.session_state.pending_messages = messages
                    st.rerun()
        else:
            st.info("No tasks were scheduled.")

        if plan.skipped_tasks:
            st.warning(f"{len(plan.skipped_tasks)} task(s) couldn't fit in today's schedule:")
            st.table(
                [
                    {"task": task.title, "priority": task.priority.value, "duration_minutes": task.duration_minutes}
                    for task in plan.skipped_tasks
                ]
            )

        st.write("### Why this plan?")
        st.text(plan.explain())
