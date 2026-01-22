"""
Pytest configuration and shared fixtures for conference scheduler tests.
"""

import os
from collections import Counter
from typing import Any

import httpx
import pytest


def get_base_url() -> str:
    port = os.environ.get("PORT", "8080")
    return f"http://localhost:{port}"


@pytest.fixture(scope="session")
def base_url() -> str:
    return get_base_url()


@pytest.fixture(scope="session")
def client(base_url: str):
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        yield client


class ScheduleValidator:
    """Validates that a schedule satisfies all hard constraints."""

    def __init__(self, input_data: dict, schedule: list[dict]):
        self.input = input_data
        self.schedule = schedule
        self.build_errors: list[str] = []
        self._build_lookups()

    def _build_lookups(self):
        """Build lookup dictionaries for efficient validation."""
        self.rooms = {r["id"]: r for r in self.input["rooms"]}
        self.sessions = {s["id"]: s for s in self.input["sessions"]}
        self.speakers = {sp["id"]: sp for sp in self.input["speakers"]}
        self.attendees = {a["id"]: a for a in self.input.get("attendees", [])}
        self.time_slots = {ts["start"]: ts for ts in self.input["time_slots"]}

        # Build schedule lookups
        self.session_assignment = {}  # session_id -> {room_id, time_slot}
        self.room_schedule = {}  # room_id -> {time_slot -> [session_ids]}
        self.speaker_schedule = {}  # speaker_id -> [time_slots]
        self.sessions_seen = []  # Track all session_ids seen for duplicate detection

        for entry in self.schedule:
            sid = entry.get("session_id")
            rid = entry.get("room_id")
            ts = entry.get("time_slot")

            # Validate entry has required fields
            if not sid or not rid or not ts:
                self.build_errors.append(f"Invalid schedule entry: {entry}")
                continue

            # Check for unknown references
            if sid not in self.sessions:
                self.build_errors.append(f"Unknown session_id in schedule: '{sid}'")
                continue
            if rid not in self.rooms:
                self.build_errors.append(f"Unknown room_id in schedule: '{rid}'")
                continue
            if ts not in self.time_slots:
                self.build_errors.append(f"Unknown time_slot in schedule: '{ts}'")
                continue

            # Track for duplicate session detection
            self.sessions_seen.append(sid)

            self.session_assignment[sid] = {"room_id": rid, "time_slot": ts}

            # Track room bookings as lists to detect double-booking
            if rid not in self.room_schedule:
                self.room_schedule[rid] = {}
            if ts not in self.room_schedule[rid]:
                self.room_schedule[rid][ts] = []
            self.room_schedule[rid][ts].append(sid)

            session = self.sessions[sid]
            for speaker_id in session["speaker_ids"]:
                if speaker_id not in self.speaker_schedule:
                    self.speaker_schedule[speaker_id] = []
                self.speaker_schedule[speaker_id].append(ts)

    def validate_all(self) -> tuple[bool, list[str]]:
        """Run all validations, return (is_valid, list of violations)."""
        violations = []

        # Include any errors from building lookups (unknown IDs, etc.)
        violations.extend(self.build_errors)

        violations.extend(self._check_all_sessions_scheduled())
        violations.extend(self._check_no_speaker_conflicts())
        violations.extend(self._check_room_capacity())
        violations.extend(self._check_room_amenities())
        violations.extend(self._check_speaker_availability())
        violations.extend(self._check_no_room_double_booking())
        violations.extend(self._check_session_fits_slot())
        violations.extend(self._check_track_non_overlap())
        violations.extend(self._check_keynote_exclusivity())
        violations.extend(self._check_attendee_must_attend())

        return len(violations) == 0, violations

    def _check_all_sessions_scheduled(self) -> list[str]:
        """HC7: Every session must be assigned exactly one room and time slot."""
        violations = []

        # Check all sessions are scheduled
        for sid in self.sessions:
            if sid not in self.session_assignment:
                violations.append(f"HC7: Session '{sid}' not scheduled")

        # Check no session is scheduled more than once
        counts = Counter(self.sessions_seen)
        for sid, count in counts.items():
            if count > 1:
                violations.append(f"HC7: Session '{sid}' scheduled {count} times (must be exactly once)")

        # Check no extra sessions in schedule
        for sid in self.sessions_seen:
            if sid not in self.sessions:
                violations.append(f"HC7: Unknown session '{sid}' in schedule")

        return violations

    def _check_no_speaker_conflicts(self) -> list[str]:
        """HC1: A speaker cannot be in two sessions in the same time slot."""
        violations = []
        for speaker_id, slots in self.speaker_schedule.items():
            if len(slots) != len(set(slots)):
                violations.append(f"HC1: Speaker '{speaker_id}' double-booked")
        return violations

    def _check_room_capacity(self) -> list[str]:
        """HC2: room.capacity >= session.expected_attendance."""
        violations = []
        for sid, assignment in self.session_assignment.items():
            session = self.sessions[sid]
            room = self.rooms[assignment["room_id"]]
            if room["capacity"] < session.get("expected_attendance", 0):
                violations.append(
                    f"HC2: Session '{sid}' expects {session['expected_attendance']} "
                    f"but room '{room['id']}' only holds {room['capacity']}"
                )
        return violations

    def _check_room_amenities(self) -> list[str]:
        """HC3: Room must have ALL amenities required by the session."""
        violations = []
        for sid, assignment in self.session_assignment.items():
            session = self.sessions[sid]
            room = self.rooms[assignment["room_id"]]
            required = set(session.get("required_amenities", []))
            available = set(room.get("amenities", []))
            missing = required - available
            if missing:
                violations.append(
                    f"HC3: Session '{sid}' requires {missing} "
                    f"but room '{room['id']}' doesn't have them"
                )
        return violations

    def _check_speaker_availability(self) -> list[str]:
        """HC4: Sessions cannot be scheduled when speakers are unavailable."""
        violations = []
        for sid, assignment in self.session_assignment.items():
            session = self.sessions[sid]
            ts = assignment["time_slot"]
            for speaker_id in session["speaker_ids"]:
                speaker = self.speakers[speaker_id]
                if ts in speaker.get("unavailable_slots", []):
                    violations.append(
                        f"HC4: Session '{sid}' at {ts} but speaker "
                        f"'{speaker_id}' is unavailable"
                    )
        return violations

    def _check_no_room_double_booking(self) -> list[str]:
        """HC5: A room can only host one session per time slot."""
        violations = []
        for rid, slot_sessions in self.room_schedule.items():
            for ts, session_list in slot_sessions.items():
                if len(session_list) > 1:
                    violations.append(
                        f"HC5: Room '{rid}' double-booked at {ts}: {session_list}"
                    )
        return violations

    def _check_session_fits_slot(self) -> list[str]:
        """HC6: session.duration_minutes <= time_slot.duration_minutes."""
        violations = []
        for sid, assignment in self.session_assignment.items():
            session = self.sessions[sid]
            ts = self.time_slots[assignment["time_slot"]]
            if session["duration_minutes"] > ts["duration_minutes"]:
                violations.append(
                    f"HC6: Session '{sid}' is {session['duration_minutes']}min "
                    f"but slot is only {ts['duration_minutes']}min"
                )
        return violations

    def _check_track_non_overlap(self) -> list[str]:
        """HC8: Sessions in the same track cannot be in the same time slot."""
        violations = []
        track_slots: dict[str, list[str]] = {}

        for sid, assignment in self.session_assignment.items():
            session = self.sessions[sid]
            track = session.get("track")
            if track:
                if track not in track_slots:
                    track_slots[track] = []
                track_slots[track].append(assignment["time_slot"])

        for track, slots in track_slots.items():
            if len(slots) != len(set(slots)):
                violations.append(f"HC8: Track '{track}' has sessions in the same time slot")

        return violations

    def _check_keynote_exclusivity(self) -> list[str]:
        """HC9: When a keynote is scheduled, no other sessions run in that slot."""
        violations = []

        # Group sessions by time slot
        slot_to_sessions: dict[str, list[str]] = {}
        for sid, assignment in self.session_assignment.items():
            ts = assignment["time_slot"]
            if ts not in slot_to_sessions:
                slot_to_sessions[ts] = []
            slot_to_sessions[ts].append(sid)

        # Check each slot: if any keynote present, must be the only session
        for ts, session_ids in slot_to_sessions.items():
            keynotes_in_slot = [
                sid for sid in session_ids
                if self.sessions[sid].get("is_keynote", False)
            ]

            if keynotes_in_slot:
                # There's at least one keynote in this slot
                if len(session_ids) > 1:
                    other_sessions = [s for s in session_ids if s not in keynotes_in_slot]
                    if other_sessions:
                        violations.append(
                            f"HC9: Non-keynote sessions {other_sessions} scheduled "
                            f"during keynote slot {ts}"
                        )
                    if len(keynotes_in_slot) > 1:
                        violations.append(
                            f"HC9: Multiple keynotes {keynotes_in_slot} scheduled "
                            f"in same slot {ts} (only one session allowed during keynote)"
                        )

        return violations

    def _check_attendee_must_attend(self) -> list[str]:
        """HC10: Attendee must_attend sessions cannot be in the same time slot."""
        violations = []

        for aid, attendee in self.attendees.items():
            must_slots = []
            for sid in attendee.get("must_attend", []):
                if sid in self.session_assignment:
                    must_slots.append(self.session_assignment[sid]["time_slot"])
            if len(must_slots) != len(set(must_slots)):
                violations.append(
                    f"HC10: Attendee '{aid}' has must_attend sessions in the same time slot"
                )

        return violations


def validate_schedule(input_data: dict, response: dict) -> tuple[bool, list[str], dict]:
    """
    Validate a schedule response.
    Returns: (is_valid, violations, scores)
    """
    if response.get("status") != "success":
        return False, ["Response status is not 'success'"], {}

    schedule = response.get("schedule", [])

    # Empty schedule is valid only if there are no sessions
    if not schedule:
        if input_data.get("sessions", []):
            return False, ["Schedule is empty but there are sessions to schedule"], {}
        else:
            return True, [], {}

    validator = ScheduleValidator(input_data, schedule)
    is_valid, violations = validator.validate_all()

    return is_valid, violations, {}


@pytest.fixture
def validator():
    return validate_schedule
