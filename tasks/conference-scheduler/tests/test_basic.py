"""Basic test cases - simple but realistic scheduling scenarios."""

import pytest


class TestBasicSchedules:
    """Basic scheduling scenarios with a few active constraints."""

    def test_room_capacity_constraint(self, client, validator):
        """Sessions must be assigned to rooms with sufficient capacity."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Small Room", "capacity": 30, "amenities": []},
                {"id": "R2", "name": "Large Room", "capacity": 200, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Popular Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 150,  # Only fits in R2
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Niche Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 20,  # Fits in either
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

        # S1 must be in R2
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["S1"]["room_id"] == "R2"

    def test_amenity_constraint(self, client, validator):
        """Sessions requiring amenities must be in appropriate rooms."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Basic Room", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "AV Room", "capacity": 100, "amenities": ["projector", "mic"]},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Presentation",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["projector"],  # Needs projector
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Discussion",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],  # No requirements
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

        # S1 must be in R2 (has projector)
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["S1"]["room_id"] == "R2"

    def test_speaker_unavailability(self, client, validator):
        """Speakers must not be scheduled during unavailable slots."""
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
                    "unavailable_slots": ["09:00"],  # Can't do 9am
                    "preferred_slots": [],
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

        # S1 must be at 10:00, not 09:00
        schedule = result["schedule"]
        assert schedule[0]["time_slot"] == "10:00"

    def test_track_non_overlap(self, client, validator):
        """Sessions in same track must not overlap."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Rust Basics",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": "rust",
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Rust Advanced",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": "rust",  # Same track
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Go Basics",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": "go",  # Different track
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
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # S1 and S2 (both rust track) must be in different slots
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["S1"]["time_slot"] != schedule["S2"]["time_slot"]

    def test_keynote_blocks_other_sessions(self, client, validator):
        """Keynote slot cannot have other sessions."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Main Hall", "capacity": 500, "amenities": []},
                {"id": "R2", "name": "Side Room", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "K1",
                    "title": "Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 400,
                    "is_keynote": True,
                },
                {
                    "id": "S1",
                    "title": "Regular Talk",
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

        # Keynote and regular talk must be in different slots
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["K1"]["time_slot"] != schedule["S1"]["time_slot"]

    def test_multiple_speakers_per_session(self, client, validator):
        """Sessions with multiple speakers - all must be available."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Panel Discussion",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1", "SP2", "SP3"],  # 3 speakers
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 80,
                    "is_keynote": False,
                }
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": ["09:00"], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": ["11:00"], "preferred_slots": []},
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

        # Must be 10:00 (SP1 unavailable at 09:00, SP3 unavailable at 11:00)
        schedule = result["schedule"]
        assert schedule[0]["time_slot"] == "10:00"

    def test_session_duration_respects_slot(self, client, validator):
        """Sessions must fit within their assigned time slot."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Short Talk",
                    "duration_minutes": 30,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Long Workshop",
                    "duration_minutes": 90,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 30,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},  # Short talk only
                {"start": "10:00", "duration_minutes": 120},  # Either fits
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # S2 (90min) must be in 10:00 slot (120min)
        schedule = {s["session_id"]: s for s in result["schedule"]}
        assert schedule["S2"]["time_slot"] == "10:00"
