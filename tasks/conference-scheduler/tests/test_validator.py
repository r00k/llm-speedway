"""
Unit tests for the validator itself.
These tests ensure our test infrastructure is correct before we use it to judge models.
"""

import pytest
from conftest import ScheduleValidator, validate_schedule


# === Minimal valid input for building test cases ===

def make_input(
    rooms=None,
    sessions=None,
    speakers=None,
    attendees=None,
    time_slots=None,
):
    """Helper to build valid input data with sensible defaults."""
    return {
        "rooms": rooms or [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
        "sessions": sessions or [],
        "speakers": speakers or [],
        "attendees": attendees or [],
        "time_slots": time_slots or [{"start": "09:00", "duration_minutes": 60}],
    }


def make_response(schedule, status="success"):
    """Helper to build a response."""
    return {"status": status, "schedule": schedule}


# =============================================================================
# HC1: No Speaker Conflicts
# =============================================================================

class TestHC1SpeakerConflicts:
    """Validator correctly detects speaker double-booking."""

    def test_accepts_speaker_in_different_slots(self):
        """Speaker giving two talks in different slots is valid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
            time_slots=[
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R1", "time_slot": "10:00"},
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_speaker_in_same_slot(self):
        """Speaker double-booked in same slot is invalid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R2", "time_slot": "09:00"},  # Same slot!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC1" in v for v in violations)


# =============================================================================
# HC2: Room Capacity
# =============================================================================

class TestHC2RoomCapacity:
    """Validator correctly checks room capacity."""

    def test_accepts_attendance_under_capacity(self):
        """Session with attendance <= capacity is valid."""
        input_data = make_input(
            rooms=[{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 100, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_attendance_over_capacity(self):
        """Session with attendance > capacity is invalid."""
        input_data = make_input(
            rooms=[{"id": "R1", "name": "Room", "capacity": 50, "amenities": []}],
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 100, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC2" in v for v in violations)


# =============================================================================
# HC3: Room Amenities
# =============================================================================

class TestHC3RoomAmenities:
    """Validator correctly checks room amenities."""

    def test_accepts_room_with_required_amenities(self):
        """Room with all required amenities is valid."""
        input_data = make_input(
            rooms=[{"id": "R1", "name": "Room", "capacity": 100, "amenities": ["projector", "mic"]}],
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": ["projector"], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_room_missing_amenity(self):
        """Room missing required amenity is invalid."""
        input_data = make_input(
            rooms=[{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": ["projector"], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC3" in v for v in violations)


# =============================================================================
# HC4: Speaker Availability
# =============================================================================

class TestHC4SpeakerAvailability:
    """Validator correctly checks speaker availability."""

    def test_accepts_speaker_in_available_slot(self):
        """Speaker scheduled in available slot is valid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": ["10:00"], "preferred_slots": []}],
            time_slots=[
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_speaker_in_unavailable_slot(self):
        """Speaker scheduled in unavailable slot is invalid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": ["09:00"], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC4" in v for v in violations)


# =============================================================================
# HC5: No Room Double-Booking
# =============================================================================

class TestHC5RoomDoubleBooking:
    """Validator correctly detects room double-booking."""

    def test_accepts_different_rooms_same_slot(self):
        """Two sessions in different rooms at same time is valid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R2", "time_slot": "09:00"},
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_same_room_same_slot(self):
        """Two sessions in same room at same time is invalid."""
        input_data = make_input(
            rooms=[{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R1", "time_slot": "09:00"},  # Same room+slot!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC5" in v for v in violations)


# =============================================================================
# HC6: Session Fits Time Slot
# =============================================================================

class TestHC6SessionDuration:
    """Validator correctly checks session duration vs slot duration."""

    def test_accepts_session_shorter_than_slot(self):
        """Session shorter than slot is valid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 30, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
            time_slots=[{"start": "09:00", "duration_minutes": 60}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_session_longer_than_slot(self):
        """Session longer than slot is invalid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 90, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
            time_slots=[{"start": "09:00", "duration_minutes": 60}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC6" in v for v in violations)


# =============================================================================
# HC7: All Sessions Scheduled (Exactly Once)
# =============================================================================

class TestHC7AllSessionsScheduled:
    """Validator correctly checks all sessions are scheduled exactly once."""

    def test_accepts_all_sessions_scheduled(self):
        """All sessions scheduled exactly once is valid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            time_slots=[
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R1", "time_slot": "10:00"},
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_missing_session(self):
        """Missing session in schedule is invalid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            # S2 missing!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC7" in v and "S2" in v for v in violations)

    def test_rejects_duplicate_session(self):
        """Session scheduled twice is invalid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
            time_slots=[
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S1", "room_id": "R1", "time_slot": "10:00"},  # Duplicate!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC7" in v and ("twice" in v.lower() or "2 times" in v.lower()) for v in violations)

    def test_rejects_unknown_session(self):
        """Unknown session in schedule is invalid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S_FAKE", "room_id": "R1", "time_slot": "09:00"},  # Unknown!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("S_FAKE" in v for v in violations)


# =============================================================================
# HC8: Track Non-Overlap
# =============================================================================

class TestHC8TrackNonOverlap:
    """Validator correctly checks track sessions don't overlap."""

    def test_accepts_track_sessions_different_slots(self):
        """Track sessions in different slots is valid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "S1", "title": "Python 101", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": "python", "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Python 201", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": "python", "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            time_slots=[
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R1", "time_slot": "10:00"},
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_track_sessions_same_slot(self):
        """Track sessions in same slot is invalid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "S1", "title": "Python 101", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": "python", "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Python 201", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": "python", "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R2", "time_slot": "09:00"},  # Same track, same slot!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC8" in v for v in violations)

    def test_accepts_different_tracks_same_slot(self):
        """Different track sessions in same slot is valid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "S1", "title": "Python Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": "python", "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Rust Talk", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": "rust", "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R2", "time_slot": "09:00"},
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"


# =============================================================================
# HC9: Keynote Exclusivity
# =============================================================================

class TestHC9KeynoteExclusivity:
    """Validator correctly checks keynote exclusivity."""

    def test_accepts_keynote_alone_in_slot(self):
        """Keynote as only session in slot is valid."""
        input_data = make_input(
            rooms=[{"id": "R1", "name": "Main Hall", "capacity": 600, "amenities": []}],
            sessions=[
                {"id": "K1", "title": "Keynote", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 500, "is_keynote": True},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "K1", "room_id": "R1", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_non_keynote_during_keynote_slot(self):
        """Non-keynote session during keynote slot is invalid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 500, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "K1", "title": "Keynote", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 400, "is_keynote": True},
                {"id": "S1", "title": "Regular Talk", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "K1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S1", "room_id": "R2", "time_slot": "09:00"},  # During keynote!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC9" in v for v in violations)

    def test_rejects_multiple_keynotes_same_slot(self):
        """Multiple keynotes in same slot is invalid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 500, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 500, "amenities": []},
            ],
            sessions=[
                {"id": "K1", "title": "Keynote 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 400, "is_keynote": True},
                {"id": "K2", "title": "Keynote 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 400, "is_keynote": True},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
        )
        schedule = [
            {"session_id": "K1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "K2", "room_id": "R2", "time_slot": "09:00"},  # Two keynotes!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC9" in v and "keynote" in v.lower() for v in violations)


# =============================================================================
# HC10: Attendee Must-Attend
# =============================================================================

class TestHC10AttendeeMustAttend:
    """Validator correctly checks attendee must_attend conflicts."""

    def test_accepts_must_attend_different_slots(self):
        """Must-attend sessions in different slots is valid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            attendees=[{"id": "A1", "must_attend": ["S1", "S2"], "wants_to_attend": []}],
            time_slots=[
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R1", "time_slot": "10:00"},
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_must_attend_same_slot(self):
        """Must-attend sessions in same slot is invalid."""
        input_data = make_input(
            rooms=[
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            sessions=[
                {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
                {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP2"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            attendees=[{"id": "A1", "must_attend": ["S1", "S2"], "wants_to_attend": []}],
        )
        schedule = [
            {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
            {"session_id": "S2", "room_id": "R2", "time_slot": "09:00"},  # Same slot!
        ]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("HC10" in v for v in violations)


# =============================================================================
# Robustness: Malformed inputs
# =============================================================================

class TestValidatorRobustness:
    """Validator handles malformed schedule entries gracefully."""

    def test_handles_unknown_room_id(self):
        """Unknown room_id is caught as error, not exception."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R_FAKE", "time_slot": "09:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("R_FAKE" in v for v in violations)

    def test_handles_unknown_time_slot(self):
        """Unknown time_slot is caught as error, not exception."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1", "time_slot": "25:00"}]

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid
        assert any("25:00" in v for v in violations)

    def test_handles_missing_fields_in_entry(self):
        """Schedule entry missing fields is caught as error."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        schedule = [{"session_id": "S1", "room_id": "R1"}]  # Missing time_slot

        validator = ScheduleValidator(input_data, schedule)
        is_valid, violations = validator.validate_all()
        assert not is_valid


# =============================================================================
# validate_schedule wrapper function
# =============================================================================

class TestValidateScheduleWrapper:
    """Tests for the top-level validate_schedule function."""

    def test_rejects_non_success_status(self):
        """Non-success status is rejected."""
        input_data = make_input()
        response = {"status": "infeasible", "reason": "test"}

        is_valid, violations, _ = validate_schedule(input_data, response)
        assert not is_valid
        assert "status" in violations[0].lower()

    def test_accepts_empty_schedule_with_no_sessions(self):
        """Empty schedule with no sessions is valid."""
        input_data = make_input(sessions=[])
        response = make_response([])

        is_valid, violations, _ = validate_schedule(input_data, response)
        assert is_valid, f"Should be valid: {violations}"

    def test_rejects_empty_schedule_with_sessions(self):
        """Empty schedule with sessions to schedule is invalid."""
        input_data = make_input(
            sessions=[
                {"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"],
                 "track": None, "required_amenities": [], "expected_attendance": 50, "is_keynote": False},
            ],
            speakers=[{"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}],
        )
        response = make_response([])

        is_valid, violations, _ = validate_schedule(input_data, response)
        assert not is_valid
        assert "empty" in violations[0].lower()
