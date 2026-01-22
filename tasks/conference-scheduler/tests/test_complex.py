"""Complex test cases - large conferences with tight constraints."""

import pytest


class TestComplexSchedules:
    """Large-scale scheduling with many interacting constraints."""

    def test_medium_conference_25_sessions(self, client, validator):
        """Medium conference: 25 sessions, 6 rooms, 5 slots."""
        # Build a realistic medium-sized conference
        rooms = [
            {"id": "R1", "name": "Grand Ballroom", "capacity": 500, "amenities": ["projector", "mic", "video_recording"]},
            {"id": "R2", "name": "Conference A", "capacity": 150, "amenities": ["projector", "mic"]},
            {"id": "R3", "name": "Conference B", "capacity": 150, "amenities": ["projector", "mic"]},
            {"id": "R4", "name": "Workshop 1", "capacity": 50, "amenities": ["projector", "whiteboard"]},
            {"id": "R5", "name": "Workshop 2", "capacity": 50, "amenities": ["projector", "whiteboard"]},
            {"id": "R6", "name": "Meeting Room", "capacity": 25, "amenities": ["whiteboard"]},
        ]

        time_slots = [
            {"start": "09:00", "duration_minutes": 60},
            {"start": "10:30", "duration_minutes": 60},
            {"start": "13:00", "duration_minutes": 60},
            {"start": "14:30", "duration_minutes": 60},
            {"start": "16:00", "duration_minutes": 60},
        ]

        # Create 25 sessions across 5 tracks
        tracks = ["frontend", "backend", "data", "devops", None]
        sessions = []
        speakers = []

        for i in range(1, 26):
            track = tracks[(i - 1) % 5] if i > 2 else None  # First 2 are keynotes
            is_keynote = i <= 2

            expected = 400 if is_keynote else (20 + (i * 7) % 100)
            required_amenities = ["projector", "mic"] if is_keynote else (["projector"] if i % 3 != 0 else [])

            sessions.append({
                "id": f"S{i}",
                "title": f"Session {i}",
                "duration_minutes": 60,
                "speaker_ids": [f"SP{i}"],
                "track": track,
                "required_amenities": required_amenities,
                "expected_attendance": expected,
                "is_keynote": is_keynote,
            })

            # Varied unavailability to create constraints
            unavailable = []
            if i % 4 == 0:
                unavailable = ["09:00"]
            elif i % 4 == 1:
                unavailable = ["16:00"]

            speakers.append({
                "id": f"SP{i}",
                "name": f"Speaker {i}",
                "unavailable_slots": unavailable,
                "preferred_slots": [],
            })

        # A few attendees with preferences
        attendees = [
            {"id": "A1", "must_attend": ["S1", "S2"], "wants_to_attend": ["S3", "S5", "S8"]},
            {"id": "A2", "must_attend": ["S1"], "wants_to_attend": ["S4", "S6", "S7", "S10"]},
            {"id": "A3", "must_attend": ["S2"], "wants_to_attend": ["S11", "S12", "S15"]},
        ]

        data = {
            "rooms": rooms,
            "sessions": sessions,
            "speakers": speakers,
            "attendees": attendees,
            "time_slots": time_slots,
            "config": {"max_compute_seconds": 30, "optimization_level": "balanced"},
        }

        response = client.post("/schedule", json=data, timeout=60)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, scores = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # All 25 sessions scheduled
        assert len(result["schedule"]) == 25

        # Score exists and is reasonable
        assert "score" in result
        assert result["score"] > 0

    def test_tight_constraints_barely_feasible(self, client, validator):
        """Tightly constrained problem that's just barely feasible."""
        # 6 sessions, 2 rooms, 3 slots = exactly enough combinations
        # But constraints make it tricky
        data = {
            "rooms": [
                {"id": "R1", "name": "Large Room", "capacity": 100, "amenities": ["projector"]},
                {"id": "R2", "name": "Small Room", "capacity": 40, "amenities": ["whiteboard"]},
            ],
            "sessions": [
                # S1: Needs large room (projector + 80 people)
                {
                    "id": "S1",
                    "title": "Big Presentation",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": "A",
                    "required_amenities": ["projector"],
                    "expected_attendance": 80,
                    "is_keynote": False,
                },
                # S2: Needs large room (90 people)
                {
                    "id": "S2",
                    "title": "Popular Talk",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": "B",
                    "required_amenities": [],
                    "expected_attendance": 90,
                    "is_keynote": False,
                },
                # S3: Needs small room (whiteboard)
                {
                    "id": "S3",
                    "title": "Workshop",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": "A",  # Same track as S1
                    "required_amenities": ["whiteboard"],
                    "expected_attendance": 30,
                    "is_keynote": False,
                },
                # S4: Fits either room
                {
                    "id": "S4",
                    "title": "Flexible Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],  # Same speaker as S1
                    "track": "C",
                    "required_amenities": [],
                    "expected_attendance": 35,
                    "is_keynote": False,
                },
                # S5: Needs large room (projector)
                {
                    "id": "S5",
                    "title": "Demo Session",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP4"],
                    "track": "B",  # Same track as S2
                    "required_amenities": ["projector"],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                # S6: Fits either room
                {
                    "id": "S6",
                    "title": "Flexible Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP5"],
                    "track": "C",
                    "required_amenities": [],
                    "expected_attendance": 25,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": ["11:00"], "preferred_slots": []},
                {"id": "SP2", "name": "Bob", "unavailable_slots": ["09:00"], "preferred_slots": []},
                {"id": "SP3", "name": "Carol", "unavailable_slots": [], "preferred_slots": []},
                {"id": "SP4", "name": "Dave", "unavailable_slots": ["10:00"], "preferred_slots": []},
                {"id": "SP5", "name": "Eve", "unavailable_slots": [], "preferred_slots": []},
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
            ],
        }

        response = client.post("/schedule", json=data, timeout=30)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        assert len(result["schedule"]) == 6

    def test_many_tracks_no_overlap(self, client, validator):
        """Multiple tracks each with several sessions - no overlaps within track."""
        rooms = [{"id": f"R{i}", "name": f"Room {i}", "capacity": 100, "amenities": []} for i in range(1, 6)]
        time_slots = [{"start": f"{9+i}:00", "duration_minutes": 60} for i in range(5)]

        sessions = []
        speakers = []
        speaker_id = 1

        # 4 tracks with 4 sessions each = 16 sessions
        for track_idx, track in enumerate(["alpha", "beta", "gamma", "delta"]):
            for session_idx in range(4):
                sid = f"S_{track}_{session_idx}"
                spid = f"SP{speaker_id}"

                sessions.append({
                    "id": sid,
                    "title": f"{track.title()} Talk {session_idx + 1}",
                    "duration_minutes": 60,
                    "speaker_ids": [spid],
                    "track": track,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                })

                speakers.append({
                    "id": spid,
                    "name": f"Speaker {speaker_id}",
                    "unavailable_slots": [],
                    "preferred_slots": [],
                })

                speaker_id += 1

        data = {
            "rooms": rooms,
            "sessions": sessions,
            "speakers": speakers,
            "attendees": [],
            "time_slots": time_slots,
        }

        response = client.post("/schedule", json=data, timeout=30)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # Verify track non-overlap explicitly
        schedule = {s["session_id"]: s for s in result["schedule"]}
        for track in ["alpha", "beta", "gamma", "delta"]:
            track_slots = [schedule[f"S_{track}_{i}"]["time_slot"] for i in range(4)]
            assert len(track_slots) == len(set(track_slots)), f"Track {track} has overlapping sessions"

    def test_multiple_keynotes_spread(self, client, validator):
        """Multiple keynotes must each have exclusive slots."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Main Hall", "capacity": 500, "amenities": ["projector"]},
                {"id": "R2", "name": "Room A", "capacity": 100, "amenities": []},
                {"id": "R3", "name": "Room B", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                # 3 keynotes
                {
                    "id": "K1",
                    "title": "Opening Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],
                    "track": None,
                    "required_amenities": ["projector"],
                    "expected_attendance": 400,
                    "is_keynote": True,
                },
                {
                    "id": "K2",
                    "title": "Midday Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP2"],
                    "track": None,
                    "required_amenities": ["projector"],
                    "expected_attendance": 350,
                    "is_keynote": True,
                },
                {
                    "id": "K3",
                    "title": "Closing Keynote",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP3"],
                    "track": None,
                    "required_amenities": ["projector"],
                    "expected_attendance": 300,
                    "is_keynote": True,
                },
                # Regular sessions
                {
                    "id": "S1",
                    "title": "Talk 1",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP4"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                },
                {
                    "id": "S2",
                    "title": "Talk 2",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP5"],
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 60,
                    "is_keynote": False,
                },
            ],
            "speakers": [
                {"id": f"SP{i}", "name": f"Speaker {i}", "unavailable_slots": [], "preferred_slots": []}
                for i in range(1, 6)
            ],
            "attendees": [],
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

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        schedule = {s["session_id"]: s for s in result["schedule"]}

        # All 3 keynotes in different slots
        keynote_slots = [schedule["K1"]["time_slot"], schedule["K2"]["time_slot"], schedule["K3"]["time_slot"]]
        assert len(set(keynote_slots)) == 3

        # Regular sessions not in keynote slots
        for sid in ["S1", "S2"]:
            assert schedule[sid]["time_slot"] not in keynote_slots

    def test_heavy_speaker_load(self, client, validator):
        """Speaker giving many talks - tests proper non-overlap."""
        data = {
            "rooms": [
                {"id": "R1", "name": "Room 1", "capacity": 100, "amenities": []},
                {"id": "R2", "name": "Room 2", "capacity": 100, "amenities": []},
            ],
            "sessions": [
                {
                    "id": f"S{i}",
                    "title": f"Alice's Talk {i}",
                    "duration_minutes": 60,
                    "speaker_ids": ["SP1"],  # All by same speaker
                    "track": None,
                    "required_amenities": [],
                    "expected_attendance": 50,
                    "is_keynote": False,
                }
                for i in range(1, 5)  # 4 talks by Alice
            ],
            "speakers": [
                {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": []}
            ],
            "attendees": [],
            "time_slots": [
                {"start": "09:00", "duration_minutes": 60},
                {"start": "10:00", "duration_minutes": 60},
                {"start": "11:00", "duration_minutes": 60},
                {"start": "14:00", "duration_minutes": 60},
            ],
        }

        response = client.post("/schedule", json=data, timeout=30)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

        is_valid, violations, _ = validator(data, result)
        assert is_valid, f"Violations: {violations}"

        # All 4 sessions in different slots
        slots = [s["time_slot"] for s in result["schedule"]]
        assert len(slots) == len(set(slots)) == 4
