"""CLI demo for PawPal+: builds a small household and prints today's schedule."""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print a list of tasks as an aligned table."""
    print(f"\n{title}")
    print("-" * len(title))
    if not tasks:
        print("  (none)")
        return
    for t in tasks:
        status = "x" if t.completed else " "
        print(
            f"  [{status}] {t.due_date.isoformat()} {t.time}  {t.pet_name:<7} "
            f"{t.description:<18} {t.duration_minutes:>3} min  "
            f"{t.priority:<6} {t.frequency}"
        )


def main() -> None:
    """Run the PawPal+ demo."""
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog", age=3)
    luna = Pet("Luna", "cat", age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Added deliberately out of order to exercise sorting.
    mochi.add_task(Task("Evening walk", "18:30", 30, "medium", "daily"))
    luna.add_task(Task("Brush coat", "12:00", 10, "low", "weekly"))
    mochi.add_task(Task("Morning walk", "07:30", 30, "high", "daily"))
    luna.add_task(Task("Breakfast", "08:00", 5, "high", "daily"))
    mochi.add_task(Task("Heartworm pill", "08:00", 5, "high", "once"))  # same time as Luna's breakfast
    luna.add_task(Task("Vet checkup", "15:00", 60, "high", "once"))

    scheduler = Scheduler(owner)
    today = date.today()

    print(f"PawPal+ for {owner.name} ({len(owner.pets)} pets, {len(owner.get_all_tasks())} tasks)")

    print_tasks("Today's Schedule (sorted by time)", scheduler.get_todays_schedule(today))

    print("\nConflict check")
    print("--------------")
    for warning in scheduler.detect_conflicts() or ["No conflicts found."]:
        print(f"  WARNING: {warning}")

    morning_walk = next(t for t in mochi.tasks if t.description == "Morning walk")
    upcoming = scheduler.mark_task_complete(morning_walk)
    print(f"\nCompleted '{morning_walk.description}' -> next one auto-created for {upcoming.due_date.isoformat()}")

    print_tasks("Mochi's tasks (filter by pet, sorted)", scheduler.sort_by_time(scheduler.filter_tasks(pet_name="Mochi")))
    print_tasks("Completed tasks (filter by status)", scheduler.filter_tasks(completed=True))
    print_tasks("Today's Schedule after completing the walk", scheduler.get_todays_schedule(today))


if __name__ == "__main__":
    main()
