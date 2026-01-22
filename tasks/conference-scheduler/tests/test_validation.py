"""Input validation tests - ensure bad input is rejected with 400."""

import pytest


class TestInputValidation:
    """Tests for input validation (400 responses)."""

    def test_missing_rooms(self, client):
        """Missing rooms field returns 400."""
        data = {
            "sessions": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_missing_sessions(self, client):
        """Missing sessions field returns 400."""
        data = {
            "rooms": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_missing_time_slots(self, client):
        """Missing time_slots field returns 400."""
        data = {
            "rooms": [],
            "sessions": [],
            "speakers": [],
            "attendees": [],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_negative_room_capacity(self, client):
        """Negative room capacity returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": -10, "amenities": []}],
            "sessions": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_zero_room_capacity(self, client):
        """Zero room capacity returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 0, "amenities": []}],
            "sessions": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_invalid_session_duration(self, client):
        """Session duration outside valid range returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk",
                    "duration_minutes": 0,  # Invalid
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
        assert response.status_code == 400

    def test_session_with_no_speakers(self, client):
        """Session with empty speaker_ids returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk",
                    "duration_minutes": 60,
                    "speaker_ids": [],  # Invalid
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                }
            ],
            "speakers": [],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_session_references_nonexistent_speaker(self, client):
        """Session referencing non-existent speaker returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP_NONEXISTENT"],
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
        assert response.status_code == 400

    def test_duplicate_room_ids(self, client):
        """Duplicate room IDs returns 400."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R1", "name": "Room B", "capacity": 50, "amenities": []},  # Duplicate
            ],
            "sessions": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_duplicate_session_ids(self, client):
        """Duplicate session IDs returns 400."""
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
                    "id": "S1",  # Duplicate
                    "title": "Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
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
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_invalid_time_slot_format(self, client):
        """Invalid time slot format returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [],
            "speakers": [],
            "attendees": [],
            "time_slots": [{"start": "9:00AM", "duration_minutes": 60}],  # Bad format
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_session_duration_exceeds_all_slots(self, client):
        """Session longer than any time slot returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Marathon Talk",
                    "duration_minutes": 120,  # 2 hours
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
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],  # Only 1 hour slots
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_attendee_references_nonexistent_session(self, client):
        """Attendee must_attend referencing non-existent session returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk",
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
            "attendees": [
                {"id": "A1", "must_attend": ["S_NONEXISTENT"], "wants_to_attend": []}
            ],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400

    def test_speaker_unavailable_slot_not_in_time_slots(self, client):
        """Speaker unavailable_slots referencing non-existent time slot returns 400."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                }
            ],
            "speakers": [
                {
                    "id": "SP1",
                    "name": "Alice",
                    "unavailable_slots": ["25:00"],  # Invalid
                    "preferred_slots": [],
                }
            ],
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 400
