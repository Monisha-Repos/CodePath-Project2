# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

Three core actions a user should be able to perform:

1. **Add a pet** to their household (name, species, age).
2. **Schedule a care task** for a pet (walk, feeding, meds, grooming) at a specific time, optionally repeating daily or weekly.
3. **See today's schedule** across all pets, in time order, with a warning if two tasks collide.

My initial UML (`diagrams/uml.mmd`) had four classes:

- **Task** (dataclass): one care activity. It holds the description, time (`"HH:MM"`), duration, priority, frequency (`once`/`daily`/`weekly`), due date, and completion status. It can mark itself complete and build its next occurrence.
- **Pet** (dataclass): the pet's details (name, species, age) plus its list of tasks. It adds and removes its own tasks.
- **Owner**: holds the list of pets. Its key method, `get_all_tasks()`, flattens every pet's tasks into one list, so no other class has to reach into individual pets.
- **Scheduler**: the "brain". It is given an `Owner` and reads tasks only through `get_all_tasks()`. It sorts, filters, detects conflicts, completes recurring tasks, and builds today's schedule.

Relationships: an Owner *has* many Pets, a Pet *has* many Tasks, and the Scheduler *depends on* the Owner.

**b. Design changes**

Yes, the design changed in a few places:

- **`Task` carries a `pet_name`.** Once the Scheduler works on a flat list from `Owner.get_all_tasks()`, it no longer knows which pet a task came from. That matters for showing the pet in the schedule, for conflict messages like "Pill (Mochi), Breakfast (Luna)", and for putting the next occurrence of a recurring task back on the right pet. `Pet.add_task()` now sets `pet_name` automatically, so callers can't get it wrong.
- **The Scheduler stores no task list of its own.** Each method calls `owner.get_all_tasks()` when it runs. An earlier idea was to copy the tasks into the Scheduler once, but that copy goes stale as soon as a pet or task is added in the UI.
- **`filter_tasks()` takes an optional `tasks` argument**, so filters can be chained with sorting. `get_todays_schedule()` is built from `filter_tasks()` + `sort_by_time()`.
- **`Task.__post_init__` validates input.** I added it after realizing that sorting `"HH:MM"` strings breaks for `"9:00"` vs `"10:00"`. Times are normalized to zero-padded `HH:MM`, and bad priorities or frequencies are rejected up front.

The final diagram is in `diagrams/uml_final.mmd`.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers:

- **Time and date:** the main ordering. A pet owner reads a schedule top to bottom through the day.
- **Priority:** used as a tie-breaker when two tasks share a time slot, so "Meds (high)" is listed before "Play (low)".
- **Completion status:** completed tasks drop out of today's schedule and are ignored by conflict detection.
- **Recurrence:** daily and weekly tasks regenerate themselves when completed.

Time came first because the core question a pet owner asks is "what do I need to do next?" Priority mattered less for ordering, because a 7:30 walk still happens before an 8:00 pill however important the pill is. So priority only breaks ties.

**b. Tradeoffs**

**Conflict detection only checks exact start-time matches, not overlapping durations.** A 30-minute walk at 07:30 and a pill at 07:45 overlap in real life, but they are not flagged.

This is reasonable for now because:

- Most pet care tasks are short, and owners usually schedule them on round times, so exact clashes are the common case.
- Exact matching is simple and fast: group by `(date, time)` in a dict and report any slot with 2+ tasks. It never produces confusing partial-overlap warnings for tasks that could easily be done back to back (feeding two pets at once is fine).
- It returns warning strings instead of raising, so a clash informs the owner without blocking them.

Interval-overlap checking (sort by start, then compare each task's end to the next task's start) would be the natural next step.

---

## 3. AI Collaboration

**a. How you used AI**

I used Claude Code (an AI coding agent in VS Code) in agent mode for most of the project. It:

- drafted the Mermaid UML from the four-class design and turned it into dataclass skeletons
- implemented the Scheduler algorithms (sorting with a `lambda` key, filtering, `timedelta` recurrence, dict-based conflict detection)
- wrote `main.py` and the pytest suite, and ran both to confirm the results
- wired `app.py` to the backend using `st.session_state`
- diagnosed an environment problem: my `.venv` uses ARM64 Python 3.13, which has no prebuilt `pyarrow` wheel, so `streamlit` would not install. The agent found that my other venv (`.venv-1`, x64 Python 3.14) already had everything installed and used that instead.

The most useful features were **agent mode with terminal access**, which let it run `python main.py` and `python -m pytest` and react to real output instead of guessing, and **multi-file editing** for the recurrence change, which touched `Task`, `Scheduler`, and the tests together.

The most helpful prompts were specific and asked for verification. For example, "the Scheduler must read from the Owner method, not a single pet" and "what are the edge cases for sorting and recurring tasks?"

**b. Judgment and verification**

- **Keeping the readable conflict detector.** A more compact version using `itertools.groupby` or a `Counter` comprehension was possible. I kept the explicit loop that builds a `dict` of slots and then emits warnings, because it is easier for a reader to follow and it is just as fast for a household-sized task list.
- **Not trusting raw string sorting.** The common suggestion is `sorted(tasks, key=lambda t: t.time)`. That only works if every time is zero-padded. Instead of accepting it as-is, I normalized times in `Task.__post_init__` and added `test_sort_handles_unpadded_hours` to prove `"9:00"` sorts before `"10:00"`.
- **Verifying the UI, not just the backend.** After wiring the Streamlit app, a headless `streamlit.testing` run showed that the "Mark complete" success message disappeared, because `st.rerun()` wiped it. The fix was to store the message in `st.session_state` and show it after the rerun. That bug would not have shown up in the backend tests.

I checked every AI change by running `main.py`, reading the printed schedule, and running the full pytest suite (17 passing).

---

## 4. Testing and Verification

**a. What you tested**

- `mark_complete()` changes the status, and `add_task()` increases the pet's task count
- the Scheduler collects tasks from **all** pets, and an empty household gives an empty schedule
- duplicate pet names are rejected, and invalid times like `"25:00"` raise an error
- sorting returns chronological order, handles unpadded hours, and breaks ties by priority
- filtering works by pet (case-insensitive), by status, and both combined
- recurrence: daily adds +1 day, weekly adds +1 week, one-off tasks create nothing, and completed tasks leave today's schedule
- conflicts: same time across pets and for the same pet are flagged, while different days or completed tasks are not

These are the behaviors a pet owner relies on. A wrong order, a missed recurring feeding, or a silent double-booking would make the app untrustworthy.

**b. Confidence**

**4/5.** All core behaviors and the main edge cases pass. What I would test next:

- overlapping durations (e.g. a 07:30 30-minute walk vs a 07:45 task) once interval checking exists
- completing an old recurring task several times in a row, or completing a task twice
- recurrence across month or year boundaries and leap days (`timedelta` should handle these, but a test would confirm it)
- removing a pet that still has tasks
- automated UI tests for the Streamlit forms

---

## 5. Reflection

**a. What went well**

The clean separation between layers. Because `Scheduler` only talks to `Owner.get_all_tasks()`, the same logic drives the CLI demo, the tests, and the Streamlit UI unchanged. Adding the UI was mostly calling methods that already existed and were already tested.

**b. What you would improve**

- Interval-based conflict detection using `duration_minutes`.
- Saving the household to a JSON file so data survives closing the browser tab (right now `st.session_state` lasts only one session).
- Editing and deleting tasks from the UI, plus "skip this occurrence" for recurring tasks.
- A "fit my day" planner that uses priority and the time the owner has available to suggest what to drop when the day is too full.

**c. Key takeaway**

Being the "lead architect" means owning the decisions that the AI will otherwise make implicitly: where data lives, which class talks to which, and what counts as "correct." The AI was fast at producing code, but the important moments were catching assumptions, such as zero-padded time strings, a stale task copy, or a UI message that vanishes on rerun, and insisting on running the code and tests rather than trusting that it looked right.

Also, this project was done in a single agent session rather than separate chat sessions per phase. Separate sessions would have kept each phase's context focused, but one session with agent mode kept the design decisions consistent from UML through UI. Committing at each phase boundary (skeleton, core logic, tests, UI, docs) gave the history the same structure that separate sessions would have.
