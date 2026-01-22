"""Intermediate test cases - multiple constraint types interacting."""

import pytest


class TestIntermediateSchedules:
    """More complex scenarios with multiple active constraints."""

    def test_constrained_room_assignment(self, client, validator):
        """Multiple sessions compete for limited suitable rooms."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Basic", "capacity": 50, "amenities": []},
                {"id": "R2", "name": "AV Room", "capacity": 100, "amenities": ["projector"]},
                {"id": "R3", "name": "Recording Studio", "capacity": 30, "amenities": ["projector", "video_recording"]},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Recorded Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["video_recording"],
                    "expected_attendance": 25,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Presentation",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": ["projector"],
                    "expected_attendance": 80,  # Too big for R3
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Discussion",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 40,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": [], "preferred_slots": []},
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

        schedule = {s["session_id"]: s for s in result["schedule"]}
        # S1 needs video_recording -> R3
        assert schedule["S1"]["room_id"] == "R3"
        # S2 needs projector and 80 capacity -> R2
        assert schedule["S2"]["room_id"] == "R2"

    def test_speaker_availability_chain(self, client, validator):
        """Complex speaker availability creates ordering constraints."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Morning Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Midday Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Afternoon Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": ["10:00", "11:00"], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": ["09:00", "11:00"], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": ["09:00", "10:00"], "preferred_slots": []},
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

        schedule = {s["session_id"]: s for s in result["schedule"]}
        # Each speaker only available in one slot
        assert schedule["S1"]["time_slot"] == "09:00"
        assert schedule["S2"]["time_slot"] == "10:00"
        assert schedule["S3"]["time_slot"] == "11:00"

    def test_track_and_keynote_interaction(self, client, validator):
        """Keynotes affect track scheduling."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Main Hall", "capacity": 500, "amenities": []},
                {"id": "R2", "name": "Track Room", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "K1",
                    "title": "Opening Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 400,
                    "is_keynote": True,
                },
                {
                    "id": "S1",
                    "title": "Python 101",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": "python",
                    "required_amenities": [],
                    "expected_attendance": 80,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Python 201",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": "python",
                    "required_amenities": [],
                    "expected_attendance": 60,
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

        schedule = {s["session_id"]: s for s in result["schedule"]}
        keynote_slot = schedule["K1"]["time_slot"]

        # No other session in keynote slot
        for sid, info in schedule.items():
            if sid != "K1":
                assert info["time_slot"] != keynote_slot

        # Python sessions in different slots (same track)
        assert schedule["S1"]["time_slot"] != schedule["S2"]["time_slot"]

    def test_mixed_duration_sessions(self, client, validator):
        """Sessions of different durations compete for appropriate slots."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Workshop Room", "capacity": 50, "amenities": []},
                {"id": "R2", "name": "Talk Room", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "W1",
                    "title": "3-Hour Workshop",
                    "duration_minutes": 180,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 30,
                    "is_keynote": False,
                },
                {
                    "id": "S1",
                    "title": "Regular Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 60,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Lightning Talk",
                    "duration_minutes": 30,
                    "speaker_ids": ["SP3"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 40,
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
                {"start": "09:00", "duration_minutes": 180},  # Morning workshop block
                {"start": "14:00", "duration_minutes": 60},   # Afternoon talks
                {"start": "15:00", "duration_minutes": 60},
            ],
        }
        response = client.post("/schedule", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        schedule = {s["session_id"]: s for s in result["schedule"]}
        # Workshop must be in morning slot (only one long enough)
        assert schedule["W1"]["time_slot"] == "09:00"

    def test_attendee_must_attend_affects_schedule(self, client, validator):
        """Attendee must_attend sessions cannot conflict."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "S1",
                    "title": "Important Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Important Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Optional Talk",
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
                {"id": "A1", "must_attend": ["S1", "S2"], "wants_to_attend": []},
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

        schedule = {s["session_id"]: s for s in result["schedule"]}
        # S1 and S2 must be in different slots (A1 must attend both)
        assert schedule["S1"]["time_slot"] != schedule["S2"]["time_slot"]

    def test_small_realistic_conference(self, client, validator):
        """Small but realistic conference with 8 sessions, 3 rooms, 4 slots."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Main Hall", "capacity": 300, "amenities": ["projector", "mic"]},
                {"id": "R2", "name": "Workshop Room", "capacity": 50, "amenities": ["projector", "whiteboard"]},
                {"id": "R3", "name": "Meeting Room", "capacity": 30, "amenities": []},
            ],
            "sessions": [
                {
                    "id": "K1",
                    "title": "Opening Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["projector", "mic"],
                    "expected_attendance": 250,
                    "is_keynote": True,
                },
                {
                    "id": "S1",
                    "title": "Web Dev 101",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": "web",
                    "required_amenities": ["projector"],
                    "expected_attendance": 40,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Web Dev Advanced",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": "web",
                    "required_amenities": ["projector"],
                    "expected_attendance": 35,
                    "is_keynote": False,
                },
                {
                    "id": "S3",
                    "title": "Data Science Intro",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": "data",
                    "required_amenities": ["projector"],
                    "expected_attendance": 45,
                    "is_keynote": False,
                },
                {
                    "id": "S4",
                    "title": "ML Workshop",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": "data",
                    "required_amenities": ["projector", "whiteboard"],
                    "expected_attendance": 30,
                    "is_keynote": False,
                },
                {
                    "id": "S5",
                    "title": "DevOps Best Practices",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP4"],
                    "track": "devops",
                    "required_amenities": [],
                    "expected_attendance": 25,
                    "is_keynote": False,
                },
                {
                    "id": "S6",
                    "title": "Cloud Architecture",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP5"],
                    "track": "devops",
                    "required_amenities": ["projector"],
                    "expected_attendance": 40,
                    "is_keynote": False,
                },
                {
                    "id": "K2",
                    "title": "Closing Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP6"],
                    "track": None,
                    "required_amenities": ["projector", "mic"],
                    "expected_attendance": 200,
                    "is_keynote": True,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": ["09:00"]},
                {"id": "SP2", "name": "Bob", "unavailable_slots": ["09:00"], "preferred_slots": ["10:00", "11:00"]},
                {"id": "SP3", "name": "Carol", "unavailable_slots": ["09:00"], "preferred_slots": ["14:00"]},
                {"id": "SP4", "name": "Dave", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP5", "name": "Eve", "unavailable_slots": ["14:00"], "preferred_slots": []},
                {"id": "SP6", "name": "Frank", "unavailable_slots": [], "preferred_slots": ["14:00"]},
            ],
            "attendees": [
                {"id": "A1", "must_attend": ["K1", "S1", "S2"], "wants_to_attend": ["S3"]},
                {"id": "A2", "must_attend": ["K1", "K2"], "wants_to_attend": ["S3", "S4", "S5"]},
            ],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
                {"start": "14:00", "duration_minutes": 60},
                {"start": "15:00", "duration_minutes": 60},
            ],
        }
        response = client.post("/schedule", json=data, timeout=30)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, scores = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # Verify we have all 8 sessions scheduled
        assert len(result["schedule"]) == 8
