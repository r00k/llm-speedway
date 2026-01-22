"""Trivial test cases - simplest possible valid schedules."""

import pytest


class TestTrivialSchedules:
    """Simplest possible scheduling scenarios - baseline sanity checks."""

    def test_single_session_single_room_single_slot(self, client, validator):
        """Absolute minimum: 1 session, 1 room, 1 slot."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Only Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                }
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}
            ],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # Verify specific assignment
        schedule = result["schedule"]
        assert len(schedule) == 1
        assert schedule[0]["session_id"] == "S1"
        assert schedule[0]["room_id"] == "R1"
        assert schedule[0]["time_slot"] == "09:00"

    def test_two_sessions_two_rooms_one_slot(self, client, validator):
        """Two parallel sessions in different rooms."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        schedule = result["schedule"]
        assert len(schedule) == 2
        rooms_used = {s["room_id"] for s in schedule}
        assert rooms_used == {"R1", "R2"}  # Both rooms used

    def test_two_sessions_one_room_two_slots(self, client, validator):
        """Two sequential sessions in same room."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        schedule = result["schedule"]
        assert len(schedule) == 2
        slots_used = {s["time_slot"] for s in schedule}
        assert slots_used == {"09:00", "10:00"}

    def test_single_keynote(self, client, validator):
        """Single keynote takes exclusive slot."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Main Hall", "capacity": 500, "amenities": ["projector"]},
                {"id": "R2", "name": "Side Room", "capacity": 50, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "K1",
                    "title": "Opening Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["projector"],
                    "expected_attendance": 400,
                    "is_keynote": True,
                }
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}
            ],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        schedule = result["schedule"]
        assert len(schedule) == 1
        assert schedule[0]["room_id"] == "R1"  # Must use room with projector

    def test_no_sessions(self, client):
        """Empty session list should return empty schedule."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["schedule"] == []

    def test_speaker_same_as_multiple_session_different_slots(self, client, validator):
        """One speaker gives two talks in different time slots."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Intro to Python",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Advanced Python",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],  # Same speaker
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # Sessions must be in different slots (same speaker)
        schedule = result["schedule"]
        slots = {s["time_slot"] for s in schedule}
        assert len(slots) == 2
