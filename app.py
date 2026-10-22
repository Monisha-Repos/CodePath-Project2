from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan your pets' daily care: feedings, walks, meds, and appointments.")

# Streamlit reruns this script on every click, so the Owner lives in session_state.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan")

owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)


def task_rows(tasks: list[Task]) -> list[dict]:
    """Turn tasks into table rows for display."""
    return [
        {
            "Date": t.due_date.isoformat(),
            "Time": t.time,
            "Pet": t.pet_name,
            "Task": t.description,
            "Minutes": t.duration_minutes,
            "Priority": t.priority,
            "Repeats": t.frequency,
            "Done": "✅" if t.completed else "",
        }
        for t in tasks
    ]


# --- Owner & pets -------------------------------------------------------------

st.subheader("Owner & pets")
owner.name = st.text_input("Owner name", value=owner.name)

with st.form("add_pet", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1, 1])
    pet_name = col1.text_input("Pet name", value="Mochi")
    species = col2.selectbox("Species", ["dog", "cat", "other"])
    age = col3.number_input("Age", min_value=0, max_value=40, value=3)
    if st.form_submit_button("Add pet"):
        try:
            owner.add_pet(Pet(pet_name.strip(), species, int(age)))
            st.success(f"Added {pet_name.strip()}!")
        except ValueError as err:
            st.error(str(err))

if owner.pets:
    st.write(", ".join(f"**{p.name}** ({p.species}, {p.age}y, {len(p.tasks)} tasks)" for p in owner.pets))
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Tasks --------------------------------------------------------------------

st.subheader("Schedule a task")

if owner.pets:
    with st.form("add_task", clear_on_submit=True):
        col1, col2 = st.columns(2)
        task_pet = col1.selectbox("Pet", [p.name for p in owner.pets])
        description = col2.text_input("Task", value="Morning walk")
        col1, col2, col3 = st.columns(3)
        task_date = col1.date_input("Date", value=date.today())
        task_time = col2.time_input("Time", value=None, step=300)
        duration = col3.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        col1, col2 = st.columns(2)
        priority = col1.selectbox("Priority", ["high", "medium", "low"])
        frequency = col2.selectbox("Repeats", ["once", "daily", "weekly"])
        if st.form_submit_button("Add task"):
            if task_time is None or not description.strip():
                st.error("Please enter a task name and a time.")
            else:
                owner.get_pet(task_pet).add_task(
                    Task(
                        description.strip(),
                        task_time.strftime("%H:%M"),
                        int(duration),
                        priority,
                        frequency,
                        due_date=task_date,
                    )
                )
                st.success(f"Scheduled '{description.strip()}' for {task_pet} at {task_time.strftime('%H:%M')}.")
else:
    st.caption("Add a pet first to schedule tasks.")

st.divider()

# --- Today's schedule ---------------------------------------------------------

st.subheader("📅 Schedule")
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

view_date = st.date_input("Show schedule for", value=date.today(), key="view_date")
todays = scheduler.get_todays_schedule(view_date)

for warning in scheduler.detect_conflicts(todays):
    st.warning(f"⚠️ {warning}. Consider moving one of these so you aren't in two places at once.")

if todays:
    st.table(task_rows(todays))
    total = sum(t.duration_minutes for t in todays)
    st.caption(f"{len(todays)} pending tasks, about {total} minutes of care.")

    labels = {f"{t.time} · {t.pet_name} · {t.description}": t for t in todays}
    with st.form("complete_task"):
        choice = st.selectbox("Mark a task complete", list(labels))
        if st.form_submit_button("Mark complete"):
            done = labels[choice]
            upcoming = scheduler.mark_task_complete(done)
            msg = f"Completed '{done.description}' for {done.pet_name}."
            if upcoming:
                msg += f" Next {upcoming.frequency} occurrence added for {upcoming.due_date.isoformat()}."
            st.session_state.flash = msg  # shown after the rerun below
            st.rerun()
else:
    st.success("Nothing pending for this day. 🎉")

st.divider()

# --- All tasks with filters ---------------------------------------------------

st.subheader("🔎 All tasks")
col1, col2 = st.columns(2)
pet_filter = col1.selectbox("Pet", ["All pets"] + [p.name for p in owner.pets])
status_filter = col2.selectbox("Status", ["All", "Pending", "Completed"])

filtered = scheduler.filter_tasks(
    pet_name=None if pet_filter == "All pets" else pet_filter,
    completed={"All": None, "Pending": False, "Completed": True}[status_filter],
)
if filtered:
    st.table(task_rows(scheduler.sort_by_time(filtered)))
else:
    st.info("No tasks match these filters.")
