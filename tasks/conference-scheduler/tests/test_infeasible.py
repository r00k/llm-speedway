"""Tests for infeasibility detection - scheduler should recognize impossible inputs."""

import pytest


class TestInfeasibilityDetection:
    """Tests that verify proper detection of unsolvable inputs."""

    def test_speaker_has_more_sessions_than_slots(self, client):
        """Speaker with 3 sessions but only 2 available slots is infeasible."""
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
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Talk 3",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {
                    "id": "SP1",
                    "name": "Alice",
                    "unavailable_slots": ["11:00"],  # Only 2 slots available
                    "preferred_slots": [],
                }
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
        assert result["status"] == "infeasible"
        assert "reason" in result
        assert len(result["reason"]) > 0

    def test_session_requires_amenity_no_room_has(self, client):
        """Session requiring amenity no room provides is infeasible."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room", "capacity": 100, "amenities": ["projector"]}
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Recording Session",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["video_recording"],  # Not available
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
        assert result["status"] == "infeasible"
        assert "reason" in result

    def test_session_attendance_exceeds_all_rooms(self, client):
        """Session expecting more attendees than any room can hold is infeasible."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Small Room", "capacity": 50, "amenities": []},
                {"id": "R2", "name": "Medium Room", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Mega Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 500,  # Too large
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
        assert result["status"] == "infeasible"
        assert "reason" in result

    def test_more_sessions_than_room_slot_combinations(self, client):
        """More sessions than (rooms × slots) is infeasible (pigeonhole)."""
        data = {
            "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
            "sessions": [
                {
                    "id": f"S{i}",
                    "title": f"Talk {i}",
                    "duration_minutes": 60,
                    "speaker_ids": [f"SP{i}"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                }
                for i in range(1, 5)  # 4 sessions
            ],
            "speakers": [
                {"id": f"SP{i}", "name": f"Speaker {i}", "unavailable_slots": [], "preferred_slots": []}
                for i in range(1, 5)
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
                # Only 3 slots, 1 room = 3 combinations, but 4 sessions
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "infeasible"
        assert "reason" in result

    def test_track_has_more_sessions_than_slots(self, client):
        """Track with more sessions than time slots is infeasible."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": f"S{i}",
                    "title": f"Rust Talk {i}",
                    "duration_minutes": 60,
                    "speaker_ids": [f"SP{i}"],
                    "track": "rust",  # All same track
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                }
                for i in range(1, 5)  # 4 sessions in rust track
            ],
            "speakers": [
                {"id": f"SP{i}", "name": f"Speaker {i}", "unavailable_slots": [], "preferred_slots": []}
                for i in range(1, 5)
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
                # Only 3 slots, but 4 sessions in same track
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "infeasible"
        assert "reason" in result

    def test_attendee_must_attend_conflicting_keynotes(self, client):
        """Two keynotes means only one slot each - attendee can attend both."""
        # This is actually feasible if keynotes are in different slots
        # Test where attendee MUST attend sessions by same speaker (who can't be in 2 places)
        pass  # Complex case, skip for now

    def test_keynote_count_exceeds_slots(self, client):
        """More keynotes than time slots is infeasible."""
        data = {
            "rooms": [{"id": "R1", "name": "Main Hall", "capacity": 500, "amenities": []}],
            "sessions": [
                {
                    "id": f"K{i}",
                    "title": f"Keynote {i}",
                    "duration_minutes": 60,
                    "speaker_ids": [f"SP{i}"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 400,
                    "is_keynote": True,  # All keynotes
                }
                for i in range(1, 4)  # 3 keynotes
            ],
            "speakers": [
                {"id": f"SP{i}", "name": f"Speaker {i}", "unavailable_slots": [], "preferred_slots": []}
                for i in range(1, 4)
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                # Only 2 slots but 3 keynotes
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "infeasible"
        assert "reason" in result

    def test_combined_constraints_make_infeasible(self, client):
        """Multiple constraints combine to make scheduling impossible."""
        # Session S1 needs video_recording (only R1 has it)
        # Session S2 needs huge capacity (only R2 has it)
        # Both have same speaker, only 1 slot available
        data = {
            "rooms": [
                {"id": "R1", "name": "Studio", "capacity": 20, "amenities": ["video_recording"]},
                {"id": "R2", "name": "Auditorium", "capacity": 500, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Recorded Session",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["video_recording"],
                    "expected_attendance": 15,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Big Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],  # Same speaker!
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 400,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {
                    "id": "SP1",
                    "name": "Alice",
                    "unavailable_slots": [],
                    "preferred_slots": [],
                }
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                # Only 1 slot but speaker has 2 sessions
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "infeasible"
        assert "reason" in result
