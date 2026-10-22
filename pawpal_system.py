"""PawPal+ logic layer: Owner, Pet, Task, and Scheduler classes."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
FREQUENCY_STEP = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1)}


def _parse_time(value: str) -> str:
    """Validate an "H:MM"/"HH:MM" string and return it zero-padded as "HH:MM"."""
    return datetime.strptime(value.strip(), "%H:%M").strftime("%H:%M")


@dataclass
class Task:
    """A single pet care activity scheduled at a time of day."""

    description: str
    time: str  # "HH:MM", 24-hour clock
    duration_minutes: int = 15
    priority: str = "medium"  # "high", "medium", "low"
    frequency: str = "once"  # "once", "daily", "weekly"
    due_date: date = field(default_factory=date.today)
    completed: bool = False
    pet_name: str = ""

    def __post_init__(self) -> None:
        """Normalize the time and reject unknown priority/frequency values."""
        self.time = _parse_time(self.time)
        if self.priority not in PRIORITY_RANK:
            raise ValueError(f"Unknown priority: {self.priority!r}")
        if self.frequency != "once" and self.frequency not in FREQUENCY_STEP:
            raise ValueError(f"Unknown frequency: {self.frequency!r}")

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a fresh copy due one period later, or None for one-off tasks."""
        step = FREQUENCY_STEP.get(self.frequency)
        if step is None:
            return None
        return replace(self, due_date=self.due_date + step, completed=False)


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and tag it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet."""
        self.tasks.remove(task)


class Owner:
    """A pet owner who manages one or more pets."""

    def __init__(self, name: str):
        """Create an owner with no pets yet."""
        self.name = name
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet, rejecting duplicate names (case-insensitive)."""
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet | None:
        """Look up a pet by name (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    def get_all_tasks(self) -> list[Task]:
        """Return every task from every pet as one flat list."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    """Retrieves, organizes, and manages tasks across all of an owner's pets."""

    def __init__(self, owner: Owner):
        """Attach the scheduler to an owner; tasks are always read live from it."""
        self.owner = owner

    def _tasks(self, tasks: list[Task] | None) -> list[Task]:
        """Use the given tasks, or fall back to all of the owner's tasks."""
        return self.owner.get_all_tasks() if tasks is None else tasks

    def sort_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Sort tasks chronologically by date then "HH:MM" time, high priority first on ties."""
        return sorted(
            self._tasks(tasks),
            key=lambda t: (t.due_date, t.time, PRIORITY_RANK[t.priority]),
        )

    def filter_tasks(
        self,
        tasks: list[Task] | None = None,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        """Keep only tasks matching the pet name and/or completion status (None = any)."""
        result = self._tasks(tasks)
        if pet_name is not None:
            result = [t for t in result if t.pet_name.lower() == pet_name.lower()]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def detect_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """Return a warning for each date/time slot that has more than one pending task.

        Only exact start-time matches count; durations are not checked for overlap.
        Completed tasks are ignored. Never raises -- an empty list means no conflicts.
        """
        slots: dict[tuple[date, str], list[Task]] = {}
        for task in self._tasks(tasks):
            if not task.completed:
                slots.setdefault((task.due_date, task.time), []).append(task)

        warnings = []
        for (day, time), clashing in sorted(slots.items()):
            if len(clashing) > 1:
                names = ", ".join(f"{t.description} ({t.pet_name})" for t in clashing)
                warnings.append(f"Conflict on {day.isoformat()} at {time}: {names}")
        return warnings

    def mark_task_complete(self, task: Task) -> Task | None:
        """Complete a task; for daily/weekly tasks, add and return the next occurrence."""
        task.mark_complete()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            pet = self.owner.get_pet(task.pet_name)
            if pet is None:
                raise ValueError(f"Task {task.description!r} is not attached to a known pet")
            pet.add_task(upcoming)
        return upcoming

    def get_todays_schedule(self, day: date | None = None) -> list[Task]:
        """Return the pending tasks due on the given day (default today), sorted by time."""
        day = day or date.today()
        due = [t for t in self.filter_tasks(completed=False) if t.due_date == day]
        return self.sort_by_time(due)
