# PawPal+ (Module 2 Project)

**PawPal+** is a pet care planner built with Python OOP and Streamlit. An owner adds pets, schedules care tasks (feedings, walks, meds, appointments), and gets a time-ordered daily schedule with conflict warnings and automatic rescheduling of recurring tasks.

## Features

- **Multiple pets per owner.** Every pet's tasks are combined into one schedule.
- **Sorting by time.** Tasks are ordered chronologically (date, then `HH:MM`). When two tasks share a time, the higher-priority one comes first.
- **Filtering.** Show tasks for one pet, only pending tasks, only completed tasks, or any combination.
- **Conflict warnings.** If two pending tasks start at the same date and time, for the same pet or different pets, you get a readable warning. The program never crashes over a clash.
- **Daily and weekly recurrence.** Completing a recurring task automatically creates the next occurrence (`+1 day` or `+1 week`, calculated with `timedelta`).
- **Input validation.** Times are checked and normalized (`"9:00"` becomes `"09:00"`). Unknown priorities or frequencies, and duplicate pet names, are rejected.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py            # CLI demo
python -m pytest          # run tests
streamlit run app.py      # web UI
```

## Implementation summary

All logic lives in `pawpal_system.py`. The UI (`app.py`) and the CLI demo (`main.py`) only call into it.

| Class | Role |
|-------|------|
| `Task` (dataclass) | One activity: description, time, duration, priority, frequency, due date, completion status, and the pet's name. `mark_complete()` marks it done. `next_occurrence()` builds the next daily or weekly copy. |
| `Pet` (dataclass) | Pet details plus its list of tasks. `add_task()` tags the task with the pet's name. |
| `Owner` | Holds the pets. `get_all_tasks()` returns every pet's tasks as one list. |
| `Scheduler` | The "brain". It reads tasks **only** through `Owner.get_all_tasks()`, then sorts, filters, detects conflicts, completes tasks, and builds the day's schedule. |

In the Streamlit app, the `Owner` object is stored in `st.session_state`, so it survives Streamlit's rerun on every click. The add-pet form calls `Owner.add_pet()`, the add-task form calls `Pet.add_task()`, and the schedule view is rendered from `Scheduler` methods.

UML diagrams: [diagrams/uml.mmd](diagrams/uml.mmd) (Phase 1 draft) and [diagrams/uml_final.mmd](diagrams/uml_final.mmd) (matches the final code).

## 🖥️ Sample Output

Output of `python main.py`:

```
PawPal+ for Jordan (2 pets, 6 tasks)

Today's Schedule (sorted by time)
---------------------------------
  [ ] 2026-10-22 07:30  Mochi   Morning walk        30 min  high   daily
  [ ] 2026-10-22 08:00  Mochi   Heartworm pill       5 min  high   once
  [ ] 2026-10-22 08:00  Luna    Breakfast            5 min  high   daily
  [ ] 2026-10-22 12:00  Luna    Brush coat          10 min  low    weekly
  [ ] 2026-10-22 15:00  Luna    Vet checkup         60 min  high   once
  [ ] 2026-10-22 18:30  Mochi   Evening walk        30 min  medium daily

Conflict check
--------------
  WARNING: Conflict on 2026-10-22 at 08:00: Heartworm pill (Mochi), Breakfast (Luna)

Completed 'Morning walk' -> next one auto-created for 2026-10-23

Mochi's tasks (filter by pet, sorted)
-------------------------------------
  [x] 2026-10-22 07:30  Mochi   Morning walk        30 min  high   daily
  [ ] 2026-10-22 08:00  Mochi   Heartworm pill       5 min  high   once
  [ ] 2026-10-22 18:30  Mochi   Evening walk        30 min  medium daily
  [ ] 2026-10-23 07:30  Mochi   Morning walk        30 min  high   daily

Completed tasks (filter by status)
----------------------------------
  [x] 2026-10-22 07:30  Mochi   Morning walk        30 min  high   daily

Today's Schedule after completing the walk
------------------------------------------
  [ ] 2026-10-22 08:00  Mochi   Heartworm pill       5 min  high   once
  [ ] 2026-10-22 08:00  Luna    Breakfast            5 min  high   daily
  [ ] 2026-10-22 12:00  Luna    Brush coat          10 min  low    weekly
  [ ] 2026-10-22 15:00  Luna    Vet checkup         60 min  high   once
  [ ] 2026-10-22 18:30  Mochi   Evening walk        30 min  medium daily
```

## 🧪 Testing PawPal+

```bash
python -m pytest
```

`tests/test_pawpal.py` has 17 tests covering:

- **Basics:** `mark_complete()` changes the status, and adding a task increases the pet's task count.
- **Multi-pet:** the scheduler sees tasks from every pet, a household with no tasks gives an empty schedule, and duplicate pet names are rejected.
- **Sorting correctness:** tasks come back in chronological order; `"9:00"` sorts before `"10:00"`; time ties are broken by priority; invalid times are rejected.
- **Filtering:** by pet name (case-insensitive), by status, and both combined.
- **Recurrence:** a daily task creates a new task for the next day, a weekly task creates one for next week, and a one-off task creates nothing. A completed task drops off today's schedule while the new one shows up tomorrow.
- **Conflict detection:** same time across pets, same time for the same pet, and no false alarms for different days or completed tasks.

Sample test output:

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\_MonishaN\CS\CodePath\Project2\ai110-module2show-pawpal-starter
plugins: anyio-4.15.1
collected 17 items

tests\test_pawpal.py .................                                   [100%]

============================= 17 passed in 0.04s ==============================
```

**Confidence level: ★★★★☆ (4/5).** Every core behavior and the main edge cases are tested and pass. One star is held back because conflict detection only catches exact start-time matches (overlapping durations are not detected), and the Streamlit UI was checked with a headless script rather than a full browser test suite.

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | `sorted()` with a `lambda` key of `(due_date, time, priority rank)`. Times are zero-padded `HH:MM` (normalized in `Task.__post_init__`), so string order equals clock order. |
| Filtering | `Scheduler.filter_tasks(pet_name=..., completed=...)` | Each filter is optional (`None` = any), and they can be combined. `get_todays_schedule()` uses it to keep only pending tasks due today. |
| Conflict handling | `Scheduler.detect_conflicts()` | Groups pending tasks by `(date, time)` in a dict and returns one warning string per slot with 2+ tasks. Lightweight: it returns a list of warnings and never raises. Only exact start times are compared. |
| Recurring tasks | `Task.next_occurrence()`, `Scheduler.mark_task_complete()` | Completing a `daily` or `weekly` task adds a copy due `+1 day` or `+1 week` (`timedelta`) to the same pet. `once` tasks just complete. |

## 📸 Demo Walkthrough

**Main UI features** (`streamlit run app.py`):

- **Owner & pets:** set the owner's name and add pets (name, species, age). Duplicate names show an error.
- **Schedule a task:** choose a pet, then enter a task name, date, time, duration, priority, and whether it repeats (once, daily, or weekly).
- **📅 Schedule:** choose a day to see its pending tasks as a table sorted by time, with the total minutes of care. Any time clashes appear as yellow `st.warning` banners above the table. A "Mark complete" form completes a task and, for recurring tasks, confirms when the next occurrence was added.
- **🔎 All tasks:** filter every task by pet and by status (all, pending, or completed).

**Example workflow:**

1. Enter the owner name "Jordan", then add a dog named **Mochi** and a cat named **Luna**.
2. Schedule "Morning walk" for Mochi at 07:30, repeating **daily**.
3. Schedule "Heartworm pill" for Mochi at 08:00 and "Breakfast" for Luna at 08:00.
4. Look at the **📅 Schedule** section: the tasks are listed 07:30, 08:00, 08:00 (sorted, even if you added them out of order). A warning reads *"Conflict on … at 08:00: Heartworm pill (Mochi), Breakfast (Luna)"*.
5. Mark "Morning walk" complete. A success message says the next daily occurrence was added for tomorrow, and the walk drops off today's list.
6. In **🔎 All tasks**, filter by Pet = Mochi and Status = Completed to see the finished walk. Change the schedule date to tomorrow to see the new walk.

**Key Scheduler behaviors shown:** chronological sorting, conflict warnings, daily recurrence, and filtering by pet and status.

**Sample CLI output** from `python main.py`:

```
Today's Schedule (sorted by time)
---------------------------------
  [ ] 2026-10-22 07:30  Mochi   Morning walk        30 min  high   daily
  [ ] 2026-10-22 08:00  Mochi   Heartworm pill       5 min  high   once
  [ ] 2026-10-22 08:00  Luna    Breakfast            5 min  high   daily
  [ ] 2026-10-22 12:00  Luna    Brush coat          10 min  low    weekly
  [ ] 2026-10-22 15:00  Luna    Vet checkup         60 min  high   once
  [ ] 2026-10-22 18:30  Mochi   Evening walk        30 min  medium daily

Conflict check
--------------
  WARNING: Conflict on 2026-10-22 at 08:00: Heartworm pill (Mochi), Breakfast (Luna)

Completed 'Morning walk' -> next one auto-created for 2026-10-23
```
