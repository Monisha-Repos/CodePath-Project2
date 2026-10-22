"""Automated tests for the PawPal+ logic layer."""

import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import Owner, Pet, Scheduler, Task  # noqa: E402

TODAY = date(2026, 10, 22)


@pytest.fixture
def household():
    """An owner with two pets and no tasks."""
    owner = Owner("Jordan")
    mochi = Pet("Mochi", "dog")
    luna = Pet("Luna", "cat")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner, mochi, luna


# --- Phase 2 quick tests ----------------------------------------------------

def test_mark_complete_changes_status():
    task = Task("Feed", "08:00")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet("Mochi", "dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk", "07:00"))
    assert len(pet.tasks) == 1
    assert pet.tasks[0].pet_name == "Mochi"


# --- Owner / multi-pet ------------------------------------------------------

def test_scheduler_sees_tasks_from_every_pet(household):
    owner, mochi, luna = household
    mochi.add_task(Task("Walk", "07:00", due_date=TODAY))
    luna.add_task(Task("Feed", "08:00", due_date=TODAY))
    assert len(Scheduler(owner).get_todays_schedule(TODAY)) == 2


def test_pet_with_no_tasks_gives_empty_schedule(household):
    owner, _, _ = household
    scheduler = Scheduler(owner)
    assert scheduler.get_todays_schedule(TODAY) == []
    assert scheduler.detect_conflicts() == []


def test_duplicate_pet_name_rejected(household):
    owner, _, _ = household
    with pytest.raises(ValueError):
        owner.add_pet(Pet("mochi", "dog"))


# --- Sorting ----------------------------------------------------------------

def test_sort_by_time_returns_chronological_order(household):
    owner, mochi, luna = household
    mochi.add_task(Task("Evening walk", "18:30", due_date=TODAY))
    luna.add_task(Task("Lunch", "12:00", due_date=TODAY))
    mochi.add_task(Task("Morning walk", "07:30", due_date=TODAY))
    times = [t.time for t in Scheduler(owner).sort_by_time()]
    assert times == ["07:30", "12:00", "18:30"]


def test_sort_handles_unpadded_hours(household):
    owner, mochi, _ = household
    mochi.add_task(Task("Late", "10:00", due_date=TODAY))
    mochi.add_task(Task("Early", "9:00", due_date=TODAY))  # would sort wrong as a raw string
    assert [t.description for t in Scheduler(owner).sort_by_time()] == ["Early", "Late"]


def test_sort_breaks_time_ties_by_priority(household):
    owner, mochi, _ = household
    mochi.add_task(Task("Play", "09:00", priority="low", due_date=TODAY))
    mochi.add_task(Task("Meds", "09:00", priority="high", due_date=TODAY))
    assert [t.description for t in Scheduler(owner).sort_by_time()] == ["Meds", "Play"]


def test_invalid_time_rejected():
    with pytest.raises(ValueError):
        Task("Walk", "25:00")


# --- Filtering --------------------------------------------------------------

def test_filter_by_pet_and_status(household):
    owner, mochi, luna = household
    walk = Task("Walk", "07:00", due_date=TODAY)
    mochi.add_task(walk)
    mochi.add_task(Task("Feed", "08:00", due_date=TODAY))
    luna.add_task(Task("Feed", "08:30", due_date=TODAY))
    walk.mark_complete()

    scheduler = Scheduler(owner)
    assert len(scheduler.filter_tasks(pet_name="mochi")) == 2
    assert scheduler.filter_tasks(completed=True) == [walk]
    assert len(scheduler.filter_tasks(pet_name="Mochi", completed=False)) == 1


# --- Recurrence -------------------------------------------------------------

def test_completing_daily_task_creates_next_day_task(household):
    owner, mochi, _ = household
    walk = Task("Walk", "07:00", frequency="daily", due_date=TODAY)
    mochi.add_task(walk)

    upcoming = Scheduler(owner).mark_task_complete(walk)

    assert walk.completed is True
    assert upcoming is not None
    assert upcoming.due_date == TODAY + timedelta(days=1)
    assert upcoming.completed is False
    assert upcoming.time == "07:00"
    assert upcoming in mochi.tasks
    assert len(mochi.tasks) == 2


def test_completing_weekly_task_creates_task_next_week(household):
    owner, _, luna = household
    brush = Task("Brush", "12:00", frequency="weekly", due_date=TODAY)
    luna.add_task(brush)
    upcoming = Scheduler(owner).mark_task_complete(brush)
    assert upcoming.due_date == TODAY + timedelta(weeks=1)


def test_completing_one_off_task_creates_nothing(household):
    owner, _, luna = household
    vet = Task("Vet", "15:00", due_date=TODAY)
    luna.add_task(vet)
    assert Scheduler(owner).mark_task_complete(vet) is None
    assert len(luna.tasks) == 1


def test_todays_schedule_excludes_completed_and_future_tasks(household):
    owner, mochi, _ = household
    walk = Task("Walk", "07:00", frequency="daily", due_date=TODAY)
    mochi.add_task(walk)
    scheduler = Scheduler(owner)
    scheduler.mark_task_complete(walk)
    assert scheduler.get_todays_schedule(TODAY) == []
    assert len(scheduler.get_todays_schedule(TODAY + timedelta(days=1))) == 1


# --- Conflict detection -----------------------------------------------------

def test_conflict_detected_for_same_time_across_pets(household):
    owner, mochi, luna = household
    mochi.add_task(Task("Pill", "08:00", due_date=TODAY))
    luna.add_task(Task("Breakfast", "08:00", due_date=TODAY))
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1
    assert "08:00" in warnings[0]
    assert "Pill (Mochi)" in warnings[0] and "Breakfast (Luna)" in warnings[0]


def test_conflict_detected_for_same_pet(household):
    owner, mochi, _ = household
    mochi.add_task(Task("Walk", "07:00", due_date=TODAY))
    mochi.add_task(Task("Feed", "07:00", due_date=TODAY))
    assert len(Scheduler(owner).detect_conflicts()) == 1


def test_no_conflict_for_different_days_or_completed_tasks(household):
    owner, mochi, luna = household
    mochi.add_task(Task("Walk", "07:00", due_date=TODAY))
    luna.add_task(Task("Feed", "07:00", due_date=TODAY + timedelta(days=1)))
    done = Task("Groom", "09:00", due_date=TODAY, completed=True)
    mochi.add_task(done)
    luna.add_task(Task("Play", "09:00", due_date=TODAY))
    assert Scheduler(owner).detect_conflicts() == []
