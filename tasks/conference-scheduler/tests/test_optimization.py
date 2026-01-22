"""Optimization tests - verify soft constraint scoring works correctly."""

import pytest


class TestOptimizationScoring:
    """Tests that verify the scheduler optimizes soft constraints."""

    def test_speaker_preferred_slots_scored(self, client, validator):
        """Speakers in preferred slots should score higher."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Alice's Talk",
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
                    "unavailable_slots": [],
                    "preferred_slots": ["10:00"],  # Prefers 10am
                }
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

        # Good optimizer should pick 10:00
        schedule = result["schedule"]
        assert schedule[0]["time_slot"] == "10:00"

        # Should have positive speaker convenience score
        assert "score_breakdown" in result
        assert result["score_breakdown"].get("speaker_convenience", 0) > 0

    def test_room_utilization_prefers_right_size(self, client, validator):
        """Should prefer rooms close to expected attendance size."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Huge Hall", "capacity": 1000, "amenities": []},
                {"id": "R2", "name": "Right-sized Room", "capacity": 60, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Small Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,  # Fits R2 better
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

        # Good optimizer should pick R2 (60 capacity for 50 people vs 1000)
        schedule = result["schedule"]
        assert schedule[0]["room_id"] == "R2"

    def test_attendee_satisfaction_scored(self, client, validator):
        """Schedule should maximize attendee ability to attend wanted sessions."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Wanted Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Wanted Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Other Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [
                {"id": "A1", "must_attend": [], "wants_to_attend": ["S1", "S2"]},  # Wants both
            ],
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

        # Good optimizer puts S1 and S2 in different slots so A1 can attend both
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["S1"]["time_slot"] != schedule["S2"]["time_slot"]

    def test_track_cohesion_same_room(self, client, validator):
        """Track sessions should ideally be in the same room."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Python 101",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": "python",
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Python 201",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": "python",
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Go Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": "go",
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
            ],
        }

        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # Good optimizer puts S1 and S2 in same room
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["S1"]["room_id"] == schedule["S2"]["room_id"]

    def test_back_to_back_speaker_sessions(self, client, validator):
        """Same speaker's sessions should be scheduled consecutively when possible."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Alice Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Alice Talk 2",
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
                {"start": "11:00", "duration_minutes": 60},
                {"start": "14:00", "duration_minutes": 60},  # Gap after lunch
            ],
        }

        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # Good optimizer puts sessions back-to-back
        schedule = {s["session_id"]: s for s in result["schedule"]}
        slot1 = schedule["S1"]["time_slot"]
        slot2 = schedule["S2"]["time_slot"]

        slots = ["09:00", "10:00", "11:00", "14:00"]
        idx1 = slots.index(slot1)
        idx2 = slots.index(slot2)

        # Should be adjacent (difference of 1)
        assert abs(idx1 - idx2) == 1

    def test_score_breakdown_present(self, client, validator):
        """Response should include score breakdown."""
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
            "attendees": [],
            "time_slots": [{"start": "09:00", "duration_minutes": 60}],
        }

        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        assert "score" in result
        assert "score_breakdown" in result
        assert isinstance(result["score_breakdown"], dict)

    def test_higher_preference_sessions_prioritized(self, client, validator):
        """Earlier items in wants_to_attend should be prioritized."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Top Priority",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Second Priority",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Third Priority",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [
                {
                    "id": "A1",
                    "must_attend": [],
                    "wants_to_attend": ["S1", "S2", "S3"],  # S1 is highest priority
                },
            ],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
            ],
        }

        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # With 3 sessions in 3 slots, attendee can attend all
        # Score should reflect this
        assert result.get("score", 0) > 0
